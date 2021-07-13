#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
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
from tempest.common import waiters
from tempest import config
from tempest.lib.common import api_version_request
from tempest.lib import decorators

from ironic_tempest_plugin.tests.scenario import baremetal_manager

LOG = logging.getLogger(__name__)
CONF = config.CONF


class BaremetalBasicOps(baremetal_manager.BaremetalScenarioTest):
    """This smoke test tests an Ironic driver.

    It follows this basic set of operations:
        * Creates a keypair
        * Boots an instance using the keypair
        * Monitors the associated Ironic node for power and
          expected state transitions
        * Validates Ironic node's port data has been properly updated
        * Validates Ironic node's resource class and traits have been honoured
        * Verifies SSH connectivity using created keypair via fixed IP
        * Associates a floating ip
        * Verifies SSH connectivity using created keypair via floating IP
        * Verifies instance rebuild with ephemeral partition preservation
        * Deletes instance
        * Monitors the associated Ironic node for power and
          expected state transitions
    """

    credentials = ['primary', 'admin', 'system_admin']

    TEST_RESCUE_MODE = False
    image_ref = None
    wholedisk_image = None

    @classmethod
    def skip_checks(cls):
        super(BaremetalBasicOps, cls).skip_checks()

        # If default rescue interface is configured to test the rescue
        # feature, then skips this test and let the test derived class
        # to be executed.
        rescue_if = CONF.baremetal.default_rescue_interface
        if cls.TEST_RESCUE_MODE:
            if not rescue_if or rescue_if == 'no-rescue':
                msg = 'Node rescue interface is not enabled.'
                raise cls.skipException(msg)
        else:
            if rescue_if and rescue_if != 'no-rescue':
                msg = ('Node rescue interface is enabled, but %s class '
                       'cannot test rescue operations.' % cls.__name__)
                raise cls.skipException(msg)

    @staticmethod
    def _is_version_supported(version):
        """Return whether an API microversion is supported."""
        min_version = api_version_request.APIVersionRequest(
            CONF.baremetal.min_microversion)
        max_version = api_version_request.APIVersionRequest(
            CONF.baremetal.max_microversion)
        version = api_version_request.APIVersionRequest(version)
        return min_version <= version <= max_version

    def rebuild_instance(self, preserve_ephemeral=False):
        self.rebuild_server(server_id=self.instance['id'],
                            preserve_ephemeral=preserve_ephemeral,
                            wait=False)

        node = self.get_node(instance_id=self.instance['id'])

        # We should remain on the same node
        self.assertEqual(self.node['uuid'], node['uuid'])
        self.node = node

        waiters.wait_for_server_status(
            self.servers_client,
            server_id=self.instance['id'],
            status='REBUILD',
            ready_wait=False)
        waiters.wait_for_server_status(
            self.servers_client,
            server_id=self.instance['id'],
            status='ACTIVE')

    def verify_partition(self, client, label, mount, gib_size):
        """Verify a labeled partition's mount point and size."""
        LOG.info("Looking for partition %s mounted on %s", label, mount)

        # Validate we have a device with the given partition label
        cmd = "/sbin/blkid -c /dev/null -l -o device -t LABEL=%s" % label
        device = client.exec_command(cmd).rstrip('\n')
        LOG.debug("Partition device is %s", device)
        self.assertNotEqual('', device)

        # Validate the mount point for the device
        cmd = "mount | grep -w '%s' | cut -d' ' -f3" % device
        actual_mount = client.exec_command(cmd).rstrip('\n')
        LOG.debug("Partition mount point is %s", actual_mount)
        self.assertEqual(actual_mount, mount)

        # Validate the partition size matches what we expect
        numbers = '0123456789'
        devnum = device.replace('/dev/', '')
        cmd = "cat /sys/block/%s/%s/size" % (devnum.rstrip(numbers), devnum)
        num_bytes = client.exec_command(cmd).rstrip('\n')
        num_bytes = int(num_bytes) * 512
        actual_gib_size = num_bytes / (1024 * 1024 * 1024)
        LOG.debug("Partition size is %d GiB", actual_gib_size)
        self.assertEqual(actual_gib_size, gib_size)

    def get_flavor_ephemeral_size(self):
        """Returns size of the ephemeral partition in GiB."""
        f_id = self.instance['flavor']['id']
        flavor = self.flavors_client.show_flavor(f_id)['flavor']
        ephemeral = flavor.get('OS-FLV-EXT-DATA:ephemeral')
        if not ephemeral or ephemeral == 'N/A':
            return None
        return int(ephemeral)

    def validate_ports(self):
        node_uuid = self.node['uuid']
        vifs = self.get_node_vifs(node_uuid)

        ir_ports = self.get_ports(node_uuid)
        ir_ports_addresses = [x['address'] for x in ir_ports]
        for vif in vifs:
            n_port_id = vif['id']
            body = self.ports_client.show_port(n_port_id)
            n_port = body['port']
            self.assertEqual(n_port['device_id'], self.instance['id'])
            self.assertIn(n_port['mac_address'], ir_ports_addresses)

    def validate_scheduling(self):
        """Validate scheduling attributes of the node against the flavor.

        Validates the resource class and traits requested by the flavor against
        those set on the node. Does not assume that resource classes and traits
        are in use.
        """
        node = self.get_node(instance_id=self.instance['id'],
                             api_version='1.37')
        f_id = self.instance['flavor']['id']
        extra_specs = self.flavors_client.list_flavor_extra_specs(f_id)
        extra_specs = extra_specs['extra_specs']

        # Pull the requested resource class and traits from the flavor.
        resource_class = None
        traits = set()
        for key, value in extra_specs.items():
            if key.startswith('resources:CUSTOM_') and value == '1':
                resource_class = key.partition(':')[2]
            if key.startswith('trait:') and value == 'required':
                trait = key.partition(':')[2]
                traits.add(trait)

        # Validate requested resource class and traits against the node.
        if resource_class is not None:
            # The resource class in ironic may be lower case, and must omit the
            # CUSTOM_ prefix. Normalise it.
            node_resource_class = node['resource_class']
            node_resource_class = node_resource_class.upper()
            node_resource_class = 'CUSTOM_' + node_resource_class
            self.assertEqual(resource_class, node_resource_class)

        if 'traits' in node and traits:
            self.assertIn('traits', node['instance_info'])
            # All flavor traits should be added as instance traits.
            self.assertEqual(traits, set(node['instance_info']['traits']))
            # Flavor traits should be a subset of node traits.
            self.assertTrue(traits.issubset(set(node['traits'])))

    def validate_uefi(self, client):
        efi_dir = '/sys/firmware/efi'
        success_string = "Found " + efi_dir
        cmd = 'test -d {dir} && echo "Found {dir}" ||'\
              ' echo "{dir} not found"'.format(dir=efi_dir)
        output = client.exec_command(cmd).rstrip()
        self.assertEqual(success_string, output)

    def baremetal_server_ops(self):
        self.add_keypair()
        self.instance, self.node = self.boot_instance()
        self.validate_ports()
        self.validate_scheduling()
        ip_address = self.get_server_ip(self.instance)
        vm_client = self.get_remote_client(ip_address)

        # We expect the ephemeral partition to be mounted on /mnt and to have
        # the same size as our flavor definition.
        eph_size = self.get_flavor_ephemeral_size()
        if eph_size:
            self.verify_partition(vm_client, 'ephemeral0', '/mnt', eph_size)
            # Create the test file
            self.create_timestamp(
                ip_address, private_key=self.keypair['private_key'])

        if CONF.baremetal.boot_mode == "uefi":
            self.validate_uefi(vm_client)

        # Test rescue mode
        if self.TEST_RESCUE_MODE:
            self.rescue_instance(self.instance, self.node, ip_address)
            self.unrescue_instance(self.instance, self.node, ip_address)

        self.terminate_instance(self.instance)

    @decorators.idempotent_id('549173a5-38ec-42bb-b0e2-c8b9f4a08943')
    @utils.services('compute', 'image', 'network')
    def test_baremetal_server_ops_partition_image(self):
        self.image_ref = CONF.baremetal.partition_image_ref
        self.wholedisk_image = False
        self.baremetal_server_ops()

    @decorators.idempotent_id('d7d48aa1-0395-4f31-a908-60969adc4322')
    @utils.services('compute', 'image', 'network')
    def test_baremetal_server_ops_wholedisk_image(self):
        self.image_ref = CONF.baremetal.whole_disk_image_ref
        self.wholedisk_image = True
        self.baremetal_server_ops()


class BaremetalBasicOpsAndRescue(BaremetalBasicOps):
    """This test includes rescue/unrescue ops."""

    TEST_RESCUE_MODE = True
