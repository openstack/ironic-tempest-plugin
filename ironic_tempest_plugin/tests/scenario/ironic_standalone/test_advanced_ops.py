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
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators

from ironic_tempest_plugin.tests.scenario import \
    baremetal_standalone_manager as bsm

CONF = config.CONF


class BaremetalRedfishDHCPLessDeploy(bsm.BaremetalStandaloneScenarioTest):

    api_microversion = '1.59'  # Ussuri for redfish-virtual-media
    driver = 'redfish'
    deploy_interface = 'direct'
    boot_interface = 'redfish-virtual-media'
    image_ref = CONF.baremetal.whole_disk_image_ref
    image_checksum = CONF.baremetal.whole_disk_image_checksum
    wholedisk_image = True

    @classmethod
    def skip_checks(cls):
        super(BaremetalRedfishDHCPLessDeploy, cls).skip_checks()
        if CONF.baremetal_feature_enabled.dhcpless_vmedia:
            raise cls.skipException("This test requires a full OS image to "
                                    "be deployed, and thus must be "
                                    "explicitly enabled for testing.")

        if (not CONF.baremetal.public_subnet_id
                or not CONF.baremetal.public_subnet_ip):
            raise cls.skipException(
                "This test requires a public sunbet ID, and public subnet "
                "IP to use on that subnet to execute. Please see the "
                "baremetal configuration options public_subnet_id "
                "and public_subnet_ip respectively, and populate with "
                "appropriate values to execute this test.")

    def create_tenant_network(self, clients, tenant_cidr, ip_version):
        # NOTE(TheJulia): self.create_network is an internal method
        # which just gets the info, doesn't actually create a network.
        network = self.create_network(
            networks_client=self.os_admin.networks_client,
            project_id=clients.credentials.project_id,
            shared=True)

        router = self.get_router(
            client=clients.routers_client,
            project_id=clients.credentials.tenant_id,
            external_gateway_info={
                'network_id': CONF.network.public_network_id,
                'external_fixed_ips': [
                    {'subnet_id': CONF.baremetal.public_subnet_id,
                     'ip_address': CONF.baremetal.public_subnet_ip}]
            })
        result = clients.subnets_client.create_subnet(
            name=data_utils.rand_name('subnet'),
            network_id=network['id'],
            tenant_id=clients.credentials.tenant_id,
            ip_version=CONF.validation.ip_version_for_ssh,
            cidr=tenant_cidr, enable_dhcp=False)
        subnet = result['subnet']
        clients.routers_client.add_router_interface(router['id'],
                                                    subnet_id=subnet['id'])
        self.addCleanup(clients.subnets_client.delete_subnet, subnet['id'])
        self.addCleanup(clients.routers_client.remove_router_interface,
                        router['id'], subnet_id=subnet['id'])
        return network, subnet, router

    def deploy_vmedia_dhcpless(self, rebuild=False):
        """Helper to facilitate vmedia testing.

        * Create Network/router without DHCP
        * Set provisioning_network for this node.
        * Set cleanup to undo the provisionign network setup.
        * Launch instance.
          * Requirement: Instance OS image supports network config from
            network_data embedded in the OS. i.e. a real image, not
            cirros.
        * If so enabled, rebuild the node, Verify rebuild completed.
        * Via cleanup: Teardown Network/Router
        """

        # Get the latest state for the node.
        self.node = self.get_node(self.node['uuid'])
        prior_prov_net = self.node['driver_info'].get('provisioning_network')

        ip_version = CONF.validation.ip_version_for_ssh
        tenant_cidr = '10.0.6.0/24'
        if ip_version == 6:
            tenant_cidr = 'fd00:33::/64'

        network, subnet, router = self.create_tenant_network(
            self.os_admin, tenant_cidr, ip_version=ip_version)
        if prior_prov_net:
            self.update_node(self.node['uuid'],
                             [{'op': 'replace',
                               'path': '/driver_info/provisioning_network',
                               'value': network['id']}])
            self.addCleanup(self.update_node,
                            self.node['uuid'],
                            [{'op': 'replace',
                              'path': '/driver_info/provisioning_network',
                              'value': prior_prov_net}])
        else:
            self.update_node(self.node['uuid'],
                             [{'op': 'add',
                               'path': '/driver_info/provisioning_network',
                               'value': network['id']}])
            self.addCleanup(self.update_node,
                            self.node['uuid'],
                            [{'op': 'remove',
                              'path': '/driver_info/provisioning_network'}])

        self.set_node_to_active(self.image_ref, self.image_checksum,
                                fallback_network=network['id'],
                                config_drive_networking=True,
                                method_to_get_ip=self.get_server_ip)

        # node_ip is set by the prior call to set_node_to_active
        self.assertTrue(self.ping_ip_address(self.node_ip))

        if rebuild:
            self.set_node_provision_state(self.node['uuid'], 'rebuild')
            self.wait_provisioning_state(self.node['uuid'], 'active',
                                         timeout=CONF.baremetal.active_timeout,
                                         interval=30)
            # Assert we were able to ping after rebuilding.
            self.assertTrue(self.ping_ip_address(self.node_ip))
        # Force delete so we remove the vifs
        self.terminate_node(self.node['uuid'], force_delete=True)

    @decorators.idempotent_id('1f420ef3-99bd-46c7-b859-ce9c2892697f')
    @utils.services('image', 'network')
    def test_ip_access_to_server(self):
        self.deploy_vmedia_dhcpless(
            rebuild=CONF.baremetal.rebuild_remote_dhcpless)
