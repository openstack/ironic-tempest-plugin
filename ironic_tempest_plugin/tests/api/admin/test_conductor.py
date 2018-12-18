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

from ironic_tempest_plugin.tests.api.admin import base

CONF = config.CONF


class TestConductors(base.BaseBaremetalTest):
    """Tests for conductors."""

    min_microversion = '1.49'

    @decorators.idempotent_id('b6d62be4-53a6-43c6-ae78-bff9d1b4efc1')
    def test_list_conductors(self):
        _, conductors = self.client.list_conductors()
        self.assertTrue(len(conductors['conductors']) > 0)
        cond = conductors['conductors'].pop()
        self.assertIn('hostname', cond)
        self.assertIn('conductor_group', cond)
        self.assertIn('alive', cond)
        self.assertNotIn('drivers', cond)

    @decorators.idempotent_id('ca3de366-d80a-4e97-b19b-42d594e8d148')
    def test_list_conductors_detail(self):
        _, conductors = self.client.list_conductors(detail=True)
        self.assertTrue(len(conductors['conductors']) > 0)
        cond = conductors['conductors'].pop()
        self.assertIn('hostname', cond)
        self.assertIn('conductor_group', cond)
        self.assertIn('alive', cond)
        self.assertIn('drivers', cond)

    @decorators.idempotent_id('7e1829e2-3945-4508-a3d9-c8ebe9463fd8')
    def test_show_conductor(self):
        _, conductors = self.client.list_conductors()
        self.assertTrue(len(conductors['conductors']) > 0)
        conductor = conductors['conductors'].pop()

        _, conductor = self.client.show_conductor(conductor['hostname'])
        self.assertIn('hostname', conductor)
        self.assertIn('conductor_group', conductor)
        self.assertIn('alive', conductor)
        self.assertIn('drivers', conductor)
