# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from tempest.lib.common.utils import data_utils
from tempest.lib import decorators

from ironic_tempest_plugin.tests.api.admin import api_microversion_fixture
from ironic_tempest_plugin.tests.api import base


class TestInspectionRules(base.BaseBaremetalTest):
    """API tests for Inspection Rules endpoints"""

    # Inspection rules API was introduced in microversion 1.96
    # We will be skipping this test for the older version.
    min_microversion = '1.96'

    def setUp(self):
        super(TestInspectionRules, self).setUp()

        _, self.node = self.create_node(None)

        self.useFixture(
            api_microversion_fixture.APIMicroversionFixture('1.96'))

    def _create_inspection_rule_payload(self, **kwargs):
        """Create a Inspection rule payload."""
        payload = {
            "description": "Inspection rule to log node UUID",
            "conditions": [],
            "actions": [
                {
                    "op": "log",
                    "args": {
                        "msg": "Node with UUID {node.uuid} is being inspected"
                    }
                }
            ],
            "phase": "main",
            "priority": 0,
            "sensitive": False
        }

        payload.update(kwargs)

        return payload

    @decorators.idempotent_id('7fb771cd-b011-409e-a255-3c71cf7251e8')
    def test_create_rule_sensitive_true(self):
        """Test creating rule with sensitive=True."""
        rule_uuid = data_utils.rand_uuid()
        payload = self._create_inspection_rule_payload(sensitive=True)

        self.create_inspection_rule(rule_uuid, payload)

        _, fetched_rule = self.client.show_inspection_rule(rule_uuid)

        self.assertTrue(fetched_rule.get('sensitive'))
        self.assertIsNone(fetched_rule.get('conditions'))
        self.assertIsNone(fetched_rule.get('actions'))

    @decorators.idempotent_id('e60b4513-7c3d-4b2c-b485-17443bf6485f')
    def test_create_rule_complex_logging_conditions_actions(self):
        """Test creating rule with loop conditions and actions"""
        complex_log_conditions = [
            {
                "op": "eq",
                "args": [
                    "{inventory.system.product_name}",
                    "{item}"
                ],
                "loop": [
                    "product_name_1",
                    "product_name_2",
                    "product_name_3"
                ],
                "multiple": "any"
            }
        ]

        complex_log_actions = [
            {
                "op": "set-attribute",
                "args": [
                    "{item[path]}",
                    "{item[value]}"
                ],
                "loop": [
                    {
                        "path": "/driver_info/ipmi_username",
                        "value": "admin"
                    },
                    {
                        "path": "/driver_info/ipmi_password",
                        "value": "password"
                    },
                    {
                        "path": "/driver_info/ipmi_address",
                        "value": "{inventory[bmc_address]}"
                    }
                ]
            }
        ]

        payload = self._create_inspection_rule_payload(
            conditions=complex_log_conditions,
            actions=complex_log_actions,
        )

        _, created_rule = self.create_inspection_rule(None, payload)

        self.assertEqual(complex_log_conditions,
                         created_rule.get('conditions'))
        self.assertEqual(complex_log_actions,
                         created_rule.get('actions'))

    @decorators.idempotent_id('a786a4ec-1e43-4fb9-8fc3-c53aa4e1f52f')
    def test_patch_conditions_actions_priority(self):
        """Test Updating rule'si priority, condition and actions"""
        payload = self._create_inspection_rule_payload()

        patch = [
            {
                "op": "replace",
                "path": "/priority",
                "value": 200
            },
            {
                "op": "replace",
                "path": "/conditions",
                "value": [
                    {
                        "op": "eq",
                        "args": ["{{ inventory.cpu.count }}", 8]
                    }
                ]
            },
            {
                "op": "replace",
                "path": "/actions",
                "value": [
                    {
                        "op": "set-attribute",
                        "args": ["{{ /properties/cpu_model }}", "cpu_xyz"]
                    },
                    {
                        "op": "log",
                        "args": ["CPU model updated via rule."]
                    }
                ]
            }
        ]

        _, created_rule = self.create_inspection_rule(None, payload)
        _, fetched_rule = self.client.update_inspection_rule(
            created_rule.get('uuid'), patch)

        self.assertEqual(fetched_rule.get('priority'),
                         patch[0]['value'])
        self.assertEqual(fetched_rule.get('conditions'),
                         patch[1]['value'])
        self.assertEqual(fetched_rule.get('actions'),
                         patch[2]['value'])
