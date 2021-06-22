# Copyright 2012 OpenStack Foundation
# Copyright 2013 IBM Corp.
# All Rights Reserved.
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

import time

from tempest.common import waiters
from tempest import config
from tempest.lib.common import api_version_utils
from tempest.lib.common.utils.linux import remote_client
from tempest.lib import exceptions as lib_exc

from ironic_tempest_plugin.common import utils
from ironic_tempest_plugin.common import waiters as ironic_waiters
from ironic_tempest_plugin import manager

CONF = config.CONF


def retry_on_conflict(func):
    def inner(*args, **kwargs):
        # TODO(vsaienko): make number of retries and delay between
        # them configurable in future.
        for att in range(10):
            try:
                return func(*args, **kwargs)
            except lib_exc.Conflict:
                if att == 9:
                    raise
                time.sleep(1)
    return inner


# power/provision states as of icehouse
class BaremetalPowerStates(object):
    """Possible power states of an Ironic node."""
    POWER_ON = 'power on'
    POWER_OFF = 'power off'
    REBOOT = 'rebooting'
    SUSPEND = 'suspended'


class BaremetalProvisionStates(object):
    """Possible provision states of an Ironic node."""
    ENROLL = 'enroll'
    NOSTATE = None
    AVAILABLE = 'available'
    INIT = 'initializing'
    ACTIVE = 'active'
    BUILDING = 'building'
    DEPLOYWAIT = 'wait call-back'
    DEPLOYING = 'deploying'
    DEPLOYFAIL = 'deploy failed'
    DEPLOYDONE = 'deploy complete'
    DELETING = 'deleting'
    DELETED = 'deleted'
    ERROR = 'error'
    MANAGEABLE = 'manageable'
    RESCUE = 'rescue'


class BaremetalScenarioTest(manager.ScenarioTest):

    credentials = ['primary', 'admin', 'system_admin']
    min_microversion = None
    max_microversion = api_version_utils.LATEST_MICROVERSION

    @classmethod
    def skip_checks(cls):
        super(BaremetalScenarioTest, cls).skip_checks()
        if not CONF.service_available.ironic:
            raise cls.skipException('Ironic is not enabled.')
        cfg_min_version = CONF.baremetal.min_microversion
        cfg_max_version = CONF.baremetal.max_microversion
        api_version_utils.check_skip_with_microversion(cls.min_microversion,
                                                       cls.max_microversion,
                                                       cfg_min_version,
                                                       cfg_max_version)

    @classmethod
    def setup_clients(cls):
        super(BaremetalScenarioTest, cls).setup_clients()
        if CONF.enforce_scope.ironic:
            client = cls.os_system_admin.baremetal.BaremetalClient()
        else:
            client = cls.os_admin.baremetal.BaremetalClient()
        cls.baremetal_client = client

    @classmethod
    def resource_setup(cls):
        super(BaremetalScenarioTest, cls).resource_setup()
        # allow any issues obtaining the node list to raise early
        cls.baremetal_client.list_nodes()

    @classmethod
    def wait_provisioning_state(cls, node_id, state, timeout=10, interval=1,
                                abort_on_error_state=True):
        ironic_waiters.wait_for_bm_node_status(
            cls.baremetal_client, node_id=node_id, attr='provision_state',
            status=state, timeout=timeout, interval=interval,
            abort_on_error_state=abort_on_error_state)

    @classmethod
    def wait_power_state(cls, node_id, state):
        ironic_waiters.wait_for_bm_node_status(
            cls.baremetal_client, node_id=node_id, attr='power_state',
            status=state, timeout=CONF.baremetal.power_timeout)

    def wait_node(self, instance_id):
        """Waits for a node to be associated with instance_id."""
        ironic_waiters.wait_node_instance_association(self.baremetal_client,
                                                      instance_id)

    @classmethod
    def get_node(cls, node_id=None, instance_id=None, api_version=None):
        return utils.get_node(cls.baremetal_client, node_id, instance_id,
                              api_version)

    def get_ports(self, node_uuid):
        ports = []
        _, body = self.baremetal_client.list_node_ports(node_uuid)
        for port in body['ports']:
            _, p = self.baremetal_client.show_port(port['uuid'])
            ports.append(p)
        return ports

    def get_node_vifs(self, node_uuid, api_version='1.28'):
        _, body = self.baremetal_client.vif_list(node_uuid,
                                                 api_version=api_version)
        return body['vifs']

    def add_keypair(self):
        self.keypair = self.create_keypair()

    @classmethod
    @retry_on_conflict
    def update_node_driver(cls, node_id, driver, **interfaces):
        _, body = cls.baremetal_client.update_node(
            node_id, driver=driver, **interfaces)
        return body

    @classmethod
    @retry_on_conflict
    def update_node(cls, node_id, patch):
        cls.baremetal_client.update_node(node_id, patch=patch)

    @classmethod
    @retry_on_conflict
    def set_node_provision_state(cls, node_id, state, configdrive=None,
                                 clean_steps=None, rescue_password=None):
        cls.baremetal_client.set_node_provision_state(
            node_id, state, configdrive=configdrive,
            clean_steps=clean_steps, rescue_password=rescue_password)

    def verify_connectivity(self, ip=None):
        if ip:
            dest = self.get_remote_client(ip)
        else:
            dest = self.get_remote_client(self.instance)
        dest.validate_authentication()

    def boot_instance(self, clients=None, keypair=None,
                      net_id=None, fixed_ip=None, **create_kwargs):
        if clients is None:
            servers_client = self.os_primary.servers_client
        else:
            servers_client = clients.servers_client
        if keypair is None:
            keypair = self.keypair

        if any([net_id, fixed_ip]):
            network = {}
            if net_id:
                network['uuid'] = net_id
            if fixed_ip:
                network['fixed_ip'] = fixed_ip
            instance = self.create_server(
                key_name=keypair['name'],
                networks=[network],
                clients=clients,
                **create_kwargs
            )
        else:
            instance = self.create_server(
                key_name=keypair['name'],
                clients=clients,
                **create_kwargs
            )

        self.wait_node(instance['id'])
        node = self.get_node(instance_id=instance['id'])

        self.wait_power_state(node['uuid'], BaremetalPowerStates.POWER_ON)

        self.wait_provisioning_state(
            node['uuid'],
            [BaremetalProvisionStates.DEPLOYWAIT,
             BaremetalProvisionStates.ACTIVE],
            timeout=CONF.baremetal.deploywait_timeout)

        self.wait_provisioning_state(node['uuid'],
                                     BaremetalProvisionStates.ACTIVE,
                                     timeout=CONF.baremetal.active_timeout,
                                     interval=30)

        waiters.wait_for_server_status(servers_client,
                                       instance['id'], 'ACTIVE')
        node = self.get_node(instance_id=instance['id'])
        instance = servers_client.show_server(instance['id'])['server']

        return instance, node

    def terminate_instance(self, instance, servers_client=None):
        if servers_client is None:
            servers_client = self.os_primary.servers_client

        node = self.get_node(instance_id=instance['id'])
        servers_client.delete_server(instance['id'])
        self.wait_power_state(node['uuid'],
                              BaremetalPowerStates.POWER_OFF)
        self.wait_provisioning_state(
            node['uuid'],
            [BaremetalProvisionStates.NOSTATE,
             BaremetalProvisionStates.AVAILABLE],
            timeout=CONF.baremetal.unprovision_timeout,
            interval=30)

    def rescue_instance(self, instance, node, server_ip,
                        servers_client=None):
        """Rescue the instance, verify we can ping and SSH."""
        if servers_client is None:
            servers_client = self.os_primary.servers_client

        rescuing_instance = servers_client.rescue_server(instance['id'])
        rescue_password = rescuing_instance['adminPass']

        self.wait_provisioning_state(
            node['uuid'],
            BaremetalProvisionStates.RESCUE,
            timeout=CONF.baremetal.rescue_timeout)
        waiters.wait_for_server_status(servers_client,
                                       instance['id'], 'RESCUE')
        # Ping server ip
        self.assertTrue(self.ping_ip_address(server_ip))
        # Open ssh connection to server
        linux_client = remote_client.RemoteClient(
            server_ip,
            'rescue',
            password=rescue_password,
            server=self.instance,
            servers_client=servers_client,
            ssh_timeout=CONF.baremetal.rescue_timeout)
        linux_client.validate_authentication()

    def unrescue_instance(self, instance, node, server_ip,
                          servers_client=None):
        if servers_client is None:
            servers_client = self.os_primary.servers_client
        self.os_primary.servers_client.unrescue_server(instance['id'])
        self.wait_provisioning_state(
            node['uuid'],
            BaremetalProvisionStates.ACTIVE,
            timeout=CONF.baremetal.unrescue_timeout)
        waiters.wait_for_server_status(servers_client,
                                       instance['id'], 'ACTIVE')
        # Verify server connection
        self.get_remote_client(server_ip)
