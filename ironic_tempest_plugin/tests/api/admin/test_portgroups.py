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

from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from ironic_tempest_plugin.tests.api.admin import api_microversion_fixture
from ironic_tempest_plugin.tests.api.admin import base


class TestPortGroups(base.BaseBaremetalTest):
    """Basic positive test cases for port groups."""

    min_microversion = '1.23'

    def setUp(self):
        super(TestPortGroups, self).setUp()
        self.useFixture(
            api_microversion_fixture.APIMicroversionFixture(
                self.min_microversion))
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis['uuid'])
        _, self.portgroup = self.create_portgroup(
            self.node['uuid'], address=data_utils.rand_mac_address(),
            name=data_utils.rand_name('portgroup'))

    @decorators.idempotent_id('110cd302-256b-4ddc-be10-fc6c9ad8e649')
    def test_create_portgroup_with_address(self):
        """Create a port group with specific MAC address."""
        _, body = self.client.show_portgroup(self.portgroup['uuid'])
        self.assertEqual(self.portgroup['address'], body['address'])

    @decorators.idempotent_id('4336fa0f-da86-4cec-b788-89f59a7635a5')
    def test_create_portgroup_no_address(self):
        """Create a port group without setting MAC address."""
        _, portgroup = self.create_portgroup(self.node['uuid'])
        _, body = self.client.show_portgroup(portgroup['uuid'])

        self._assertExpected(portgroup, body)
        self.assertIsNone(body['address'])

    @decorators.idempotent_id('8378c69f-f806-454b-8ddd-6b7fd93ab12b')
    def test_delete_portgroup(self):
        """Delete a port group."""
        self.delete_portgroup(self.portgroup['uuid'])
        self.assertRaises(lib_exc.NotFound, self.client.show_portgroup,
                          self.portgroup['uuid'])

    @decorators.idempotent_id('f6be5e70-3e3b-435c-b2fc-bbb2cc9b3185')
    def test_show_portgroup(self):
        """Show a specified port group."""
        _, portgroup = self.client.show_portgroup(self.portgroup['uuid'])
        self._assertExpected(self.portgroup, portgroup)

    @decorators.idempotent_id('cf2dfd95-5ea1-4109-8ad3-297cd76aa5d3')
    def test_list_portgroups(self):
        """List port groups."""
        _, body = self.client.list_portgroups()
        self.assertIn(self.portgroup['uuid'],
                      [i['uuid'] for i in body['portgroups']])
        self.assertIn(self.portgroup['address'],
                      [i['address'] for i in body['portgroups']])
        self.assertIn(self.portgroup['name'],
                      [i['name'] for i in body['portgroups']])

    @decorators.idempotent_id('6a491006-2dd5-4c82-be39-a4fa015071c0')
    def test_update_portgroup_replace(self):
        """Update portgroup by replacing it's address and extra data."""
        new_address = data_utils.rand_mac_address()
        new_extra = {'foo': 'test'}

        patch = [{'path': '/address',
                  'op': 'replace',
                  'value': new_address},
                 {'path': '/extra/foo',
                  'op': 'replace',
                  'value': new_extra['foo']},
                 ]

        self.client.update_portgroup(self.portgroup['uuid'], patch)

        _, body = self.client.show_portgroup(self.portgroup['uuid'])

        self.assertEqual(new_address, body['address'])
        self._assertExpected(new_extra, body['extra'])

    @decorators.idempotent_id('9834a4ec-be41-40b4-a3a4-8e46ad7eb19d')
    def test_update_portgroup_remove_by_key(self):
        """Update portgroup by removing value from extra data."""
        self.client.update_portgroup(
            self.portgroup['uuid'],
            [{'path': '/extra/foo', 'op': 'remove'}]
        )
        _, body = self.client.show_portgroup(self.portgroup['uuid'])
        self.assertNotIn('foo', body['extra'])
        self._assertExpected({'open': 'stack'}, body['extra'])

    @decorators.idempotent_id('5da2f7c7-03e8-4db0-8c3e-2fe6ebcc4439')
    def test_update_portgroup_remove_collection(self):
        """Update portgroup by removing collection from extra data."""
        self.client.update_portgroup(
            self.portgroup['uuid'],
            [{'path': '/extra', 'op': 'remove'}]
        )
        _, body = self.client.show_portgroup(self.portgroup['uuid'])
        self.assertEqual({}, body['extra'])

    @decorators.idempotent_id('a1123416-7bb6-4a6a-9f14-859c72550552')
    def test_update_portgroup_add(self):
        """Update portgroup by adding new extra data and properties."""
        patch = [{'path': '/extra/key1',
                  'op': 'add',
                  'value': 'value1'},
                 {'path': '/properties/key1',
                  'op': 'add',
                  'value': 'value1'}]

        self.client.update_portgroup(self.portgroup['uuid'], patch)

        _, body = self.client.show_portgroup(self.portgroup['uuid'])
        self._assertExpected({'key1': 'value1'}, body['extra'])
        self._assertExpected({'key1': 'value1'}, body['properties'])

    @decorators.idempotent_id('67d5013e-5158-44e8-8d1c-a01d04542be4')
    def test_update_portgroup_mixed_ops(self):
        """Update port group with add, replace and remove ops in one patch."""
        new_address = data_utils.rand_mac_address()
        new_extra = {'key3': {'cat': 'meow'}}

        patch = [{'path': '/address',
                  'op': 'replace',
                  'value': new_address},
                 {'path': '/extra/foo',
                  'op': 'remove'},
                 {'path': '/extra/key3',
                  'op': 'add',
                  'value': new_extra['key3']}]

        self.client.update_portgroup(self.portgroup['uuid'], patch)

        _, body = self.client.show_portgroup(self.portgroup['uuid'])
        self.assertEqual(new_address, body['address'])
        self._assertExpected(new_extra, body['extra'])
        self.assertNotIn('foo', body['extra'])
