#
# Copyright (c) 2015 Mirantis, Inc.
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
from tempest.lib.common.utils import data_utils
from tempest.lib.common.utils import test_utils
from tempest.lib import decorators

from ironic_tempest_plugin import manager
from ironic_tempest_plugin.tests.scenario import baremetal_manager

LOG = logging.getLogger(__name__)
CONF = config.CONF


class BaremetalMultitenancy(baremetal_manager.BaremetalScenarioTest,
                            manager.NetworkScenarioTest):
    """Check L2 isolation of baremetal and VM instances in different tenants:

    * Create a keypair, network, subnet and router for the primary tenant
    * Boot 2 instances in the different tenant's network using the keypair
    * Associate floating ips to both instance
    * Verify there is no L3 connectivity between instances of different tenants
    * Verify connectivity between instances floating IP's
    * Delete both instances
    """

    credentials = ['primary', 'alt', 'admin', 'system_admin']

    @classmethod
    def skip_checks(cls):
        super(BaremetalMultitenancy, cls).skip_checks()
        if not CONF.baremetal.use_provision_network:
            msg = 'Ironic/Neutron tenant isolation is not configured.'
            raise cls.skipException(msg)

    def create_tenant_network(self, clients, tenant_cidr, create_router=True):
        network = self.create_network(
            networks_client=clients.networks_client,
            project_id=clients.credentials.project_id)

        router = None
        if create_router:
            router = self.get_router(
                client=clients.routers_client,
                project_id=clients.credentials.tenant_id)

        result = clients.subnets_client.create_subnet(
            name=data_utils.rand_name('subnet'),
            network_id=network['id'],
            tenant_id=clients.credentials.tenant_id,
            ip_version=4,
            cidr=tenant_cidr)
        subnet = result['subnet']
        if create_router:
            clients.routers_client.add_router_interface(router['id'],
                                                        subnet_id=subnet['id'])
        self.addCleanup(clients.subnets_client.delete_subnet, subnet['id'])

        if create_router:
            self.addCleanup(clients.routers_client.remove_router_interface,
                            router['id'], subnet_id=subnet['id'])
        return network, subnet, router

    def verify_l3_connectivity(self, source_ip, private_key,
                               destination_ip, conn_expected=True, timeout=15):
        remote = self.get_remote_client(source_ip, private_key=private_key)
        remote.validate_authentication()

        output = remote.exec_command('ip route')
        LOG.debug("Routing table on %s is %s", source_ip, output)

        cmd = 'ping %s -c4 -w4 || exit 0' % destination_ip
        success_substring = " bytes from %s" % destination_ip

        def ping_remote():
            output = remote.exec_command(cmd)
            LOG.debug("Got output %s while pinging %s", output, destination_ip)
            if conn_expected:
                return success_substring in output
            else:
                return success_substring not in output

        # NOTE(vsaienko): we may lost couple of pings due to missing ARPs
        # so do several retries to get stable output.
        res = test_utils.call_until_true(ping_remote, timeout, 1)
        self.assertTrue(res)

    def multitenancy_check(self, use_vm=False):
        tenant_cidr = '10.0.100.0/24'
        keypair = self.create_keypair()
        network, subnet, router = self.create_tenant_network(
            self.os_primary, tenant_cidr)
        alt_keypair = self.create_keypair(self.os_alt.keypairs_client)
        alt_network, alt_subnet, alt_router = self.create_tenant_network(
            self.os_alt, tenant_cidr)
        # Create single BM guest as Primary
        instance1, node1 = self.boot_instance(
            clients=self.os_primary,
            keypair=keypair,
            net_id=network['id'],
        )
        fixed_ip1 = instance1['addresses'][network['name']][0]['addr']
        floating_ip1 = self.create_floating_ip(
            instance1,
        )['floating_ip_address']
        self.check_vm_connectivity(ip_address=floating_ip1,
                                   private_key=keypair['private_key'],
                                   server=instance1)
        if use_vm:
            # Create VM on compute node
            alt_instance = self.create_server(
                clients=self.os_alt,
                key_name=alt_keypair['name'],
                flavor=CONF.compute.flavor_ref_alt,
                networks=[{'uuid': alt_network['id']}]
            )
        else:
            # Create BM
            alt_instance, alt_node = self.boot_instance(
                keypair=alt_keypair,
                clients=self.os_alt,
                net_id=alt_network['id'],
            )
        fixed_ip2 = alt_instance['addresses'][alt_network['name']][0]['addr']
        alt_floating_ip = self.create_floating_ip(
            alt_instance,
            client=self.os_alt.floating_ips_client
        )['floating_ip_address']
        self.check_vm_connectivity(
            ip_address=alt_floating_ip,
            private_key=alt_keypair['private_key'],
            server=alt_instance)
        self.verify_l3_connectivity(
            alt_floating_ip,
            alt_keypair['private_key'],
            fixed_ip1,
            conn_expected=False
        )
        self.verify_l3_connectivity(
            floating_ip1,
            keypair['private_key'],
            fixed_ip2,
            conn_expected=False
        )
        self.verify_l3_connectivity(
            floating_ip1,
            keypair['private_key'],
            alt_floating_ip,
            conn_expected=True
        )
        self.terminate_instance(
            instance=alt_instance,
            servers_client=self.os_alt.servers_client)
        self.terminate_instance(instance=instance1)

    @decorators.idempotent_id('26e2f145-2a8e-4dc7-8457-7f2eb2c6749d')
    @utils.services('compute', 'image', 'network')
    def test_baremetal_multitenancy(self):
        self.multitenancy_check()

    @decorators.idempotent_id('9e38631a-2df2-11e9-810e-8c16450ea513')
    @utils.services('compute', 'image', 'network')
    def test_baremetal_vm_multitenancy(self):
        if not CONF.service_available.nova:
            self.skipTest('Compute service Nova is disabled,'
                          ' VM is required to run this test')
        self.multitenancy_check(use_vm=True)

    @decorators.idempotent_id('6891929f-a254-43b1-bd97-6ea3ec74d6a9')
    @utils.services('compute', 'image', 'network')
    def test_baremetal_vm_multitenancy_trunk(self):
        """Check Trunk scenario for two baremetal servers


        fipA -- RouterA -- NetworkA (10.0.100.0/24)
                              |
                              |eth0
                             eth0:instanceA
                              |eth0.vlan_id
                              |
                           NetworkB(10.0.101.0/24)
                              |
                              |eth0
                           instanceB


        * Create instanceA within networkA and FIPA with trunk port plugged to
          networkA as parent(native vlan/untagged) and networkB as
          vlan subport
        * Create instanceB within networkB
        * Verify connectivity to instanceB from instanceA failed
        * Assign ip address on subport inside instanceA. This step is needed
          only unless nova configdrive support of trunks is not implemented.
        * Verify connectivity to instanceB from instanceA success
        * Remove subport from instanceA
        * Verify connectivity to instanceB from instanceA failed
        * Add subport to instanceA
        * Verify connectivity to instanceB from instanceA Passed
        """

        if not CONF.baremetal_feature_enabled.trunks_supported:
            msg = 'Trunks with baremetal are not supported.'
            raise self.skipException(msg)

        tenant_a_cidr = '10.0.100.0/24'
        tenant_b_cidr = '10.0.101.0/24'

        keypair = self.create_keypair()
        networkA, subnetA, routerA = self.create_tenant_network(
            self.os_primary, tenant_a_cidr)
        networkB, subnetB, _ = self.create_tenant_network(
            self.os_primary, tenant_b_cidr, create_router=False)
        portB = self.create_port(network_id=networkB["id"])

        parent_port = self.create_port(network_id=networkA["id"])
        subport = self.create_port(network_id=networkB["id"])
        subports = [{'port_id': subport['id'], 'segmentation_type': 'inherit'}]
        trunk = self.os_primary.trunks_client.create_trunk(
            name="test-trunk", port_id=parent_port['id'],
            sub_ports=subports)['trunk']
        self.addCleanup(self.os_primary.trunks_client.delete_trunk,
                        trunk['id'])

        # Create instanceB first as we will not check if its booted,
        # as we don't have FIP, so it has more time than instanceA
        # to boot.
        instanceB, nodeB = self.boot_instance(
            clients=self.os_primary,
            keypair=keypair,
            networks=[{'port': portB['id']}]
        )

        instanceA, nodeA = self.boot_instance(
            clients=self.os_primary,
            keypair=keypair,
            networks=[{'port': parent_port['id']}]
        )

        floating_ipA = self.create_floating_ip(
            instanceA,
        )['floating_ip_address']

        fixed_ipB = instanceB['addresses'][networkB['name']][0]['addr']

        self.check_vm_connectivity(ip_address=floating_ipA,
                                   private_key=keypair['private_key'],
                                   server=instanceA)
        ssh_client = self.get_remote_client(floating_ipA,
                                            private_key=keypair['private_key'])

        # TODO(vsaienko): add when cloudinit support is implemented
        # add validation of network_data.json and drop next ip assignment

        self.verify_l3_connectivity(
            floating_ipA,
            keypair['private_key'],
            fixed_ipB,
            conn_expected=False
        )
        vlan_id = trunk['sub_ports'][0]['segmentation_id']
        subport_ip = subport['fixed_ips'][0]['ip_address']

        interface_name = ssh_client.exec_command(
            "sudo ip route | awk '/default/ {print $5}'").rstrip()
        cmds = [
            f"sudo ip link add link {interface_name} name "
            f"{interface_name}.{vlan_id} type vlan id {vlan_id}",
            f"sudo ip addr add {subport_ip}/24 dev {interface_name}.{vlan_id}",
            f"sudo ip link set dev {interface_name}.{vlan_id} up"]

        for cmd in cmds:
            ssh_client.exec_command(cmd)

        self.verify_l3_connectivity(
            floating_ipA,
            keypair['private_key'],
            fixed_ipB,
            conn_expected=True
        )

        self.os_primary.trunks_client.delete_subports_from_trunk(
            trunk['id'], trunk['sub_ports'])
        self.verify_l3_connectivity(
            floating_ipA,
            keypair['private_key'],
            fixed_ipB,
            conn_expected=False
        )
        self.os_primary.trunks_client.add_subports_to_trunk(
            trunk['id'], trunk['sub_ports'])

        # NOTE(vsaienko): it may take some time for network driver to
        # setup vlans as this is async operation.
        self.verify_l3_connectivity(
            floating_ipA,
            keypair['private_key'],
            fixed_ipB,
            conn_expected=True
        )
        self.terminate_instance(instance=instanceA)
        self.terminate_instance(instance=instanceB)
