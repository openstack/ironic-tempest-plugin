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

from oslo_utils import uuidutils
import six
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from ironic_tempest_plugin.common import waiters
from ironic_tempest_plugin.tests.api.admin import api_microversion_fixture
from ironic_tempest_plugin.tests.api.admin import base

CONF = config.CONF


class TestNodes(base.BaseBaremetalTest):
    """Tests for baremetal nodes."""

    def setUp(self):
        super(TestNodes, self).setUp()

        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis['uuid'])

    def _associate_node_with_instance(self):
        self.client.set_node_power_state(self.node['uuid'], 'power off')
        waiters.wait_for_bm_node_status(self.client, self.node['uuid'],
                                        'power_state', 'power off')
        instance_uuid = data_utils.rand_uuid()
        self.client.update_node(self.node['uuid'],
                                instance_uuid=instance_uuid)
        self.addCleanup(self.client.update_node,
                        uuid=self.node['uuid'], instance_uuid=None)
        return instance_uuid

    @decorators.idempotent_id('4e939eb2-8a69-4e84-8652-6fffcbc9db8f')
    def test_create_node(self):
        params = {'cpu_arch': 'x86_64',
                  'cpus': '12',
                  'local_gb': '10',
                  'memory_mb': '1024'}

        _, body = self.create_node(self.chassis['uuid'], **params)
        self._assertExpected(params, body['properties'])

    @decorators.idempotent_id('9ade60a4-505e-4259-9ec4-71352cbbaf47')
    def test_delete_node(self):
        _, node = self.create_node(self.chassis['uuid'])

        self.delete_node(node['uuid'])

        self.assertRaises(lib_exc.NotFound, self.client.show_node,
                          node['uuid'])

    @decorators.idempotent_id('55451300-057c-4ecf-8255-ba42a83d3a03')
    def test_show_node(self):
        _, loaded_node = self.client.show_node(self.node['uuid'])
        self._assertExpected(self.node, loaded_node)

    @decorators.idempotent_id('4ca123c4-160d-4d8d-a3f7-15feda812263')
    def test_list_nodes(self):
        _, body = self.client.list_nodes()
        self.assertIn(self.node['uuid'],
                      [i['uuid'] for i in body['nodes']])

    @decorators.idempotent_id('85b1f6e0-57fd-424c-aeff-c3422920556f')
    def test_list_nodes_association(self):
        _, body = self.client.list_nodes(associated=True)
        self.assertNotIn(self.node['uuid'],
                         [n['uuid'] for n in body['nodes']])

        self._associate_node_with_instance()

        _, body = self.client.list_nodes(associated=True)
        self.assertIn(self.node['uuid'], [n['uuid'] for n in body['nodes']])

        _, body = self.client.list_nodes(associated=False)
        self.assertNotIn(self.node['uuid'], [n['uuid'] for n in body['nodes']])

    @decorators.idempotent_id('18c4ebd8-f83a-4df7-9653-9fb33a329730')
    def test_node_port_list(self):
        _, port = self.create_port(self.node['uuid'],
                                   data_utils.rand_mac_address())
        _, body = self.client.list_node_ports(self.node['uuid'])
        self.assertIn(port['uuid'],
                      [p['uuid'] for p in body['ports']])

    @decorators.idempotent_id('72591acb-f215-49db-8395-710d14eb86ab')
    def test_node_port_list_no_ports(self):
        _, node = self.create_node(self.chassis['uuid'])
        _, body = self.client.list_node_ports(node['uuid'])
        self.assertEmpty(body['ports'])

    @decorators.idempotent_id('4fed270a-677a-4d19-be87-fd38ae490320')
    def test_update_node(self):
        props = {'cpu_arch': 'x86_64',
                 'cpus': '12',
                 'local_gb': '10',
                 'memory_mb': '128'}

        _, node = self.create_node(self.chassis['uuid'], **props)

        new_p = {'cpu_arch': 'x86',
                 'cpus': '1',
                 'local_gb': '10000',
                 'memory_mb': '12300'}

        _, body = self.client.update_node(node['uuid'], properties=new_p)
        _, node = self.client.show_node(node['uuid'])
        self._assertExpected(new_p, node['properties'])

    @decorators.idempotent_id('cbf1f515-5f4b-4e49-945c-86bcaccfeb1d')
    def test_validate_driver_interface(self):
        _, body = self.client.validate_driver_interface(self.node['uuid'])
        core_interfaces = ['power', 'deploy']
        for interface in core_interfaces:
            self.assertIn(interface, body)

    @decorators.idempotent_id('5519371c-26a2-46e9-aa1a-f74226e9d71f')
    def test_set_node_boot_device(self):
        self.client.set_node_boot_device(self.node['uuid'], 'pxe')

    @decorators.idempotent_id('9ea73775-f578-40b9-bc34-efc639c4f21f')
    def test_get_node_boot_device(self):
        body = self.client.get_node_boot_device(self.node['uuid'])
        self.assertIn('boot_device', body)
        self.assertIn('persistent', body)
        self.assertIsInstance(body['boot_device'], six.string_types)
        self.assertIsInstance(body['persistent'], bool)

    @decorators.idempotent_id('3622bc6f-3589-4bc2-89f3-50419c66b133')
    def test_get_node_supported_boot_devices(self):
        body = self.client.get_node_supported_boot_devices(self.node['uuid'])
        self.assertIn('supported_boot_devices', body)
        self.assertIsInstance(body['supported_boot_devices'], list)

    @decorators.idempotent_id('f63b6288-1137-4426-8cfe-0d5b7eb87c06')
    def test_get_console(self):
        _, body = self.client.get_console(self.node['uuid'])
        con_info = ['console_enabled', 'console_info']
        for key in con_info:
            self.assertIn(key, body)

    @decorators.idempotent_id('80504575-9b21-4670-92d1-143b948f9437')
    def test_set_console_mode(self):
        self.client.set_console_mode(self.node['uuid'], True)
        waiters.wait_for_bm_node_status(self.client, self.node['uuid'],
                                        'console_enabled', True)

    @decorators.idempotent_id('b02a4f38-5e8b-44b2-aed2-a69a36ecfd69')
    def test_get_node_by_instance_uuid(self):
        instance_uuid = self._associate_node_with_instance()
        _, body = self.client.show_node_by_instance_uuid(instance_uuid)
        self.assertEqual(1, len(body['nodes']))
        self.assertIn(self.node['uuid'], [n['uuid'] for n in body['nodes']])


class TestNodesResourceClass(base.BaseBaremetalTest):

    min_microversion = '1.21'

    def setUp(self):
        super(TestNodesResourceClass, self).setUp()
        self.useFixture(
            api_microversion_fixture.APIMicroversionFixture(
                TestNodesResourceClass.min_microversion)
        )
        _, self.chassis = self.create_chassis()
        self.resource_class = data_utils.rand_name(name='Resource_Class')
        _, self.node = self.create_node(
            self.chassis['uuid'], resource_class=self.resource_class)

    @decorators.idempotent_id('2a00340c-8152-4a61-9fc5-0b3cdefec258')
    def test_create_node_resource_class_long(self):
        """Create new node with specified longest name of resource class."""
        res_class_long_name = data_utils.arbitrary_string(80)
        _, body = self.create_node(
            self.chassis['uuid'],
            resource_class=res_class_long_name)
        self.assertEqual(res_class_long_name, body['resource_class'])

    @decorators.idempotent_id('142db00d-ac0f-415b-8da8-9095fbb561f7')
    def test_update_node_resource_class(self):
        """Update existing node with specified resource class."""
        new_res_class_name = data_utils.rand_name(name='Resource_Class')
        _, body = self.client.update_node(
            self.node['uuid'], resource_class=new_res_class_name)
        _, body = self.client.show_node(self.node['uuid'])
        self.assertEqual(new_res_class_name, body['resource_class'])

    @decorators.idempotent_id('73e6f7b5-3e51-49ea-af5b-146cd49f40ee')
    def test_show_node_resource_class(self):
        """Show resource class field of specified node."""
        _, body = self.client.show_node(self.node['uuid'])
        self.assertEqual(self.resource_class, body['resource_class'])

    @decorators.idempotent_id('f2bf4465-280c-4fdc-bbf7-fcf5188befa4')
    def test_list_nodes_resource_class(self):
        """List nodes of specified resource class only."""
        res_class = 'ResClass-{0}'.format(data_utils.rand_uuid())
        for node in range(3):
            _, body = self.create_node(
                self.chassis['uuid'], resource_class=res_class)

        _, body = self.client.list_nodes(resource_class=res_class)
        self.assertEqual(3, len([i['uuid'] for i in body['nodes']]))

    @decorators.idempotent_id('40733bad-bb79-445e-a094-530a44042995')
    def test_list_nodes_detail_resource_class(self):
        """Get detailed nodes list of specified resource class only."""
        res_class = 'ResClass-{0}'.format(data_utils.rand_uuid())
        for node in range(3):
            _, body = self.create_node(
                self.chassis['uuid'], resource_class=res_class)

        _, body = self.client.list_nodes_detail(resource_class=res_class)
        self.assertEqual(3, len([i['uuid'] for i in body['nodes']]))

        for node in body['nodes']:
            self.assertEqual(res_class, node['resource_class'])

    @decorators.attr(type='negative')
    @decorators.idempotent_id('e75136d4-0690-48a5-aef3-75040aee73ad')
    def test_create_node_resource_class_too_long(self):
        """Try to create a node with too long resource class name."""
        resource_class = data_utils.arbitrary_string(81)
        self.assertRaises(lib_exc.BadRequest, self.create_node,
                          self.chassis['uuid'], resource_class=resource_class)

    @decorators.attr(type='negative')
    @decorators.idempotent_id('f0aeece4-8671-44ea-a482-b4047fc4cf74')
    def test_update_node_resource_class_too_long(self):
        """Try to update a node with too long resource class name."""
        resource_class = data_utils.arbitrary_string(81)
        self.assertRaises(lib_exc.BadRequest, self.client.update_node,
                          self.node['uuid'], resource_class=resource_class)


class TestNodesResourceClassOldApi(base.BaseBaremetalTest):

    def setUp(self):
        super(TestNodesResourceClassOldApi, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis['uuid'])

    @decorators.attr(type='negative')
    @decorators.idempotent_id('2c364408-4746-4b3c-9821-20d47b57bdec')
    def test_create_node_resource_class_old_api(self):
        """Try to create a node with resource class using older api version."""
        resource_class = data_utils.arbitrary_string()
        self.assertRaises(lib_exc.UnexpectedResponseCode, self.create_node,
                          self.chassis['uuid'], resource_class=resource_class)

    @decorators.attr(type='negative')
    @decorators.idempotent_id('666f3c1a-4922-4a3d-b6d9-dea7c74d30bc')
    def test_update_node_resource_class_old_api(self):
        """Try to update a node with resource class using older api version."""
        resource_class = data_utils.arbitrary_string()
        self.assertRaises(lib_exc.UnexpectedResponseCode,
                          self.client.update_node,
                          self.node['uuid'], resource_class=resource_class)

    @decorators.attr(type='negative')
    @decorators.idempotent_id('95903480-f16d-4774-8775-6c7f87b27c59')
    def test_list_nodes_by_resource_class_old_api(self):
        """Try to list nodes with resource class using older api version."""
        resource_class = data_utils.arbitrary_string()
        self.assertRaises(
            lib_exc.UnexpectedResponseCode,
            self.client.list_nodes, resource_class=resource_class)
        self.assertRaises(
            lib_exc.UnexpectedResponseCode,
            self.client.list_nodes_detail, resource_class=resource_class)


class TestNodesVif(base.BaseBaremetalTest):

    min_microversion = '1.28'

    @classmethod
    def skip_checks(cls):
        super(TestNodesVif, cls).skip_checks()
        if not CONF.service_available.neutron:
            raise cls.skipException('Neutron is not enabled.')

    def setUp(self):
        super(TestNodesVif, self).setUp()

        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis['uuid'])
        if CONF.network.shared_physical_network:
            self.net = self.os_admin.networks_client.list_networks(
                name=CONF.compute.fixed_network_name)['networks'][0]
        else:
            self.net = self.os_admin.networks_client.\
                create_network()['network']
            self.addCleanup(self.os_admin.networks_client.delete_network,
                            self.net['id'])

        self.nport_id = self.os_admin.ports_client.create_port(
            network_id=self.net['id'])['port']['id']
        self.addCleanup(self.os_admin.ports_client.delete_port,
                        self.nport_id)

    @decorators.idempotent_id('a3d319d0-cacb-4e55-a3dc-3fa8b74880f1')
    def test_vif_on_port(self):
        """Test attachment and detachment of VIFs on the node with port.

        Test steps:
        1) Create chassis and node in setUp.
        2) Create port for the node.
        3) Attach VIF to the node.
        4) Check VIF info in VIFs list and port internal_info.
        5) Detach VIF from the node.
        6) Check that no more VIF info in VIFs list and port internal_info.
        """
        self.useFixture(
            api_microversion_fixture.APIMicroversionFixture('1.28'))
        _, self.port = self.create_port(self.node['uuid'],
                                        data_utils.rand_mac_address())
        self.client.vif_attach(self.node['uuid'], self.nport_id)
        _, body = self.client.vif_list(self.node['uuid'])
        self.assertEqual({'vifs': [{'id': self.nport_id}]}, body)
        _, port = self.client.show_port(self.port['uuid'])
        self.assertEqual(self.nport_id,
                         port['internal_info']['tenant_vif_port_id'])
        self.client.vif_detach(self.node['uuid'], self.nport_id)
        _, body = self.client.vif_list(self.node['uuid'])
        self.assertEqual({'vifs': []}, body)
        _, port = self.client.show_port(self.port['uuid'])
        self.assertNotIn('tenant_vif_port_id', port['internal_info'])

    @decorators.idempotent_id('95279515-7d0a-4f5f-987f-93e36aae5585')
    def test_vif_on_portgroup(self):
        """Test attachment and detachment of VIFs on the node with port group.

        Test steps:
        1) Create chassis and node in setUp.
        2) Create port for the node.
        3) Create port group for the node.
        4) Plug port into port group.
        5) Attach VIF to the node.
        6) Check VIF info in VIFs list and port group internal_info, but
           not in port internal_info.
        7) Detach VIF from the node.
        8) Check that no VIF info in VIFs list and port group internal_info.
        """
        self.useFixture(
            api_microversion_fixture.APIMicroversionFixture('1.28'))
        _, self.port = self.create_port(self.node['uuid'],
                                        data_utils.rand_mac_address())
        _, self.portgroup = self.create_portgroup(
            self.node['uuid'], address=data_utils.rand_mac_address())

        patch = [{'path': '/portgroup_uuid',
                  'op': 'add',
                  'value': self.portgroup['uuid']}]
        self.client.update_port(self.port['uuid'], patch)

        self.client.vif_attach(self.node['uuid'], self.nport_id)
        _, body = self.client.vif_list(self.node['uuid'])
        self.assertEqual({'vifs': [{'id': self.nport_id}]}, body)

        _, port = self.client.show_port(self.port['uuid'])
        self.assertNotIn('tenant_vif_port_id', port['internal_info'])
        _, portgroup = self.client.show_portgroup(self.portgroup['uuid'])
        self.assertEqual(self.nport_id,
                         portgroup['internal_info']['tenant_vif_port_id'])

        self.client.vif_detach(self.node['uuid'], self.nport_id)
        _, body = self.client.vif_list(self.node['uuid'])
        self.assertEqual({'vifs': []}, body)
        _, portgroup = self.client.show_portgroup(self.portgroup['uuid'])
        self.assertNotIn('tenant_vif_port_id', portgroup['internal_info'])

    @decorators.idempotent_id('a3d319d0-cacb-4e55-a3dc-3fa8b74880f2')
    def test_vif_already_set_on_extra(self):
        self.useFixture(
            api_microversion_fixture.APIMicroversionFixture('1.28'))
        _, self.port = self.create_port(self.node['uuid'],
                                        data_utils.rand_mac_address())
        patch = [{'path': '/extra/vif_port_id',
                  'op': 'add',
                  'value': self.nport_id}]
        self.client.update_port(self.port['uuid'], patch)

        _, body = self.client.vif_list(self.node['uuid'])
        self.assertEqual({'vifs': [{'id': self.nport_id}]}, body)

        self.assertRaises(lib_exc.Conflict, self.client.vif_attach,
                          self.node['uuid'], self.nport_id)

        self.client.vif_detach(self.node['uuid'], self.nport_id)


class TestNodesTraits(base.BaseBaremetalTest):

    min_microversion = '1.37'

    def setUp(self):
        super(TestNodesTraits, self).setUp()
        self.useFixture(
            api_microversion_fixture.APIMicroversionFixture(
                TestNodesTraits.min_microversion)
        )
        _, self.chassis = self.create_chassis()
        # One standard trait & one custom trait.
        self.traits = ['CUSTOM_TRAIT1', 'HW_CPU_X86_VMX']
        _, self.node = self.create_node(self.chassis['uuid'])

    @decorators.idempotent_id('5c3a2dd0-af10-474d-a209-d30426e1eb5d')
    def test_list_node_traits(self):
        """List traits for a node."""
        _, body = self.client.list_node_traits(self.node['uuid'])
        self.assertEqual([], body['traits'])

        self.client.set_node_traits(self.node['uuid'], self.traits)
        _, body = self.client.list_node_traits(self.node['uuid'])
        self.assertEqual(self.traits, sorted(body['traits']))

    @decorators.attr(type='negative')
    @decorators.idempotent_id('3b83dbd3-4a89-4173-920a-ca33ed3aad69')
    def test_list_node_traits_non_existent_node(self):
        """Try to list traits for a non-existent node."""
        node_uuid = uuidutils.generate_uuid()
        self.assertRaises(
            lib_exc.NotFound,
            self.client.list_node_traits, node_uuid)

    @decorators.idempotent_id('aa961bf6-ea2f-484b-961b-eae2da0e6b7e')
    def test_set_node_traits(self):
        """Set the traits for a node."""
        self.client.set_node_traits(self.node['uuid'], self.traits)

        _, body = self.client.list_node_traits(self.node['uuid'])
        self.assertEqual(self.traits, sorted(body['traits']))

        self.client.set_node_traits(self.node['uuid'], [])

        _, body = self.client.list_node_traits(self.node['uuid'])
        self.assertEqual([], body['traits'])

    @decorators.idempotent_id('727a5e11-5654-459f-8af6-e14eb987a283')
    def test_set_node_traits_max_traits(self):
        """Set the maximum number of traits for a node."""
        traits = ['CUSTOM_TRAIT%d' % i for i in range(50)]
        self.client.set_node_traits(self.node['uuid'], traits)

        _, body = self.client.list_node_traits(self.node['uuid'])
        self.assertEqual(sorted(traits), sorted(body['traits']))

    @decorators.attr(type='negative')
    @decorators.idempotent_id('75831f5d-ca44-403b-8fd6-f7cad95b1c54')
    def test_set_node_traits_too_many(self):
        """Set more than the maximum number of traits for a node."""
        traits = ['CUSTOM_TRAIT%d' % i for i in range(51)]
        self.assertRaises(
            lib_exc.BadRequest,
            self.client.set_node_traits, self.node['uuid'], traits)

        _, body = self.client.list_node_traits(self.node['uuid'])
        self.assertEqual([], body['traits'])

    @decorators.idempotent_id('d81ceeab-a50f-427a-bc5a-aa916478d0d3')
    def test_set_node_traits_duplicate_trait(self):
        """Set the traits for a node, ensuring duplicates are ignored."""
        self.client.set_node_traits(self.node['uuid'],
                                    ['CUSTOM_TRAIT1', 'CUSTOM_TRAIT1'])

        _, body = self.client.list_node_traits(self.node['uuid'])
        self.assertEqual(['CUSTOM_TRAIT1'], body['traits'])

    @decorators.attr(type='negative')
    @decorators.idempotent_id('2fb4c9d9-8e5b-4189-b547-26596014491c')
    def test_set_node_traits_non_existent_node(self):
        """Try to set traits for a non-existent node."""
        node_uuid = uuidutils.generate_uuid()
        self.assertRaises(
            lib_exc.NotFound,
            self.client.set_node_traits, node_uuid, ['CUSTOM_TRAIT1'])

    @decorators.idempotent_id('47db09d9-af2b-424d-9d51-7efca2920f20')
    def test_add_node_trait_long(self):
        """Add a node trait of the largest possible length."""
        trait_long_name = 'CUSTOM_' + data_utils.arbitrary_string(248).upper()
        self.client.add_node_trait(self.node['uuid'], trait_long_name)

        _, body = self.client.list_node_traits(self.node['uuid'])
        self.assertEqual([trait_long_name], body['traits'])

    @decorators.attr(type='negative')
    @decorators.idempotent_id('2a4daa8d-2b85-40ac-a8a0-0462cc9a57ef')
    def test_add_node_trait_too_long(self):
        """Try to add a node trait longer than the largest possible length."""
        trait_long_name = 'CUSTOM_' + data_utils.arbitrary_string(249).upper()
        self.assertRaises(
            lib_exc.BadRequest,
            self.client.add_node_trait, self.node['uuid'], trait_long_name)

        _, body = self.client.list_node_traits(self.node['uuid'])
        self.assertEqual([], body['traits'])

    @decorators.idempotent_id('4b737e7f-101e-493e-b5ce-494fbffe18fd')
    def test_add_node_trait_duplicate_trait(self):
        """Add a node trait that already exists."""
        self.client.add_node_trait(self.node['uuid'], 'CUSTOM_TRAIT1')
        self.client.add_node_trait(self.node['uuid'], 'CUSTOM_TRAIT1')

        _, body = self.client.list_node_traits(self.node['uuid'])
        self.assertEqual(['CUSTOM_TRAIT1'], body['traits'])

    @decorators.attr(type='negative')
    @decorators.idempotent_id('65bce181-89ce-435e-a7d8-3ba60aafd08d')
    def test_add_node_trait_too_many(self):
        """Add a trait to a node that would exceed the maximum."""
        traits = ['CUSTOM_TRAIT%d' % i for i in range(50)]
        self.client.set_node_traits(self.node['uuid'], traits)

        self.assertRaises(
            lib_exc.BadRequest,
            self.client.add_node_trait, self.node['uuid'], 'CUSTOM_TRAIT50')

        _, body = self.client.list_node_traits(self.node['uuid'])
        self.assertEqual(sorted(traits), sorted(body['traits']))

    @decorators.attr(type='negative')
    @decorators.idempotent_id('cca0e831-32af-4ce9-bfce-d3834fea57aa')
    def test_add_node_trait_non_existent_node(self):
        """Try to add a trait to a non-existent node."""
        node_uuid = uuidutils.generate_uuid()
        self.assertRaises(
            lib_exc.NotFound,
            self.client.add_node_trait, node_uuid, 'CUSTOM_TRAIT1')

    @decorators.idempotent_id('e4bf8bf0-3004-44bc-8bfe-f9f1a167d999')
    def test_remove_node_traits(self):
        """Remove all traits from a node."""
        self.client.set_node_traits(self.node['uuid'], self.traits)

        self.client.remove_node_traits(self.node['uuid'])

        _, body = self.client.list_node_traits(self.node['uuid'])
        self.assertEqual([], body['traits'])

    @decorators.idempotent_id('4d8c9a35-0036-4139-85c1-5f242395680f')
    def test_remove_node_traits_no_traits(self):
        """Remove all traits from a node that has no traits."""
        self.client.remove_node_traits(self.node['uuid'])

        _, body = self.client.list_node_traits(self.node['uuid'])
        self.assertEqual([], body['traits'])

    @decorators.attr(type='negative')
    @decorators.idempotent_id('625c911a-48e8-4bef-810b-7cf33c0846a2')
    def test_remove_node_traits_non_existent_node(self):
        """Try to remove all traits from a non-existent node."""
        node_uuid = uuidutils.generate_uuid()
        self.assertRaises(
            lib_exc.NotFound,
            self.client.remove_node_traits, node_uuid)

    @decorators.idempotent_id('3591d514-39b9-425e-9afe-ea74ae347486')
    def test_remove_node_trait(self):
        """Remove a trait from a node."""
        self.client.set_node_traits(self.node['uuid'], self.traits)

        self.client.remove_node_trait(self.node['uuid'], 'CUSTOM_TRAIT1')

        _, body = self.client.list_node_traits(self.node['uuid'])
        self.assertEqual(['HW_CPU_X86_VMX'], body['traits'])

    @decorators.attr(type='negative')
    @decorators.idempotent_id('b50ae543-5e5e-4b1a-b2f2-9e00fe55974b')
    def test_remove_node_trait_non_existent_trait(self):
        """Try to remove a non-existent trait from a node."""
        self.assertRaises(
            lib_exc.NotFound,
            self.client.remove_node_trait, self.node['uuid'], 'CUSTOM_TRAIT1')

    @decorators.attr(type='negative')
    @decorators.idempotent_id('f1469745-7cdf-4cae-9699-73d029c47bc3')
    def test_remove_node_trait_non_existent_node(self):
        """Try to remove a trait from a non-existent node."""
        node_uuid = uuidutils.generate_uuid()
        self.assertRaises(
            lib_exc.NotFound,
            self.client.remove_node_trait, node_uuid, 'CUSTOM_TRAIT1')

    @decorators.idempotent_id('03f9e57f-e584-448a-926f-53035e583e7e')
    def test_list_nodes_detail(self):
        """Get detailed nodes list."""
        self.client.set_node_traits(self.node['uuid'], self.traits)

        _, body = self.client.list_nodes_detail()
        self.assertGreaterEqual(len(body['nodes']), 1)

        for node in body['nodes']:
            self.assertIn('traits', node)
            if node['uuid'] == self.node['uuid']:
                self.assertEqual(self.traits, sorted(node['traits']))

    @decorators.idempotent_id('2b82f704-1580-403a-af92-92c29a7eebb7')
    def test_list_nodes_traits_field(self):
        """Get nodes list with the traits field."""
        self.client.set_node_traits(self.node['uuid'], self.traits)

        _, body = self.client.list_nodes(fields='uuid,traits')
        self.assertGreaterEqual(len(body['nodes']), 1)

        for node in body['nodes']:
            self.assertIn('traits', node)
            if node['uuid'] == self.node['uuid']:
                self.assertEqual(self.traits, sorted(node['traits']))

    @decorators.idempotent_id('c83c537a-76aa-4d8a-8673-128d01ee403d')
    def test_show_node(self):
        """Show a node with traits."""
        self.client.set_node_traits(self.node['uuid'], self.traits)

        _, body = self.client.show_node(self.node['uuid'])

        self.assertIn('traits', body)
        self.assertEqual(self.traits, sorted(body['traits']))

    @decorators.attr(type='negative')
    @decorators.idempotent_id('9ab6a19c-83b9-4600-b55b-325a51e2f8f6')
    def test_update_node_traits(self):
        """Try updating an existing node with traits."""
        patch = [{'path': '/traits',
                  'op': 'add',
                  'value': ['CUSTOM_TRAIT1']}]
        self.assertRaises(
            lib_exc.BadRequest,
            self.client.update_node, self.node['uuid'], patch)

        _, body = self.client.list_node_traits(self.node['uuid'])
        self.assertEqual([], body['traits'])


class TestNodesTraitsOldApi(base.BaseBaremetalTest):

    def setUp(self):
        super(TestNodesTraitsOldApi, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis['uuid'])

    @decorators.attr(type='negative')
    @decorators.idempotent_id('5419af7b-4e27-4be4-88f6-e01c598a8102')
    def test_list_node_traits_old_api(self):
        """Try to list traits for a node using an older api version."""
        exc = self.assertRaises(
            lib_exc.UnexpectedResponseCode,
            self.client.list_node_traits, self.node['uuid'])
        self.assertEqual(406, exc.resp.status)

    @decorators.attr(type='negative')
    @decorators.idempotent_id('a4353f3a-bedc-4579-9c7e-4bebcd95903d')
    def test_add_node_trait_old_api(self):
        """Try to add a trait to a node using an older api version."""
        exc = self.assertRaises(
            lib_exc.UnexpectedResponseCode,
            self.client.add_node_trait, self.node['uuid'], 'CUSTOM_TRAIT1')
        self.assertEqual(405, exc.resp.status)

    @decorators.attr(type='negative')
    @decorators.idempotent_id('91cc43d8-2f6f-4b1b-95e9-68dedca54e6b')
    def test_set_node_traits_old_api(self):
        """Try to set traits for a node using an older api version."""
        exc = self.assertRaises(
            lib_exc.UnexpectedResponseCode,
            self.client.set_node_traits, self.node['uuid'], ['CUSTOM_TRAIT1'])
        self.assertEqual(405, exc.resp.status)

    @decorators.attr(type='negative')
    @decorators.idempotent_id('0f9af890-a57a-4c25-86c8-6418d1b8f4d4')
    def test_remove_node_trait_old_api(self):
        """Try to remove a trait from a node using an older api version."""
        self.assertRaises(
            lib_exc.NotFound,
            self.client.remove_node_trait, self.node['uuid'], 'CUSTOM_TRAIT1')

    @decorators.attr(type='negative')
    @decorators.idempotent_id('f8375b3c-1939-4d1c-97c4-d23e10680090')
    def test_remove_node_traits_old_api(self):
        """Try to remove all traits from a node using an older api version."""
        self.assertRaises(
            lib_exc.NotFound,
            self.client.remove_node_traits, self.node['uuid'])

    @decorators.attr(type='negative')
    @decorators.idempotent_id('525eeb59-b7ce-413d-a37b-401e67402a4c')
    def test_list_nodes_detail_old_api(self):
        """Get detailed nodes list, ensure they have no traits."""
        _, body = self.client.list_nodes_detail()
        self.assertGreaterEqual(len(body['nodes']), 1)

        for node in body['nodes']:
            self.assertNotIn('traits', node)

    @decorators.attr(type='negative')
    @decorators.idempotent_id('eb75b3c8-ac9c-4399-90a2-c0030bfde7a6')
    def test_list_nodes_traits_field(self):
        """Try to list nodes' traits field using older api version."""
        exc = self.assertRaises(
            lib_exc.UnexpectedResponseCode,
            self.client.list_nodes, fields='traits')
        self.assertEqual(406, exc.resp.status)

    @decorators.attr(type='negative')
    @decorators.idempotent_id('214ae7fc-149b-4657-b6bc-66353d49ade8')
    def test_show_node_old_api(self):
        """Show a node, ensure it has no traits."""
        _, body = self.client.show_node(self.node['uuid'])
        self.assertNotIn('traits', body)
