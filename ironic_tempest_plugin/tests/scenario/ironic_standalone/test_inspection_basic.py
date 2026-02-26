#    Copyright (c) 2022 Dell Inc. or its subsidiaries.
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

from tempest import config
from tempest.lib import decorators

from ironic_tempest_plugin.tests.scenario import \
    baremetal_standalone_manager as bsm

CONF = config.CONF


class BaremetalInspectBase:

    mandatory_attr = ['driver', 'inspect_interface']
    # (# v1.31: Support for updating inspect_interface).
    api_microversion = '1.31'
    delete_node = False
    wait_provisioning_state_interval = 1

    def _verify_node_inspection_data(self, node):
        self.assertIn(node['properties']['cpu_arch'], ['x86_64', 'aarch64'])

    @decorators.idempotent_id('47ea4487-4720-43e8-a024-53ae82f8c264')
    def test_baremetal_inspect(self):
        """This test case follows this set of operations:

            * Sets nodes to manageable state
            * Inspects nodes
            * Verifies inspection data
            * Sets node to available state
        """
        self.baremetal_client.set_node_provision_state(self.node['uuid'],
                                                       'manage')
        _, node = self.baremetal_client.show_node(self.node['uuid'])
        if 'cpu_arch' in node['properties']:
            new_properties = node['properties'].copy()
            new_properties.pop('cpu_arch')
            self.baremetal_client.update_node(self.node['uuid'],
                                              properties=new_properties)

        self.baremetal_client.set_node_provision_state(self.node['uuid'],
                                                       'inspect')
        self.wait_provisioning_state(
            self.node['uuid'], 'manageable',
            timeout=CONF.baremetal.inspect_timeout,
            interval=self.wait_provisioning_state_interval)

        _, node = self.baremetal_client.show_node(self.node['uuid'])
        self._verify_node_inspection_data(node)

        self.baremetal_client.set_node_provision_state(self.node['uuid'],
                                                       'provide')
        self.wait_provisioning_state(self.node['uuid'], 'available')


class BaremetalRedfishAgentInspect(BaremetalInspectBase,
                                   bsm.BaremetalStandaloneScenarioTest):
    driver = 'redfish'
    inspect_interface = 'agent'
    wait_provisioning_state_interval = 15
    # 1.81 adds support for inventory API
    api_microversion = '1.81'

    def _verify_node_inspection_data(self, node):
        super()._verify_node_inspection_data(node)
        inspection_data = self.baremetal_client.show_inventory(
            self.node['uuid'])
        self.assertEqual({'inventory', 'plugin_data'}, set(inspection_data))

        # Inventory sanity check
        inventory = inspection_data['inventory']
        self.assertGreater(inventory['cpu']['count'], 0)
        self.assertGreater(inventory['memory']['physical_mb'], 256)
        self.assertGreater(len(inventory['disks']), 0)
        self.assertGreater(len(inventory['interfaces']), 0)

    @decorators.idempotent_id('82670a85-49b7-4d28-b8a8-6e18b0d4c8d1')
    def test_inspect_abort(self):
        _, node = self.baremetal_client.show_node(self.node['uuid'])
        current_state = node['provision_state']

        def cleanup():
            nonlocal current_state

            if current_state == 'inspect failed':
                self.baremetal_client.set_node_provision_state(
                    self.node['uuid'], 'manage')
                self.wait_provisioning_state(self.node['uuid'], 'manageable')
                current_state = 'manageable'

            if current_state == 'manageable':
                self.baremetal_client.set_node_provision_state(
                    self.node['uuid'], 'provide')
                self.wait_provisioning_state(self.node['uuid'], 'available')

        self.addCleanup(cleanup)

        if current_state != 'manageable':
            self.baremetal_client.set_node_provision_state(self.node['uuid'],
                                                           'manage')
        current_state = 'manageable'

        self.baremetal_client.set_node_provision_state(self.node['uuid'],
                                                       'inspect')
        self.wait_provisioning_state(
            self.node['uuid'], 'inspect wait',
            timeout=300, interval=5)

        self.baremetal_client.set_node_provision_state(self.node['uuid'],
                                                       'abort')
        self.wait_provisioning_state(
            self.node['uuid'], 'inspect failed',
            timeout=60, interval=1)
        current_state = 'inspect failed'


class BaremetalIdracInspect(BaremetalInspectBase,
                            bsm.BaremetalStandaloneScenarioTest):
    driver = 'idrac'

    def _verify_node_inspection_data(self, node):
        super()._verify_node_inspection_data(node)
        self.assertGreater(int(node['properties']['memory_mb']), 0)
        self.assertGreater(int(node['properties']['cpus']), 0)
        self.assertGreater(int(node['properties']['local_gb']), 0)


class BaremetalIdracRedfishInspect(BaremetalIdracInspect):
    inspect_interface = 'idrac-redfish'
