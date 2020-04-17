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


class BaremetalAdoptionDriverWholedisk(
        bsm.BaremetalStandaloneScenarioTest):

    if 'redfish' in CONF.baremetal.enabled_hardware_types:
        driver = 'redfish'
    else:
        driver = 'ipmi'
    image_ref = CONF.baremetal.whole_disk_image_ref
    wholedisk_image = True
    deploy_interface = 'iscsi'
    # 1.37 is required to be able to copy traits
    api_microversion = '1.37'

    @classmethod
    def skip_checks(cls):
        super(BaremetalAdoptionDriverWholedisk, cls).skip_checks()
        if cls.driver == 'ipmi':
            skip_msg = ("Adoption feature is covered by redfish driver")
            raise cls.skipException(skip_msg)
        if not CONF.baremetal_feature_enabled.adoption:
            skip_msg = ("Adoption feature is not enabled")
            raise cls.skipException(skip_msg)

    @classmethod
    def recreate_node(cls):
        # Now record all up-to-date node information for creation
        cls.node = cls.get_node(cls.node['uuid'])
        body = {'driver_info': cls.node['driver_info'],
                'instance_info': cls.node['instance_info'],
                'driver': cls.node['driver'],
                'properties': cls.node['properties']}
        if set(body['driver_info'].get('redfish_password')) == {'*'}:
            # A hack to enable devstack testing without showing secrets
            # secrets. Use the hardcoded devstack value.
            body['driver_info']['redfish_password'] = 'password'
        # configdrive is hidden and anyway should be supplied on rebuild
        body['instance_info'].pop('configdrive', None)
        for key, value in cls.node.items():
            if key.endswith('_interface') and value:
                body[key] = value
        traits = cls.node['traits']
        _, vifs = cls.baremetal_client.vif_list(cls.node['uuid'])
        _, ports = cls.baremetal_client.list_ports(node=cls.node['uuid'])

        # Delete the active node using maintenance
        cls.update_node(cls.node['uuid'], [{'op': 'replace',
                                            'path': '/maintenance',
                                            'value': True}])
        cls.baremetal_client.delete_node(cls.node['uuid'])

        # Now create an identical node and attach VIFs
        _, cls.node = cls.baremetal_client.create_node_raw(**body)
        if traits:
            cls.baremetal_client.set_node_traits(cls.node['uuid'], traits)
        for port in ports['ports']:
            cls.baremetal_client.create_port(cls.node['uuid'],
                                             address=port['address'])

        cls.set_node_provision_state(cls.node['uuid'], 'manage')
        cls.wait_provisioning_state(cls.node['uuid'], 'manageable',
                                    timeout=300, interval=5)

        for vif in vifs['vifs']:
            cls.vif_attach(cls.node['uuid'], vif['id'])

        return cls.node

    @decorators.idempotent_id('2f51890e-20d9-43ef-af39-41b335ec066b')
    @utils.services('image', 'network')
    def test_adoption(self):
        # First, prepare a deployed node.
        self.boot_node()

        # Then re-create it with the same parameters.
        self.recreate_node()

        # Now adoption!
        self.set_node_provision_state(self.node['uuid'], 'adopt')
        self.wait_provisioning_state(self.node['uuid'], 'active',
                                     timeout=300, interval=5)

        # Try to rebuild the server to make sure we can manage it now.
        self.set_node_provision_state(self.node['uuid'], 'rebuild')
        self.wait_provisioning_state(self.node['uuid'], 'active',
                                     timeout=CONF.baremetal.active_timeout,
                                     interval=30)
