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

from oslo_utils import timeutils
from tempest import config
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from ironic_tempest_plugin.tests.api import base


CONF = config.CONF

# enabling a console blocks in the conductor until the container is listening
CONSOLE_TIMEOUT = 120


class TestGraphicalConsole(base.BaseBaremetalTest):
    """Tests for the graphical console of a node.

    A console is only reported as enabled once the configured console
    container provider has started the container and its published VNC
    endpoint is listening.
    """

    # 1.31 is where console_interface can be set on a node
    min_microversion = '1.31'

    @classmethod
    def skip_checks(cls):
        super(TestGraphicalConsole, cls).skip_checks()
        if 'fake-graphical' not in CONF.baremetal.enabled_console_interfaces:
            raise cls.skipException(
                'The fake-graphical console interface is not enabled.')

    def setUp(self):
        super(TestGraphicalConsole, self).setUp()
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(
            self.chassis['uuid'], console_interface='fake-graphical')

    def _set_console_mode(self, enabled):
        """Set the console mode and wait for the conductor to apply it.

        :param enabled: whether the console should be enabled or disabled.
        :returns: the console state once it matches the request.

        """
        self.client.set_node_console_mode(self.node['uuid'], enabled)

        start = timeutils.utcnow()
        while timeutils.delta_seconds(
                start, timeutils.utcnow()) < CONSOLE_TIMEOUT:
            _, console = self.client.show_node_console(self.node['uuid'])
            if console['console_enabled'] == enabled:
                return console
            _, node = self.client.show_node(self.node['uuid'])
            if node['last_error']:
                self.fail('Failed to set the console mode to %s: %s'
                          % (enabled, node['last_error']))
            time.sleep(1)

        message = ('Failed to set the console mode within '
                   'the required time: %s sec.' % CONSOLE_TIMEOUT)
        raise lib_exc.TimeoutException(message)

    @decorators.idempotent_id('8c49e738-e328-4382-aa7b-008bfa6391e9')
    def test_console_enable_disable(self):
        console = self._set_console_mode(True)
        self.assertEqual('vnc', console['console_info']['type'])
        self.assertIn(self.node['uuid'], console['console_info']['url'])

        # the novnc proxy has to be able to connect to the endpoint, so an
        # unspecified bind address is never published
        _, node = self.client.show_node(self.node['uuid'])
        driver_internal_info = node['driver_internal_info']
        self.assertNotIn(driver_internal_info['vnc_host'], ('0.0.0.0', '::'))
        self.assertGreater(driver_internal_info['vnc_port'], 0)

        console = self._set_console_mode(False)
        self.assertIsNone(console['console_info'])

        _, node = self.client.show_node(self.node['uuid'])
        self.assertNotIn('vnc_host', node['driver_internal_info'])
        self.assertNotIn('vnc_port', node['driver_internal_info'])
