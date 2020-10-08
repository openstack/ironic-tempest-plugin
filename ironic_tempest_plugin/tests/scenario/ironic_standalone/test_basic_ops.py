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

from tempest.common import utils
from tempest import config
from tempest.lib import decorators

from ironic_tempest_plugin.tests.scenario import \
    baremetal_standalone_manager as bsm

CONF = config.CONF


class BaremetalAgentIpmitoolWholedisk(bsm.BaremetalStandaloneScenarioTest):

    driver = 'agent_ipmitool'
    image_ref = CONF.baremetal.whole_disk_image_ref
    wholedisk_image = True

    @decorators.idempotent_id('defff515-a6ff-44f6-9d8d-2ded51196d98')
    @utils.services('image', 'network', 'object_storage')
    def test_ip_access_to_server(self):
        self.boot_and_verify_node()


class BaremetalAgentIpmitoolWholediskHttpLink(
        bsm.BaremetalStandaloneScenarioTest):

    driver = 'agent_ipmitool'
    image_ref = CONF.baremetal.whole_disk_image_url
    image_checksum = CONF.baremetal.whole_disk_image_checksum
    wholedisk_image = True

    @classmethod
    def skip_checks(cls):
        super(BaremetalAgentIpmitoolWholediskHttpLink, cls).skip_checks()
        if not CONF.baremetal_feature_enabled.ipxe_enabled:
            skip_msg = ("HTTP server is not available when ipxe is disabled.")
            raise cls.skipException(skip_msg)

    @decorators.idempotent_id('d926c683-1a32-44df-afd0-e60134346fd0')
    @utils.services('network')
    def test_ip_access_to_server(self):
        self.boot_and_verify_node()


class BaremetalAgentIpmitoolPartitioned(bsm.BaremetalStandaloneScenarioTest):

    driver = 'agent_ipmitool'
    image_ref = CONF.baremetal.partition_image_ref
    wholedisk_image = False

    @decorators.idempotent_id('27b86130-d8dc-419d-880a-fbbbe4ce3f8c')
    @utils.services('image', 'network', 'object_storage')
    def test_ip_access_to_server(self):
        self.boot_and_verify_node()


class BaremetalPxeIpmitoolWholedisk(bsm.BaremetalStandaloneScenarioTest):

    driver = 'pxe_ipmitool'
    image_ref = CONF.baremetal.whole_disk_image_ref
    wholedisk_image = True

    @decorators.idempotent_id('d8c5badd-45db-4d05-bbe8-35babbed6e86')
    @utils.services('image', 'network')
    def test_ip_access_to_server(self):
        self.boot_and_verify_node()


class BaremetalPxeIpmitoolWholediskHttpLink(
        bsm.BaremetalStandaloneScenarioTest):

    driver = 'pxe_ipmitool'
    image_ref = CONF.baremetal.whole_disk_image_url
    image_checksum = CONF.baremetal.whole_disk_image_checksum
    wholedisk_image = True

    @classmethod
    def skip_checks(cls):
        super(BaremetalPxeIpmitoolWholediskHttpLink, cls).skip_checks()
        if not CONF.baremetal_feature_enabled.ipxe_enabled:
            skip_msg = ("HTTP server is not available when ipxe is disabled.")
            raise cls.skipException(skip_msg)

    @decorators.idempotent_id('71ccf06f-6765-40fd-8252-1b1bfa423b9b')
    @utils.services('network')
    def test_ip_access_to_server(self):
        self.boot_and_verify_node()


class BaremetalPxeIpmitoolPartitioned(bsm.BaremetalStandaloneScenarioTest):

    driver = 'pxe_ipmitool'
    image_ref = CONF.baremetal.partition_image_ref
    wholedisk_image = False

    @decorators.idempotent_id('ea85e19c-6869-4577-b9bb-2eb150f77c90')
    @utils.services('image', 'network')
    def test_ip_access_to_server(self):
        self.boot_and_verify_node()


class BaremetalDriverIscsiWholedisk(bsm.BaremetalStandaloneScenarioTest):

    api_microversion = '1.31'  # to set the deploy_interface
    if 'redfish' in CONF.baremetal.enabled_hardware_types:
        driver = 'redfish'
    else:
        driver = 'ipmi'

    deploy_interface = 'iscsi'
    image_ref = CONF.baremetal.whole_disk_image_ref
    wholedisk_image = True

    @classmethod
    def skip_checks(cls):
        super(BaremetalDriverIscsiWholedisk, cls).skip_checks()
        if cls.driver == 'redfish':
            skip_msg = ("Test covered when using ipmi")
            raise cls.skipException(skip_msg)

    @decorators.idempotent_id('f25b71df-2150-45d7-a780-7f5b07124808')
    @utils.services('image', 'network')
    def test_ip_access_to_server(self):
        self.boot_and_verify_node()


class BaremetalDriverDirectWholedisk(bsm.BaremetalStandaloneScenarioTest):

    api_microversion = '1.31'  # to set the deploy_interface
    if 'redfish' in CONF.baremetal.enabled_hardware_types:
        driver = 'redfish'
    else:
        driver = 'ipmi'
    deploy_interface = 'direct'
    image_ref = CONF.baremetal.whole_disk_image_ref
    wholedisk_image = True

    @classmethod
    def skip_checks(cls):
        super(BaremetalDriverDirectWholedisk, cls).skip_checks()
        if cls.driver == 'ipmi':
            skip_msg = ("Test covered when using redfish")
            raise cls.skipException(skip_msg)

    @decorators.idempotent_id('c2db24e7-07dc-4a20-8f93-d4efae2bfd4e')
    @utils.services('image', 'network')
    def test_ip_access_to_server(self):
        self.boot_and_verify_node()


class BaremetalDriverIscsiPartitioned(bsm.BaremetalStandaloneScenarioTest):

    api_microversion = '1.31'  # to set the deploy_interface
    if 'redfish' in CONF.baremetal.enabled_hardware_types:
        driver = 'redfish'
    else:
        driver = 'ipmi'
    deploy_interface = 'iscsi'
    image_ref = CONF.baremetal.partition_image_ref
    wholedisk_image = False
    boot_option = 'netboot' if CONF.baremetal.partition_netboot else 'local'

    @classmethod
    def skip_checks(cls):
        super(BaremetalDriverIscsiPartitioned, cls).skip_checks()
        if cls.driver == 'ipmi':
            skip_msg = ("Test covered when using redfish")
            raise cls.skipException(skip_msg)

    @decorators.idempotent_id('7d0b205e-edbc-4e2d-9f6d-95cd74eefecb')
    @utils.services('image', 'network')
    def test_ip_access_to_server(self):
        self.boot_and_verify_node()


class BaremetalDriverDirectPartitioned(bsm.BaremetalStandaloneScenarioTest):

    api_microversion = '1.31'  # to set the deploy_interface
    if 'redfish' in CONF.baremetal.enabled_hardware_types:
        driver = 'redfish'
    else:
        driver = 'ipmi'
    deploy_interface = 'direct'
    image_ref = CONF.baremetal.partition_image_ref
    wholedisk_image = False
    boot_option = 'netboot' if CONF.baremetal.partition_netboot else 'local'

    @classmethod
    def skip_checks(cls):
        super(BaremetalDriverDirectPartitioned, cls).skip_checks()
        if cls.driver == 'redfish':
            skip_msg = ("Test covered when using ipmi")
            raise cls.skipException(skip_msg)

    @decorators.idempotent_id('7b4b2dcd-2bbb-44f5-991f-0964300af6b7')
    @utils.services('image', 'network')
    def test_ip_access_to_server(self):
        self.boot_and_verify_node()


class BaremetalDriverAnsibleWholedisk(bsm.BaremetalStandaloneScenarioTest):

    api_microversion = '1.31'  # to set the deploy_interface
    if 'redfish' in CONF.baremetal.enabled_hardware_types:
        driver = 'redfish'
    else:
        driver = 'ipmi'
    deploy_interface = 'ansible'
    image_ref = CONF.baremetal.whole_disk_image_ref
    wholedisk_image = True

    @decorators.idempotent_id('cde532cc-81ba-4489-b374-b4a85cc203eb')
    @utils.services('image', 'network')
    def test_ip_access_to_server(self):
        self.boot_and_verify_node()


class BaremetalIpmiRescueWholedisk(bsm.BaremetalStandaloneScenarioTest):

    api_microversion = '1.38'
    min_microversion = '1.38'
    driver = 'ipmi'
    rescue_interface = 'agent'
    image_ref = CONF.baremetal.whole_disk_image_ref
    wholedisk_image = True

    # NOTE(tiendc) Using direct deploy interface and a whole disk
    # image may lead to the bug:
    # https://bugs.launchpad.net/ironic/+bug/1750958
    # This is a workaround by using iscsi deploy interface.
    deploy_interface = 'iscsi'

    @decorators.idempotent_id('d6a1780f-c4bb-4136-8144-29e822e14d66')
    @utils.services('image', 'network')
    def test_rescue_mode(self):
        self.set_node_to_active(self.image_ref)
        self.rescue_unrescue()


class BaremetalIpmiRescuePartitioned(bsm.BaremetalStandaloneScenarioTest):

    api_microversion = '1.38'
    min_microversion = '1.38'
    driver = 'ipmi'
    rescue_interface = 'agent'
    image_ref = CONF.baremetal.partition_image_ref
    wholedisk_image = False
    boot_option = 'netboot' if CONF.baremetal.partition_netboot else 'local'

    # NOTE(jroll) the ansible deploy interface doesn't support partition images
    # with netboot mode. Since that's what is happening here, explicitly choose
    # a deploy interface to be sure we don't end up with a node using the
    # ansible interface here.
    deploy_interface = 'iscsi'

    @decorators.idempotent_id('113acd0a-9872-4631-b3ee-54da7e3bb262')
    @utils.services('image', 'network')
    def test_rescue_mode(self):
        self.set_node_to_active(self.image_ref)
        self.rescue_unrescue()


class BaremetalIloDirectWholediskHttpLink(
        bsm.BaremetalStandaloneScenarioTest):

    api_microversion = '1.31'  # to set the deploy_interface
    driver = 'ilo'
    deploy_interface = 'direct'
    boot_interface = 'ilo-virtual-media'
    image_ref = CONF.baremetal.whole_disk_image_url
    image_checksum = CONF.baremetal.whole_disk_image_checksum
    wholedisk_image = True

    @decorators.idempotent_id('c2db24e7-b9bb-44df-6765-e60134346fd0')
    @utils.services('network')
    def test_ip_access_to_server(self):
        self.boot_and_verify_node()


class BaremetalIloDirectPartitioned(bsm.BaremetalStandaloneScenarioTest):

    api_microversion = '1.31'  # to set the deploy_interface
    driver = 'ilo'
    deploy_interface = 'direct'
    boot_interface = 'ilo-virtual-media'
    image_ref = CONF.baremetal.partition_image_ref
    wholedisk_image = False

    @decorators.idempotent_id('ea85e19c-d8dc-4577-4d05-fbbbe4ce3f8c')
    @utils.services('image', 'network')
    def test_ip_access_to_server(self):
        self.boot_and_verify_node()


class BaremetalIloIscsiWholediskHttpLink(
        bsm.BaremetalStandaloneScenarioTest):

    api_microversion = '1.31'  # to set the deploy_interface
    driver = 'ilo'
    deploy_interface = 'iscsi'
    boot_interface = 'ilo-virtual-media'
    image_ref = CONF.baremetal.whole_disk_image_url
    image_checksum = CONF.baremetal.whole_disk_image_checksum
    wholedisk_image = True

    @decorators.idempotent_id('71ccf06f-45db-8f93-afd0-d4efae2bfd4e')
    @utils.services('network')
    def test_ip_access_to_server(self):
        self.boot_and_verify_node()


class BaremetalIloIscsiPartitioned(bsm.BaremetalStandaloneScenarioTest):

    api_microversion = '1.31'  # to set the deploy_interface
    driver = 'ilo'
    deploy_interface = 'iscsi'
    boot_interface = 'ilo-virtual-media'
    image_ref = CONF.baremetal.partition_image_ref
    wholedisk_image = False

    @decorators.idempotent_id('d926c683-4d05-8252-b9bb-35babbed6e86')
    @utils.services('image', 'network')
    def test_ip_access_to_server(self):
        self.boot_and_verify_node()


class BaremetalIloPxeWholediskHttpLink(
        bsm.BaremetalStandaloneScenarioTest):

    api_microversion = '1.31'  # to set the deploy_interface
    driver = 'ilo'
    deploy_interface = 'direct'
    boot_interface = 'ilo-pxe'
    image_ref = CONF.baremetal.whole_disk_image_url
    image_checksum = CONF.baremetal.whole_disk_image_checksum
    wholedisk_image = True

    @decorators.idempotent_id('d926c683-1a32-edbc-07dc-95cd74eefecb')
    @utils.services('network')
    def test_ip_access_to_server(self):
        self.boot_and_verify_node()


class BaremetalIloPxePartitioned(bsm.BaremetalStandaloneScenarioTest):

    api_microversion = '1.31'  # to set the deploy_interface
    driver = 'ilo'
    deploy_interface = 'direct'
    boot_interface = 'ilo-pxe'
    image_ref = CONF.baremetal.partition_image_ref
    wholedisk_image = False

    @decorators.idempotent_id('71ccf06f-07dc-4577-6869-1b1bfa423b9b')
    @utils.services('image', 'network')
    def test_ip_access_to_server(self):
        self.boot_and_verify_node()


class BaremetalIloIPxeWholediskHttpLink(
        bsm.BaremetalStandaloneScenarioTest):

    api_microversion = '1.31'  # to set the deploy_interface
    driver = 'ilo'
    deploy_interface = 'direct'
    boot_interface = 'ilo-ipxe'
    image_ref = CONF.baremetal.whole_disk_image_url
    image_checksum = CONF.baremetal.whole_disk_image_checksum
    wholedisk_image = True

    @decorators.idempotent_id('d926c683-1a32-edbc-07dc-95cd74eefecb')
    @utils.services('network')
    def test_ip_access_to_server(self):
        self.boot_and_verify_node()


class BaremetalIlo5UefiHTTPSWholediskHttpsLink(
        bsm.BaremetalStandaloneScenarioTest):

    api_microversion = '1.31'  # to set the deploy_interface
    driver = 'ilo5'
    deploy_interface = 'direct'
    boot_interface = 'ilo-uefi-https'
    image_ref = CONF.baremetal.whole_disk_image_url
    image_checksum = CONF.baremetal.whole_disk_image_checksum
    wholedisk_image = True

    @decorators.idempotent_id('d926c683-1a32-edbc-07dc-95cd74eefecb')
    @utils.services('network')
    def test_ip_access_to_server(self):
        self.boot_and_verify_node()


class BaremetalRedfishDirectWholediskHttpLink(
        bsm.BaremetalStandaloneScenarioTest):

    api_microversion = '1.31'  # to set the deploy_interface
    driver = 'redfish'
    deploy_interface = 'direct'
    boot_interface = 'redfish-virtual-media'
    image_ref = CONF.baremetal.whole_disk_image_url
    image_checksum = CONF.baremetal.whole_disk_image_checksum
    wholedisk_image = True

    @decorators.idempotent_id('113acd0a-9872-4631-b3ee-54da7e3bb262')
    @utils.services('network')
    def test_ip_access_to_server(self):
        self.boot_and_verify_node()


class BaremetalRedfishIPxeWholediskHttpLink(
        bsm.BaremetalStandaloneScenarioTest):

    api_microversion = '1.31'  # to set the deploy_interface
    driver = 'redfish'
    deploy_interface = 'direct'
    boot_interface = 'ipxe'
    image_ref = CONF.baremetal.whole_disk_image_url
    image_checksum = CONF.baremetal.whole_disk_image_checksum
    wholedisk_image = True

    @decorators.idempotent_id('113acd0a-9872-4631-b3ee-54da7e3bb262')
    @utils.services('network')
    def test_ip_access_to_server(self):
        self.boot_and_verify_node()
