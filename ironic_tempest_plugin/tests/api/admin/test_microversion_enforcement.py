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

from oslo_utils import uuidutils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from ironic_tempest_plugin.services.baremetal.v1.json.baremetal_client import \
    BaremetalClient
from ironic_tempest_plugin.tests.api.admin import api_microversion_fixture
from ironic_tempest_plugin.tests.api import base


class MicroversionTestMixin:
    """Mixin class containing shared microversion test functionality."""

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


class BaseTestMicroversionEnforcement(base.BaseBaremetalTest):
    """Base class for microversion enforcement tests."""

    def setUp(self):
        super(BaseTestMicroversionEnforcement, self).setUp()
        self.resource_class = uuidutils.generate_uuid()


class TestShardMicroversions(
        BaseTestMicroversionEnforcement,
        MicroversionTestMixin):
    """Tests for shard-related API microversion enforcement."""

    min_microversion = "1.82"

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


class TestAllocationMicroversions(
        BaseTestMicroversionEnforcement,
        MicroversionTestMixin):
    """Tests for allocation-related API microversion enforcement."""

    min_microversion = "1.52"

    @decorators.idempotent_id('8f527b3d-d5f1-4859-920f-8022b5d13621')
    def test_create_allocations(self):
        self._microversion_test(
            BaremetalClient.create_allocation, "1.52",
            lib_exc.UnexpectedResponseCode, {
                "resource_class": self.resource_class
            }
        )

    @decorators.idempotent_id('511e0c4b-1320-4ac5-9c4a-fb0394d3ff67')
    def test_list_allocations(self):
        self._microversion_test(
            BaremetalClient.list_allocations, "1.52",
            lib_exc.NotFound, {}
        )

    @decorators.idempotent_id('a0d17f90-baa0-4518-95f7-a7eab73ff6d1')
    def test_show_allocations(self):
        _, allocation = self.create_allocation(self.resource_class)

        self._microversion_test(
            BaremetalClient.show_allocation, "1.52",
            lib_exc.NotFound, {
                "allocation_ident": allocation['uuid']
            }
        )

    @decorators.idempotent_id('b05a9b1a-4a12-4b55-93c7-530c3f35c7d9')
    def test_delete_allocations(self):
        _, allocation = self.create_allocation(self.resource_class)

        self._microversion_test(
            BaremetalClient.delete_allocation, "1.52",
            lib_exc.UnexpectedResponseCode, {
                "allocation_ident": allocation['uuid']
            }
        )


class TestNodeFirmwarenMicroversions(
        BaseTestMicroversionEnforcement,
        MicroversionTestMixin):

    min_microversion = "1.86"

    def setUp(self):
        super(TestNodeFirmwarenMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis['uuid'])

    @decorators.idempotent_id('f50e9098-1870-46b1-b05c-660d0f8c534d')
    def test_list_node_firmware(self):
        self._microversion_test(
            BaremetalClient.list_node_firmware, "1.86",
            lib_exc.NotFound, {"node_uuid": self.node['uuid']}
        )
