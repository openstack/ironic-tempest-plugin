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

    @decorators.idempotent_id('065238db-1b6d-4d75-a9da-c240f8cbd956')
    @utils.services('image', 'network')
    def test_manual_cleaning(self):
        self.check_manual_partition_cleaning(self.node)
