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

from oslo_utils import uuidutils
from tempest import config
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from ironic_tempest_plugin.common import waiters
from ironic_tempest_plugin.tests.api.admin import base

CONF = config.CONF


class Base(base.BaseBaremetalTest):
    @classmethod
    def provide_and_power_off_node(cls, node_id, cleaning_timeout=None):
        cls.provide_node(node_id, cleaning_timeout)
        # Force non-empty power state, otherwise allocation API won't pick it
        cls.client.set_node_power_state(node_id, 'power off')
        waiters.wait_for_bm_node_status(cls.client, node_id,
                                        'power_state', 'power off')

    def setUp(self):
        super(Base, self).setUp()

        # Generate a resource class to prevent parallel tests from clashing
        # with each other.
        self.resource_class = uuidutils.generate_uuid()

        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis['uuid'],
                                        resource_class=self.resource_class)
        self.provide_and_power_off_node(self.node['uuid'])


class TestAllocations(Base):
    """Tests for baremetal allocations."""

    min_microversion = '1.52'

    @decorators.idempotent_id('9203ea28-3c61-4108-8498-22247b654ff6')
    def test_create_show_allocation(self):
        self.assertIsNone(self.node['allocation_uuid'])
        _, body = self.create_allocation(self.resource_class)
        uuid = body['uuid']

        self.assertTrue(uuid)
        self.assertEqual('allocating', body['state'])
        self.assertEqual(self.resource_class, body['resource_class'])
        self.assertIsNone(body['last_error'])
        self.assertIsNone(body['node_uuid'])

        _, body = waiters.wait_for_allocation(self.client, uuid)
        self.assertEqual('active', body['state'])
        self.assertEqual(self.resource_class, body['resource_class'])
        self.assertIsNone(body['last_error'])
        self.assertEqual(self.node['uuid'], body['node_uuid'])

        _, body2 = self.client.show_node_allocation(body['node_uuid'])
        self.assertEqual(body, body2)

        _, node = self.client.show_node(self.node['uuid'])
        self.assertEqual(uuid, node['allocation_uuid'])

    @decorators.idempotent_id('eb074d06-e5f4-4fb4-b992-c9929db488ae')
    def test_create_allocation_with_traits(self):
        _, node2 = self.create_node(self.chassis['uuid'],
                                    resource_class=self.resource_class)
        self.client.set_node_traits(node2['uuid'], ['CUSTOM_MEOW'])
        self.provide_and_power_off_node(node2['uuid'])

        _, body = self.create_allocation(self.resource_class,
                                         traits=['CUSTOM_MEOW'])
        uuid = body['uuid']

        self.assertTrue(uuid)
        self.assertEqual('allocating', body['state'])
        self.assertEqual(['CUSTOM_MEOW'], body['traits'])
        self.assertIsNone(body['last_error'])

        _, body = waiters.wait_for_allocation(self.client, uuid)
        self.assertEqual('active', body['state'])
        self.assertEqual(['CUSTOM_MEOW'], body['traits'])
        self.assertIsNone(body['last_error'])
        self.assertEqual(node2['uuid'], body['node_uuid'])

    @decorators.idempotent_id('12d19297-f35a-408a-8b1e-3cd244e30abe')
    def test_create_allocation_candidate_node(self):
        node_name = 'allocation-test-1'
        _, node2 = self.create_node(self.chassis['uuid'],
                                    resource_class=self.resource_class,
                                    name=node_name)
        self.provide_and_power_off_node(node2['uuid'])

        _, body = self.create_allocation(self.resource_class,
                                         candidate_nodes=[node_name])
        uuid = body['uuid']

        self.assertTrue(uuid)
        self.assertEqual('allocating', body['state'])
        self.assertEqual([node2['uuid']], body['candidate_nodes'])
        self.assertIsNone(body['last_error'])

        _, body = waiters.wait_for_allocation(self.client, uuid)
        self.assertEqual('active', body['state'])
        self.assertEqual([node2['uuid']], body['candidate_nodes'])
        self.assertIsNone(body['last_error'])
        self.assertEqual(node2['uuid'], body['node_uuid'])

    @decorators.idempotent_id('84eb3c21-4e16-4f33-9551-dce0f8689462')
    def test_delete_allocation(self):
        _, body = self.create_allocation(self.resource_class)
        self.client.delete_allocation(body['uuid'])
        self.assertRaises(lib_exc.NotFound, self.client.show_allocation,
                          body['uuid'])

    @decorators.idempotent_id('5e30452d-ee92-4342-82c1-5eea5e55c937')
    def test_delete_allocation_by_name(self):
        name = 'alloc-%s' % uuidutils.generate_uuid()
        _, body = self.create_allocation(self.resource_class, name=name)
        self.client.delete_allocation(name)
        self.assertRaises(lib_exc.NotFound, self.client.show_allocation, name)

    @decorators.idempotent_id('fbbc13bc-86da-438b-af01-d1bc1bab57d6')
    def test_show_by_name(self):
        name = 'alloc-%s' % uuidutils.generate_uuid()
        _, body = self.create_allocation(self.resource_class, name=name)
        _, loaded_body = self.client.show_allocation(name)
        # The allocation will likely have been processed by this time, so do
        # not compare the whole body.
        for field in ('name', 'uuid', 'resource_class'):
            self.assertEqual(body[field], loaded_body[field])

    @decorators.idempotent_id('4ca123c4-160d-4d8d-a3f7-15feda812263')
    def test_list_allocations(self):
        _, body = self.create_allocation(self.resource_class)

        _, listing = self.client.list_allocations()
        self.assertIn(body['uuid'],
                      [i['uuid'] for i in listing['allocations']])

        _, listing = self.client.list_allocations(
            resource_class=self.resource_class)
        self.assertEqual([body['uuid']],
                         [i['uuid'] for i in listing['allocations']])

    @decorators.idempotent_id('092b7148-9ff0-4107-be57-2cfcd21eb5d7')
    def test_list_allocations_by_state(self):
        _, body = self.create_allocation(self.resource_class)
        _, body2 = self.create_allocation(self.resource_class + 'foo2')

        waiters.wait_for_allocation(self.client, body['uuid'])
        waiters.wait_for_allocation(self.client, body2['uuid'],
                                    expect_error=True)

        _, listing = self.client.list_allocations(state='active')
        uuids = [i['uuid'] for i in listing['allocations']]
        self.assertIn(body['uuid'], uuids)
        self.assertNotIn(body2['uuid'], uuids)

        _, listing = self.client.list_allocations(state='error')
        uuids = [i['uuid'] for i in listing['allocations']]
        self.assertNotIn(body['uuid'], uuids)
        self.assertIn(body2['uuid'], uuids)

        _, listing = self.client.list_allocations(state='allocating')
        uuids = [i['uuid'] for i in listing['allocations']]
        self.assertNotIn(body['uuid'], uuids)
        self.assertNotIn(body2['uuid'], uuids)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('bf7e1375-019a-466a-a294-9c1052827ada')
    def test_create_allocation_resource_class_mismatch(self):
        _, body = self.create_allocation(self.resource_class + 'foo')

        _, body = waiters.wait_for_allocation(self.client, body['uuid'],
                                              expect_error=True)
        self.assertEqual('error', body['state'])
        self.assertTrue(body['last_error'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('b4eeddee-ca34-44f9-908b-490b78b18486')
    def test_create_allocation_traits_mismatch(self):
        _, body = self.create_allocation(
            self.resource_class, traits=['CUSTOM_DOES_NOT_EXIST'])

        _, body = waiters.wait_for_allocation(self.client, body['uuid'],
                                              expect_error=True)
        self.assertEqual('error', body['state'])
        self.assertTrue(body['last_error'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('2378727f-77c3-4289-9562-bd2f3b147a60')
    def test_create_allocation_node_mismatch(self):
        _, node2 = self.create_node(self.chassis['uuid'],
                                    resource_class=self.resource_class + 'alt')
        # Mismatch between the resource class and the candidate node
        _, body = self.create_allocation(
            self.resource_class, candidate_nodes=[node2['uuid']])

        _, body = waiters.wait_for_allocation(self.client, body['uuid'],
                                              expect_error=True)
        self.assertEqual('error', body['state'])
        self.assertTrue(body['last_error'])


class TestBackfill(Base):
    """Tests for backfilling baremetal allocations."""

    min_microversion = '1.58'

    @decorators.idempotent_id('10774c1d-6b79-453a-8e26-9bf04ab580a4')
    def test_backfill_allocation(self):
        self.deploy_node(self.node['uuid'])

        _, body = self.client.create_allocation(self.resource_class,
                                                node=self.node['uuid'])
        uuid = body['uuid']
        self.assertEqual(self.node['uuid'], body['node_uuid'])
        self.assertEqual('active', body['state'])
        self.assertIsNone(body['last_error'])

        _, body2 = self.client.show_node_allocation(body['node_uuid'])
        self.assertEqual(self.node['uuid'], body2['node_uuid'])
        self.assertEqual('active', body2['state'])
        self.assertIsNone(body2['last_error'])

        _, node = self.client.show_node(self.node['uuid'])
        self.assertEqual(uuid, node['allocation_uuid'])

    @decorators.idempotent_id('c33d4b65-1232-4a3f-9aad-942e32f6f7b0')
    def test_backfill_without_resource_class(self):
        self.deploy_node(self.node['uuid'])

        _, body = self.client.create_allocation(None, node=self.node['uuid'])
        uuid = body['uuid']
        self.assertEqual(self.node['uuid'], body['node_uuid'])
        self.assertEqual('active', body['state'])
        self.assertIsNone(body['last_error'])
        # Resource class is copied from node
        self.assertEqual(self.node['resource_class'], body['resource_class'])

        _, body2 = self.client.show_node_allocation(body['node_uuid'])
        self.assertEqual(self.node['uuid'], body2['node_uuid'])
        self.assertEqual('active', body2['state'])
        self.assertIsNone(body2['last_error'])
        self.assertEqual(self.node['resource_class'], body2['resource_class'])

        _, node = self.client.show_node(self.node['uuid'])
        self.assertEqual(uuid, node['allocation_uuid'])
