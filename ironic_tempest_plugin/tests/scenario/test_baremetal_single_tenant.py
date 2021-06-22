#
# Copyright 2019 Red Hat, Inc.
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
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators

from ironic_tempest_plugin import manager
from ironic_tempest_plugin.tests.scenario import baremetal_manager

CONF = config.CONF


class BaremetalSingleTenant(baremetal_manager.BaremetalScenarioTest,
                            manager.NetworkScenarioTest):
    """Check "No L2 isolation" of baremetal and VM instances of same tenant:

    * Create a keypair, network, subnet and router for the primary tenant
    * Boot 2 instances in the same tenant's network using the keypair
    * Associate floating ips to both instances
    * Verify there is L3 connectivity between instances of same tenant
    * Verify connectivity between instances floating IP's
    * Delete both instances
    """

    credentials = ['primary', 'alt', 'admin', 'system_admin']

    @classmethod
    def skip_checks(cls):
        super(BaremetalSingleTenant, cls).skip_checks()
        if not CONF.baremetal.use_provision_network:
            msg = 'Ironic/Neutron tenant isolation is not configured.'
            raise cls.skipException(msg)
        if (CONF.baremetal.available_nodes is not None
                and CONF.baremetal.available_nodes < 2):
            msg = ('Not enough baremetal nodes, %d configured, test requires '
                   'a minimum of 2') % CONF.baremetal.available_nodes
            raise cls.skipException(msg)

    def create_tenant_network(self, clients, tenant_cidr):
        network = self._create_network(
            networks_client=clients.networks_client,
            tenant_id=clients.credentials.tenant_id)
        router = self._get_router(
            client=clients.routers_client,
            tenant_id=clients.credentials.tenant_id)

        extra_subnet_args = {}
        if CONF.validation.ip_version_for_ssh == 6:
            extra_subnet_args['ipv6_address_mode'] = 'dhcpv6-stateless'
            extra_subnet_args['ipv6_ra_mode'] = 'dhcpv6-stateless'
            extra_subnet_args['gateway_ip'] = 'fd00:33::1'

        result = clients.subnets_client.create_subnet(
            name=data_utils.rand_name('subnet'),
            network_id=network['id'],
            tenant_id=clients.credentials.tenant_id,
            ip_version=CONF.validation.ip_version_for_ssh,
            cidr=tenant_cidr, **extra_subnet_args)
        subnet = result['subnet']
        clients.routers_client.add_router_interface(router['id'],
                                                    subnet_id=subnet['id'])
        self.addCleanup(clients.subnets_client.delete_subnet, subnet['id'])
        self.addCleanup(clients.routers_client.remove_router_interface,
                        router['id'], subnet_id=subnet['id'])

        return network, subnet, router

    def verify_l3_connectivity(self, source_ip, private_key,
                               destination_ip, conn_expected=True):
        remote = self.get_remote_client(source_ip, private_key=private_key)
        remote.validate_authentication()

        cmd = 'ping %s -c4 -w4 || exit 0' % destination_ip
        success_substring = " bytes from %s" % destination_ip
        output = remote.exec_command(cmd)
        if conn_expected:
            self.assertIn(success_substring, output)
        else:
            self.assertNotIn(success_substring, output)

    def tenancy_check(self, use_vm=False):

        ip_version = CONF.validation.ip_version_for_ssh

        tenant_cidr = '10.0.100.0/24'
        if ip_version == 6:
            tenant_cidr = 'fd00:33::/64'

        keypair = self.create_keypair()
        network, subnet, router = self.create_tenant_network(
            self.os_primary, tenant_cidr)

        instance1, node1 = self.boot_instance(
            clients=self.os_primary,
            keypair=keypair,
            net_id=network['id'],
        )

        fixed_ip1 = instance1['addresses'][network['name']][0]['addr']
        if ip_version == 6:
            floating_ip1 = fixed_ip1
        else:
            floating_ip1 = self.create_floating_ip(
                instance1,
            )['floating_ip_address']
        self.check_vm_connectivity(ip_address=floating_ip1,
                                   private_key=keypair['private_key'])

        if use_vm:
            # Create VM on compute node
            instance2 = self.create_server(
                clients=self.os_primary,
                key_name=keypair['name'],
                flavor=CONF.compute.flavor_ref,
                networks=[{'uuid': network['id']}]
            )
        else:
            # Create BM
            instance2, node2 = self.boot_instance(
                keypair=keypair,
                clients=self.os_primary,
                net_id=network['id'],
            )
        fixed_ip2 = \
            instance2['addresses'][network['name']][0]['addr']
        if ip_version == 6:
            floating_ip2 = fixed_ip2
        else:
            floating_ip2 = self.create_floating_ip(
                instance2,
                client=self.os_primary.floating_ips_client
            )['floating_ip_address']
        self.check_vm_connectivity(
            ip_address=floating_ip2,
            private_key=keypair['private_key'])

        self.verify_l3_connectivity(
            floating_ip2,
            keypair['private_key'],
            fixed_ip1,
            conn_expected=True
        )
        self.verify_l3_connectivity(
            floating_ip1,
            keypair['private_key'],
            fixed_ip2,
            conn_expected=True
        )
        self.verify_l3_connectivity(
            floating_ip1,
            keypair['private_key'],
            floating_ip2,
            conn_expected=True
        )
        self.terminate_instance(
            instance=instance2,
            servers_client=self.os_primary.servers_client)
        self.terminate_instance(instance=instance1)

    @decorators.idempotent_id('8fe15552-3788-11e9-b599-74e5f9e2a801')
    @utils.services('compute', 'image', 'network')
    def test_baremetal_single_tenant(self):
        if CONF.service_available.nova:
            self.skipTest('Compute service Nova is running,'
                          ' BM to BM test will be skipped,'
                          ' to save test execution time')
        self.tenancy_check()

    @decorators.idempotent_id('90b3b6be-3788-11e9-b599-74e5f9e2a801')
    @utils.services('compute', 'image', 'network')
    def test_baremetal_vm_single_tenant(self):
        if not CONF.service_available.nova:
            self.skipTest('Compute service Nova is disabled,'
                          ' VM is required to run this test')
        self.tenancy_check(use_vm=True)
