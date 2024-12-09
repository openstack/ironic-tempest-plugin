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


from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from ironic_tempest_plugin.services.baremetal.v1.json.baremetal_client import \
    BaremetalClient
from ironic_tempest_plugin.tests.api.admin import api_microversion_fixture
from ironic_tempest_plugin.tests.api import base


class TestMicroversionEnforcement(base.BaseBaremetalTest):
    """Tests for API microversion enforcement."""

    def setUp(self):
        super(TestMicroversionEnforcement, self).setUp()

    def _microversion_test(
            self, method_name, min_version, expected_error, required_args):
        """Test methods with invalid API versions"""

        major, minor = map(int, min_version.split('.'))
        # Set limits, as lowest microversion is 1.1
        if minor <= 10:
            minor = 11
        if minor <= 1:
            minor = 2
        invalid_versions = [
            f"{major}.{minor - 1}",
            f"{major}.{minor - 10}",
        ]

        # Get method name from method object
        # This way, users can pass the method object,
        # and we can still get the instantiated method
        method_name = method_name.__name__

        for microversion in invalid_versions:
            for arg_name, arg_value in required_args.items():
                msg = (
                    f"Testing {method_name} with version {microversion} "
                    f"and argument {arg_name}={arg_value}"
                )
                with self.subTest(
                    msg=msg, method=method_name, version=microversion
                ):
                    self.useFixture(
                        api_microversion_fixture.APIMicroversionFixture(
                            microversion
                        )
                    )
                    method = getattr(self.client, method_name)

                    self.assertRaises(
                        expected_error,
                        method,
                        **{arg_name: arg_value},
                    )

    @decorators.idempotent_id("e5403a31-e12b-4f97-a776-dcb819e5e9a0")
    def test_shard(self):
        self._microversion_test(
            BaremetalClient.get_shards, "1.82", lib_exc.NotFound, {}
        )

    @decorators.idempotent_id("5df533c6-7a9c-4639-a47f-1377a2a87e6a")
    def test_list_node_filter_shard(self):
        self._microversion_test(
            BaremetalClient.list_nodes, "1.82",
            lib_exc.NotAcceptable, {"shard": "testshard"}
        )
