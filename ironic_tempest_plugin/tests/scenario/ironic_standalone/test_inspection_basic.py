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


class BaremetalIdracInspect(bsm.BaremetalStandaloneScenarioTest):

    driver = 'idrac'
    mandatory_attr = ['driver', 'inspect_interface']
    # The test cases clean up at the end by detaching the VIF.
    # Support for VIFs was introduced by version 1.28
    # (# v1.28: Add vifs subcontroller to node).
    api_microversion = '1.28'
    delete_node = False

    def _verify_node_inspection_data(self):
        _, node = self.baremetal_client.show_node(self.node['uuid'])

        self.assertEqual(node['properties']['cpu_arch'], 'x86_64')
        self.assertGreater(int(node['properties']['memory_mb']), 0)
        self.assertGreater(int(node['properties']['cpus']), 0)
        self.assertGreater(int(node['properties']['local_gb']), 0)

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
        self.baremetal_client.set_node_provision_state(self.node['uuid'],
                                                       'inspect')

        self.wait_provisioning_state(self.node['uuid'], 'manageable',
                                     timeout=CONF.baremetal.inspect_timeout)

        self._verify_node_inspection_data()

        self.baremetal_client.set_node_provision_state(self.node['uuid'],
                                                       'provide')
        self.wait_provisioning_state(self.node['uuid'], 'available')


class BaremetalIdracRedfishInspect(BaremetalIdracInspect):
    inspect_interface = 'idrac-redfish'


class BaremetalIdracWSManInspect(BaremetalIdracInspect):
    inspect_interface = 'idrac-wsman'
