#
# Copyright 2018 Red Hat Inc.
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

from oslo_log import log as logging
from tempest import config
from tempest.lib import decorators

from ironic_tempest_plugin.tests.scenario import \
    baremetal_standalone_manager as bsm

LOG = logging.getLogger(__name__)
CONF = config.CONF


class BaremetalFakeBios(
        bsm.BaremetalStandaloneScenarioTest):

    driver = 'fake-hardware'
    bios_interface = 'fake'
    deploy_interface = 'iscsi'
    image_ref = CONF.baremetal.whole_disk_image_ref
    wholedisk_image = True
    delete_node = False
    api_microversion = '1.40'

    @decorators.idempotent_id('ef55c44a-cc10-4cf6-8fda-85f0c0793150')
    def test_bios_apply_and_reset_configuration(self):
        settings = [
            {
                "name": "setting1_name",
                "value": "setting1_value"
            },
            {
                "name": "setting2_name",
                "value": "setting2_value"
            }
        ]

        self.check_bios_apply_and_reset_configuration(self.node, settings)


class BaremetalIdracBiosCleaning(
        bsm.BaremetalStandaloneScenarioTest):

    mandatory_attr = ['driver', 'bios_interface']

    credentials = ['primary', 'admin']
    driver = 'idrac'
    delete_node = False
    api_microversion = '1.40'

    def _get_bios_setting_to_update(self):
        _, bios_settings = self.baremetal_client.\
            list_node_bios_settings(self.node['uuid'])

        for attr_name in bios_settings['bios']:
            if attr_name['name'] == "ProcVirtualization":
                if attr_name['value'] == 'Disabled':
                    new_attr_value = "Enabled"
                else:
                    new_attr_value = "Disabled"
        setting_to_update = [
            {
                "name": "ProcVirtualization",
                "value": new_attr_value
            }
        ]

        return setting_to_update

    def _verify_bios_settings(self, bios_settings_to_verify):
        _, current_bios_settings = self.baremetal_client.\
            list_node_bios_settings(self.node['uuid'])

        for setting in bios_settings_to_verify:
            found_setting = None
            for i in current_bios_settings['bios']:
                if i['name'] == setting['name']:
                    found_setting = i
                    break
            self.assertIsNotNone(found_setting)
            self.assertEqual(setting['value'], found_setting['value'])

    @decorators.idempotent_id('6ded82ab-b444-436b-bb78-06fa5957d6c3')
    def test_bios_apply_configuration(self):
        setting = self._get_bios_setting_to_update()
        clean_steps = [
            {
                "interface": "bios",
                "step": "apply_configuration",
                "args": {"settings": setting}
            }
        ]

        self.manual_cleaning(self.node, clean_steps=clean_steps)
        self._verify_bios_settings(setting)

        restore_setting = self._get_bios_setting_to_update()
        clean_steps_restore = [
            {
                "interface": "bios",
                "step": "apply_configuration",
                "args": {"settings": restore_setting}
            }
        ]

        self.manual_cleaning(self.node, clean_steps=clean_steps_restore)
        self._verify_bios_settings(restore_setting)


class BaremetalIdracRedfishBios(
        BaremetalIdracBiosCleaning):
    bios_interface = 'idrac-redfish'


class BaremetalIdracWSManBios(
        BaremetalIdracBiosCleaning):
    bios_interface = 'idrac-wsman'
