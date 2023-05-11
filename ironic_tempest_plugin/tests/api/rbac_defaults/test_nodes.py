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

from tempest import config
# from tempest.lib.common import rest_client
# from tempest.lib.common.utils import data_utils
# from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from ironic_tempest_plugin.common import waiters
from ironic_tempest_plugin.tests.api import base

CONF = config.CONF


class TestNodeProjectReader(base.BaseBaremetalRBACTest):
    """Tests for baremetal nodes with a tempest project reader."""

    credentials = ['system_admin', 'project_reader']

    def setUp(self):
        super(TestNodeProjectReader, self).setUp()

        self.client = self.os_system_admin.baremetal.BaremetalClient()
        self.reader_client = self.os_project_reader.baremetal.BaremetalClient()
        _, self.chassis = self.create_chassis()
        # Bare node, no inherent permissions by default for project readers.
        _, self.node = self.create_node(self.chassis['uuid'])

    # Default policy is:
    # ('role:reader and '
    #  '(project_id:%(node.owner)s or project_id:%(node.lessee)s)')

    def test_reader_cannot_create_node(self):
        try:
            resp, body = self.reader_client.create_node(self.chassis['uuid'])
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_get_node(self):
        """Reader cannot get node

        baremetal:node:list
        """
        try:
            resp, body = self.reader_client.show_node(self.node['uuid'])
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_list_is_empty(self):
        """Expected default for no lessee or owner rights is an empty list.

        baremetal:node:list and baremetal:node:list_all
        """
        resp, body = self.reader_client.list_nodes()
        self.assertEqual(0, len(body['nodes']))

    def test_reader_cannot_update_node(self):
        """Reader cannot update node

        baremetal:node:update
        """
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'])
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_update_node_driver_info(self):
        """Reader cannot update node driver_info

        baremetal:node:update:driver_info
        """
        patch = [{'path': '/driver_info/ipmi_username', 'op': 'replace',
                  'value': 'foo_user'}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_update_node_properties(self):
        """Reader cannot update node properties

        baremetal:node:update:properties
        """
        new_p = {'cpu_arch': 'arm64', 'cpus': '1', 'local_gb': '10000',
                 'memory_mb': '12300'}
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        properties=new_p)
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_update_node_chassis_uuid(self):
        """Reader cannot update node chassis uuid

        baremetal:node:update:chassis_uuid
        """
        patch = [{'path': '/chassis_uuid', 'op': 'replace',
                  'value': 'new_chassis_uuid'}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_update_node_instance_uuid(self):
        """Reader cannot update node instance uuid

        baremetal:node:update:instance_uuid
        """
        patch = [{'path': '/instance_uuid', 'op': 'replace',
                  'value': 'new_instance_uuid'}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_update_node_lessee(self):
        """Reader cannot update node lessee

        baremetal:node:update:lessee
        """
        patch = [{'path': '/lessee', 'op': 'replace',
                  'value': 'new_lessee'}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_update_node_owner(self):
        """Reader cannot update node owner

        baremetal:node:update:owner
        """
        patch = [{'path': '/owner', 'op': 'replace',
                  'value': 'new_owner'}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_update_node_driver_interfaces(self):
        """Reader cannot update node driver interfaces

        baremetal:node:update:driver_interfaces
        """
        patch = [{'path': '/driver', 'op': 'replace', 'value': 'ipmi'}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_update_node_network_data(self):
        """Reader cannot update node network data

        baremetal:node:update:network_data
        """
        new_net_data = {'networks': [], 'services': [], 'links': []}
        patch = [{'path': '/network_data', 'op': 'replace',
                  'value': new_net_data}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_update_node_conductor_group(self):
        """Reader cannot update node conductor group

        baremetal:node:update:conductor_group
        """
        patch = [{'path': '/conductor_group', 'op': 'replace',
                  'value': 'new_group'}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_update_node_name(self):
        """Reader cannot update node name

        baremetal:node:update:name
        """
        patch = [{'path': '/name', 'op': 'replace', 'value': 'new_name'}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_update_node_retired(self):
        """Reader cannot update node retired

        baremetal:node:update:retired
        """
        patch = [{'path': '/retired', 'op': 'replace', 'value': True}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_update_node_extra(self):
        """Reader cannot update node extra

        baremetal:node:update:extra
        """
        patch = [{'path': '/extra', 'op': 'replace',
                  'value': {'extra': 'extra'}}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_update_instance_info(self):
        """Reader cannot update node instance info

        baremetal:node:update:instance_info
        """
        patch = [{'path': '/instance_info', 'op': 'replace',
                  'value': {'display_name': 'new_display_name'}}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_update_owner_provisioned(self):
        """Reader cannot update node owner provisioned

        baremetal:node:update_owner_provisioned
        """
        provision_states_list = ['manage', 'provide', 'active']
        target_states_list = ['manageable', 'available', 'active']
        for (provision_state, target_state) in zip(provision_states_list,
                                                   target_states_list):
            self.client.set_node_provision_state(self.node['uuid'],
                                                 provision_state)
            waiters.wait_for_bm_node_status(self.client, self.node['uuid'],
                                            attr='provision_state',
                                            status=target_state, timeout=10)

        patch = [{'path': '/owner', 'op': 'replace',
                  'value': {'display_name': 'new_owner'}}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.NotFound as e:
            resp = e.resp
        finally:
            self.client.set_node_provision_state(self.node['uuid'],
                                                 'deleted')

        self.assertEqual(404, resp.status)

    def test_reader_cannot_delete_node(self):
        """Reader cannot delete node

        baremetal:node:delete
        """
        try:
            resp, body = self.reader_client.delete_node(self.node['uuid'])
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_validate_node(self):
        """Reader cannot validate node

        baremetal:node:validate
        """
        try:
            resp, body = self.reader_client.validate_driver_interface(
                self.node['uuid'])
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_set_maintenance(self):
        """Reader cannot set maintenance mode

        baremetal:node:set_maintenance
        """
        patch = [{'path': '/maintenance', 'op': 'replace', 'value': True}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_unset_maintenance(self):
        """Reader cannot unset maintenance mode

        baremetal:node:clear_maintenance
        """
        patch = [{'path': '/maintenance', 'op': 'replace', 'value': False}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_get_boot_device(self):
        """Reader cannot get boot device

        baremetal:node:get_boot_device
        """
        try:
            resp, body = self.reader_client.get_node_boot_device(
                self.node['uuid'])
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_set_boot_device(self):
        """Reader cannot set boot device

        baremetal:node:set_boot_device
        """
        try:
            resp, body = self.reader_client.set_node_boot_device(
                self.node['uuid'], 'pxe')
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_get_indicator_state(self):
        """Reader cannot get indicator state

        baremetal:node:get_indicator_state
        """
        try:
            resp, body = self.reader_client.get_node_indicator_state(
                self.node['uuid'], 'system', 'led')
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_set_indicator_state(self):
        """Reader cannot set indicator state

        baremetal:node:set_indicator_state
        """
        try:
            resp, body = self.reader_client.set_node_indicator_state(
                self.node['uuid'], 'system', 'led', 'BLINKING')
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_inject_nmi(self):
        """Reader cannot inject NMI

        baremetal:node:inject_nmi
        """
        try:
            resp, body = self.reader_client._put_request(
                '/v1/nodes/%s/management/inject_nmi' % self.node['uuid'], {})
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_get_states(self):
        """Reader cannot list the states of the node

        baremetal:node:get_states
        """
        try:
            resp, body = self.reader_client.list_nodestates(self.node['uuid'])
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_set_power_state(self):
        """Reader cannot set power state

        baremetal:node:set_power_state
        """
        try:
            resp, body = self.reader_client.set_node_power_state(
                self.node['uuid'], 'off')
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_set_boot_mode(self):
        """Reader cannot set boot mode

        baremetal:node:set_boot_mode
        """
        try:
            resp, body = self.reader_client.set_node_state(
                self.node['uuid'], 'boot_mode', 'uefi')
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_set_secure_boot(self):
        """Reader cannot set secure boot

        baremetal:node:set_secure_boot
        """
        try:
            resp, body = self.reader_client.set_node_state(
                self.node['uuid'], 'secure_boot', True)
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_set_provision_state(self):
        """Reader cannot set provision state

        baremetal:node:set_provision_state
        """
        try:
            resp, body = self.reader_client.set_node_provision_state(
                self.node['uuid'], 'manage')
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_set_raid_state(self):
        """Reader cannot set raid state

        baremetal:node:set_raid_state
        """
        try:
            resp, body = self.reader_client.set_node_state(
                self.node['uuid'], 'target_raid_config', {'raid': 'config'})
        except lib_exc.UnexpectedResponseCode as e:
            resp = e.resp

        self.assertEqual(405, resp.status)

    def test_reader_cannot_get_console(self):
        """Reader cannot get console

        baremetal:node:get_console
        """
        try:
            resp, body = self.reader_client.get_console(self.node['uuid'])
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_set_console_state(self):
        """Reader cannot set console state

        baremetal:node:set_console_state
        """
        try:
            resp, body = self.reader_client.set_console_mode(
                self.node['uuid'], enabled=True)
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_vif_list(self):
        """Reader cannot list vifs

        baremetal:node:vif:list
        """
        try:
            resp, body = self.reader_client.vif_list(self.node['uuid'])
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_vif_attach(self):
        """Reader cannot attach vif

        baremetal:node:vif:attach
        """
        try:
            resp = self.reader_client.vif_attach(
                self.node['uuid'], 'vifid')
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_vif_detach(self):
        """Reader cannot detach vif

        baremetal:node:vif:detach
        """
        try:
            resp, body = self.reader_client.vif_detach(
                self.node['uuid'], 'vifid')
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_traits_list(self):
        """Reader cannot list traits

        baremetal:node:traits:list
        """
        try:
            resp, body = self.reader_client.list_node_traits(self.node['uuid'])
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_traits_set(self):
        """Reader cannot set traits

        baremetal:node:traits:set
        """
        try:
            resp, body = self.reader_client.set_node_traits(
                self.node['uuid'], ['CUSTOM_TRAIT_A', 'CUSTOM_TRAIT_B'])
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_traits_delete(self):
        """Reader cannot delete traits

        baremetal:node:traits:delete
        """
        try:
            resp, body = self.reader_client.remove_node_traits(
                self.node['uuid'])
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_bios_get(self):
        """Reader cannot get bios settings

        baremetal:node:bios:get
        """
        try:
            resp, body = self.reader_client.list_node_bios_settings(
                self.node['uuid'])
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_disable_cleaning(self):
        """Reader cannot disable automated node cleaning

        baremetal:node:disable_cleaning
        """
        patch = [{'path': '/automated_clean', 'op': 'replace', 'value': False}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_history_get(self):
        """Reader cannot list history entries for a node

        baremetal:node:history:get
        """
        try:
            resp, body = self.reader_client.list_node_history(
                self.node['uuid'])
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_vendor_passthru(self):
        """Reader cannot list vendor-specific extensions

        baremetal:node:vendor_passthru
        """
        try:
            resp, body = self.reader_client.list_vendor_passthru_methods(
                self.node['uuid'])
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_ipa_heartbeat(self):
        """Reader cannot heartbeat

        baremetal:node:ipa_heartbeat
        """
        # TODO(hjensas)
        # try:
        #     resp, body = self.reader_client.ipa_heartbeat(
        #         self.node['uuid'], callback_url='http://foo/',
        #         agent_token=uuidutils.generate_uuid(), agent_version='1')
        # except lib_exc.BadRequest as e:
        #     resp = e.resp
        #
        # self.assertEqual(400, resp.status)
        pass


class TestNodeSystemReader(base.BaseBaremetalRBACTest):
    """Tests for baremetal nodes with a tempest system reader.

    All tests here must always expect *multiple* nodes visible, since
    this is a global reader role.

    https://opendev.org/openstack/ironic/src/branch/master/ironic/common/policy.py#L60  # noqa
    """

    credentials = ['system_admin', 'system_reader']

    def setUp(self):
        super(TestNodeSystemReader, self).setUp()

        self.client = self.os_system_admin.baremetal.BaremetalClient()
        self.reader_client = self.os_system_reader.baremetal.BaremetalClient()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis['uuid'])

    def test_reader_cannot_create_node(self):
        """Reader cannot create node

        baremetal:node:create
        """
        try:
            resp, body = self.reader_client.create_node(self.chassis['uuid'])
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_can_get_node(self):
        """Reader can get node

        baremetal:node:??get??list??
        """
        resp, body = self.reader_client.show_node(self.node['uuid'])
        self.assertEqual(200, resp.status)

    def test_reader_list_is_not_empty(self):
        """List nodes return all nodes

        baremetal:node:list and baremetal:node:list_all
        """
        resp, body = self.reader_client.list_nodes()
        self.assertGreater(len(body['nodes']), 0)

    def test_reader_cannot_update_node(self):
        """Reader cannot update node

        baremetal:node:update
        """
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'])
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_update_node_driver_info(self):
        """Reader cannot update node driver_info

        baremetal:node:update:driver_info
        """
        patch = [{'path': '/driver_info/ipmi_username', 'op': 'replace',
                  'value': 'foo_user'}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_update_node_properties(self):
        """Reader cannot update node properties

        baremetal:node:update:properties
        """
        new_p = {'cpu_arch': 'arm64', 'cpus': '1', 'local_gb': '10000',
                 'memory_mb': '12300'}
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        properties=new_p)
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_update_node_chassis_uuid(self):
        """Reader cannot update node chassis uuid

        baremetal:node:update:chassis_uuid
        """
        patch = [{'path': '/chassis_uuid', 'op': 'replace',
                  'value': 'new_chassis_uuid'}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_update_node_instance_uuid(self):
        """Reader cannot update node instance uuid

        baremetal:node:update:instance_uuid
        """
        patch = [{'path': '/instance_uuid', 'op': 'replace',
                  'value': 'new_instance_uuid'}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_update_node_lessee(self):
        """Reader cannot update node lessee

        baremetal:node:update:lessee
        """
        patch = [{'path': '/lessee', 'op': 'replace',
                  'value': 'new_lessee'}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_update_node_owner(self):
        """Reader cannot update node owner

        baremetal:node:update:owner
        """
        patch = [{'path': '/owner', 'op': 'replace',
                  'value': 'new_owner'}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_update_node_driver_interfaces(self):
        """Reader cannot update node driver interfaces

        baremetal:node:update:driver_interfaces
        """
        patch = [{'path': '/driver', 'op': 'replace', 'value': 'ipmi'}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_update_node_network_data(self):
        """Reader cannot update node network data

        baremetal:node:update:network_data
        """
        new_net_data = {'networks': [], 'services': [], 'links': []}
        patch = [{'path': '/network_data', 'op': 'replace',
                  'value': new_net_data}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_update_node_conductor_group(self):
        """Reader cannot update node conductor group

        baremetal:node:update:conductor_group
        """
        patch = [{'path': '/conductor_group', 'op': 'replace',
                  'value': 'new_group'}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_update_node_name(self):
        """Reader cannot update node name

        baremetal:node:update:name
        """
        patch = [{'path': '/name', 'op': 'replace', 'value': 'new_name'}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_update_node_retired(self):
        """Reader cannot update node retired

        baremetal:node:update:retired
        """
        patch = [{'path': '/retired', 'op': 'replace', 'value': True}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_update_node_extra(self):
        """Reader cannot update node extra

        baremetal:node:update:extra
        """
        patch = [{'path': '/extra', 'op': 'replace',
                  'value': {'extra': 'extra'}}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_update_instance_info(self):
        """Reader cannot update node instance info

        baremetal:node:update:instance_info
        """
        patch = [{'path': '/instance_info', 'op': 'replace',
                  'value': {'display_name': 'new_display_name'}}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_update_owner_provisioned(self):
        """Reader cannot update node owner provisioned

        baremetal:node:update_owner_provisioned
        """
        provision_states_list = ['manage', 'provide', 'active']
        target_states_list = ['manageable', 'available', 'active']
        for (provision_state, target_state) in zip(provision_states_list,
                                                   target_states_list):
            self.client.set_node_provision_state(self.node['uuid'],
                                                 provision_state)
            waiters.wait_for_bm_node_status(self.client, self.node['uuid'],
                                            attr='provision_state',
                                            status=target_state, timeout=10)

        patch = [{'path': '/owner', 'op': 'replace',
                  'value': {'display_name': 'new_owner'}}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.Forbidden as e:
            resp = e.resp
        finally:
            self.client.set_node_provision_state(self.node['uuid'],
                                                 'deleted')

        self.assertEqual(403, resp.status)

    def test_reader_cannot_delete_node(self):
        """Reader cannot delete node

        baremetal:node:delete
        """
        try:
            resp, body = self.reader_client.delete_node(self.node['uuid'])
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_validate_node(self):
        """Reader cannot validate node

        baremetal:node:validate
        """
        try:
            resp, body = self.reader_client.validate_driver_interface(
                self.node['uuid'])
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_set_maintenance(self):
        """Reader cannot set maintenance mode

        baremetal:node:set_maintenance
        """
        patch = [{'path': '/maintenance', 'op': 'replace', 'value': True}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_unset_maintenance(self):
        """Reader cannot unset maintenance mode

        baremetal:node:clear_maintenance
        """
        patch = [{'path': '/maintenance', 'op': 'replace', 'value': False}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_get_boot_device(self):
        """Reader cannot get boot device

        baremetal:node:get_boot_device
        """
        try:
            resp, body = self.reader_client.get_node_boot_device(
                self.node['uuid'])
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_set_boot_device(self):
        """Reader cannot set boot device

        baremetal:node:set_boot_device
        """
        try:
            resp, body = self.reader_client.set_node_boot_device(
                self.node['uuid'], 'pxe')
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_can_get_indicator_state(self):
        """Reader can get indicator state

        baremetal:node:get_indicator_state
        """
        resp, body = self.reader_client.get_node_indicator_state(
            self.node['uuid'], 'system', 'led')
        self.assertEqual(200, resp.status)

    def test_reader_cannot_set_indicator_state(self):
        """Reader cannot set indicator state

        baremetal:node:set_indicator_state
        """
        try:
            resp, body = self.reader_client.set_node_indicator_state(
                self.node['uuid'], 'system', 'led', 'BLINKING')
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_inject_nmi(self):
        """Reader cannot inject NMI

        baremetal:node:inject_nmi
        """
        try:
            resp, body = self.reader_client._put_request(
                '/v1/nodes/%s/management/inject_nmi' % self.node['uuid'], {})
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_can_get_states(self):
        """Reader can list the states of the node

        baremetal:node:get_states
        """
        resp, body = self.reader_client.list_nodestates(self.node['uuid'])
        self.assertEqual(200, resp.status)

    def test_reader_cannot_set_power_state(self):
        """Reader cannot set power state

        baremetal:node:set_power_state
        """
        try:
            resp, body = self.reader_client.set_node_power_state(
                self.node['uuid'], 'off')
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_set_boot_mode(self):
        """Reader cannot set boot mode

        baremetal:node:set_boot_mode
        """
        try:
            resp, body = self.reader_client.set_node_state(
                self.node['uuid'], 'boot_mode', 'uefi')
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_set_secure_boot(self):
        """Reader cannot set secure boot

        baremetal:node:set_secure_boot
        """
        try:
            resp, body = self.reader_client.set_node_state(
                self.node['uuid'], 'secure_boot', True)
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_set_provision_state(self):
        """Reader cannot set provision state

        baremetal:node:set_provision_state
        """
        try:
            resp, body = self.reader_client.set_node_provision_state(
                self.node['uuid'], 'manage')
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_set_raid_state(self):
        """Reader cannot set raid state

        baremetal:node:set_raid_state
        """
        try:
            resp, body = self.reader_client.set_node_state(
                self.node['uuid'], 'target_raid_config', {'raid': 'config'})
        except lib_exc.UnexpectedResponseCode as e:
            resp = e.resp

        self.assertEqual(405, resp.status)

    def test_reader_cannot_get_console(self):
        """Reader cannot get console

        baremetal:node:get_console
        """
        try:
            resp, body = self.reader_client.get_console(self.node['uuid'])
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_set_console_state(self):
        """Reader cannot set console state

        baremetal:node:set_console_state
        """
        try:
            resp, body = self.reader_client.set_console_mode(
                self.node['uuid'], enabled=True)
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_can_vif_list(self):
        """Reader can list vifs

        baremetal:node:vif:list
        """
        resp, body = self.reader_client.vif_list(self.node['uuid'])
        self.assertEqual(200, resp.status)

    def test_reader_cannot_vif_attach(self):
        """Reader cannot attach vif

        baremetal:node:vif:attach
        """
        try:
            resp = self.reader_client.vif_attach(
                self.node['uuid'], 'vifid')
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_vif_detach(self):
        """Reader cannot detach vif

        baremetal:node:vif:detach
        """
        try:
            resp, body = self.reader_client.vif_detach(
                self.node['uuid'], 'vifid')
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_can_traits_list(self):
        """Reader can list traits

        baremetal:node:traits:list
        """
        resp, body = self.reader_client.list_node_traits(self.node['uuid'])
        self.assertEqual(200, resp.status)

    def test_reader_cannot_traits_set(self):
        """Reader cannot set traits

        baremetal:node:traits:set
        """
        try:
            resp, body = self.reader_client.set_node_traits(
                self.node['uuid'], ['CUSTOM_TRAIT_A', 'CUSTOM_TRAIT_B'])
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_traits_delete(self):
        """Reader cannot delete traits

        baremetal:node:traits:delete
        """
        try:
            resp, body = self.reader_client.remove_node_traits(
                self.node['uuid'])
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_can_bios_get(self):
        """Reader can get bios settings

        baremetal:node:bios:get
        """
        resp, body = self.reader_client.list_node_bios_settings(
            self.node['uuid'])
        self.assertEqual(200, resp.status)

    def test_reader_cannot_disable_cleaning(self):
        """Reader cannot disable automated node cleaning

        baremetal:node:disable_cleaning
        """
        patch = [{'path': '/automated_clean', 'op': 'replace', 'value': False}]
        try:
            resp, body = self.reader_client.update_node(self.node['uuid'],
                                                        patch=patch)
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_history_get(self):
        """Reader cannot list history entries for a node

        baremetal:node:history:get
        """
        try:
            resp, body = self.reader_client.list_node_history(
                self.node['uuid'])
        except lib_exc.NotFound as e:
            resp = e.resp

        self.assertEqual(404, resp.status)

    def test_reader_cannot_vendor_passthru(self):
        """Reader cannot list vendor-specific extensions

        baremetal:node:vendor_passthru
        """
        try:
            resp, body = self.reader_client.list_vendor_passthru_methods(
                self.node['uuid'])
        except lib_exc.Forbidden as e:
            resp = e.resp

        self.assertEqual(403, resp.status)

    def test_reader_cannot_ipa_heartbeat(self):
        """Reader cannot heartbeat

        baremetal:node:ipa_heartbeat
        """
        # TODO(hjensas)
        pass
