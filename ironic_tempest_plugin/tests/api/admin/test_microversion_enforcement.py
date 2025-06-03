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

import random

from oslo_utils import timeutils
from oslo_utils import uuidutils
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from ironic_tempest_plugin.services.baremetal.v1.json.baremetal_client import \
    BaremetalClient
from ironic_tempest_plugin.tests.api.admin import api_microversion_fixture
from ironic_tempest_plugin.tests.api import base

CONF = config.CONF


class MicroversionTestMixin:
    """Mixin class containing shared microversion test functionality."""

    def _microversion_test(
        self,
        method_name,
        min_version,
        expected_error,
        required_args,
        ignore_positive=False,
    ):
        """Test methods with invalid API versions"""

        major, minor = map(int, min_version.split("."))
        invalid_versions = []
        if minor >= 11:
            invalid_versions.append(f"{major}.{minor - 10}")
        if minor >= 2:
            invalid_versions.append(f"{major}.{minor - 1}")
        elif minor == 0 and major > 1:
            invalid_versions.append(f"{major - 1}.99")
        elif minor == 1:
            invalid_versions.append(f"{major}.0")
        else:
            # We expect fails for v1.0 and below
            raise ValueError(f"Invalid microversion {min_version}")

        # Get method name from method object
        method_name = method_name.__name__

        # Test with invalid versions (should fail)
        for microversion in invalid_versions:
            msg = (
                f"Testing {method_name} with version {microversion} "
                f"and arguments {required_args} - should fail"
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

                try:
                    method(**required_args)
                    self.fail(
                        f"Request for microversion {microversion} for "
                        f"{method_name} unexpectedly succeeded. We expected "
                        f"{expected_error.__name__}."
                    )
                except expected_error:
                    pass  # Expected error, test passes
                except Exception as e:
                    self.fail(
                        f"Request for microversion {microversion} for "
                        f"{method_name} raised unexpected exception: {e}"
                    )

        if ignore_positive:
            return True

        # Test with valid version (should succeed)
        # Use the minimum required version
        msg = (
            f"Testing {method_name} with version {min_version} "
            f"and arguments {required_args} - should succeed"
        )
        with self.subTest(
            msg=msg, method=method_name, version=min_version
        ):
            self.useFixture(
                api_microversion_fixture.APIMicroversionFixture(
                    min_version
                )
            )
            method = getattr(self.client, method_name)

            try:
                # We don't check the actual response, just
                # that it doesn't raise
                # the expected error from the negative test
                method(**required_args)
                return True

            except expected_error as e:
                self.fail(
                    f"Method {method_name} failed with valid "
                    f"microversion {min_version}: {e}"
                )
            except Exception as e:
                # Other exceptions might be expected due to invalid test data
                # For example, a 404 might be expected if we're using fake IDs
                self.assertNotIsInstance(
                    e,
                    expected_error,
                    (
                        f"Got unexpected {expected_error.__name__} with valid "
                        f"microversion {min_version}: {e}"
                    ),
                )


class BaseTestMicroversionEnforcement(base.BaseBaremetalTest):
    """Base class for microversion enforcement tests."""

    def setUp(self):
        super().setUp()
        self.resource_class = uuidutils.generate_uuid()


class TestNodesMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for nodes-related API microversion enforcement."""

    min_microversion = "1.1"

    def setUp(self):
        super(TestNodesMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()

    # NOTE(adamcarthur) - We test the positive case in the other
    # tests. Doing it here would require changing the test function
    # to allow returns.
    @decorators.idempotent_id("be29d566-43d5-41ce-8c8a-ce360af9995b")
    def test_create_node(self):
        self._microversion_test(
            BaremetalClient.create_node,
            "1.1",
            lib_exc.NotAcceptable,
            {"chassis_id": self.chassis["uuid"]},
            ignore_positive=True
        )

    @decorators.idempotent_id("3ddd0ae9-979b-44ac-9cdc-2cabd2f61118")
    def test_list_nodes(self):
        self._microversion_test(
            BaremetalClient.list_nodes, "1.1", lib_exc.NotAcceptable, {}
        )

    @decorators.idempotent_id("d47160dd-654e-427b-91b0-9a4298a7ff54")
    def test_list_nodes_detail(self):
        self._microversion_test(
            BaremetalClient.list_nodes_detail, "1.1", lib_exc.NotAcceptable, {}
        )

    @decorators.idempotent_id("a612b489-d4c6-4f29-9dcd-ca7a71d93f77")
    def test_show_node(self):
        _, node = self.create_node(self.chassis["uuid"])
        self._microversion_test(
            BaremetalClient.show_node,
            "1.1",
            lib_exc.NotAcceptable,
            {"uuid": node["uuid"]},
        )
        # delete the node
        self.client.delete_node(node["uuid"])

    @decorators.idempotent_id("02623737-84f5-42f1-a8f3-0f3a8c1319da")
    def test_update_node(self):
        _, node = self.create_node(self.chassis["uuid"])
        instance_uuid = data_utils.rand_uuid()
        self._microversion_test(
            BaremetalClient.update_node,
            "1.1",
            lib_exc.NotAcceptable,
            {"uuid": node["uuid"], "patch": instance_uuid},
        )
        # delete the node
        self.client.delete_node(node["uuid"])

    @decorators.idempotent_id("59f433f1-05b8-47a9-b14a-f4aba337698d")
    def test_delete_node(self):
        _, node = self.create_node(self.chassis["uuid"])
        self._microversion_test(
            BaremetalClient.delete_node,
            "1.1",
            lib_exc.NotAcceptable,
            {"uuid": node["uuid"]},
        )


class TestNodeManagementMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for node management-related API microversion enforcement."""

    min_microversion = "1.1"

    def setUp(self):
        super(TestNodeManagementMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis["uuid"])

    def _validate_provision_state(self, node_uuid, target_state):
        # Validate that provision state is set within timeout
        start = timeutils.utcnow()
        while timeutils.delta_seconds(
                start, timeutils.utcnow()) < self.unprovision_timeout:
            _, node = self.client.show_node(node_uuid)
            if node['provision_state'] == target_state:
                return
        message = ('Failed to set provision state %(state)s within '
                   'the required time: %(timeout)s sec.',
                   {'state': target_state,
                    'timeout': self.unprovision_timeout})
        raise lib_exc.TimeoutException(message)

    @decorators.idempotent_id("54a58e1e-8334-4152-84b4-2974cabb74e8")
    def test_validate_driver_interface(self):
        self._microversion_test(
            BaremetalClient.validate_driver_interface,
            "1.1",
            lib_exc.NotAcceptable,
            {"node_uuid": self.node["uuid"]},
        )

    @decorators.idempotent_id("9adfa595-8937-4a99-83e5-6012ddcbddc0")
    def test_set_node_power_state(self):
        self._microversion_test(
            BaremetalClient.set_node_power_state,
            "1.1",
            lib_exc.NotAcceptable,
            {"node_uuid": self.node["uuid"], "state": "power off"},
        )

    @decorators.idempotent_id("efd978ce-2ce5-4dc3-8f69-ff063644a550")
    def test_set_node_provision_state(self):
        contd = self._microversion_test(
            BaremetalClient.set_node_provision_state,
            "1.1",
            lib_exc.NotAcceptable,
            {"node_uuid": self.node["uuid"], "state": "manageable"},
        )

        if contd:
            self._validate_provision_state(self.node["uuid"], "manageable")

    @decorators.idempotent_id("893e4815-2c55-40f6-84e3-1816e28f6803")
    def test_set_node_raid_config(self):
        self._microversion_test(
            BaremetalClient.set_node_raid_config,
            "1.12",
            lib_exc.NotAcceptable,
            {"node_uuid": self.node["uuid"], "target_raid_config": {}},
        )

    @decorators.idempotent_id("f6b835da-dea3-46b2-8e16-6f910ad7cc86")
    def test_get_console(self):
        self._microversion_test(
            BaremetalClient.get_console,
            "1.1",
            lib_exc.NotAcceptable,
            {"node_uuid": self.node["uuid"]},
        )

    @decorators.idempotent_id("2dc96b6b-5713-467d-9707-389292ae5460")
    def test_set_console_mode(self):
        self._microversion_test(
            BaremetalClient.set_console_mode,
            "1.1",
            lib_exc.NotAcceptable,
            {"node_uuid": self.node["uuid"], "enabled": True},
        )

    @decorators.idempotent_id("4b4e23ae-3d18-4f35-a140-d10abcf22110")
    def test_set_node_boot_device(self):
        self._microversion_test(
            BaremetalClient.set_node_boot_device,
            "1.1",
            lib_exc.NotAcceptable,
            {"node_uuid": self.node["uuid"], "boot_device": "pxe"},
        )

    @decorators.idempotent_id("f13b398e-cde1-4862-a183-f20eb56d3234")
    def test_get_node_boot_device(self):
        self._microversion_test(
            BaremetalClient.get_node_boot_device,
            "1.1",
            lib_exc.NotAcceptable,
            {"node_uuid": self.node["uuid"]},
        )

    @decorators.idempotent_id("88985d9e-ccd1-4894-bc5d-e712ce29b892")
    def test_get_node_supported_boot_devices(self):
        self._microversion_test(
            BaremetalClient.get_node_supported_boot_devices,
            "1.1",
            lib_exc.NotAcceptable,
            {"node_uuid": self.node["uuid"]},
        )


class TestNodeVMediaMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for node vmedia-related API microversion enforcement."""

    min_microversion = "1.89"

    def setUp(self):
        super(TestNodeVMediaMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis["uuid"])

    @decorators.idempotent_id("305c0689-c43b-407c-8b78-932ff86e4b3d")
    def test_attach_node_vmedia(self):
        self._microversion_test(
            BaremetalClient._put_request,
            "1.89",
            lib_exc.NotFound,
            {
                "resource": f"nodes/{self.node['uuid']}/vmedia",
                "put_object": {
                    "device_type": "CDROM", "image_url": "http://image"
                },
            },
        )

    @decorators.idempotent_id("1d4d15bb-a66c-47f9-bf41-cc5e09854bcc")
    def test_detach_node_vmedia(self):
        self._microversion_test(
            BaremetalClient._delete_request,
            "1.89",
            lib_exc.NotFound,
            {"resource": f"nodes/{self.node['uuid']}/vmedia", "uuid": ""},
        )


class TestNodeVendorPassthruMethodsMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for node vendor passthru methods API microversion enforcement."""

    min_microversion = "1.1"

    def setUp(self):
        super(TestNodeVendorPassthruMethodsMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis["uuid"])

    @decorators.idempotent_id("8599e266-debc-4548-af5a-cd2223a5e051")
    def test_list_vendor_passthru_methods(self):
        self._microversion_test(
            BaremetalClient.list_vendor_passthru_methods,
            "1.1",
            lib_exc.NotAcceptable,
            {"node_uuid": self.node["uuid"]},
        )


class TestNodeVendorPassthruCallMethodMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for vendor passthru call method API microversion"""

    min_microversion = "1.1"

    def setUp(self):
        super(TestNodeVendorPassthruCallMethodMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis["uuid"])

    @decorators.idempotent_id("35b34e5d-78d4-49e6-81b3-48b536f9fb60")
    def test_call_vendor_passthru_method(self):
        self._microversion_test(
            BaremetalClient._put_request,
            "1.1",
            lib_exc.NotAcceptable,
            {
                "resource": f"nodes/{self.node['uuid']}/vendor_passthru",
                "put_object": {"method": "fakemethod"},
            },
        )


class TestNodeTraitsMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for node traits-related API microversion enforcement."""

    min_microversion = "1.37"

    def setUp(self):
        super(TestNodeTraitsMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis["uuid"])
        self.traits = ["CUSTOM_TRAIT1", "HW_CPU_X86_VMX"]

    @decorators.idempotent_id("3f4ba6c1-5b39-4cb1-a823-21dcea802d61")
    def test_list_node_traits(self):
        self._microversion_test(
            BaremetalClient.list_node_traits,
            "1.37",
            lib_exc.NotAcceptable,
            {"node_uuid": self.node["uuid"]},
        )

    @decorators.idempotent_id("10d77871-cd8a-4ecb-b6a4-f38d6ad719fe")
    def test_set_node_traits(self):
        self._microversion_test(
            BaremetalClient.set_node_traits,
            "1.37",
            lib_exc.UnexpectedResponseCode,
            {"node_uuid": self.node["uuid"], "traits": self.traits},
        )

    @decorators.idempotent_id("12ca1f62-9d4a-490c-8f8a-a10fc742630a")
    def test_add_node_trait(self):
        self._microversion_test(
            BaremetalClient.add_node_trait,
            "1.37",
            lib_exc.UnexpectedResponseCode,
            {"node_uuid": self.node["uuid"], "trait": "CUSTOM_TRAIT1"},
        )

    @decorators.idempotent_id("dd2f3b89-3fe3-4861-ba11-608b365ff484")
    def test_remove_node_traits(self):
        # add a trait to remove it
        self.client.add_node_trait(self.node["uuid"], "CUSTOM_TRAIT1")
        self._microversion_test(
            BaremetalClient.remove_node_traits,
            "1.37",
            lib_exc.NotFound,
            {"node_uuid": self.node["uuid"]},
        )

    @decorators.idempotent_id("be438903-26d0-4ee6-970e-2d6d66058842")
    def test_remove_node_trait(self):
        self.client.add_node_trait(self.node["uuid"], "CUSTOM_TRAIT1")
        self._microversion_test(
            BaremetalClient.remove_node_trait,
            "1.37",
            lib_exc.NotFound,
            {"node_uuid": self.node["uuid"], "trait": "CUSTOM_TRAIT1"},
        )


class TestNodeVIFsMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for node VIFs-related API microversion enforcement."""

    min_microversion = "1.28"

    def setUp(self):
        super(TestNodeVIFsMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis["uuid"])
        self.vif_id = uuidutils.generate_uuid()

    @decorators.idempotent_id("9b26c364-0623-4bd4-ac53-a3eca8d58fea")
    def test_list_node_vifs(self):
        self._microversion_test(
            BaremetalClient.vif_list,
            "1.28",
            lib_exc.NotFound,
            {"node_uuid": self.node["uuid"]},
        )

    @decorators.idempotent_id("4e91a305-145d-408d-9aea-08d73ef8d082")
    def test_attach_node_vif(self):
        self._microversion_test(
            BaremetalClient.vif_attach,
            "1.28",
            lib_exc.NotFound,
            {"node_uuid": self.node["uuid"], "vif_id": self.vif_id},
        )

    @decorators.idempotent_id("ce93713b-5df8-44ce-815c-c18ae0203c63")
    def test_detach_node_vif(self):
        self._microversion_test(
            BaremetalClient.vif_detach,
            "1.28",
            lib_exc.NotFound,
            {"node_uuid": self.node["uuid"], "vif_id": self.vif_id},
        )


class TestNodeIndicatorsMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for node indicators-related API microversion enforcement."""

    min_microversion = "1.1"

    def setUp(self):
        super(TestNodeIndicatorsMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis["uuid"])
        self.component = "system"
        self.ind_ident = "led"
        self.state = "ON"

    @decorators.idempotent_id("79194e54-c98d-4e55-a368-2a2ba2199844")
    def test_get_node_indicator_state(self):
        self._microversion_test(
            BaremetalClient.get_node_indicator_state,
            "1.1",
            lib_exc.NotAcceptable,
            {
                "node_uuid": self.node["uuid"],
                "component": self.component,
                "ind_ident": self.ind_ident,
            },
        )


class TestPortgroupMicroversions(BaseTestMicroversionEnforcement,
                                 MicroversionTestMixin):
    """Tests for Portgroup-related API microversion enforcement.

    Portgroup APIs (e.g. listing, creating, showing, updating and deleting)
    were introduced in microversion 1.23.
    """

    min_microversion = "1.23"

    def setUp(self):
        super(TestPortgroupMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis['uuid'])

    @decorators.idempotent_id("a8b52cdf-8471-40d7-9bc0-6ecfefa33adf")
    def test_list_portgroups(self):
        self._microversion_test(
            BaremetalClient.list_portgroups,
            "1.23",
            lib_exc.NotFound,
            {}  # Empty dict for no required args
        )

    @decorators.idempotent_id("cb5b92f0-fdb6-4789-b9b5-ae147cbe288b")
    def test_list_portgroups_detail(self):
        self._microversion_test(
            BaremetalClient.list_portgroups_detail,
            "1.23",
            lib_exc.NotFound,
            {}  # Empty dict for no required args
        )

    @decorators.idempotent_id("aafb5f2d-22e4-4b07-98c6-7f8f5f4a6699")
    def test_create_portgroup(self):
        self._microversion_test(
            BaremetalClient.create_portgroup,
            "1.23",
            lib_exc.NotFound,
            {
                "node_uuid": self.node['uuid'],
                "address": "11:11:11:11:11:11",
                "name": "test_portgroup"
            }
        )

    @decorators.idempotent_id("ea27635c-132f-4cff-9f93-b11bd4baa5a2")
    def test_show_portgroup(self):
        _, portgroup = self.client.create_portgroup(self.node['uuid'])
        self._microversion_test(
            BaremetalClient.show_portgroup,
            "1.23",
            lib_exc.NotFound,
            {"portgroup_ident": portgroup['uuid']}
        )

    @decorators.idempotent_id("48dfef1f-b95f-4767-86ee-d6257c52cefd")
    def test_update_portgroup(self):
        patch_doc = [
            {"op": "replace", "path": "/address", "value": "22:22:22:22:22:22"}
        ]
        # Need to create a portgroup to delete it
        _, portgroup = self.create_portgroup(self.node['uuid'])
        self._microversion_test(
            BaremetalClient.update_portgroup,
            "1.23",
            lib_exc.NotFound,
            {
                "uuid": portgroup['uuid'],
                "patch": patch_doc
            }
        )

    @decorators.idempotent_id("e0884cbe-bacc-4347-be14-72e475855eff")
    def test_delete_portgroup(self):
        # Need to create a portgroup to delete it
        _, portgroup = self.create_portgroup(self.node['uuid'])

        self._microversion_test(
            BaremetalClient.delete_portgroup,
            "1.23",
            lib_exc.NotFound,
            {"portgroup_ident": portgroup['uuid']}
        )


class TestPortgroupByNodeMicroversions(BaseTestMicroversionEnforcement,
                                       MicroversionTestMixin):
    """Tests for listing Portgroups by Node.

    These endpoints (e.g. /v1/nodes/{node_ident}/portgroups and
    /v1/nodes/{node_ident}/portgroups/detail) were introduced
    in microversion 1.24.
    """

    min_microversion = "1.24"

    def setUp(self):
        super(TestPortgroupByNodeMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis['uuid'])

    @decorators.idempotent_id("c967b02f-1acc-4714-98b0-07e49e9b3482")
    def test_list_portgroups_by_node(self):
        self._microversion_test(
            BaremetalClient.list_portgroups_by_node,
            "1.24",
            lib_exc.NotFound,
            {"node_ident": self.node['uuid']}
        )

    @decorators.idempotent_id("8c38415b-1aad-4519-81fb-0792ebf3731a")
    def test_list_portgroups_details_by_node(self):
        self._microversion_test(
            BaremetalClient.list_portgroups_details_by_node,
            "1.24",
            lib_exc.NotFound,
            {"node_ident": self.node['uuid']}
        )


class TestPortMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for port-related API microversion enforcement."""

    min_microversion = "1.1"

    def setUp(self):
        super(TestPortMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis["uuid"])
        random_mac = (
            f"02:00:00:{random.randint(0, 255):02x}"
            f":{random.randint(0, 255):02x}"
            f":{random.randint(0, 255):02x}"
        )

        _, self.port = self.create_port(
            self.node["uuid"], address=random_mac
        )

    @decorators.idempotent_id("99e628a4-0d10-44a1-aed5-0b82d0155103")
    def test_list_ports(self):
        self._microversion_test(
            BaremetalClient.list_ports,
            "1.1",
            lib_exc.NotAcceptable,
            {},  # Empty dict for no required args
        )

    @decorators.idempotent_id("0c01ce9a-8945-4604-b315-3f8a1856c621")
    def test_list_ports_detail(self):
        self._microversion_test(
            BaremetalClient.list_ports_detail,
            "1.1",
            lib_exc.NotAcceptable,
            {},  # Empty dict for no required args
        )

    @decorators.idempotent_id("15b3f4d5-d8ca-44af-b0fe-75f9a86896b1")
    def test_create_port(self):
        self._microversion_test(
            BaremetalClient.create_port,
            "1.1",
            lib_exc.NotAcceptable,
            {
                "node_id": self.node["uuid"],
                "address": "11:11:11:11:11:11",
            },
        )

    @decorators.idempotent_id("637f088f-1460-46c4-a3cf-3568c1997461")
    def test_show_port(self):
        self._microversion_test(
            BaremetalClient.show_port,
            "1.1",
            lib_exc.NotAcceptable,
            {"uuid": "fake_port"},
        )

    @decorators.idempotent_id("5cf7930d-3e0b-44f7-b9b8-a941dea2782e")
    def test_update_port(self):
        patch_doc = [
            {"op": "replace", "path": "/address", "value": "22:22:22:22:22:22"}
        ]
        self._microversion_test(
            BaremetalClient.update_port,
            "1.1",
            lib_exc.NotAcceptable,
            {"uuid": self.port["uuid"], "patch": patch_doc},
        )

    @decorators.idempotent_id("b5d92c53-9d2e-485f-ac6c-1e0d020d5af3")
    def test_delete_port(self):
        self._microversion_test(
            BaremetalClient.delete_port,
            "1.1",
            lib_exc.NotAcceptable,
            {"uuid": self.port["uuid"]},
        )


class TestNodePortsMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for listing Ports by Node API microversion enforcement."""

    min_microversion = "1.1"

    def setUp(self):
        super(TestNodePortsMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis["uuid"])

    @decorators.idempotent_id("7a0acf09-d527-4d77-92bd-3eac81687bc7")
    def test_list_ports_by_node(self):
        self._microversion_test(
            BaremetalClient.list_node_ports,
            "1.1",
            lib_exc.NotAcceptable,
            {"uuid": self.node["uuid"]},
        )

    @decorators.idempotent_id("df017231-a8d3-4b6b-8583-0e6fbf61e834")
    def test_list_ports_details_by_node(self):
        self._microversion_test(
            BaremetalClient.list_node_ports,
            "1.1",
            lib_exc.NotAcceptable,
            {"uuid": self.node["uuid"]},
        )


class TestPortgroupPortsMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for listing Ports by Portgroup API microversion enforcement."""

    min_microversion = "1.24"

    def setUp(self):
        super(TestPortgroupPortsMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis["uuid"])
        _, self.portgroup = self.create_portgroup(self.node["uuid"])

    @decorators.idempotent_id("bb3a1fa6-52cf-4e19-98d0-746c2421ff9a")
    def test_list_ports_by_portgroup(self):
        self._microversion_test(
            BaremetalClient.list_ports,
            "1.24",
            lib_exc.NotAcceptable,
            {"portgroup": self.portgroup["uuid"]},
        )

    @decorators.idempotent_id("6740fe09-539d-415b-bc44-f38f458f2547")
    def test_list_ports_details_by_portgroup(self):
        self._microversion_test(
            BaremetalClient.list_ports_detail,
            "1.24",
            lib_exc.NotAcceptable,
            {"portgroup": self.portgroup["uuid"]},
        )


class TestVolumeConnectorMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for volume connector-related API microversion enforcement."""

    min_microversion = "1.32"

    def setUp(self):
        super(TestVolumeConnectorMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis["uuid"])

    @decorators.idempotent_id("1bde0eb4-c63c-4d05-897d-b2247dd97863")
    def test_list_volume_connectors(self):
        self._microversion_test(
            BaremetalClient.list_volume_connectors,
            "1.32",
            lib_exc.NotFound,
            {},
        )

    @decorators.idempotent_id("7673b980-b882-45d7-bc89-8e255e2228cc")
    def test_show_volume_connector(self):
        self._microversion_test(
            BaremetalClient.show_volume_connector,
            "1.32",
            lib_exc.NotFound,
            {"volume_connector_ident": "fake_volume_connector"},
        )

    @decorators.idempotent_id("3e7d6a89-5302-4087-a10a-200b8d9dc026")
    def test_create_volume_connector(self):
        self._microversion_test(
            BaremetalClient.create_volume_connector,
            "1.32",
            lib_exc.NotFound,
            {
                "node_uuid": self.node["uuid"],
                "type": "iqn",
                "connector_id": "fake_connector_id",
            },
        )

    @decorators.idempotent_id("cca4b764-12cc-4d4d-a702-0b52ef1b0e94")
    def test_update_volume_connector(self):
        patch = [{"op": "replace", "path": "/connector_id", "value": "new_id"}]
        self._microversion_test(
            BaremetalClient.update_volume_connector,
            "1.32",
            lib_exc.NotFound,
            {"uuid": "fake_volume_connector", "patch": patch},
        )

    @decorators.idempotent_id("e05e85d1-da6b-43b6-adc4-5e4bc8e4c72d")
    def test_delete_volume_connector(self):
        self._microversion_test(
            BaremetalClient.delete_volume_connector,
            "1.32",
            lib_exc.NotFound,
            {"volume_connector_ident": "fake_volume_connector"},
        )


class TestVolumeTargetMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for volume target-related API microversion enforcement."""

    min_microversion = "1.32"

    def setUp(self):
        super(TestVolumeTargetMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis["uuid"])

    @decorators.idempotent_id("c7511a8a-4d6b-4439-bfb1-c659808c0967")
    def test_list_volume_targets(self):
        self._microversion_test(
            BaremetalClient.list_volume_targets, "1.32", lib_exc.NotFound, {}
        )

    @decorators.idempotent_id("ddb8223e-2f63-4a74-aa2f-229a522ae3e8")
    def test_show_volume_target(self):
        self._microversion_test(
            BaremetalClient.show_volume_target,
            "1.32",
            lib_exc.NotFound,
            {"volume_target_ident": "fake_volume_target"},
        )

    @decorators.idempotent_id("3fb1e9c5-8154-4308-a765-393ab80762c8")
    def test_create_volume_target(self):
        self._microversion_test(
            BaremetalClient.create_volume_target,
            "1.32",
            lib_exc.NotFound,
            {
                "node_uuid": self.node["uuid"],
                "volume_type": "iscsi",
                "volume_id": "fake_volume_id",
                "boot_index": 0,
            },
        )

    @decorators.idempotent_id("16d83cd1-0425-4e28-bfd4-33199e5a87c7")
    def test_update_volume_target(self):
        patch = [{"op": "replace", "path": "/volume_id", "value": "new_id"}]
        self._microversion_test(
            BaremetalClient.update_volume_target,
            "1.32",
            lib_exc.NotFound,
            {"uuid": "fake_volume_target", "patch": patch},
        )

    @decorators.idempotent_id("697b67be-ccc5-4a7b-99ca-276e5e8c931a")
    def test_delete_volume_target(self):
        self._microversion_test(
            BaremetalClient.delete_volume_target,
            "1.32",
            lib_exc.NotFound,
            {"volume_target_ident": "fake_volume_target"},
        )


class TestNodeVolumeMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for node volume-related API microversion enforcement."""

    min_microversion = "1.32"

    def setUp(self):
        super(TestNodeVolumeMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis["uuid"])

    @decorators.idempotent_id("2ff700e6-4914-4eed-8342-308a6f2134a5")
    def test_list_node_volume(self):
        self._microversion_test(
            BaremetalClient._list_request,
            "1.32",
            lib_exc.NotFound,
            {"resource": f"nodes/{self.node['uuid']}/volume"},
        )

    @decorators.idempotent_id("3e56f64f-6bac-4126-ba7d-d89275318975")
    def test_list_node_volume_connectors(self):
        self._microversion_test(
            BaremetalClient._list_request,
            "1.32",
            lib_exc.NotFound,
            {"resource": f"nodes/{self.node['uuid']}/volume/connectors"},
        )

    @decorators.idempotent_id("060008fe-d478-49d2-bdf0-d327f1e360a5")
    def test_list_node_volume_targets(self):
        self._microversion_test(
            BaremetalClient._list_request,
            "1.32",
            lib_exc.NotFound,
            {"resource": f"nodes/{self.node['uuid']}/volume/targets"},
        )


class TestDriverMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for driver-related API microversion enforcement."""

    min_microversion = "1.1"

    @decorators.idempotent_id("c5f179c9-3b8a-49c6-bee0-734979d544bc")
    def test_list_drivers(self):
        self._microversion_test(
            BaremetalClient.list_drivers, "1.1", lib_exc.NotAcceptable, {}
        )

    @decorators.idempotent_id("f79931be-dc7b-4e60-89ce-90a4e2793714")
    def test_show_driver(self):
        self._microversion_test(
            BaremetalClient.show_driver,
            "1.1",
            lib_exc.NotAcceptable,
            {"driver_name": "testdriver"},
        )

    @decorators.idempotent_id("daef2f42-e343-4640-a5d4-d8938e956ddb")
    def test_show_driver_properties(self):
        self._microversion_test(
            BaremetalClient.get_driver_properties,
            "1.1",
            lib_exc.NotAcceptable,
            {"driver_name": "testdriver"},
        )

    @decorators.idempotent_id("bade310a-0699-4470-8da3-6f8ae26e9d71")
    def test_show_driver_logical_disk_properties(self):
        self._microversion_test(
            BaremetalClient.get_driver_logical_disk_properties,
            "1.12",
            lib_exc.NotAcceptable,
            {"driver_name": "testdriver"},
        )


class TestDriverVendorPassthruMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for driver vendor passthru API microversion enforcement."""

    min_microversion = "1.1"

    @decorators.idempotent_id("27c0157d-758a-40c9-b0fd-bde05ed8a6fc")
    def test_list_vendor_passthru_methods(self):
        self._microversion_test(
            BaremetalClient.list_vendor_passthru_methods,
            "1.1",
            lib_exc.NotAcceptable,
            {"node_uuid": "fake_node"},
        )


class TestNodeBiosMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for node bios-related API microversion enforcement."""

    min_microversion = "1.40"

    def setUp(self):
        super(TestNodeBiosMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis["uuid"])

    @decorators.idempotent_id("126de288-71f9-4e4f-8591-6ddfc9ac3095")
    def test_list_node_bios(self):
        self._microversion_test(
            BaremetalClient.list_node_bios_settings,
            "1.40",
            lib_exc.NotFound,
            {"uuid": self.node["uuid"]},
        )


class TestNodeBiosDetailsMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for node bios details API microversion enforcement."""

    min_microversion = "1.40"

    def setUp(self):
        super(TestNodeBiosDetailsMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis["uuid"])

    @decorators.idempotent_id("68583cd5-63d0-4bda-a836-9bda6d5b2ab4")
    def test_list_node_bios_details(self):
        self._microversion_test(
            BaremetalClient.list_node_bios_settings,
            "1.40",
            lib_exc.NotFound,
            {"uuid": self.node["uuid"]},
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


class TestConductorMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):

    min_microversion = "1.49"

    def setUp(self):
        super(TestConductorMicroversions, self).setUp()

    @decorators.idempotent_id("412fde59-afe7-442d-83c9-538c87b95687")
    def test_list_conductors(self):
        self._microversion_test(
            BaremetalClient.list_conductors, "1.49", lib_exc.NotFound, {}
        )

    @decorators.idempotent_id("ad496ff6-2d6e-4e63-9c64-60c5184a18a7")
    def test_show_conductor(self):
        _, conductors = self.client.list_conductors()
        self.assertTrue(len(conductors['conductors']) > 0)
        conductor = conductors['conductors'].pop()

        _, conductor = self.client.show_conductor(conductor['hostname'])
        self._microversion_test(
            BaremetalClient.show_conductor,
            "1.49",
            lib_exc.NotFound,
            {"hostname": conductor['hostname']},
        )


class TestAllocationMicroversions(
        BaseTestMicroversionEnforcement,
        MicroversionTestMixin):
    """Tests for allocation-related API microversion enforcement."""

    min_microversion = "1.52"

    @decorators.idempotent_id('ef7bd40a-c1ef-4d40-a0b6-f388d23943c3')
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


class TestNodeAllocationMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for node allocation-related API microversion enforcement."""

    min_microversion = "1.52"

    def setUp(self):
        super(TestNodeAllocationMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis["uuid"])

    @decorators.idempotent_id("9b170cac-18f7-4a17-be2e-314b548244ba")
    def test_show_allocation_by_node(self):
        _, body = self.create_allocation(self.resource_class)

        self._microversion_test(
            BaremetalClient.show_node_allocation,
            "1.52",
            lib_exc.NotFound,
            {"node_ident": body["node_uuid"]},
        )


class TestDeployTemplateMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for deploy template-related API microversion enforcement."""

    min_microversion = "1.55"

    def setUp(self):
        super(TestDeployTemplateMicroversions, self).setUp()
        self.deploy_template_name = "CUSTOM_TEMPLATE_123"
        self.steps = [
            {
                "interface": "bios",
                "step": "apply_configuration",
                "args": {
                    "settings": [
                        {"name": "LogicalProc", "value": "Enabled"}
                    ]
                },
                "priority": 150,
            }
        ]

    @decorators.idempotent_id("52806f1d-d64a-4b7f-a799-e623ecc09bda")
    def test_create_deploy_template(self):
        self._microversion_test(
            BaremetalClient.create_deploy_template,
            "1.55",
            lib_exc.UnexpectedResponseCode,
            {"name": self.deploy_template_name, "steps": self.steps},
        )

    @decorators.idempotent_id("1a3bb543-faa9-4da6-a1c4-20cb8177f53d")
    def test_list_deploy_templates(self):
        self._microversion_test(
            BaremetalClient.list_deploy_templates, "1.55", lib_exc.NotFound, {}
        )

    @decorators.idempotent_id("a0933551-8569-4638-acd4-fad0a9daefd9")
    def test_show_deploy_template(self):
        _, deploy_template = self.client.create_deploy_template(
            "CUSTOM_TEMPLATE_456", steps=self.steps
        )
        self._microversion_test(
            BaremetalClient.show_deploy_template,
            "1.55",
            lib_exc.NotFound,
            {"deploy_template_ident": deploy_template["uuid"]},
        )

    @decorators.idempotent_id("f47a12a7-71b7-4ff0-ab17-9f45c9ac68e7")
    def test_update_deploy_template(self):
        patch = [{"op": "replace", "path": "/name", "value": "new_name"}]
        self._microversion_test(
            BaremetalClient.update_deploy_template,
            "1.55",
            lib_exc.UnexpectedResponseCode,
            {"deploy_template_ident": "fakedt", "patch": patch},
        )

    @decorators.idempotent_id("b987a887-22ca-4ec9-a074-0a9bd3eac7ac")
    def test_delete_deploy_template(self):
        self._microversion_test(
            BaremetalClient.delete_deploy_template,
            "1.55",
            lib_exc.UnexpectedResponseCode,
            {"deploy_template_ident": "fakedt"},
        )


class TestRunbookMicroversions(BaseTestMicroversionEnforcement,
                               MicroversionTestMixin):
    """Tests for runbook-related API microversion enforcement.

    The runbook API was introduced in microversion 1.92. Operations such as
    creating, updating, and deleting runbooks are expected to fail with an
    error if used with an unsupported microversion.
    """

    min_microversion = "1.92"

    @decorators.idempotent_id("e37be789-fcdf-435a-8a16-3d2f8f21e6e2")
    def test_create_runbook(self):
        # Define a minimal valid runbook payload.
        steps = [
            {
                "interface": "bios",
                "step": "apply_configuration",
                "order": 1,
                "args": {
                    "settings": [
                        {"name": "LogicalProc", "value": "Enabled"}
                    ]
                }
            }
        ]
        self._microversion_test(
            BaremetalClient.create_runbook,
            "1.92",
            lib_exc.UnexpectedResponseCode,
            {"name": "CUSTOM_TEST", "steps": steps}
        )

    @decorators.idempotent_id("f1b5b500-6b9c-41f6-bb99-3a77e3bd6ac4")
    def test_list_runbooks(self):
        self._microversion_test(
            BaremetalClient.list_runbooks,
            "1.92",
            lib_exc.NotFound,
            {}
        )

    @decorators.idempotent_id("3d12345a-3d56-4fbb-afd2-7bd0ebc32e19")
    def test_show_runbook(self):
        steps = [
            {
                "interface": "bios",
                "step": "apply_configuration",
                "order": 1,
                "args": {
                    "settings": [
                        {"name": "LogicalProc", "value": "Enabled"}
                    ]
                }
            }
        ]
        _, runbook = self.client.create_runbook("CUSTOM_TEST_2", steps=steps)
        self._microversion_test(
            BaremetalClient.show_runbook,
            "1.92",
            lib_exc.NotFound,
            {"runbook_ident": runbook['uuid']}
        )

    @decorators.idempotent_id("a1e4cd23-56be-4b39-b756-9a9b73f21492")
    def test_update_runbook(self):
        # Using an example JSON PATCH document to update the runbook.
        patch_doc = [
            {"op": "replace", "path": "/name", "value": "CUSTOM_TEST2"}
        ]
        self._microversion_test(
            BaremetalClient.update_runbook,
            "1.92",
            lib_exc.UnexpectedResponseCode,
            {"runbook_ident": "fake_runbook", "patch": patch_doc}
        )

    @decorators.idempotent_id("cb9cf9a6-2a3f-4aa7-9488-098f8aeeb5d9")
    def test_delete_runbook(self):
        self._microversion_test(
            BaremetalClient.delete_runbook,
            "1.92",
            lib_exc.UnexpectedResponseCode,
            {"runbook_ident": "fake_runbook"}
        )


class TestNodeHistoryMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for node history-related API microversion enforcement."""

    min_microversion = "1.78"

    def setUp(self):
        super(TestNodeHistoryMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis["uuid"])

    @decorators.idempotent_id("aea6cb45-6519-44d9-a33e-aab7cd72d769")
    def test_list_node_history(self):
        self._microversion_test(
            BaremetalClient.list_node_history,
            "1.78",
            lib_exc.NotFound,
            {"node_uuid": self.node["uuid"]},
        )


# NOTE(adamcarthur) - The positive test for this will need a configured
# node to have history.
class TestNodeInventoryMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for node inventory-related API microversion enforcement."""

    min_microversion = "1.81"

    def setUp(self):
        super(TestNodeInventoryMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis["uuid"])

    @decorators.idempotent_id("ca557dca-9b3e-44cb-a101-f31d58a0dedd")
    def test_show_node_inventory(self):
        _, node = self.client.show_node(self.node['uuid'])
        self._microversion_test(
            BaremetalClient.show_inventory,
            "1.81",
            lib_exc.NotFound,
            {"uuid": node["uuid"]},
            ignore_positive=True
        )


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


class TestChassisMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for chassis-related API microversion enforcement."""

    min_microversion = "1.1"

    def setUp(self):
        super(TestChassisMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()

    @decorators.idempotent_id("59c20dbf-280e-4148-ac8e-be3b8d75d021")
    def test_create_chassis(self):
        self._microversion_test(
            BaremetalClient.create_chassis, "1.1", lib_exc.NotAcceptable, {}
        )

    @decorators.idempotent_id("0e840e17-5659-4ad9-a218-84b14bc8b013")
    def test_list_chassis(self):
        self._microversion_test(
            BaremetalClient.list_chassis, "1.1", lib_exc.NotAcceptable, {}
        )

    @decorators.idempotent_id("6c3a5728-0d96-41aa-a3ca-295bfbbe341e")
    def test_show_chassis(self):
        self._microversion_test(
            BaremetalClient.show_chassis,
            "1.1",
            lib_exc.NotAcceptable,
            {"uuid": self.chassis["uuid"]},
        )

    @decorators.idempotent_id("7ae8ca94-b7d9-4975-87c6-37d89779b8b5")
    def test_update_chassis(self):
        patch = [
            {"op": "replace", "path": "/description", "value": "new_desc"}
        ]
        self._microversion_test(
            BaremetalClient.update_chassis,
            "1.1",
            lib_exc.NotAcceptable,
            {"uuid": self.chassis["uuid"], "patch": patch},
        )

    @decorators.idempotent_id("f6d70a3a-9212-46af-bb7b-c95a3043a722")
    def test_delete_chassis(self):
        self._microversion_test(
            BaremetalClient.delete_chassis,
            "1.1",
            lib_exc.NotAcceptable,
            {"uuid": self.chassis["uuid"]},
        )


class TestUtilityMicroversions(
    BaseTestMicroversionEnforcement, MicroversionTestMixin
):
    """Tests for utility-related API microversion enforcement."""

    min_microversion = "1.22"

    def setUp(self):
        super(TestUtilityMicroversions, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis["uuid"])
        self.callback_url = "http://example.com/callback"
        self.agent_version = "1.0"
        self.agent_token = "test_token"

    @decorators.idempotent_id("dd2b17d9-c847-49bd-acfd-b3d63ae59f2f")
    def test_ipa_heartbeat(self):
        self._microversion_test(
            BaremetalClient.ipa_heartbeat,
            "1.22",
            lib_exc.NotFound,
            {
                "node_uuid": self.node["uuid"],
                "callback_url": self.callback_url,
                "agent_version": self.agent_version,
                "agent_token": self.agent_token,
            },
        )
