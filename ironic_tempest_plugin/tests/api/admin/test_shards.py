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

from tempest import config
from tempest.lib import decorators

from ironic_tempest_plugin.tests.api import base


CONF = config.CONF


class TestAddShardsToNode(base.BaseBaremetalTest):
    """Tests for baremetal shards."""

    min_microversion = '1.82'

    def setUp(self):
        super(TestAddShardsToNode, self).setUp()
        # set a minimum API version
        _, self.chassis = self.create_chassis()

    @decorators.idempotent_id('6f1e241d-4386-4730-b9ff-28c6a3dcad31')
    def test_add_shard_to_node_at_create(self):
        shard = 'at-create'

        _, body = self.create_node(self.chassis['uuid'], shard=shard)
        self.assertEqual(shard, body['shard'])

    @decorators.idempotent_id('2eb91d29-e0a5-472b-aeb8-ef6d98eb0f3c')
    def test_add_shard_to_node_post_create(self):
        shard = 'post-create'

        _, node = self.create_node(self.chassis['uuid'])
        _, before = self.client.show_node(node['uuid'])
        self.assertIsNone(before['shard'])

        self.client.update_node(node['uuid'], shard=shard)

        _, after = self.client.show_node(node['uuid'])
        self.assertEqual(shard, after['shard'])


class TestNodeShardQueries(base.BaseBaremetalTest):
    """Tests for baremetal shards."""

    min_microversion = '1.82'

    def setUp(self):
        super(TestNodeShardQueries, self).setUp()
        _, self.chassis = self.create_chassis()
        _, bad_node = self.create_node(self.chassis['uuid'], shard='bad')
        _, none_node = self.create_node(self.chassis['uuid'])  # shard=None
        self.bad_node_id = bad_node['uuid']
        self.none_node_id = none_node['uuid']

    def _setup_nodes(self, good_shard, num=2):
        good_node_ids = []
        for i in range(num):
            _, node = self.create_node(self.chassis['uuid'], shard=good_shard)
            good_node_ids.append(node['uuid'])

        return good_node_ids

    @decorators.idempotent_id('df74c989-6972-4104-a8d6-bd8e8d811353')
    def test_show_all_nodes(self):
        """Validate unfiltered API query will return nodes with a shard."""
        shard = "oneshardtest"
        good_node_ids = self._setup_nodes(shard)

        _, fetched_nodes = self.client.list_nodes()
        fetched_node_ids = [node['uuid'] for node in fetched_nodes['nodes']]

        for node_id in good_node_ids:
            self.assertIn(node_id, fetched_node_ids)

    @decorators.idempotent_id('6f1e241d-4386-4730-b9ff-28c6a3dcad31')
    def test_only_show_requested_shard(self):
        """Validate filtering nodes by shard."""
        shard = "oneshardtest"
        good_node_ids = self._setup_nodes(shard)

        _, fetched_nodes = self.client.list_nodes(shard=shard)
        fetched_node_ids = [node['uuid'] for node in fetched_nodes['nodes']]

        self.assertCountEqual(good_node_ids, fetched_node_ids)

    @decorators.idempotent_id('6f1e241d-4386-4730-b9ff-28c6a3dcad31')
    def test_only_show_multiple_requested_shards(self):
        """Validate filtering nodes by multiple shards."""
        shard = "multishardtest"
        second_shard = "multishardtest2"
        good_node_ids = self._setup_nodes(shard)
        _, second_shard_node = self.create_node(
            self.chassis['uuid'], shard=second_shard)
        good_node_ids.append(second_shard_node['uuid'])

        _, fetched_nodes = self.client.list_nodes(
            shard=','.join([shard, second_shard]))
        fetched_node_ids = [node['uuid'] for node in fetched_nodes['nodes']]

        self.assertCountEqual(good_node_ids, fetched_node_ids)
        self.assertNotIn(self.bad_node_id, fetched_node_ids)
        self.assertNotIn(self.none_node_id, fetched_node_ids)

    @decorators.idempotent_id('f7a2eeb7-d16e-480c-b698-3448491c73a1')
    def test_show_sharded_nodes(self):
        _, fetched_nodes = self.client.list_nodes(sharded=True)
        fetched_node_ids = [node['uuid'] for node in fetched_nodes['nodes']]

        # NOTE(JayF): All other nodes under test are sharded
        self.assertNotIn(self.none_node_id, fetched_node_ids)

    @decorators.idempotent_id('f7a2eeb7-d16e-480c-b698-3448491c73a1')
    def test_show_unsharded_nodes(self):
        _, fetched_nodes = self.client.list_nodes(sharded=False)
        fetched_node_ids = [node['uuid'] for node in fetched_nodes['nodes']]

        self.assertIn(self.none_node_id, fetched_node_ids)
        self.assertNotIn(self.bad_node_id, fetched_node_ids)


class TestGetAllShards(base.BaseBaremetalTest):
    """Tests for baremetal shards."""

    min_microversion = '1.82'

    def setUp(self):
        super(TestGetAllShards, self).setUp()
        _, self.chassis = self.create_chassis()
        self.shards = ["shard1", "shard2", "shard3"]
        self.node_ids = []
        for shard in self.shards:
            _, node = self.create_node(self.chassis['uuid'], shard=shard)
            self.node_ids.append(node['uuid'])

    @decorators.idempotent_id('fc786196-63c7-4e0d-bd14-3e478d4d1e3e')
    def test_get_all_shards(self):
        _, fetched_shards = self.client.get_shards()
        fetched_shards = [shard['name'] for shard in fetched_shards['shards']]

        self.assertCountEqual(self.shards, fetched_shards)
