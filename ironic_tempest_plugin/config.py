# Copyright 2015 NEC Corporation
# All Rights Reserved.
#
# Copyright (c) 2022 Dell Inc. or its subsidiaries.
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

from oslo_config import cfg

from tempest import config  # noqa


# NOTE(TheJulia): The following options are loaded into a tempest
# plugin configuration option via plugin.py.
ironic_service_option = cfg.BoolOpt('ironic',
                                    default=False,
                                    help='Whether or not ironic is expected '
                                    'to be available')

inspector_service_option = cfg.BoolOpt("ironic_inspector",
                                       default=False,
                                       help="Whether or not ironic-inspector "
                                       "is expected to be available")

ironic_scope_enforcement = cfg.BoolOpt('ironic',
                                       default=True,
                                       help='Wheter or not ironic is '
                                            'exepcted to enforce auth '
                                            'scope.')

inspector_scope_enforcement = cfg.BoolOpt('ironic_inspector',
                                          default=True,
                                          help='Whether or not '
                                               'ironic-inspector is expected '
                                               'to enforce auth scope.')

baremetal_group = cfg.OptGroup(name='baremetal',
                               title='Baremetal provisioning service options',
                               help='When enabling baremetal tests, Nova '
                                    'must be configured to use the Ironic '
                                    'driver. The following parameters for the '
                                    '[compute] section must be disabled: '
                                    'console_output, interface_attach, '
                                    'live_migration, pause, rescue, resize, '
                                    'shelve, snapshot, and suspend')

# The bulk of the embedded configuration is below.

baremetal_introspection_group = cfg.OptGroup(
    name="baremetal_introspection",
    title="Baremetal introspection service options",
    help="When enabling baremetal introspection tests,"
         "Ironic must be configured.")

baremetal_features_group = cfg.OptGroup(
    name='baremetal_feature_enabled',
    title="Enabled Baremetal Service Features")

BaremetalGroup = [
    cfg.StrOpt('catalog_type',
               default='baremetal',
               help="Catalog type of the baremetal provisioning service"),
    cfg.StrOpt('driver',
               default='fake-hardware',
               help="Driver name to use for API tests"),
    cfg.StrOpt('endpoint_type',
               default='publicURL',
               choices=['public', 'admin', 'internal',
                        'publicURL', 'adminURL', 'internalURL'],
               help="The endpoint type to use for the baremetal provisioning"
                    " service"),
    cfg.StrOpt('root_device_name',
               default='/dev/md0',
               help="Root device name to be used for node deployment"),
    cfg.IntOpt('deploywait_timeout',
               default=15,
               help="Timeout for Ironic node to reach the "
                    "wait-callback state after powering on."),
    cfg.IntOpt('active_timeout',
               default=300,
               help="Timeout for Ironic node to completely provision"),
    cfg.IntOpt('anaconda_active_timeout',
               default=3600,
               help="Timeout for Ironic node to completely provision "
                    "when using the anaconda deployment interface."),
    cfg.IntOpt('association_timeout',
               default=30,
               help="Timeout for association of Nova instance and Ironic "
                    "node"),
    cfg.IntOpt('inspect_timeout',
               default=10,
               help="Timeout for inspecting an Ironic node."),
    cfg.IntOpt('power_timeout',
               default=60,
               help="Timeout for Ironic power transitions."),
    cfg.IntOpt('unprovision_timeout',
               default=300,
               help="Timeout for unprovisioning an Ironic node. "
                    "Takes longer since Kilo as Ironic performs an extra "
                    "step in Node cleaning."),
    cfg.IntOpt('rescue_timeout',
               default=300,
               help="Timeout for rescuing an Ironic node."),
    cfg.IntOpt('unrescue_timeout',
               default=300,
               help="Timeout for unrescuing an Ironic node."),
    cfg.StrOpt('min_microversion',
               help="Lower version of the test target microversion range. "
                    "The format is 'X.Y', where 'X' and 'Y' are int values. "
                    "Tempest selects tests based on the range between "
                    "min_microversion and max_microversion. "
                    "If both values are None, Tempest avoids tests which "
                    "require a microversion."),
    cfg.StrOpt('max_microversion',
               default='latest',
               help="Upper version of the test target microversion range. "
                    "The format is 'X.Y', where 'X' and 'Y' are int values. "
                    "Tempest selects tests based on the range between "
                    "min_microversion and max_microversion. "
                    "If both values are None, Tempest avoids tests which "
                    "require a microversion."),
    cfg.BoolOpt('use_provision_network',
                default=False,
                help="Whether the Ironic/Neutron tenant isolation is enabled"),
    cfg.StrOpt('whole_disk_image_ref',
               help="UUID of the wholedisk image to use in the tests."),
    cfg.StrOpt('whole_disk_image_url',
               help="An http link to the wholedisk image to use in the "
                    "tests."),
    cfg.StrOpt('whole_disk_image_checksum',
               help="An checksum of the image. Recommend SHA256 or SHA512"
                    "as MD5 is deprecated."),
    cfg.StrOpt('partition_image_ref',
               help="UUID of the partitioned image to use in the tests."),
    cfg.StrOpt('ramdisk_iso_image_ref',
               help=("UUID (or url) of an ISO image for the ramdisk boot "
                     "tests.")),
    cfg.StrOpt('storage_inventory_file',
               help="Path to storage inventory file for RAID cleaning tests."),
    cfg.StrOpt('export_location',
               help="Export config location for configuration molds."),
    cfg.StrOpt('import_location',
               help="Import config location for configuration molds."),
    cfg.StrOpt('rollback_import_location',
               help="Rollback import config location for configuration "
                    "molds. Optional. If not provided, rollback is skipped."),
    # TODO(TheJulia): For now, anaconda can be url based and we can move in
    # to being tested with glance as soon as we get a public stage2 image.
    cfg.StrOpt('anaconda_image_ref',
               help="URL of an anaconda repository to set as image_source"),
    cfg.StrOpt('anaconda_kernel_ref',
               help="URL of the kernel to utilize for anaconda deploys."),
    cfg.StrOpt('anaconda_initial_ramdisk_ref',
               help="URL of the initial ramdisk to utilize for anaconda "
                    "deploy operations."),
    cfg.StrOpt('anaconda_stage2_ramdisk_ref',
               help="URL of the anaconda second stage ramdisk. Presence of "
                    "this setting will also determine if a stage2 specific "
                    "anaconda test is run, or not."),
    cfg.StrOpt('anaconda_exit_test_at',
               default='heartbeat',
               choices=['heartbeat', 'active'],
               help='When to end the anaconda test job at. Due to '
                    'the use model of the anaconda driver, as well '
                    'as the performance profile, the anaconda test is '
                    'normally only executed until we observe a heartbeat '
                    'operation indicating that anaconda *has* booted and '
                    'successfully parsed the URL.'),
    cfg.ListOpt('enabled_drivers',
                default=['fake', 'pxe_ipmitool', 'agent_ipmitool'],
                help="List of Ironic enabled drivers."),
    cfg.ListOpt('enabled_hardware_types',
                default=['ipmi'],
                help="List of Ironic enabled hardware types."),
    cfg.ListOpt('enabled_bios_interfaces',
                default=['fake'],
                help="List of Ironic enabled bios interfaces."),
    cfg.ListOpt('enabled_deploy_interfaces',
                default=['iscsi', 'direct'],
                help="List of Ironic enabled deploy interfaces."),
    cfg.ListOpt('enabled_rescue_interfaces',
                default=['no-rescue'],
                help="List of Ironic enabled rescue interfaces."),
    cfg.ListOpt('enabled_boot_interfaces',
                default=['fake', 'pxe'],
                help="List of Ironic enabled boot interfaces."),
    cfg.ListOpt('enabled_raid_interfaces',
                default=['no-raid', 'agent'],
                help="List of Ironic enabled RAID interfaces."),
    cfg.ListOpt('enabled_management_interfaces',
                default=['fake', 'ipmitool', 'noop'],
                help="List of Ironic enabled management interfaces."),
    cfg.ListOpt('enabled_power_interfaces',
                default=['fake', 'ipmitool'],
                help="List of Ironic enabled power interfaces."),
    cfg.StrOpt('default_rescue_interface',
               help="Ironic default rescue interface."),
    cfg.StrOpt('firmware_image_url',
               help="Image URL of firmware image file supported by "
                    "update_firmware clean step."),
    cfg.StrOpt('firmware_image_checksum',
               help="SHA1 checksum of firmware image file."),
    cfg.StrOpt('firmware_rollback_image_url',
               help="Image URL of firmware update cleaning step's "
                    "rollback image. Optional. If not provided, "
                    "rollback is skipped."),
    cfg.StrOpt('firmware_rollback_image_checksum',
               help="SHA1 checksum of firmware rollback image file. "
                    "This is required if firmware_rollback_image_url is set."),
    cfg.IntOpt('adjusted_root_disk_size_gb',
               min=0,
               help="Ironic adjusted disk size to use in the standalone tests "
                    "as instance_info/root_gb value."),
    cfg.IntOpt('available_nodes', min=0, default=None,
               help="The number of baremetal hosts available to use for "
                    "the tests."),
    cfg.BoolOpt('partition_netboot',
                default=True,
                help="Treat partition images as netbooted as opposed to "
                     "attempting to populate a boot loader. IF cirros is "
                     "being used, this option should be set to True as "
                     "it lacks the needed components to make it locally "
                     "from a partition image."),
    cfg.StrOpt('boot_mode',
               default='bios',
               choices=['bios', 'uefi'],
               help="The desired boot_mode to be used on testing nodes."),
    cfg.StrOpt('default_boot_option',
               # No good default here, we need to actually set it.
               help="The default boot option the testing nodes are using."),
    cfg.BoolOpt("rebuild_remote_dhcpless",
                default=True,
                help="If we should issue a rebuild request when testing "
                     "dhcpless virtual media deployments. This may be useful "
                     "if bug 2032377 is not fixed in the agent ramdisk."),
    cfg.StrOpt("public_subnet_id",
               help="The public subnet ID where routers will be bound for "
                    "testing purposes with the dhcp-less test scenario."),
    cfg.StrOpt("public_subnet_ip",
               help="The public subnet IP to bind the public router to for "
                    "dhcp-less testing.")
]

BaremetalFeaturesGroup = [
    cfg.BoolOpt('ipxe_enabled',
                default=True,
                help="Defines if IPXE is enabled"),
    cfg.BoolOpt('adoption',
                # Defaults to False since it's a destructive operation AND it
                # requires the plugin to be able to read ipmi_password.
                default=False,
                help="Defines if adoption is enabled"),
    cfg.BoolOpt('software_raid',
                default=False,
                help="Defines if software RAID is enabled (available "
                     "starting with Train). Requires at least two disks "
                     "on testing nodes."),
    cfg.BoolOpt('deploy_time_raid',
                default=False,
                help="Defines if in-band RAID can be built in deploy time "
                     "(possible starting with Victoria)."),
    cfg.BoolOpt('dhcpless_vmedia',
                default=False,
                help="Defines if it is possible to execute DHCP-Less "
                     "deployment of baremetal nodes through virtual media. "
                     "This test requires full OS images with configuration "
                     "support for embedded network metadata through glean "
                     "or cloud-init, and thus cannot be executed with "
                     "most default job configurations."),
]

BaremetalIntrospectionGroup = [
    cfg.StrOpt('catalog_type',
               default='baremetal-introspection',
               help="Catalog type of the baremetal provisioning service"),
    cfg.StrOpt('endpoint_type',
               default='publicURL',
               choices=['public', 'admin', 'internal',
                        'publicURL', 'adminURL', 'internalURL'],
               help="The endpoint type to use for the baremetal introspection"
                    " service"),
    cfg.IntOpt('introspection_sleep',
               default=30,
               help="Introspection sleep before check status"),
    cfg.IntOpt('introspection_timeout',
               default=600,
               help="Introspection time out"),
    cfg.IntOpt('introspection_start_timeout',
               default=90,
               help="Timeout to start introspection"),
    cfg.IntOpt('hypervisor_update_sleep',
               default=60,
               help="Time to wait until nova becomes aware of "
                    "bare metal instances"),
    cfg.IntOpt('hypervisor_update_timeout',
               default=300,
               help="Time out for wait until nova becomes aware of "
                    "bare metal instances"),
    # NOTE(aarefiev): status_check_period default is 60s, but checking
    # node state takes some time(API call), so races appear here,
    # 80s would be enough to make one more check.
    cfg.IntOpt('ironic_sync_timeout',
               default=80,
               help="Time it might take for Ironic--Inspector "
                    "sync to happen"),
    cfg.IntOpt('discovery_timeout',
               default=300,
               help="Time to wait until new node would enrolled in "
                    "ironic"),
    cfg.BoolOpt('auto_discovery_feature',
                default=False,
                help="Is the auto-discovery feature enabled. Enroll hook "
                     "should be specified in node_not_found_hook - processing "
                     "section of inspector.conf"),
    cfg.StrOpt('auto_discovery_default_driver',
               # TODO(dtantsur): change to fake-hardware when Queens is no
               # longer supported.
               default='fake',
               help="The driver expected to be set on newly discovered nodes. "
                    "Only has effect with auto_discovery_feature is True."),
    cfg.StrOpt('auto_discovery_target_driver',
               help="The driver to set on the newly discovered nodes. "
                    "Only has effect with auto_discovery_feature is True."),
    cfg.StrOpt('data_store',
               help="The storage backend for storing introspection data."),
]
