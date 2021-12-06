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

import six
from tempest import config
from tempest.lib.common import api_version_utils
from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions as lib_exc
from tempest import test

from ironic_tempest_plugin.common import waiters
from ironic_tempest_plugin.services.baremetal import base
from ironic_tempest_plugin.tests.api.admin import api_microversion_fixture

CONF = config.CONF


# NOTE(adam_g): The baremetal API tests exercise operations such as enroll
# node, power on, power off, etc.  Testing against real drivers (ie, IPMI)
# will require passing driver-specific data to Tempest (addresses,
# credentials, etc).  Until then, only support testing against the fake driver,
# which has no external dependencies.
SUPPORTED_DRIVERS = ['fake', 'fake-hardware']

# NOTE(jroll): resources must be deleted in a specific order, this list
# defines the resource types to clean up, and the correct order.
RESOURCE_TYPES = ['port', 'portgroup', 'node', 'volume_connector',
                  'volume_target', 'chassis', 'deploy_template']


def creates(resource):
    """Decorator that adds resources to the appropriate cleanup list."""

    def decorator(f):
        @six.wraps(f)
        def wrapper(cls, *args, **kwargs):
            resp, body = f(cls, *args, **kwargs)

            if 'uuid' in body:
                cls.created_objects[resource].add(body['uuid'])

            return resp, body
        return wrapper
    return decorator


class BaseBaremetalTest(api_version_utils.BaseMicroversionTest,
                        test.BaseTestCase):
    """Base class for Baremetal API tests."""

    credentials = ['admin', 'system_admin']

    @classmethod
    def skip_checks(cls):
        super(BaseBaremetalTest, cls).skip_checks()
        if not CONF.service_available.ironic:
            raise cls.skipException('Ironic is not enabled.')
        if CONF.baremetal.driver not in SUPPORTED_DRIVERS:
            skip_msg = ('%s skipped as Ironic driver %s is not supported for '
                        'testing.' %
                        (cls.__name__, CONF.baremetal.driver))
            raise cls.skipException(skip_msg)

        cfg_min_version = CONF.baremetal.min_microversion
        cfg_max_version = CONF.baremetal.max_microversion
        api_version_utils.check_skip_with_microversion(cls.min_microversion,
                                                       cls.max_microversion,
                                                       cfg_min_version,
                                                       cfg_max_version)

    @classmethod
    def setup_credentials(cls):
        cls.request_microversion = (
            api_version_utils.select_request_microversion(
                cls.min_microversion,
                CONF.baremetal.min_microversion))
        cls.services_microversion = {
            CONF.baremetal.catalog_type: cls.request_microversion}

        super(BaseBaremetalTest, cls).setup_credentials()

    @classmethod
    def setup_clients(cls):
        super(BaseBaremetalTest, cls).setup_clients()
        if CONF.enforce_scope.ironic:
            cls.client = cls.os_system_admin.baremetal.BaremetalClient()
        else:
            cls.client = cls.os_admin.baremetal.BaremetalClient()

    @classmethod
    def resource_setup(cls):
        super(BaseBaremetalTest, cls).resource_setup()
        cls.request_microversion = (
            api_version_utils.select_request_microversion(
                cls.min_microversion,
                CONF.baremetal.min_microversion))
        cls.driver = CONF.baremetal.driver
        cls.power_timeout = CONF.baremetal.power_timeout
        cls.unprovision_timeout = CONF.baremetal.unprovision_timeout
        cls.created_objects = {}
        for resource in RESOURCE_TYPES + ['allocation']:
            cls.created_objects[resource] = set()
        cls.deployed_nodes = set()

    @classmethod
    def resource_cleanup(cls):
        """Ensure that all created objects get destroyed."""
        # Use the requested microversion for cleanup to ensure we can delete
        # resources.
        base.set_baremetal_api_microversion(cls.request_microversion)
        try:
            for node in cls.deployed_nodes:
                try:
                    cls.set_node_provision_state(node, 'deleted',
                                                 ['available', None])
                except lib_exc.BadRequest:
                    pass

            # Delete allocations explicitly after unprovisioning instances, but
            # before deleting nodes.
            for allocation in cls.created_objects['allocation']:
                try:
                    cls.client.delete_allocation(allocation)
                except lib_exc.NotFound:
                    pass

            for node in cls.created_objects['node']:
                try:
                    cls.client.update_node(node, instance_uuid=None)
                except lib_exc.TempestException:
                    pass

            for resource in RESOURCE_TYPES:
                uuids = cls.created_objects[resource]
                delete_method = getattr(cls.client, 'delete_%s' % resource)
                for u in uuids:
                    delete_method(u, ignore_errors=lib_exc.NotFound)
        finally:
            base.reset_baremetal_api_microversion()
            super(BaseBaremetalTest, cls).resource_cleanup()

    def _assertExpected(self, expected, actual):
        """Check if expected keys/values exist in actual response body.

        Check if the expected keys and values are in the actual response body.
        It will not check the keys 'created_at' and 'updated_at', since they
        will always have different values. Asserts if any expected key (or
        corresponding value) is not in the actual response.

        Note: this method has an underscore even though it is used outside of
        this class, in order to distinguish this method from the more standard
        assertXYZ methods.

        :param expected: dict of key-value pairs that are expected to be in
                         'actual' dict.
        :param actual: dict of key-value pairs.

        """
        for key, value in expected.items():
            if key not in ('created_at', 'updated_at'):
                self.assertIn(key, actual)
                self.assertEqual(value, actual[key])

    def setUp(self):
        super(BaseBaremetalTest, self).setUp()
        self.useFixture(api_microversion_fixture.APIMicroversionFixture(
            self.request_microversion))

    @classmethod
    @creates('chassis')
    def create_chassis(cls, description=None, **kwargs):
        """Wrapper utility for creating test chassis.

        :param description: A description of the chassis. If not supplied,
            a random value will be generated.
        :return: A tuple with the server response and the created chassis.

        """
        description = description or data_utils.rand_name('test-chassis')
        resp, body = cls.client.create_chassis(description=description,
                                               **kwargs)
        return resp, body

    @classmethod
    @creates('node')
    def create_node(cls, chassis_id, cpu_arch='x86_64', cpus=8, local_gb=10,
                    memory_mb=4096, **kwargs):
        """Wrapper utility for creating test baremetal nodes.

        :param chassis_id: The unique identifier of the chassis.
        :param cpu_arch: CPU architecture of the node. Default: x86_64.
        :param cpus: Number of CPUs. Default: 8.
        :param local_gb: Disk size. Default: 10.
        :param memory_mb: Available RAM. Default: 4096.
        :param kwargs: Other optional node fields.
        :return: A tuple with the server response and the created node.

        """
        resp, body = cls.client.create_node(chassis_id, cpu_arch=cpu_arch,
                                            cpus=cpus, local_gb=local_gb,
                                            memory_mb=memory_mb,
                                            driver=cls.driver,
                                            **kwargs)

        return resp, body

    @classmethod
    def set_node_provision_state(cls, node_id, target, expected, timeout=None,
                                 interval=None):
        """Sets the node's provision state.

        :param node_id: The unique identifier of the node.
        :param target: Target provision state.
        :param expected: Expected final provision state or list of states.
        :param timeout: The timeout for reaching the expected state.
            Defaults to client.build_timeout.
        :param interval: An interval between show_node calls for status check.
            Defaults to client.build_interval.
        """
        cls.client.set_node_provision_state(node_id, target)
        waiters.wait_for_bm_node_status(cls.client, node_id,
                                        'provision_state', expected,
                                        timeout=timeout, interval=interval)

    @classmethod
    def provide_node(cls, node_id, cleaning_timeout=None):
        """Make the node available.

        :param node_id: The unique identifier of the node.
        :param cleaning_timeout: The timeout to wait for cleaning.
            Defaults to client.build_timeout.
        """
        _, body = cls.client.show_node(node_id)
        current_state = body['provision_state']
        if current_state == 'enroll':
            cls.set_node_provision_state(node_id, 'manage', 'manageable',
                                         timeout=60, interval=1)
            current_state = 'manageable'
        if current_state == 'manageable':
            cls.set_node_provision_state(node_id, 'provide',
                                         ['available', None],
                                         timeout=cleaning_timeout)
            current_state = 'available'
        if current_state not in ('available', None):
            raise RuntimeError("Cannot reach state 'available': node %(node)s "
                               "is in unexpected state %(state)s" %
                               {'node': node_id, 'state': current_state})

    @classmethod
    def deploy_node(cls, node_id, cleaning_timeout=None, deploy_timeout=None):
        """Deploy the node.

        :param node_id: The unique identifier of the node.
        :param cleaning_timeout: The timeout to wait for cleaning.
            Defaults to client.build_timeout.
        :param deploy_timeout: The timeout to wait for deploy.
            Defaults to client.build_timeout.
        """
        cls.provide_node(node_id, cleaning_timeout=cleaning_timeout)
        cls.set_node_provision_state(node_id, 'active', 'active',
                                     timeout=deploy_timeout)
        cls.deployed_nodes.add(node_id)

    @classmethod
    @creates('port')
    def create_port(cls, node_id, address, extra=None, uuid=None,
                    portgroup_uuid=None, physical_network=None):
        """Wrapper utility for creating test ports.

        :param node_id: The unique identifier of the node.
        :param address: MAC address of the port.
        :param extra: Meta data of the port. If not supplied, an empty
            dictionary will be created.
        :param uuid: UUID of the port.
        :param portgroup_uuid: The UUID of a portgroup of which this port is a
            member.
        :param physical_network: The physical network to which the port is
            attached.
        :return: A tuple with the server response and the created port.

        """
        extra = extra or {}
        resp, body = cls.client.create_port(address=address, node_id=node_id,
                                            extra=extra, uuid=uuid,
                                            portgroup_uuid=portgroup_uuid,
                                            physical_network=physical_network)

        return resp, body

    @classmethod
    @creates('portgroup')
    def create_portgroup(cls, node_uuid, **kwargs):
        """Wrapper utility for creating test port groups.

        :param node_uuid: The unique identifier of the node.
        :return: A tuple with the server response and the created port group.
        """
        resp, body = cls.client.create_portgroup(node_uuid=node_uuid, **kwargs)

        return resp, body

    @classmethod
    @creates('volume_connector')
    def create_volume_connector(cls, node_uuid, **kwargs):
        """Wrapper utility for creating test volume connector.

        :param node_uuid: The unique identifier of the node.
        :return: A tuple with the server response and the created volume
            connector.
        """
        resp, body = cls.client.create_volume_connector(node_uuid=node_uuid,
                                                        **kwargs)

        return resp, body

    @classmethod
    @creates('volume_target')
    def create_volume_target(cls, node_uuid, **kwargs):
        """Wrapper utility for creating test volume target.

        :param node_uuid: The unique identifier of the node.
        :return: A tuple with the server response and the created volume
            target.
        """
        resp, body = cls.client.create_volume_target(node_uuid=node_uuid,
                                                     **kwargs)

        return resp, body

    @classmethod
    @creates('deploy_template')
    def create_deploy_template(cls, name, **kwargs):
        """Wrapper utility for creating test deploy template.

        :param name: The name of the deploy template.
        :return: A tuple with the server response and the created deploy
            template.
        """
        resp, body = cls.client.create_deploy_template(name=name, **kwargs)

        return resp, body

    @classmethod
    def delete_chassis(cls, chassis_id):
        """Deletes a chassis having the specified UUID.

        :param chassis_id: The unique identifier of the chassis.
        :return: Server response.

        """

        resp, body = cls.client.delete_chassis(chassis_id)

        if chassis_id in cls.created_objects['chassis']:
            cls.created_objects['chassis'].remove(chassis_id)

        return resp

    @classmethod
    def delete_node(cls, node_id):
        """Deletes a node having the specified UUID.

        :param node_id: The unique identifier of the node.
        :return: Server response.

        """

        resp, body = cls.client.delete_node(node_id)

        if node_id in cls.created_objects['node']:
            cls.created_objects['node'].remove(node_id)

        return resp

    @classmethod
    def delete_port(cls, port_id):
        """Deletes a port having the specified UUID.

        :param port_id: The unique identifier of the port.
        :return: Server response.

        """

        resp, body = cls.client.delete_port(port_id)

        if port_id in cls.created_objects['port']:
            cls.created_objects['port'].remove(port_id)

        return resp

    @classmethod
    def delete_portgroup(cls, portgroup_ident):
        """Deletes a port group having the specified UUID or name.

        :param portgroup_ident: The name or UUID of the port group.
        :return: Server response.
        """
        resp, body = cls.client.delete_portgroup(portgroup_ident)

        if portgroup_ident in cls.created_objects['portgroup']:
            cls.created_objects['portgroup'].remove(portgroup_ident)

        return resp

    @classmethod
    def delete_volume_connector(cls, volume_connector_id):
        """Deletes a volume connector having the specified UUID.

        :param volume_connector_id: The UUID of the volume connector.
        :return: Server response.
        """
        resp, body = cls.client.delete_volume_connector(volume_connector_id)

        if volume_connector_id in cls.created_objects['volume_connector']:
            cls.created_objects['volume_connector'].remove(
                volume_connector_id)

        return resp

    @classmethod
    def delete_volume_target(cls, volume_target_id):
        """Deletes a volume target having the specified UUID.

        :param volume_target_id: The UUID of the volume target.
        :return: Server response.
        """
        resp, body = cls.client.delete_volume_target(volume_target_id)

        if volume_target_id in cls.created_objects['volume_target']:
            cls.created_objects['volume_target'].remove(volume_target_id)

        return resp

    @classmethod
    def delete_deploy_template(cls, deploy_template_ident):
        """Deletes a deploy template having the specified name or UUID.

        :param deploy_template_ident: Name or UUID of the deploy template.
        :return: Server response.
        """
        resp, body = cls.client.delete_deploy_template(deploy_template_ident)

        if deploy_template_ident in cls.created_objects['deploy_template']:
            cls.created_objects['deploy_template'].remove(
                deploy_template_ident)

        return resp

    def validate_self_link(self, resource, uuid, link):
        """Check whether the given self link formatted correctly."""
        expected_link = "{base}/{pref}/{res}/{uuid}".format(
                        base=self.client.base_url.rstrip('/'),
                        pref=self.client.uri_prefix,
                        res=resource,
                        uuid=uuid)
        self.assertEqual(expected_link, link)

    @classmethod
    @creates('allocation')
    def create_allocation(cls, resource_class, **kwargs):
        """Wrapper utility for creating test allocations.

        :param resource_class: Resource class to request.
        :param kwargs: Other fields to pass.
        :return: A tuple with the server response and the created allocation.
        """
        resp, body = cls.client.create_allocation(resource_class, **kwargs)
        return resp, body
