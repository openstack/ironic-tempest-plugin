# All Rights Reserved.
#
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

from oslo_log import log
from tempest import config
from tempest.lib.common.utils import test_utils
from tempest.lib import exceptions as lib_exc

from ironic_tempest_plugin.common import utils
from ironic_tempest_plugin import exceptions as ironic_exc

LOG = log.getLogger(__name__)

CONF = config.CONF


def _determine_and_check_timeout_interval(timeout, default_timeout,
                                          interval, default_interval):
    if timeout is None:
        timeout = default_timeout
    if interval is None:
        interval = default_interval
    if (not isinstance(timeout, int)
            or not isinstance(interval, int)
            or timeout < 0 or interval < 0):
        raise AssertionError(
            'timeout and interval should be >= 0 or None, current values are: '
            '%(timeout)s, %(interval)s respectively. If timeout and/or '
            'interval are None, the default_timeout and default_interval are '
            'used, and they should be integers >= 0, current values are: '
            '%(default_timeout)s, %(default_interval)s respectively.' % dict(
                timeout=timeout, interval=interval,
                default_timeout=default_timeout,
                default_interval=default_interval)
        )
    return timeout, interval


def wait_for_bm_node_status(client, node_id, attr, status, timeout=None,
                            interval=None, abort_on_error_state=False):
    """Waits for a baremetal node attribute to reach given status.

    :param client: an instance of tempest plugin BaremetalClient.
    :param node_id: identifier of the node.
    :param attr: node's API-visible attribute to check status of.
    :param status: desired status. Can be a list of statuses.
    :param timeout: the timeout after which the check is considered as failed.
        Defaults to client.build_timeout.
    :param interval: an interval between show_node calls for status check.
        Defaults to client.build_interval.
    :param abort_on_error_state: whether to abort waiting if the node reaches
        an error state.

    The client should have a show_node(node_id) method to get the node.
    """
    timeout, interval = _determine_and_check_timeout_interval(
        timeout, client.build_timeout, interval, client.build_interval)

    if not isinstance(status, list):
        status = [status]

    def is_attr_in_status():
        node = utils.get_node(client, node_id=node_id)
        if node[attr] in status:
            return True
        elif (abort_on_error_state
              and (node['provision_state'].endswith(' failed')
                   or node['provision_state'] == 'error')):
            msg = ('Node %(node)s reached failure state %(state)s while '
                   'waiting for %(attr)s=%(expected)s. '
                   'Error: %(error)s' %
                   {'node': node_id, 'state': node['provision_state'],
                    'attr': attr, 'expected': status,
                    'error': node.get('last_error')})
            LOG.debug(msg)
            raise lib_exc.TempestException(msg)
        return False

    if not test_utils.call_until_true(is_attr_in_status, timeout,
                                      interval):
        message = ('Node %(node_id)s failed to reach %(attr)s=%(status)s '
                   'within the required time (%(timeout)s s).' %
                   {'node_id': node_id,
                    'attr': attr,
                    'status': status,
                    'timeout': timeout})
        caller = test_utils.find_test_caller()
        if caller:
            message = '(%s) %s' % (caller, message)
        LOG.debug(message)
        raise lib_exc.TimeoutException(message)


def wait_node_instance_association(client, instance_uuid, timeout=None,
                                   interval=None):
    """Waits for a node to be associated with instance_id.

    :param client: an instance of tempest plugin BaremetalClient.
    :param instance_uuid: UUID of the instance.
    :param timeout: the timeout after which the check is considered as failed.
        Defaults to CONF.baremetal.association_timeout.
    :param interval: an interval between show_node calls for status check.
        Defaults to client.build_interval.
    """
    timeout, interval = _determine_and_check_timeout_interval(
        timeout, CONF.baremetal.association_timeout,
        interval, client.build_interval)

    def is_some_node_associated():
        node = utils.get_node(client, instance_uuid=instance_uuid)
        return node is not None

    if not test_utils.call_until_true(is_some_node_associated, timeout,
                                      interval):
        msg = ('Timed out waiting to get Ironic node by instance UUID '
               '%(instance_uuid)s within the required time (%(timeout)s s).'
               % {'instance_uuid': instance_uuid, 'timeout': timeout})
        raise lib_exc.TimeoutException(msg)


def wait_for_allocation(client, allocation_ident, timeout=15, interval=1,
                        expect_error=False):
    """Wait for the allocation to become active.

    :param client: an instance of tempest plugin BaremetalClient.
    :param allocation_ident: UUID or name of the allocation.
    :param timeout: the timeout after which the allocation is considered as
        failed. Defaults to 15 seconds.
    :param interval: an interval between show_allocation calls.
        Defaults to 1 second.
    :param expect_error: if True, return successfully even in case of an error.
    """
    result = [None]  # a mutable object to modify in the closure

    def check():
        result[0] = client.show_allocation(allocation_ident)
        allocation = result[0][1]

        if allocation['state'] == 'error' and not expect_error:
            raise lib_exc.TempestException(
                "Allocation %(ident)s failed: %(error)s" %
                {'ident': allocation_ident,
                 'error': allocation.get('last_error')})
        else:
            return allocation['state'] != 'allocating'

    if not test_utils.call_until_true(check, timeout, interval):
        msg = ('Timed out waiting for the allocation %s to become active' %
               allocation_ident)
        raise lib_exc.TimeoutException(msg)

    return result[0]


def wait_node_value_in_field(client, node_id, field, value,
                             raise_if_insufficent_access=True,
                             timeout=None, interval=None,
                             abort_on_error_state=False):
    """Waits for a node to have a field value appear.

    :param client: an instance of tempest plugin BaremetalClient.
    :param node_id: the UUID of the node
    :param field: the field in the node object to examine
    :param value: the value/key with-in the field to look for.
    :param timeout: the timeout after which the check is considered as failed.
    :param interval: an interval between show_node calls for status check.
    :param abort_on_error_state: whether to abort waiting if the node reaches
        an error state.
    """

    def is_field_updated():
        node = utils.get_node(client, node_id=node_id)
        field_value = node[field]
        if raise_if_insufficent_access and '** Redacted' in field_value:
            msg = ('Unable to see contents of redacted field '
                   'indicating insufficient access to execute this test.')
            raise ironic_exc.InsufficientAPIAccess(msg)
        elif (abort_on_error_state
              and (node['provision_state'].endswith('failed')
                   or node['provision_state'] == 'error')):
            msg = ('Node %(node)s reached failure state %(state)s while '
                   'waiting Error: %(error)s' %
                   {'node': node_id, 'state': node['provision_state'],
                    'error': node.get('last_error')})
            LOG.debug(msg)
            raise lib_exc.TempestException(msg)
        return value in field_value

    if not test_utils.call_until_true(is_field_updated, timeout,
                                      interval):
        msg = ('Timed out waiting to get Ironic node by node_id '
               '%(node_id)s within the required time (%(timeout)s s). '
               'Field value %(value) did not appear in field %(field)s.'
               % {'node_id': node_id, 'timeout': timeout,
                  'field': field, 'value': value})
        raise lib_exc.TimeoutException(msg)
