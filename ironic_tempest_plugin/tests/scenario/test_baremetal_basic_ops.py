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
from tempest.common import compute
from tempest.common import utils
from tempest.common import waiters
from tempest import config
from tempest.lib.common import api_version_request
from tempest.lib import decorators

from ironic_tempest_plugin.services.baremetal import base
from ironic_tempest_plugin.tests.scenario import baremetal_manager

LOG = logging.getLogger(__name__)
CONF = config.CONF


class BaremetalBasicOps(baremetal_manager.BaremetalScenarioTest,
                        compute.NoVNCValidateMixin):
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

    # Note: 1.65 API microversion is needed to enable the graphical console
    # and lesse. So that we can validate the graphical console functionality.
    min_microversion = '1.65'

    TEST_RESCUE_MODE = False
    image_ref = None
    wholedisk_image = None
    auto_lease = False
    console_interface = 'fake-graphical'

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

    @classmethod
    def resource_setup(cls):
        "Setup the default API microversion."
        super(BaremetalBasicOps, cls).resource_setup()
        base.set_baremetal_api_microversion(cls.min_microversion)
        cls.addClassCleanup(base.reset_baremetal_api_microversion)

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
        LOG.info("Starting instance rebuild (preserve_ephemeral=%s)",
                 preserve_ephemeral)
        self.rebuild_server(server_id=self.instance['id'],
                            preserve_ephemeral=preserve_ephemeral,
                            wait=False)
        node = self.get_node(instance_id=self.instance['id'])

        # We should remain on the same node
        LOG.info("Instance rebuild initiated on node %s", node['uuid'])
        self.assertEqual(self.node['uuid'], node['uuid'])
        self.node = node

        LOG.info("Waiting for server to enter REBUILD status")
        waiters.wait_for_server_status(
            self.servers_client,
            server_id=self.instance['id'],
            status='REBUILD',
            ready_wait=False)
        LOG.info("Server entered REBUILD status")

        LOG.info("Waiting for server to return to ACTIVE status")
        waiters.wait_for_server_status(
            self.servers_client,
            server_id=self.instance['id'],
            status='ACTIVE')
        LOG.info("Instance rebuild completed successfully")

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
            node_resource_class = node_resource_class.translate(
                str.maketrans(" -.:", "____", "!@#$%^&*()+=/\\?<>|\"'")
            )
            node_resource_class = 'CUSTOM_' + node_resource_class
            self.assertEqual(resource_class, node_resource_class)

        if 'traits' in node and traits:
            self.assertIn('traits', node['instance_info'])
            # All flavor traits should be added as instance traits.
            self.assertEqual(traits, set(node['instance_info']['traits']))
            # Flavor traits should be a subset of node traits.
            self.assertTrue(traits.issubset(set(node['traits'])))

    def validate_image(self):
        iinfo = self.node['instance_info']
        if self.wholedisk_image is not None and self.wholedisk_image:
            # If None, we have nothing to do here. If False, we don't
            # want to fall into this either.
            self.assertNotIn('kernel', iinfo)
            self.assertNotIn('ramdisk', iinfo)
        else:
            if 'image_type' in iinfo:
                self.assertEqual('partition', iinfo['image_type'])
            else:
                self.assertTrue(iinfo['kernel'])
                self.assertTrue(iinfo['ramdisk'])
            self.assertGreater(int(iinfo['root_gb']), 0)

    def validate_uefi(self, client):
        efi_dir = '/sys/firmware/efi'
        success_string = "Found " + efi_dir
        cmd = 'test -d {dir} && echo "Found {dir}" ||'\
              ' echo "{dir} not found"'.format(dir=efi_dir)
        output = client.exec_command(cmd).rstrip()
        self.assertEqual(success_string, output)

    def validate_lessee(self):
        iinfo = self.node.get('instance_info')
        dii = self.node.get('driver_internal_info', {})
        if 'automatic_lessee' in dii and iinfo:
            # NOTE(JayF): This item not being in instance_info tells us we
            # set the lessee.
            self.assertEqual(iinfo['project_id'], self.node['lessee'])

    def validate_console(self):
        """Validate graphical console functionality.

        Tests that nova-novncproxy can connect to the console container.
        Validation passing here means the novnc console will be available
        in horizon for an instance using the ironic nova driver.
        """
        LOG.info("Requesting VNC console for instance %s", self.instance['id'])
        body = self.servers_client.get_vnc_console(self.instance['id'],
                                                   type='novnc')['console']
        LOG.info("VNC console URL obtained: %s", body['url'])
        self.assertEqual('novnc', body['type'])
        # Do the initial HTTP Request to novncproxy to get the NoVNC JavaScript
        LOG.info("Starting NoVNC HTML response validation")
        self.validate_novnc_html(body['url'])
        # Do the WebSockify HTTP Request to novncproxy to do the RFB connection
        LOG.info("Creating WebSocket connection for RFB")
        self.websocket = compute.create_websocket(body['url'])
        self.addCleanup(self.websocket.close)
        # Validate that we successfully connected and upgraded to Web Sockets
        LOG.info("Validating WebSocket upgrade")
        self.validate_websocket_upgrade()
        # Validate the RFB Negotiation to determine if a valid VNC session
        LOG.info("Validating RFB negotiation")
        self.validate_rfb_negotiation()
        LOG.info("Console validation completed successfully")

    def baremetal_server_ops(self):
        LOG.info("Starting baremetal server operations test")

        LOG.info("Creating keypair")
        self.add_keypair()

        LOG.info("Booting instance with image_id=%s", self.image_ref)
        self.instance, self.node = self.boot_instance(image_id=self.image_ref)
        LOG.info("Instance booted successfully: instance_id=%s, node_uuid=%s",
                 self.instance['id'], self.node['uuid'])

        # Validate graphical console if fake-graphical interface is configured.
        # Note: Only fake-graphical is tested (redfish-graphical excluded as
        # sushy-tools doesn't support VNC yet). If configured but proxy is
        # missing, test will fail revealing the misconfiguration.
        if self.node.get('console_interface') == 'fake-graphical':
            LOG.info("Starting graphical console validation for instance %s",
                     self.instance['id'])
            self.validate_console()

        LOG.info("Starting image validation")
        self.validate_image()
        LOG.info("Image validation completed")

        LOG.info("Starting port validation for node %s", self.node['uuid'])
        self.validate_ports()
        LOG.info("Port validation completed")

        LOG.info("Starting scheduling validation")
        self.validate_scheduling()
        LOG.info("Scheduling validation completed")

        LOG.info("Starting lessee validation")
        self.validate_lessee()
        LOG.info("Lessee validation completed")

        LOG.info("Getting server IP address")
        ip_address = self.get_server_ip(self.instance)
        LOG.info("Server IP address: %s", ip_address)

        LOG.info("Checking VM connectivity to %s", ip_address)
        self.check_vm_connectivity(ip_address=ip_address,
                                   private_key=self.keypair['private_key'],
                                   server=self.instance)
        LOG.info("VM connectivity verified")

        LOG.info("Getting remote client for instance")
        vm_client = self.get_remote_client(ip_address, server=self.instance)

        # We expect the ephemeral partition to be mounted on /mnt and to have
        # the same size as our flavor definition.
        eph_size = self.get_flavor_ephemeral_size()
        if eph_size and not self.wholedisk_image:
            LOG.info("Starting ephemeral partition verification (size=%d GiB)",
                     eph_size)
            self.verify_partition(vm_client, 'ephemeral0', '/mnt', eph_size)
            LOG.info("Ephemeral partition verified successfully")

            LOG.info("Creating timestamp file on ephemeral partition")
            # Create the test file
            self.create_timestamp(ip_address,
                                  private_key=self.keypair['private_key'],
                                  server=self.instance)
            LOG.info("Timestamp file created")

        if CONF.baremetal.boot_mode == "uefi":
            LOG.info("Starting UEFI boot mode validation")
            self.validate_uefi(vm_client)
            LOG.info("UEFI validation completed")

        # Test rescue mode
        if self.TEST_RESCUE_MODE:
            LOG.info("Starting rescue mode test for instance %s, node %s",
                     self.instance['id'], self.node['uuid'])
            self.rescue_instance(self.instance, self.node, ip_address)

            LOG.info("Starting unrescue operation for instance %s",
                     self.instance['id'])
            self.unrescue_instance(self.instance, self.node, ip_address)

        LOG.info("Terminating instance %s", self.instance['id'])
        self.terminate_instance(self.instance)

    @decorators.idempotent_id('549173a5-38ec-42bb-b0e2-c8b9f4a08943')
    @utils.services('compute', 'image', 'network')
    def test_baremetal_server_ops_partition_image(self):
        # NOTE(dtantsur): cirros partition images don't have grub, we cannot
        # use local boot on BIOS with them.
        if (CONF.baremetal.partition_netboot
                and CONF.baremetal.default_boot_option == 'local'):
            raise self.skipException(
                "Cannot test partition images with local boot on cirros")

        self.image_ref = CONF.baremetal.partition_image_ref
        self.wholedisk_image = False
        self.baremetal_server_ops()

    @decorators.idempotent_id('d7d48aa1-0395-4f31-a908-60969adc4322')
    @utils.services('compute', 'image', 'network')
    def test_baremetal_server_ops_wholedisk_image(self):
        self.image_ref = CONF.baremetal.whole_disk_image_ref
        self.wholedisk_image = True
        self.auto_lease = True
        self.baremetal_server_ops()


class BaremetalBasicOpsAndRescue(BaremetalBasicOps):
    """This test includes rescue/unrescue ops."""

    TEST_RESCUE_MODE = True
