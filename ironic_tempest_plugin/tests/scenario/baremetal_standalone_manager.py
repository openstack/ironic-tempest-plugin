#
#    Copyright 2017 Mirantis Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import random

from oslo_utils import uuidutils
from tempest import config
from tempest.lib.common.utils.linux import remote_client
from tempest.lib.common.utils import test_utils
from tempest.lib import exceptions as lib_exc
from tempest.scenario import manager

from ironic_tempest_plugin.services.baremetal import base
from ironic_tempest_plugin.tests.scenario import baremetal_manager as bm

CONF = config.CONF


class BaremetalStandaloneManager(bm.BaremetalScenarioTest,
                                 manager.NetworkScenarioTest):

    credentials = ['primary', 'admin', 'system_admin']
    # NOTE(vsaienko): Standalone tests are using v1/node/<node_ident>/vifs to
    # attach VIF to a node.
    min_microversion = '1.28'

    image_ref = None
    image_checksum = None
    boot_option = None

    @classmethod
    def skip_checks(cls):
        """Defines conditions to skip these tests."""
        super(BaremetalStandaloneManager, cls).skip_checks()
        if CONF.service_available.nova:
            raise cls.skipException('Nova is enabled. Stand-alone tests will '
                                    'be skipped.')

    @classmethod
    def create_networks(cls):
        """Create a network with a subnet connected to a router.

        Return existed network specified in compute/fixed_network_name
        config option.
        TODO(vsaienko): Add network/subnet/router when we setup
        ironic-standalone with multitenancy.

        :returns: network, subnet, router
        """
        network = None
        subnet = None
        router = None
        if CONF.network.shared_physical_network:
            if not CONF.compute.fixed_network_name:
                m = ('Configuration option "[compute]/fixed_network_name" '
                     'must be set.')
                raise lib_exc.InvalidConfiguration(m)
            network = cls.os_admin.networks_client.list_networks(
                name=CONF.compute.fixed_network_name)['networks'][0]
        return network, subnet, router

    @classmethod
    def get_available_nodes(cls):
        """Get all ironic nodes that can be deployed.

        We can deploy on nodes when the following conditions are met:
          * provision_state is 'available'
          * maintenance is False
          * No instance_uuid is associated to node.

        :returns: a list of Ironic nodes.
        """
        fields = ['uuid', 'driver', 'instance_uuid', 'provision_state',
                  'name', 'maintenance']
        _, body = cls.baremetal_client.list_nodes(provision_state='available',
                                                  associated=False,
                                                  maintenance=False,
                                                  fields=','.join(fields))
        return body['nodes']

    @classmethod
    def get_random_available_node(cls):
        """Randomly pick an available node for deployment."""
        nodes = cls.get_available_nodes()
        if nodes:
            return random.choice(nodes)

    @classmethod
    def create_neutron_port(cls, *args, **kwargs):
        """Creates a neutron port.

        For a full list of available parameters, please refer to the official
        API reference:
        https://docs.openstack.org/api-ref/network/v2/index.html#create-port

        :returns: server response body.
        """
        port = cls.ports_client.create_port(*args, **kwargs)['port']
        return port

    @classmethod
    def _associate_instance_with_node(cls, node_id, instance_uuid):
        """Update instance_uuid for a given node.

        :param node_id: Name or UUID of the node.
        :param instance_uuid: UUID of the instance to associate.
        :returns: server response body.
        """
        _, body = cls.baremetal_client.update_node(
            node_id, instance_uuid=instance_uuid)
        return body

    @classmethod
    def get_node_vifs(cls, node_id):
        """Return a list of VIFs for a given node.

        :param node_id: Name or UUID of the node.
        :returns: A list of VIFs associated with the node.
        """
        _, body = cls.baremetal_client.vif_list(node_id)
        vifs = [v['id'] for v in body['vifs']]
        return vifs

    @classmethod
    def add_floatingip_to_node(cls, node_id):
        """Add floating IP to node.

        Create and associate floating IP with node VIF.

        :param node_id: Name or UUID of the node.
        :returns: IP address of associated floating IP.
        """
        vif = cls.get_node_vifs(node_id)[0]
        body = cls.floating_ips_client.create_floatingip(
            floating_network_id=CONF.network.public_network_id)
        floating_ip = body['floatingip']
        cls.floating_ips_client.update_floatingip(floating_ip['id'],
                                                  port_id=vif)
        return floating_ip['floating_ip_address']

    @classmethod
    def get_server_ip(cls, node_id):
        """Get the server fixed IP.

        :param node_id: Name or UUID of the node.
        :returns: IP address of associated fixed IP.
        """
        vif = cls.get_node_vifs(node_id)[0]
        body = cls.ports_client.show_port(vif)['port']
        fixed_ip = body['fixed_ips'][0]
        return fixed_ip['ip_address']

    @classmethod
    def cleanup_floating_ip(cls, ip_address):
        """Removes floating IP."""
        body = cls.os_admin.floating_ips_client.list_floatingips()
        floating_ip_id = [f['id'] for f in body['floatingips'] if
                          f['floating_ip_address'] == ip_address][0]
        cls.os_admin.floating_ips_client.delete_floatingip(floating_ip_id)

    @classmethod
    @bm.retry_on_conflict
    def detach_all_vifs_from_node(cls, node_id, force_delete=False):
        """Detach all VIFs from a given node.

        :param node_id: Name or UUID of the node.
        """
        vifs = cls.get_node_vifs(node_id)
        for vif in vifs:
            cls.baremetal_client.vif_detach(node_id, vif)
            if force_delete:
                try:
                    cls.ports_client.delete_port(vif)
                except lib_exc.NotFound:
                    pass

    @classmethod
    @bm.retry_on_conflict
    def vif_attach(cls, node_id, vif_id):
        """Attach VIF to a give node.

        :param node_id: Name or UUID of the node.
        :param vif_id: Identifier of the VIF to attach.
        """
        cls.baremetal_client.vif_attach(node_id, vif_id)

    @classmethod
    def get_and_reserve_node(cls, node=None):
        """Pick an available node for deployment and reserve it.

        Only one instance_uuid may be associated, use this behaviour as
        reservation node when tests are launched concurrently. If node is
        not passed directly pick random available for deployment node.

        :param node: Ironic node to associate instance_uuid with.
        :returns: Ironic node.
        """
        instance_uuid = uuidutils.generate_uuid()
        nodes = []

        def _try_to_associate_instance():
            n = node or cls.get_random_available_node()
            if n is None:
                return False
            try:
                cls._associate_instance_with_node(n['uuid'], instance_uuid)
                nodes.append(n)
            except lib_exc.Conflict:
                return False
            return True

        if (not test_utils.call_until_true(
                _try_to_associate_instance,
                duration=CONF.baremetal.association_timeout, sleep_for=1)):
            msg = ('Timed out waiting to associate instance to ironic node '
                   'uuid %s' % instance_uuid)
            raise lib_exc.TimeoutException(msg)

        return nodes[0]

    @classmethod
    def boot_node(cls, image_ref=None, image_checksum=None,
                  boot_option=None):
        """Boot ironic node.

        The following actions are executed:
          * Create/Pick networks to boot node in.
          * Create Neutron port and attach it to node.
          * Update node image_source/root_gb.
          * Deploy node.
          * Wait until node is deployed.

        :param image_ref: Reference to user image to boot node with.
        :param image_checksum: md5sum of image specified in image_ref.
                               Needed only when direct HTTP link is provided.
        :param boot_option: The defaut boot option to utilize. If not
                            specified, the ironic deployment default shall
                            be utilized.
        """
        if image_ref is None:
            image_ref = cls.image_ref
        if image_checksum is None:
            image_checksum = cls.image_checksum
        if boot_option is None:
            boot_option = cls.boot_option

        network, subnet, router = cls.create_networks()
        n_port = cls.create_neutron_port(network_id=network['id'])
        cls.vif_attach(node_id=cls.node['uuid'], vif_id=n_port['id'])
        patch = [{'path': '/instance_info/image_source',
                  'op': 'add',
                  'value': image_ref}]
        if image_checksum is not None:
            patch.append({'path': '/instance_info/image_checksum',
                          'op': 'add',
                          'value': image_checksum})
        patch.append({'path': '/instance_info/root_gb',
                      'op': 'add',
                      'value': CONF.baremetal.adjusted_root_disk_size_gb})

        if boot_option:
            patch.append({'path': '/instance_info/capabilities',
                          'op': 'add',
                          'value': {'boot_option': boot_option}})
        # TODO(vsaienko) add testing for custom configdrive
        cls.update_node(cls.node['uuid'], patch=patch)
        cls.set_node_provision_state(cls.node['uuid'], 'active')
        cls.wait_power_state(cls.node['uuid'],
                             bm.BaremetalPowerStates.POWER_ON)
        cls.wait_provisioning_state(cls.node['uuid'],
                                    bm.BaremetalProvisionStates.ACTIVE,
                                    timeout=CONF.baremetal.active_timeout,
                                    interval=30)

    @classmethod
    def terminate_node(cls, node_id, force_delete=False):
        """Terminate active ironic node.

        The following actions are executed:
           * Detach all VIFs from the given node.
           * Unprovision node.
           * Wait until node become available.

        :param node_id: Name or UUID for the node.
        """
        cls.detach_all_vifs_from_node(node_id, force_delete=force_delete)

        if cls.delete_node or force_delete:
            cls.set_node_provision_state(node_id, 'deleted')
            # NOTE(vsaienko) We expect here fast switching from deleted to
            # available as automated cleaning is disabled so poll status
            # each 1s.
            cls.wait_provisioning_state(
                node_id,
                [bm.BaremetalProvisionStates.NOSTATE,
                 bm.BaremetalProvisionStates.AVAILABLE],
                timeout=CONF.baremetal.unprovision_timeout,
                interval=1)

    @classmethod
    def rescue_node(cls, node_id, rescue_password):
        """Rescue the node."""
        cls.set_node_provision_state(node_id, 'rescue',
                                     rescue_password=rescue_password)
        cls.wait_provisioning_state(
            node_id,
            bm.BaremetalProvisionStates.RESCUE,
            timeout=CONF.baremetal.rescue_timeout,
            interval=1)

    @classmethod
    def unrescue_node(cls, node_id):
        """Unrescue the node."""
        cls.set_node_provision_state(node_id, 'unrescue')
        cls.wait_provisioning_state(
            node_id,
            bm.BaremetalProvisionStates.ACTIVE,
            timeout=CONF.baremetal.unrescue_timeout,
            interval=1)

    def manual_cleaning(self, node, clean_steps):
        """Performs manual cleaning.

        The following actions are executed:
           * Expects node to be in available state.
           * Brings the node to manageable state.
           * Do manual cleaning.
           * Brings the node back to original available.

        :param node: Ironic node to associate instance_uuid with.
        :param clean_steps: clean steps for manual cleaning.
        """
        self.set_node_provision_state(node['uuid'], 'manage')
        self.wait_provisioning_state(
            node['uuid'],
            [bm.BaremetalProvisionStates.MANAGEABLE],
            timeout=CONF.baremetal.unprovision_timeout,
            interval=30)
        self.set_node_provision_state(
            node['uuid'], 'clean', clean_steps=clean_steps)
        self.wait_provisioning_state(
            node['uuid'],
            [bm.BaremetalProvisionStates.MANAGEABLE],
            timeout=CONF.baremetal.unprovision_timeout,
            interval=30)
        self.set_node_provision_state(node['uuid'], 'provide')
        self.wait_provisioning_state(
            node['uuid'],
            [bm.BaremetalProvisionStates.NOSTATE,
             bm.BaremetalProvisionStates.AVAILABLE],
            timeout=CONF.baremetal.unprovision_timeout,
            interval=30)

    def check_manual_partition_cleaning(self, node):
        """Tests the cleanup step for erasing devices metadata.

        :param node: Ironic node to associate instance_uuid with, it is
            expected to be in 'active' state
        """
        clean_steps = [
            {
                "interface": "deploy",
                "step": "erase_devices_metadata"
            }
        ]
        self.manual_cleaning(node, clean_steps=clean_steps)
        # TODO(yolanda): we currently are not checking it the cleanup
        # was actually removing the metadata, because there was not a good
        # way to achieve that check for vms and baremetal

    def check_bios_apply_and_reset_configuration(self, node, settings):
        clean_steps = [
            {
                "interface": "bios",
                "step": "apply_configuration",
                "args": {"settings": settings}
            }
        ]
        self.manual_cleaning(node, clean_steps=clean_steps)

        # query the api to check node bios settings
        _, bios_settings = self.baremetal_client.list_node_bios_settings(
            node['uuid'])

        for setting in settings:
            self.assertIn(setting['name'],
                          [i['name'] for i in bios_settings['bios']])
            self.assertIn(setting['value'],
                          [i['value'] for i in bios_settings['bios']])

        # reset bios and ensure that the settings are not there
        clean_steps = [
            {
                "interface": "bios",
                "step": "factory_reset"
            }
        ]
        self.manual_cleaning(node, clean_steps=clean_steps)
        _, bios_settings = self.baremetal_client.list_node_bios_settings(
            node['uuid'])
        self.assertEqual([], bios_settings['bios'])


class BaremetalStandaloneScenarioTest(BaremetalStandaloneManager):

    # API microversion to use among all calls
    api_microversion = '1.28'

    # The node driver to use in the test
    driver = None

    # The bios interface to use by the HW type. The bios interface of the
    # node used in the test will be set to this value. If set to None, the
    # node will retain its existing bios_interface value (which may have been
    # set via a different test).
    bios_interface = None

    # The deploy interface to use by the HW type. The deploy interface of
    # the node used in the test will be set to this value. If set to None,
    # the node will retain its existing deploy_interface value (which may have
    # been set via a different test).
    deploy_interface = None

    # The rescue interface to use by the HW type. The rescue interface of
    # the node used in the test will be set to this value. If set to None,
    # the node will retain its existing rescue_interface value (which may have
    # been set via a different test).
    rescue_interface = None

    # The boot interface to use by the HW type. The boot interface of the
    # node used in the test will be set to this value. If set to None, the
    # node will retain its existing boot_interface value (which may have been
    # set via a different test).
    boot_interface = None

    # The raid interface to use by the HW type. The raid interface of the
    # node used in the test will be set to this value. If set to None, the
    # node will retain its existing raid_interface value (which may have been
    # set via a different test).
    raid_interface = None

    # Boolean value specify if image is wholedisk or not.
    wholedisk_image = None

    # If we need to set provision state 'deleted' for the node  after test
    delete_node = True

    mandatory_attr = ['driver', 'image_ref', 'wholedisk_image']

    node = None
    node_ip = None

    @classmethod
    def skip_checks(cls):
        super(BaremetalStandaloneScenarioTest, cls).skip_checks()
        if (cls.driver not in CONF.baremetal.enabled_drivers
                + CONF.baremetal.enabled_hardware_types):
            raise cls.skipException(
                'The driver: %(driver)s used in test is not in the list of '
                'enabled_drivers %(enabled_drivers)s or '
                'enabled_hardware_types %(enabled_hw_types)s '
                'in the tempest config.' % {
                    'driver': cls.driver,
                    'enabled_drivers': CONF.baremetal.enabled_drivers,
                    'enabled_hw_types': CONF.baremetal.enabled_hardware_types})
        if (cls.bios_interface and cls.bios_interface not in
                CONF.baremetal.enabled_bios_interfaces):
            raise cls.skipException(
                "Bios interface %(iface)s required by the test is not in the "
                "list of enabled bios interfaces %(enabled)s" % {
                    'iface': cls.bios_interface,
                    'enabled': CONF.baremetal.enabled_bios_interfaces})
        if (cls.deploy_interface and cls.deploy_interface not in
                CONF.baremetal.enabled_deploy_interfaces):
            raise cls.skipException(
                "Deploy interface %(iface)s required by test is not "
                "in the list of enabled deploy interfaces %(enabled)s" % {
                    'iface': cls.deploy_interface,
                    'enabled': CONF.baremetal.enabled_deploy_interfaces})
        if (cls.rescue_interface and cls.rescue_interface not in
                CONF.baremetal.enabled_rescue_interfaces):
            raise cls.skipException(
                "Rescue interface %(iface)s required by test is not "
                "in the list of enabled rescue interfaces %(enabled)s" % {
                    'iface': cls.rescue_interface,
                    'enabled': CONF.baremetal.enabled_rescue_interfaces})
        if (cls.boot_interface and cls.boot_interface not in
                CONF.baremetal.enabled_boot_interfaces):
            raise cls.skipException(
                "Boot interface %(iface)s required by test is not "
                "in the list of enabled boot interfaces %(enabled)s" % {
                    'iface': cls.boot_interface,
                    'enabled': CONF.baremetal.enabled_boot_interfaces})
        if (cls.raid_interface and cls.raid_interface not in
                CONF.baremetal.enabled_raid_interfaces):
            raise cls.skipException(
                "RAID interface %(iface)s required by test is not "
                "in the list of enabled RAID interfaces %(enabled)s" % {
                    'iface': cls.raid_interface,
                    'enabled': CONF.baremetal.enabled_raid_interfaces})
        if not cls.wholedisk_image and CONF.baremetal.use_provision_network:
            raise cls.skipException(
                'Partitioned images are not supported with multitenancy.')

    @classmethod
    def set_node_to_active(cls, image_ref=None, image_checksum=None):
        cls.boot_node(image_ref, image_checksum)
        if CONF.validation.connect_method == 'floating':
            cls.node_ip = cls.add_floatingip_to_node(cls.node['uuid'])
        elif CONF.validation.connect_method == 'fixed':
            cls.node_ip = cls.get_server_ip(cls.node['uuid'])
        else:
            m = ('Configuration option "[validation]/connect_method" '
                 'must be set.')
            raise lib_exc.InvalidConfiguration(m)

    @classmethod
    def resource_setup(cls):
        super(BaremetalStandaloneScenarioTest, cls).resource_setup()
        base.set_baremetal_api_microversion(cls.api_microversion)
        for v in cls.mandatory_attr:
            if getattr(cls, v) is None:
                raise lib_exc.InvalidConfiguration(
                    "Mandatory attribute %s not set." % v)
        image_checksum = None
        if not uuidutils.is_uuid_like(cls.image_ref):
            image_checksum = cls.image_checksum
        boot_kwargs = {'image_checksum': image_checksum}
        if cls.bios_interface:
            boot_kwargs['bios_interface'] = cls.bios_interface
        if cls.deploy_interface:
            boot_kwargs['deploy_interface'] = cls.deploy_interface
        if cls.rescue_interface:
            boot_kwargs['rescue_interface'] = cls.rescue_interface
        if cls.boot_interface:
            boot_kwargs['boot_interface'] = cls.boot_interface
        if cls.raid_interface:
            boot_kwargs['raid_interface'] = cls.raid_interface

        # just get an available node
        cls.node = cls.get_and_reserve_node()
        cls.update_node_driver(cls.node['uuid'], cls.driver, **boot_kwargs)

    @classmethod
    def resource_cleanup(cls):
        if CONF.validation.connect_method == 'floating':
            if cls.node_ip:
                cls.cleanup_floating_ip(cls.node_ip)

        vifs = cls.get_node_vifs(cls.node['uuid'])
        # Remove ports before deleting node, to catch regression for cases
        # when user did this prior unprovision node.
        for vif in vifs:
            try:
                cls.ports_client.delete_port(vif)
            except lib_exc.NotFound:
                pass
        cls.terminate_node(cls.node['uuid'])
        base.reset_baremetal_api_microversion()
        super(BaremetalStandaloneManager, cls).resource_cleanup()

    def boot_and_verify_node(self, image_ref=None, image_checksum=None,
                             should_succeed=True):
        self.set_node_to_active(image_ref, image_checksum)
        self.assertTrue(self.ping_ip_address(self.node_ip,
                                             should_succeed=should_succeed))

    def build_raid_and_verify_node(self, config=None, deploy_time=False):
        config = config or self.raid_config
        if deploy_time:
            steps = [
                {
                    "interface": "deploy",
                    "step": "erase_devices_metadata",
                    "priority": 98,
                    "args": {},
                },
                {
                    "interface": "raid",
                    "step": "apply_configuration",
                    "priority": 97,
                    "args": {"raid_config": config},
                }
            ]
            self.baremetal_client.create_deploy_template(
                'CUSTOM_RAID', steps=steps)
            self.baremetal_client.add_node_trait(self.node['uuid'],
                                                 'CUSTOM_RAID')

        else:
            steps = [
                {
                    "interface": "raid",
                    "step": "delete_configuration"
                },
                {
                    "interface": "deploy",
                    "step": "erase_devices_metadata",
                },
                {
                    "interface": "raid",
                    "step": "create_configuration",
                }
            ]
            self.baremetal_client.set_node_raid_config(self.node['uuid'],
                                                       config)
            self.manual_cleaning(self.node, clean_steps=steps)

        # The node has been changed, anything at this point, we need to back
        # out the raid configuration.
        if not deploy_time:
            self.addCleanup(self.remove_raid_configuration, self.node)

        # NOTE(dtantsur): this is not required, but it allows us to check that
        # the RAID device was in fact created and is used for deployment.
        patch = [{'path': '/properties/root_device',
                  'op': 'add', 'value': {'name': '/dev/md0'}}]
        if deploy_time:
            patch.append({'path': '/instance_info/traits',
                          'op': 'add', 'value': ['CUSTOM_RAID']})
        self.update_node(self.node['uuid'], patch=patch)
        # NOTE(dtantsur): apparently cirros cannot boot from md devices :(
        # So we only move the node to active (verifying deployment).
        self.set_node_to_active()
        if deploy_time:
            self.addCleanup(self.remove_raid_configuration, self.node)

    def remove_root_device_hint(self):
        patch = [{'path': '/properties/root_device',
                  'op': 'remove'}]
        self.update_node(self.node['uuid'], patch=patch)

    def remove_raid_configuration(self, node):
        self.baremetal_client.set_node_raid_config(node['uuid'], {})
        steps = [
            {
                "interface": "raid",
                "step": "delete_configuration",
            },
            {
                "interface": "deploy",
                "step": "erase_devices_metadata",
            }
        ]
        self.manual_cleaning(node, clean_steps=steps)

    def rescue_unrescue(self):
        rescue_password = uuidutils.generate_uuid()
        self.rescue_node(self.node['uuid'], rescue_password)
        self.assertTrue(self.ping_ip_address(self.node_ip,
                                             should_succeed=True))

        # Open ssh connection to server
        linux_client = remote_client.RemoteClient(
            self.node_ip,
            'rescue',
            password=rescue_password,
            ssh_timeout=CONF.baremetal.rescue_timeout)
        linux_client.validate_authentication()

        self.unrescue_node(self.node['uuid'])
        self.assertTrue(self.ping_ip_address(self.node_ip,
                                             should_succeed=True))

    @classmethod
    def boot_node_ramdisk(cls, ramdisk_ref, iso=False):
        """Boot ironic using a ramdisk node.

        The following actions are executed:
          * Create/Pick networks to boot node in.
          * Create Neutron port and attach it to node.
          * Update node image_source.
          * Deploy node.
          * Wait until node is deployed.

        :param ramdisk_ref: Reference to user image or ramdisk to boot
                            the node with.
        :param iso: Boolean, default False, to indicate if the image ref
                    us actually an ISO image.
        """
        if ramdisk_ref is None:
            ramdisk_ref = cls.image_ref

        network, subnet, router = cls.create_networks()
        n_port = cls.create_neutron_port(network_id=network['id'])
        cls.vif_attach(node_id=cls.node['uuid'], vif_id=n_port['id'])
        if iso:
            patch_path = '/instance_info/boot_iso'
        else:
            # NOTE(TheJulia): The non ISO ramdisk path supports this
            # and it being here makes it VERY easy for us to add a test
            # of just a kernel/ramdisk loading from glance at some point.
            patch_path = '/instance_info/image_source'
        patch = [{'path': patch_path,
                  'op': 'add',
                  'value': ramdisk_ref}]
        cls.update_node(cls.node['uuid'], patch=patch)
        cls.set_node_provision_state(cls.node['uuid'], 'active')
        if CONF.validation.connect_method == 'floating':
            cls.node_ip = cls.add_floatingip_to_node(cls.node['uuid'])
        elif CONF.validation.connect_method == 'fixed':
            cls.node_ip = cls.get_server_ip(cls.node['uuid'])
        else:
            m = ('Configuration option "[validation]/connect_method" '
                 'must be set.')
            raise lib_exc.InvalidConfiguration(m)
        cls.wait_power_state(cls.node['uuid'],
                             bm.BaremetalPowerStates.POWER_ON)
        cls.wait_provisioning_state(cls.node['uuid'],
                                    bm.BaremetalProvisionStates.ACTIVE,
                                    timeout=CONF.baremetal.active_timeout,
                                    interval=30)

    def boot_and_verify_ramdisk_node(self, ramdisk_ref=None, iso=False,
                                     should_succeed=True):
        self.boot_node_ramdisk(ramdisk_ref, iso)
        self.assertTrue(self.ping_ip_address(self.node_ip,
                                             should_succeed=should_succeed))
