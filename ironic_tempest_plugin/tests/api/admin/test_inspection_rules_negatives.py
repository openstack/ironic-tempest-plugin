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

from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from ironic_tempest_plugin.tests.api.admin import api_microversion_fixture
from ironic_tempest_plugin.tests.api import base


class TestInspectionRulesNegative(base.BaseBaremetalTest):
    """Negative Inspection Rules test"""

    # Inspection rules API was introduced in microversion 1.96
    # We will be skipping this test for the older version.
    min_microversion = '1.96'

    def setUp(self):
        super(TestInspectionRulesNegative, self).setUp()

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

    @decorators.idempotent_id('55403d94-53ce-41ab-989a-da3399314c9d')
    @decorators.attr(type=['negative'])
    def test_create_invalid_priority_fails(self):
        """Test to create Inspection rule with invalid priorities"""
        invalid_priorities = [-1, 10000, 5000.50]

        for priority_val in invalid_priorities:
            payload = self._create_inspection_rule_payload(
                priority=priority_val)

            self.assertRaises(lib_exc.BadRequest,
                              self.create_inspection_rule,
                              rule_uuid=None, payload=payload)

    @decorators.idempotent_id('cf9615b3-904e-4456-b00a-622d39892b88')
    @decorators.attr(type=['negative'])
    def test_delete_by_wrong_uiid(self):
        """Test to delete Inspection Rule with wrong uuid"""
        rule_uuid = data_utils.rand_uuid()
        self.assertRaises(lib_exc.NotFound,
                          self.delete_inspection_rule,
                          rule_uuid=rule_uuid)
