# Copyright 2017 FUJITSU LIMITED
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


from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from ironic_tempest_plugin.tests.api.admin import api_microversion_fixture
from ironic_tempest_plugin.tests.api.admin import base


class TestVolumeResource(base.BaseBaremetalTest):

    min_microversion = '1.32'
    extra = {'key1': 'value1', 'key2': 'value2'}

    def setUp(self):
        super(TestVolumeResource, self).setUp()
        self.useFixture(
            api_microversion_fixture.APIMicroversionFixture(
                self.min_microversion))
        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis['uuid'])
        _, self.volume_connector = self.create_volume_connector(
            self.node['uuid'], type='iqn',
            connector_id=data_utils.rand_name('connector_id'),
            extra=self.extra)
        _, self.volume_target = self.create_volume_target(
            self.node['uuid'], volume_type=data_utils.rand_name('volume_type'),
            volume_id=data_utils.rand_name('volume_id'),
            boot_index=10,
            extra=self.extra)


    @decorators.idempotent_id('a4725778-e164-4ee5-96a0-66119a35f784')
    def test_list_volume_resource_by_node(self):
        """List volume resource by node."""
        _, body = self.client.list_volume_resource_by_node(self.node['uuid'])
       

