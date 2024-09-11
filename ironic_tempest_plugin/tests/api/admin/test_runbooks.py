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

import copy

from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from ironic_tempest_plugin.tests.api.admin import api_microversion_fixture
from ironic_tempest_plugin.tests.api import base


EXAMPLE_STEPS = [{
    'interface': 'bios',
    'step': 'apply_configuration',
    'args': {},
    'order': 1
}]


def _get_random_trait():
    return data_utils.rand_name('CUSTOM', '').replace('-', '_')


class TestRunbooks(base.BaseBaremetalTest):
    """Tests for runbooks."""

    min_microversion = '1.92'

    def setUp(self):
        super(TestRunbooks, self).setUp()
        self.name = _get_random_trait()
        self.steps = copy.deepcopy(EXAMPLE_STEPS)
        _, self.runbook = self.create_runbook(self.name,
                                              steps=self.steps)

        _, self.chassis = self.create_chassis()
        _, self.test_node = self.create_node(self.chassis['uuid'])

    @decorators.idempotent_id('5a0cfe27-b7e8-d4f0-d3c5-e6e1eef63241')
    def test_create_runbook_specifying_uuid(self):
        name = _get_random_trait()
        uuid = data_utils.rand_uuid()

        _, runbook = self.create_runbook(name=name, steps=self.steps,
                                         uuid=uuid)

        _, body = self.client.show_runbook(uuid)
        self._assertExpected(runbook, body)

    @decorators.idempotent_id('b8bfb388-97b0-aa6e-5130-1a1ed34f94db')
    def test_delete_runbook(self):
        self.delete_runbook(self.runbook['uuid'])
        self.assertRaises(lib_exc.NotFound, self.client.show_runbook,
                          self.runbook['uuid'])

    @decorators.idempotent_id('f1cba93a-2894-7296-0f4b-58867359480b')
    def test_show_runbook(self):
        _, runbook = self.client.show_runbook(self.runbook['uuid'])
        self._assertExpected(self.runbook, runbook)
        self.assertEqual(self.name, runbook['name'])
        self.assertEqual(self.steps, runbook['steps'])
        self.assertIn('uuid', runbook)
        self.assertEqual({}, runbook['extra'])

    @decorators.idempotent_id('c95e2631-24e2-914b-db00-c8dafc35a677')
    def test_show_runbook_with_links(self):
        _, runbook = self.client.show_runbook(self.runbook['uuid'])
        self.assertIn('links', runbook)
        self.assertEqual(2, len(runbook['links']))
        self.assertIn(runbook['uuid'], runbook['links'][0]['href'])

    @decorators.idempotent_id('7b7951b3-e177-21d7-933a-1f29891dea52')
    def test_list_runbooks(self):
        _, body = self.client.list_runbooks()
        self.assertIn(self.runbook['uuid'],
                      [i['uuid'] for i in body['runbooks']])

        for runbook in body['runbooks']:
            self.validate_self_link('runbooks', runbook['uuid'],
                                    runbook['links'][0]['href'])

    @decorators.idempotent_id('6aafc619-0d98-5341-7d94-b293e194dcf7')
    def test_list_with_limit(self):
        for _ in range(2):
            name = _get_random_trait()
            self.create_runbook(name, steps=self.steps)

        _, body = self.client.list_runbooks(limit=3)

        next_marker = body['runbooks'][-1]['uuid']
        self.assertIn(next_marker, body['next'])

    @decorators.idempotent_id('ebd762c3-c10e-b71f-5efd-af14ac9f6092')
    def test_list_runbooks_detail(self):
        uuids = [
            self.create_runbook(_get_random_trait(), steps=self.steps)
            [1]['uuid'] for _ in range(0, 5)]

        _, body = self.client.list_runbooks(detail=True)

        runbooks_dict = dict((runbook['uuid'], runbook)
                             for runbook in body['runbooks']
                             if runbook['uuid'] in uuids)

        for uuid in uuids:
            self.assertIn(uuid, runbooks_dict)
            runbook = runbooks_dict[uuid]
            self.assertIn('name', runbook)
            self.assertEqual(self.steps, runbook['steps'])
            self.assertIn('uuid', runbook)
            self.assertEqual({}, runbook['extra'])
            self.validate_self_link('runbooks', runbook['uuid'],
                                    runbook['links'][0]['href'])

    @decorators.idempotent_id('fb192fdd-ea6a-c637-a36e-390c46a7663b')
    def test_update_runbook_replace(self):
        new_name = _get_random_trait()
        new_steps = [{
            'interface': 'raid',
            'step': 'create_configuration',
            'args': {},
            'order': 2,
        }]

        patch = [{'path': '/name', 'op': 'replace', 'value': new_name},
                 {'path': '/steps', 'op': 'replace', 'value': new_steps}]

        self.client.update_runbook(self.runbook['uuid'], patch)

        _, body = self.client.show_runbook(self.runbook['uuid'])
        self.assertEqual(new_name, body['name'])
        self.assertEqual(new_steps, body['steps'])

    @decorators.idempotent_id('99f52546-9906-6ded-9186-7262591b99ec')
    def test_update_runbook_add(self):
        new_steps = [
            {
                'interface': 'bios',
                'step': 'cache_bios_settings',
                'args': {},
                'order': 2
            },
            {
                'interface': 'bios',
                'step': 'factory_reset',
                'args': {},
                'order': 3
            },
        ]

        patch = [{'path': '/steps/1', 'op': 'add', 'value': new_steps[0]},
                 {'path': '/steps/2', 'op': 'add', 'value': new_steps[1]}]

        self.client.update_runbook(self.runbook['uuid'], patch)

        _, body = self.client.show_runbook(self.runbook['uuid'])
        self.assertEqual(self.steps + new_steps, body['steps'])

    @decorators.idempotent_id('ec1550c3-264e-fcce-b131-d2815fdb733b')
    def test_update_runbook_mixed_ops(self):
        new_name = _get_random_trait()
        new_steps = [
            {
                'interface': 'bios',
                'step': 'apply_configuration',
                'args': {},
                'order': 2
            },
            {
                'interface': 'bios',
                'step': 'apply_configuration',
                'args': {},
                'order': 3
            },
        ]

        patch = [{'path': '/name', 'op': 'replace', 'value': new_name},
                 {'path': '/steps/0', 'op': 'replace', 'value': new_steps[0]},
                 {'path': '/steps/0', 'op': 'remove'},
                 {'path': '/steps/0', 'op': 'add', 'value': new_steps[1]}]

        self.client.update_runbook(self.runbook['uuid'], patch)

        _, body = self.client.show_runbook(self.runbook['uuid'])
        self.assertEqual(new_name, body['name'])
        self.assertEqual([new_steps[1]], body['steps'])

    @decorators.idempotent_id('5c7f0aca-cee3-d083-ef2a-e33a8dc467c5')
    def test_combining_runbook_and_explicit_steps(self):
        explicit_steps = [{'interface': 'deploy', 'step': 'deploy',
                           'args': {}}]

        self.assertRaises(lib_exc.BadRequest,
                          self.client.set_node_provision_state,
                          self.test_node['uuid'], 'active',
                          runbook=self.runbook['uuid'],
                          clean_steps=explicit_steps)

    @decorators.idempotent_id('ddf4a9b7-144d-386a-fd3fcf8960d77199')
    def test_create_runbook_with_invalid_step_format(self):
        name = _get_random_trait()
        invalid_steps = [{'invalid_key': 'value'}]

        self.assertRaises(lib_exc.BadRequest, self.create_runbook,
                          name, steps=invalid_steps)


class TestRunbooksOldAPI(base.BaseBaremetalTest):
    """Negative tests for runbooks using an old API version."""

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('e9481a0d-23e0-4757-bc11-c3c9ab9d3839')
    def test_create_runbook_old_api(self):
        # With runbooks support, ironic returns 404. Without, 405.
        self.assertRaises((lib_exc.NotFound, lib_exc.UnexpectedResponseCode),
                          self.create_runbook,
                          name=_get_random_trait(), steps=EXAMPLE_STEPS)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('0d3af2aa-ba53-4c8a-92d4-91f9b4179fe7')
    def test_update_runbook_old_api(self):
        patch = [{'path': '/name', 'op': 'replace',
                  'value': _get_random_trait()}]

        # With runbooks support, ironic returns 404. Without, 405.
        self.assertRaises((lib_exc.NotFound, lib_exc.UnexpectedResponseCode),
                          self.client.update_runbook,
                          _get_random_trait(), patch)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('1646b1e5-ab81-45a8-9ea0-30444a4dcaa2')
    def test_delete_runbook_old_api(self):
        # With runbooks support, ironic returns 404. Without, 405.
        self.assertRaises((lib_exc.NotFound, lib_exc.UnexpectedResponseCode),
                          self.client.delete_runbook,
                          _get_random_trait())

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('819480ac-f36a-4402-b1d5-504d7cf55b1f')
    def test_list_runbooks_old_api(self):
        self.assertRaises(lib_exc.NotFound,
                          self.client.list_runbooks)


class TestRunbooksNegative(base.BaseBaremetalTest):
    """Negative tests for runbooks."""

    min_microversion = '1.92'

    def setUp(self):
        super(TestRunbooksNegative, self).setUp()
        self.useFixture(
            api_microversion_fixture.APIMicroversionFixture(
                self.min_microversion)
        )
        self.steps = EXAMPLE_STEPS

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('a4085c08-e718-4c2f-a796-0e115b659243')
    def test_create_runbook_invalid_name(self):
        name = 'invalid-name'
        self.assertRaises(lib_exc.BadRequest,
                          self.create_runbook, name=name,
                          steps=self.steps)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('6390acc4-9490-4b23-8b4c-41888a78c9b7')
    def test_create_runbook_duplicated_name(self):
        name = _get_random_trait()
        self.create_runbook(name=name, steps=self.steps)
        self.assertRaises(lib_exc.Conflict, self.create_runbook,
                          name=name, steps=self.steps)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('ed3f0cec-13e8-4175-9fdb-d129e7b7fe10')
    def test_create_runbook_no_mandatory_field_name(self):
        self.assertRaises(lib_exc.BadRequest, self.create_runbook,
                          name=None, steps=self.steps)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('af5dd0df-d903-463f-9535-9e4e9d6fd576')
    def test_create_runbook_no_mandatory_field_steps(self):
        self.assertRaises(lib_exc.BadRequest, self.create_runbook,
                          name=_get_random_trait())

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('cbd33bc5-7602-40b7-943e-3e92217567a3')
    def test_create_runbook_malformed_steps(self):
        steps = {'key': 'value'}
        self.assertRaises(lib_exc.BadRequest, self.create_runbook,
                          name=_get_random_trait(), steps=steps)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('2a562fca-f377-4a6e-b332-37ee82d3a983')
    def test_create_runbook_malformed_runbook_uuid(self):
        uuid = 'malformed:uuid'
        self.assertRaises(lib_exc.BadRequest, self.create_runbook,
                          name=_get_random_trait(), steps=self.steps,
                          uuid=uuid)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('2c006994-88ca-43b7-b605-897d479229d9')
    def test_show_runbook_nonexistent(self):
        self.assertRaises(lib_exc.NotFound, self.client.show_runbook,
                          data_utils.rand_uuid())

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('5a815f37-f015-4d68-9b22-099504f74805')
    def test_update_runbook_remove_mandatory_field_steps(self):
        name = _get_random_trait()
        _, runbook = self.create_runbook(name=name, steps=self.steps)

        self.assertRaises(lib_exc.BadRequest,
                          self.client.update_runbook,
                          runbook['uuid'],
                          [{'path': '/steps/0', 'op': 'remove'}])

        self.assertRaises(lib_exc.BadRequest,
                          self.client.update_runbook,
                          runbook['uuid'],
                          [{'path': '/steps', 'op': 'remove'}])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('ee852ebb-a601-4593-9d59-063fcbc8f964')
    def test_update_runbook_remove_mandatory_field_name(self):
        name = _get_random_trait()
        _, runbook = self.create_runbook(name=name, steps=self.steps)
        self.assertRaises(lib_exc.BadRequest,
                          self.client.update_runbook,
                          runbook['uuid'],
                          [{'path': '/name', 'op': 'remove'}])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('e59bf38d-272f-4490-b21e-9db217f11378')
    def test_update_runbook_replace_empty_name(self):
        name = _get_random_trait()
        _, runbook = self.create_runbook(name=name, steps=self.steps)
        self.assertRaises(lib_exc.BadRequest,
                          self.client.update_runbook,
                          runbook['uuid'],
                          [{'path': '/name', 'op': 'replace', 'value': ''}])
