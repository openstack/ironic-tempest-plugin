#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


import functools
from http import client as http_client
from urllib import parse as urllib_parse

from oslo_log import log
from oslo_serialization import jsonutils as json
from tempest.lib.common import api_version_utils
from tempest.lib.common import rest_client
from tempest.lib import exceptions as lib_exc
import tenacity

LOG = log.getLogger(__name__)

# NOTE(vsaienko): concurrent tests work because they are launched in
# separate processes so global variables are not shared among them.
BAREMETAL_MICROVERSION = None

# Interfaces that can be set via the baremetal client and by logic in scenario
# managers.
SUPPORTED_INTERFACES = (['bios', 'deploy', 'rescue', 'boot', 'raid',
                         'management', 'power', 'inspect', 'console'])


# Number of times a request is retried when the node is locked, in addition
# to the initial attempt. Ironic itself already retries for a couple of
# seconds before returning the 409, so this covers longer lock holders such
# as a conductor worker that is still finishing the previous action.
NODE_LOCKED_RETRIES = 3


def _is_node_locked(exc):
    # NOTE: Ironic does not use a distinct status code for this, it is a
    # plain 409 whose message is "Node <uuid> is locked by host <host>,
    # please retry after the current operation is completed."
    return (isinstance(exc, lib_exc.Conflict)
            and 'is locked by host' in str(exc))


def retry_on_node_locked(f):
    """Retry a node request that fails because the node is locked.

    The decorated method must take the node identifier as its first argument
    after ``self``. Only the "node is locked" flavour of 409 is retried, so
    tests that expect a Conflict for any other reason are unaffected. When
    the retries are exhausted the original exception is raised.
    """

    @functools.wraps(f)
    def wrapper(self, node_uuid, *args, **kwargs):
        def _log_retry(retry_state):
            LOG.warning('Node %(node)s was locked during %(func)s, retrying '
                        '(attempt %(att)d of %(max)d): %(err)s',
                        {'node': node_uuid, 'func': f.__name__,
                         'att': retry_state.attempt_number,
                         'max': NODE_LOCKED_RETRIES + 1,
                         'err': retry_state.outcome.exception()})

        def _log_giving_up(retry_state):
            exc = retry_state.outcome.exception()
            LOG.error('Node %(node)s was still locked after %(att)d '
                      'attempts of %(func)s(%(args)s). The lock was held by '
                      'an earlier operation that had not finished: %(err)s',
                      {'node': node_uuid, 'att': retry_state.attempt_number,
                       'func': f.__name__,
                       'args': ', '.join(
                           [repr(a) for a in args]
                           + ['%s=%r' % kv for kv in kwargs.items()
                              if kv[1] is not None]),
                       'err': exc})
            raise exc

        retrying = tenacity.Retrying(
            retry=tenacity.retry_if_exception(_is_node_locked),
            stop=tenacity.stop_after_attempt(NODE_LOCKED_RETRIES + 1),
            # 2s, 4s, 8s
            wait=tenacity.wait_exponential(multiplier=2, max=10),
            before_sleep=_log_retry,
            retry_error_callback=_log_giving_up,
            reraise=False)
        return retrying(f, self, node_uuid, *args, **kwargs)

    return wrapper


def set_baremetal_api_microversion(baremetal_microversion):
    global BAREMETAL_MICROVERSION
    BAREMETAL_MICROVERSION = baremetal_microversion


def reset_baremetal_api_microversion():
    global BAREMETAL_MICROVERSION
    BAREMETAL_MICROVERSION = None


def handle_errors(f):
    """A decorator that allows to ignore certain types of errors."""

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        param_name = 'ignore_errors'
        ignored_errors = kwargs.get(param_name, tuple())

        if param_name in kwargs:
            del kwargs[param_name]

        try:
            return f(*args, **kwargs)
        except ignored_errors:
            # Silently ignore errors
            pass

    return wrapper


class BaremetalClient(rest_client.RestClient):
    """Base Tempest REST client for Ironic API."""

    api_microversion_header_name = 'X-OpenStack-Ironic-API-Version'
    uri_prefix = ''

    def get_headers(self):
        headers = super(BaremetalClient, self).get_headers()
        if BAREMETAL_MICROVERSION:
            # NOTE(TheJulia): This is not great, because it can blind a test
            # to the actual version supported.
            headers[self.api_microversion_header_name] = BAREMETAL_MICROVERSION
        return headers

    def get_raw_headers(self):
        """A proper get headers without guessing the microversion."""
        return super(BaremetalClient, self).get_headers()

    def get_min_max_api_microversions(self):
        """Returns a tuple of minimum and remote microversions."""
        if '/v1' in self.base_url:
            root_uri = '/'
        else:
            # NOTE(dtantsur): we should just use / here but due to a bug in
            # Ironic, / does not contain the microversion headers. See
            # https://bugs.launchpad.net/ironic/+bug/2079023
            root_uri = '/v1'
        _, resp_body = self._show_request(None, uri=root_uri)
        try:
            version = resp_body['default_version']
        except KeyError:
            version = resp_body['version']
        api_min = version.get('min_version')
        api_max = version.get('version')
        return (api_min, api_max)

    def request(self, *args, **kwargs):
        resp, resp_body = super(BaremetalClient, self).request(*args, **kwargs)
        latest_microversion = api_version_utils.LATEST_MICROVERSION
        if (BAREMETAL_MICROVERSION
                and BAREMETAL_MICROVERSION != latest_microversion):
            api_version_utils.assert_version_header_matches_request(
                self.api_microversion_header_name,
                BAREMETAL_MICROVERSION,
                resp)
        return resp, resp_body

    def serialize(self, object_dict):
        """Serialize an Ironic object."""

        return json.dumps(object_dict)

    def deserialize(self, object_str):
        """Deserialize an Ironic object."""

        return json.loads(object_str)

    def _get_uri(self, resource_name, uuid=None, permanent=False,
                 params=None):
        """Get URI for a specific resource or object.

        :param resource_name: The name of the REST resource, e.g., 'nodes'.
        :param uuid: The unique identifier of an object in UUID format.
        :returns: Relative URI for the resource or object.

        """
        prefix = self.uri_prefix if not permanent else ''
        if params:
            params = '?' + '&'.join('%s=%s' % tpl for tpl in params.items())
        else:
            params = ''

        return '{pref}/{res}{uuid}{params}'.format(
            pref=prefix, res=resource_name,
            uuid='/%s' % uuid if uuid else '',
            params=params)

    def _make_patch(self, allowed_attributes, **kwargs):
        """Create a JSON patch according to RFC 6902.

        :param allowed_attributes: An iterable object that contains a set of
            allowed attributes for an object.
        :param **kwargs: Attributes and new values for them.
        :returns: A JSON path that sets values of the specified attributes to
            the new ones.

        """
        def get_change(kwargs, path='/'):
            for name, value in kwargs.items():
                if isinstance(value, dict):
                    for ch in get_change(value, path + '%s/' % name):
                        yield ch
                else:
                    if value is None:
                        yield {'path': path + name,
                               'op': 'remove'}
                    else:
                        yield {'path': path + name,
                               'value': value,
                               'op': 'replace'}

        patch = [ch for ch in get_change(kwargs)
                 if ch['path'].lstrip('/') in allowed_attributes]

        return patch

    def _list_request(self, resource, permanent=False, headers=None,
                      extra_headers=False, **kwargs):
        """Get the list of objects of the specified type.

        :param resource: The name of the REST resource, e.g., 'nodes'.
        :param headers: List of headers to use in request.
        :param extra_headers: Specify whether to use headers.
        :param **kwargs: Parameters for the request.
        :returns: A tuple with the server response and deserialized JSON list
                 of objects

        """
        uri = self._get_uri(resource, permanent=permanent)
        if kwargs:
            uri += "?%s" % urllib_parse.urlencode(kwargs)

        resp, body = self.get(uri, headers=headers,
                              extra_headers=extra_headers)
        self.expected_success(http_client.OK, resp.status)

        return resp, self.deserialize(body)

    def _show_request(self,
                      resource,
                      uuid=None,
                      permanent=False,
                      headers=None,
                      extra_headers=False,
                      **kwargs):
        """Gets a specific object of the specified type.

        :param uuid: Unique identifier of the object in UUID format.
        :param headers: List of headers to use in request.
        :param extra_headers: Specify whether to use headers.
        :returns: Serialized object as a dictionary.

        """
        if 'uri' in kwargs:
            uri = kwargs['uri']
        else:
            uri = self._get_uri(resource, uuid=uuid, permanent=permanent)
        resp, body = self.get(uri, headers=headers,
                              extra_headers=extra_headers)
        self.expected_success(http_client.OK, resp.status)

        return resp, self.deserialize(body)

    def _create_request(self, resource, object_dict):
        """Create an object of the specified type.

        :param resource: The name of the REST resource, e.g., 'nodes'.
        :param object_dict: A Python dict that represents an object of the
                            specified type.
        :returns: A tuple with the server response and the deserialized created
                 object.

        """
        body = self.serialize(object_dict)
        uri = self._get_uri(resource)

        resp, body = self.post(uri, body=body)
        self.expected_success(http_client.CREATED, resp.status)

        return resp, self.deserialize(body)

    def _create_request_no_response_body(self, resource, object_dict):
        """Create an object of the specified type.

           Do not expect any body in the response.

        :param resource: The name of the REST resource, e.g., 'nodes'.
        :param object_dict: A Python dict that represents an object of the
                            specified type.
        :returns: The server response.
        """

        body = self.serialize(object_dict)
        uri = self._get_uri(resource)

        resp, body = self.post(uri, body=body)
        self.expected_success(http_client.NO_CONTENT, resp.status)

        return resp

    def _delete_request(self, resource, uuid,
                        expected_status=http_client.NO_CONTENT):
        """Delete specified object.

        :param resource: The name of the REST resource, e.g., 'nodes'.
        :param uuid: The unique identifier of an object in UUID format.
        :param expected_status: Expected response status code. By default is
                                http_client.NO_CONTENT (204)
        :returns: A tuple with the server response and the response body.

        """
        uri = self._get_uri(resource, uuid)

        resp, body = self.delete(uri)
        self.expected_success(expected_status, resp.status)
        return resp, body

    def _patch_request(self, resource, uuid, patch_object, params=None):
        """Update specified object with JSON-patch.

        :param resource: The name of the REST resource, e.g., 'nodes'.
        :param uuid: The unique identifier of an object in UUID format.
        :param params: query parameters to pass.
        :returns: A tuple with the server response and the serialized patched
                 object.

        """
        uri = self._get_uri(resource, uuid, params=params)
        patch_body = json.dumps(patch_object)

        resp, body = self.patch(uri, body=patch_body)
        self.expected_success(http_client.OK, resp.status)
        return resp, self.deserialize(body)

    @handle_errors
    def get_api_description(self):
        """Retrieves all versions of the Ironic API."""

        return self._list_request('', permanent=True)

    @handle_errors
    def get_version_description(self, version='v1'):
        """Retrieves the description of the API.

        :param version: The version of the API. Default: 'v1'.
        :returns: Serialized description of API resources.

        """
        return self._list_request(version, permanent=True)

    def _put_request(self, resource, put_object):
        """Update specified object with JSON-patch."""
        uri = self._get_uri(resource)
        put_body = json.dumps(put_object)

        resp, body = self.put(uri, body=put_body)
        self.expected_success([http_client.ACCEPTED, http_client.NO_CONTENT],
                              resp.status)
        return resp, body
