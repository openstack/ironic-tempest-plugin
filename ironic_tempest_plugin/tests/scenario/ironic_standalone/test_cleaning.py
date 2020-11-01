#
# Copyright 2017 Mirantis Inc.
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

from oslo_log import log as logging
from tempest.common import utils
from tempest import config
from tempest.lib import decorators

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
