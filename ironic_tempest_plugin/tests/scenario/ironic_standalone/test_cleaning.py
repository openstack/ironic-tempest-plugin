#
# Copyright 2017 Mirantis Inc.
#
# Copyright (c) 2022 Dell Inc. or its subsidiaries.
#
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

import json
import os

import jsonschema
from jsonschema import exceptions as json_schema_exc
from oslo_log import log as logging
from tempest.common import utils
from tempest import config
from tempest.lib import decorators

from ironic_tempest_plugin import exceptions
from ironic_tempest_plugin.tests.scenario import \
    baremetal_standalone_manager as bsm

LOG = logging.getLogger(__name__)
CONF = config.CONF


class BaremetalCleaningAgentIpmitoolWholedisk(
        bsm.BaremetalStandaloneScenarioTest):

    driver = 'agent_ipmitool'
    image_ref = CONF.baremetal.whole_disk_image_ref
    wholedisk_image = True
    delete_node = False
    api_microversion = '1.28'

    @decorators.idempotent_id('0d82cedd-9697-4cf7-8e4a-80d510f53615')
    @utils.services('image', 'network')
    def test_manual_cleaning(self):
        self.check_manual_partition_cleaning(self.node)


class BaremetalCleaningPxeIpmitoolWholedisk(
        bsm.BaremetalStandaloneScenarioTest):

    driver = 'pxe_ipmitool'
    image_ref = CONF.baremetal.whole_disk_image_ref
    wholedisk_image = True
    delete_node = False
    api_microversion = '1.28'

    @decorators.idempotent_id('fb03abfa-cdfc-41ec-aaa8-c70402786a85')
    @utils.services('image', 'network')
    def test_manual_cleaning(self):
        self.check_manual_partition_cleaning(self.node)


class BaremetalCleaningIpmiWholedisk(
        bsm.BaremetalStandaloneScenarioTest):

    driver = 'ipmi'
    image_ref = CONF.baremetal.whole_disk_image_ref
    wholedisk_image = True
    delete_node = False
    deploy_interface = 'iscsi'
    api_microversion = '1.31'

    @classmethod
    def skip_checks(cls):
        super(BaremetalCleaningIpmiWholedisk, cls).skip_checks()
        if CONF.baremetal_feature_enabled.software_raid:
            raise cls.skipException("Cleaning is covered in the RAID test")

    @decorators.idempotent_id('065238db-1b6d-4d75-a9da-c240f8cbd956')
    @utils.services('image', 'network')
    def test_manual_cleaning(self):
        self.check_manual_partition_cleaning(self.node)


class SoftwareRaidIscsi(bsm.BaremetalStandaloneScenarioTest):

    if 'redfish' in CONF.baremetal.enabled_hardware_types:
        driver = 'redfish'
    else:
        driver = 'ipmi'
    image_ref = CONF.baremetal.whole_disk_image_ref
    wholedisk_image = True
    deploy_interface = 'iscsi'
    raid_interface = 'agent'
    api_microversion = '1.55'
    # Software RAID is always local boot
    boot_option = 'local'
    delete_node = False

    raid_config = {
        "logical_disks": [
            {
                "size_gb": "MAX",
                "raid_level": "1",
                "controller": "software"
            },
        ]
    }

    @classmethod
    def skip_checks(cls):
        super(SoftwareRaidIscsi, cls).skip_checks()
        if cls.driver == 'ipmi':
            raise cls.skipException("Testing with redfish driver")
        if not CONF.baremetal_feature_enabled.software_raid:
            raise cls.skipException("Software RAID feature is not enabled")

    @decorators.idempotent_id('7ecba4f7-98b8-4ea1-b95e-3ec399f46798')
    @utils.services('image', 'network')
    def test_software_raid(self):
        self.build_raid_and_verify_node(
            deploy_time=CONF.baremetal_feature_enabled.deploy_time_raid)
        # NOTE(TheJulia): tearing down/terminating the instance does not
        # remove the root device hint, so it is best for us to go ahead
        # and remove it before exiting the test.
        self.remove_root_device_hint()
        self.terminate_node(self.node['uuid'], force_delete=True)


class SoftwareRaidDirect(bsm.BaremetalStandaloneScenarioTest):

    if 'redfish' in CONF.baremetal.enabled_hardware_types:
        driver = 'redfish'
    else:
        driver = 'ipmi'
    image_ref = CONF.baremetal.whole_disk_image_ref
    wholedisk_image = True
    deploy_interface = 'direct'
    raid_interface = 'agent'
    api_microversion = '1.55'
    # Software RAID is always local boot
    boot_option = 'local'
    delete_node = False

    # TODO(dtantsur): more complex layout in this job
    raid_config = {
        "logical_disks": [
            {
                "size_gb": "MAX",
                "raid_level": "1",
                "controller": "software"
            },
        ]
    }

    @classmethod
    def skip_checks(cls):
        super(SoftwareRaidDirect, cls).skip_checks()
        if cls.driver == 'redfish':
            raise cls.skipException("Testing with ipmi driver")
        if not CONF.baremetal_feature_enabled.software_raid:
            raise cls.skipException("Software RAID feature is not enabled")

    @decorators.idempotent_id('125361ac-0eb3-4d79-8be2-a91936aa3f46')
    @utils.services('image', 'network')
    def test_software_raid(self):
        self.build_raid_and_verify_node(
            deploy_time=CONF.baremetal_feature_enabled.deploy_time_raid)
        # NOTE(TheJulia): tearing down/terminating the instance does not
        # remove the root device hint, so it is best for us to go ahead
        # and remove it before exiting the test.
        self.remove_root_device_hint()
        self.terminate_node(self.node['uuid'], force_delete=True)


class BaremetalIdracManagementCleaning(
        bsm.BaremetalStandaloneScenarioTest):

    mandatory_attr = ['driver', 'management_interface',
                      'power_interface']

    driver = 'idrac'
    delete_node = False
    # Minimum version for manual cleaning is 1.15 (# v1.15: Add ability to
    # do manual cleaning of nodes). The test cases clean up at the end by
    # detaching the VIF. Support for VIFs was introduced by version 1.28
    # (# v1.28: Add vifs subcontroller to node).
    api_microversion = '1.28'

    @decorators.idempotent_id('d085ff72-abef-4931-a5b0-06efd5f9a037')
    def test_reset_idrac(self):
        clean_steps = [
            {
                "interface": "management",
                "step": "reset_idrac"
            }
        ]
        self.manual_cleaning(self.node, clean_steps=clean_steps)

    @decorators.idempotent_id('9252ec6f-6b5b-447e-a323-c52775b88b4e')
    def test_clear_job_queue(self):
        clean_steps = [
            {
                "interface": "management",
                "step": "clear_job_queue"
            }
        ]
        self.manual_cleaning(self.node, clean_steps=clean_steps)

    @decorators.idempotent_id('7baeff52-7d6e-4dea-a48f-a85a6bfc9f62')
    def test_known_good_state(self):
        clean_steps = [
            {
                "interface": "management",
                "step": "known_good_state"
            }
        ]
        self.manual_cleaning(self.node, clean_steps=clean_steps)


class BaremetalIdracRedfishManagementCleaning(
        BaremetalIdracManagementCleaning):

    management_interface = 'idrac-redfish'
    power_interface = 'idrac-redfish'


class BaremetalIdracWSManManagementCleaning(
        BaremetalIdracManagementCleaning):

    management_interface = 'idrac-wsman'
    power_interface = 'idrac-wsman'


class BaremetalIdracRaidCleaning(bsm.BaremetalStandaloneScenarioTest):

    mandatory_attr = ['driver', 'raid_interface']
    image_ref = CONF.baremetal.whole_disk_image_ref
    wholedisk_image = True
    storage_inventory_info = None
    driver = 'idrac'
    api_microversion = '1.31'  # to set raid_interface
    delete_node = False

    @classmethod
    def skip_checks(cls):
        """Validates the storage information passed in file using JSON schema.

        :raises: skipException if,
            1) storage inventory path is not provided in tempest execution
            file.
            2) storage inventory file is not found on given path.
        :raises: RaidCleaningInventoryValidationFailed if,
            validation of the storage inventory fails.
        """
        super(BaremetalIdracRaidCleaning, cls).skip_checks()
        storage_inventory = CONF.baremetal.storage_inventory_file
        if not storage_inventory:
            raise cls.skipException("Storage inventory file path missing "
                                    "in tempest configuration file. "
                                    "Skipping Test case.")
        try:
            with open(storage_inventory, 'r') as storage_invent_fobj:
                cls.storage_inventory_info = json.load(storage_invent_fobj)
        except IOError:
            msg = ("Storage Inventory file %(inventory)s is not found. "
                   "Skipping Test Case." %
                   {'inventory': storage_inventory})
            raise cls.skipException(msg)
        storage_inventory_schema = os.path.join(os.path.dirname(
            __file__), 'storage_inventory_schema.json')
        with open(storage_inventory_schema, 'r') as storage_schema_fobj:
            schema = json.load(storage_schema_fobj)
        try:
            jsonschema.validate(cls.storage_inventory_info, schema)
        except json_schema_exc.ValidationError as e:
            error_msg = ("Storage Inventory validation error: %(error)s " %
                         {'error': e})
            raise exceptions.RaidCleaningInventoryValidationFailed(error_msg)

    def _validate_raid_type_and_drives_count(self, raid_type,
                                             minimum_drives_required):
        for controller in (self.storage_inventory_info[
                           'storage_inventory']['controllers']):
            supported_raid_types = controller['supported_raid_types']
            physical_disks = [pdisk['id'] for pdisk in (
                controller['drives'])]
            if raid_type in supported_raid_types and (
                    minimum_drives_required <= len(physical_disks)):
                return controller
        error_msg = ("No Controller present in storage inventory which "
                     "supports RAID type %(raid_type)s "
                     "and has at least %(disk_count)s drives." %
                     {'raid_type': raid_type,
                      'disk_count': minimum_drives_required})
        raise exceptions.RaidCleaningInventoryValidationFailed(error_msg)

    @decorators.idempotent_id('8a908a3c-f2af-48fb-8553-9163715aa403')
    @utils.services('image', 'network')
    def test_hardware_raid(self):
        controller = self._validate_raid_type_and_drives_count(
            raid_type='1', minimum_drives_required=2)
        raid_config = {
            "logical_disks": [
                {
                    "size_gb": 40,
                    "raid_level": "1",
                    "controller": controller['id']
                }
            ]
        }
        self.build_raid_and_verify_node(
            config=raid_config,
            deploy_time=CONF.baremetal_feature_enabled.deploy_time_raid,
            erase_device_metadata=False)
        self.remove_root_device_hint()
        self.terminate_node(self.node['uuid'], force_delete=True)

    @decorators.idempotent_id('92fe534d-77f1-422d-84e4-e30fe9e3d928')
    @utils.services('image', 'network')
    def test_raid_cleaning_max_size_raid_10(self):
        controller = self._validate_raid_type_and_drives_count(
            raid_type='1+0', minimum_drives_required=4)
        physical_disks = [pdisk['id'] for pdisk in (
            controller['drives'])]
        raid_config = {
            "logical_disks": [
                {
                    "size_gb": "MAX",
                    "raid_level": "1+0",
                    "controller": controller['id'],
                    "physical_disks": physical_disks
                }
            ]
        }
        self.build_raid_and_verify_node(
            config=raid_config,
            deploy_time=CONF.baremetal_feature_enabled.deploy_time_raid,
            erase_device_metadata=False)
        self.remove_root_device_hint()
        self.terminate_node(self.node['uuid'], force_delete=True)


class BaremetalIdracRedfishRaidCleaning(
        BaremetalIdracRaidCleaning):
    raid_interface = 'idrac-redfish'


class BaremetalIdracWSManRaidCleaning(
        BaremetalIdracRaidCleaning):
    raid_interface = 'idrac-wsman'


class BaremetalRedfishFirmwareUpdate(bsm.BaremetalStandaloneScenarioTest):

    api_microversion = '1.68'  # to support redfish firmware update
    driver = 'redfish'
    delete_node = False
    image_ref = CONF.baremetal.whole_disk_image_ref
    wholedisk_image = True

    @classmethod
    def skip_checks(cls):
        super(BaremetalRedfishFirmwareUpdate, cls).skip_checks()
        if not CONF.baremetal.firmware_image_url:
            raise cls.skipException("Firmware image URL is not "
                                    "provided. Skipping test case.")
        if not CONF.baremetal.firmware_image_checksum:
            raise cls.skipException("Firmware image SHA1 checksum is not "
                                    "provided. Skipping test case.")

    def _firmware_update(self, fw_image_url, fw_image_checksum):
        steps = [
            {
                "interface": "management",
                "step": "update_firmware",
                "args": {
                    "firmware_images": [
                        {
                            "url": fw_image_url,
                            "checksum": fw_image_checksum,
                            "wait": 300
                        }
                    ]
                }
            }
        ]
        self.manual_cleaning(self.node, clean_steps=steps)

    @utils.services('network')
    @decorators.idempotent_id('360e0c0e-3c17-4d2e-b052-55a932c1a4c7')
    def test_firmware_update(self):
        # WARNING: Removing power from a server while it is in the process of
        # updating firmware may result in devices in the server, or the server
        # itself becoming inoperable.
        # Execution of firmware test case needs careful execution as it
        # changes state of server, may result in break down of server on
        # interruption. As it deals with firmware of component, make sure
        # to provide proper image url path while testing with correct SHA1
        # checksum of image.
        self._firmware_update(CONF.baremetal.firmware_image_url,
                              CONF.baremetal.firmware_image_checksum)
        if (CONF.baremetal.firmware_rollback_image_url
                and CONF.baremetal.firmware_rollback_image_checksum):
            self.addCleanup(self._firmware_update,
                            CONF.baremetal.firmware_rollback_image_url,
                            CONF.baremetal.firmware_rollback_image_checksum)


class BaremetalIdracRedfishFirmwareUpdate(BaremetalRedfishFirmwareUpdate):

    driver = 'idrac'
    boot_interface = 'ipxe'
    management_interface = 'idrac-redfish'
    power_interface = 'idrac-redfish'


class BaremetalIdracRedfishConfigurationMolds(
        bsm.BaremetalStandaloneScenarioTest):

    api_microversion = '1.72'  # to support configuration molds functionality
    delete_node = False
    image_ref = CONF.baremetal.whole_disk_image_ref
    driver = 'idrac'
    boot_interface = 'ipxe'
    management_interface = 'idrac-redfish'
    power_interface = 'idrac-redfish'
    wholedisk_image = True

    @utils.services('network')
    @decorators.idempotent_id('69386cf6-bbf2-451e-b927-f68c66075f02')
    def test_configuration_molds_export(self):
        if not CONF.baremetal.export_location:
            raise self.skipException("Export configuration location path "
                                     "is not provided. Skipping test case. "
                                     "Make sure to provide correct "
                                     "configuration path in which "
                                     "configuration would be exported. "
                                     "In case of Swift object storage, "
                                     "make to sure to provide proper "
                                     "container path.")

        steps = [
            {
                "interface": "management",
                "step": "export_configuration",
                "args": {
                    "export_configuration_location":
                        CONF.baremetal.export_location
                }
            }
        ]
        self.manual_cleaning(self.node, clean_steps=steps)

    @utils.services('network')
    @decorators.idempotent_id('cad15719-c293-4338-8fa9-986ef02b4682')
    def test_configuration_molds_import(self):
        if not CONF.baremetal.import_location:
            raise self.skipException("Import configuration JSON file location "
                                     "is not provided. Make sure to provide "
                                     "correct configuration file with proper "
                                     "configuration which needs to be tested "
                                     "during execution of this test. "
                                     "Skipping test case.")
        steps = [
            {
                "interface": "management",
                "step": "import_configuration",
                "args": {
                    "import_configuration_location":
                        CONF.baremetal.import_location
                }
            }
        ]
        self.manual_cleaning(self.node, clean_steps=steps)
        if CONF.baremetal.rollback_import_location:
            rollback_steps = [
                {
                    "interface": "management",
                    "step": "import_configuration",
                    "args": {
                        "import_configuration_location":
                            CONF.baremetal.rollback_import_location
                    }
                }
            ]
            self.addCleanup(self.manual_cleaning, self.node,
                            clean_steps=rollback_steps)
