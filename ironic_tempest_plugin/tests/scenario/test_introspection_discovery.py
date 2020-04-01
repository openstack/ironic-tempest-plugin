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
from tempest import test  # noqa

from ironic_tempest_plugin.tests.scenario import baremetal_manager
from ironic_tempest_plugin.tests.scenario import introspection_manager

CONF = config.CONF

ProvisionStates = baremetal_manager.BaremetalProvisionStates


class InspectorDiscoveryTest(introspection_manager.InspectorScenarioTest):
    @classmethod
    def skip_checks(cls):
        super(InspectorDiscoveryTest, cls).skip_checks()
        if not CONF.baremetal_introspection.auto_discovery_feature:
            msg = ("Please, provide a value for node_not_found_hook in "
                   "processing section of inspector.conf for enable "
                   "auto-discovery feature.")
            raise cls.skipException(msg)

    def setUp(self):
        super(InspectorDiscoveryTest, self).setUp()

        discovered_node = self._get_discovery_node()
        self.node_info = self._get_node_info(discovered_node)
        self.default_driver = (
            CONF.baremetal_introspection.auto_discovery_default_driver
        )
        self.expected_driver = (
            CONF.baremetal_introspection.auto_discovery_target_driver
            or CONF.baremetal_introspection.auto_discovery_default_driver
        )

        rule = {
            "description": "Auto-discovery rule",
            "actions": [
                # Set an attribute in case we cannot access the introspection
                # data to check the auto_discovered flag directly.
                {"action": "set-attribute",
                 "path": "/extra/discovered",
                 "value": "yes"},
                # Re-assign the name to use it later in the test.
                {"action": "set-attribute",
                 "path": "/name",
                 "value": self.node_info['name']},
            ],
            "conditions": [
                # This flag must be automatically set by the auto-discovery
                # process.
                {"op": "eq",
                 "field": "data://auto_discovered",
                 "value": True},
                # Making sure the initial driver matches the expected.
                {"op": "eq",
                 "field": "node://driver",
                 "value": self.default_driver},
            ]
        }

        if self.expected_driver != self.default_driver:
            rule['actions'].append({
                'action': 'set-attribute',
                'path': '/driver',
                'value': self.expected_driver
            })

        self.rule_import_from_dict(rule)
        self.addCleanup(self.rule_purge)

    def _get_node_info(self, node_uuid):
        node = self.node_show(node_uuid)
        ports = self.node_port_list(node_uuid)
        node['port_macs'] = [port['address'] for port in ports]
        return node

    def _get_discovery_node(self):
        nodes = self.node_list()

        discovered_node = None
        for node in nodes:
            if (node['provision_state'] == ProvisionStates.AVAILABLE
                    or node['provision_state'] == ProvisionStates.ENROLL
                    or node['provision_state'] is ProvisionStates.NOSTATE):
                discovered_node = node['uuid']
                break

        self.assertIsNotNone(discovered_node)
        return discovered_node

    def verify_node_introspection_data(self, node):
        data = self.introspection_data(node['uuid'])
        self.assertTrue(data['auto_discovered'])
        self.assertEqual(data['cpu_arch'],
                         self.flavor['properties']['cpu_arch'])
        self.assertEqual(int(data['memory_mb']),
                         int(self.flavor['ram']))
        self.assertEqual(int(data['cpus']), int(self.flavor['vcpus']))

    def verify_node_flavor(self, node):
        expected_cpus = self.flavor['vcpus']
        expected_memory_mb = self.flavor['ram']
        expected_cpu_arch = self.flavor['properties']['cpu_arch']
        disk_size = self.flavor['disk']
        ephemeral_size = self.flavor['OS-FLV-EXT-DATA:ephemeral']
        expected_local_gb = disk_size + ephemeral_size

        self.assertEqual(expected_cpus,
                         int(node['properties']['cpus']))
        self.assertEqual(expected_memory_mb,
                         int(node['properties']['memory_mb']))
        self.assertEqual(expected_local_gb,
                         int(node['properties']['local_gb']))
        self.assertEqual(expected_cpu_arch,
                         node['properties']['cpu_arch'])

    @decorators.idempotent_id('dd3abe5e-0d23-488d-bb4e-344cdeff7dcb')
    def test_bearmetal_auto_discovery(self):
        """This test case follows this set of operations:

           * Choose appropriate node, based on provision state;
           * Get node info;
           * Generate discovery rule;
           * Start introspection via ironic-inspector API;
           * Delete the node from ironic;
           * Wating for node discovery;
           * Verify introspected node.
        """
        # NOTE(aarefiev): workaround for infra, 'tempest' user doesn't
        # have virsh privileges, so lets power on the node via ironic
        # and then delete it. Because of node is blacklisted in inspector
        # we can't just power on it, therefor start introspection is used
        # to whitelist discovered node first.
        self.baremetal_client.set_node_provision_state(
            self.node_info['uuid'], 'manage')
        self.introspection_start(self.node_info['uuid'])
        self.wait_power_state(
            self.node_info['uuid'],
            baremetal_manager.BaremetalPowerStates.POWER_ON)
        self.node_delete(self.node_info['uuid'])

        self.wait_for_node(self.node_info['name'])

        inspected_node = self.node_show(self.node_info['name'])
        self.verify_node_flavor(inspected_node)
        data_store = CONF.baremetal_introspection.data_store
        if data_store is None:
            # Backward compatibility, the option is not set.
            data_store = ('swift' if CONF.service_available.swift
                          else 'none')
        if data_store != 'none':
            self.verify_node_introspection_data(inspected_node)
        self.assertEqual(ProvisionStates.ENROLL,
                         inspected_node['provision_state'])
        self.assertEqual(self.expected_driver, inspected_node['driver'])
        self.assertEqual('yes', inspected_node['extra']['discovered'])
