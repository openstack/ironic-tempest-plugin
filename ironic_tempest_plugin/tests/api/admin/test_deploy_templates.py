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
from ironic_tempest_plugin.tests.api.admin import base


EXAMPLE_STEPS = [{
    'interface': 'bios',
    'step': 'apply_configuration',
    'args': {},
    'priority': 10
}]


def _get_random_trait():
    return data_utils.rand_name('CUSTOM', '').replace('-', '_')


class TestDeployTemplates(base.BaseBaremetalTest):
    """Tests for deploy templates."""

    min_microversion = '1.55'

    def setUp(self):
        super(TestDeployTemplates, self).setUp()
        self.name = _get_random_trait()
        self.steps = copy.deepcopy(EXAMPLE_STEPS)
        _, self.template = self.create_deploy_template(self.name,
                                                       steps=self.steps)

    @decorators.idempotent_id('8f39c794-4e6f-42fc-bfcb-e1f6eafff2e9')
    def test_create_deploy_template_specifying_uuid(self):
        name = _get_random_trait()
        uuid = data_utils.rand_uuid()

        _, template = self.create_deploy_template(name=name, steps=self.steps,
                                                  uuid=uuid)

        _, body = self.client.show_deploy_template(uuid)
        self._assertExpected(template, body)

    @decorators.idempotent_id('7ac8fdd5-928b-4fbc-8341-3ebaad9def5e')
    def test_delete_deploy_template(self):
        self.delete_deploy_template(self.template['uuid'])

        self.assertRaises(lib_exc.NotFound, self.client.show_deploy_template,
                          self.template['uuid'])

    @decorators.idempotent_id('f424dd67-46c3-4169-b8f0-7e0c18b70437')
    def test_show_deploy_template(self):
        _, template = self.client.show_deploy_template(self.template['uuid'])
        self._assertExpected(self.template, template)
        self.assertEqual(self.name, template['name'])
        self.assertEqual(self.steps, template['steps'])
        self.assertIn('uuid', template)
        self.assertEqual({}, template['extra'])

    @decorators.idempotent_id('2fd98e9a-10ce-405a-a32c-0d6079766183')
    def test_show_deploy_template_with_links(self):
        _, template = self.client.show_deploy_template(self.template['uuid'])
        self.assertIn('links', template)
        self.assertEqual(2, len(template['links']))
        self.assertIn(template['uuid'], template['links'][0]['href'])

    @decorators.idempotent_id('cec2a01d-07af-4062-a8b0-9a1703f65bcf')
    def test_list_deploy_templates(self):
        _, body = self.client.list_deploy_templates()
        self.assertIn(self.template['uuid'],
                      [i['uuid'] for i in body['deploy_templates']])
        # Verify self links.
        for template in body['deploy_templates']:
            self.validate_self_link('deploy_templates', template['uuid'],
                                    template['links'][0]['href'])

    @decorators.idempotent_id('89aea2bf-c094-445f-b869-9fd56d1dfe5a')
    def test_list_with_limit(self):
        for i in range(2):
            name = _get_random_trait()
            self.create_deploy_template(name, steps=self.steps)

        _, body = self.client.list_deploy_templates(limit=3)

        next_marker = body['deploy_templates'][-1]['uuid']
        self.assertIn(next_marker, body['next'])

    @decorators.idempotent_id('c09c917e-c4d2-4148-9b6a-459bd126ed7c')
    def test_list_deploy_templates_detail(self):
        uuids = [
            self.create_deploy_template(_get_random_trait(), steps=self.steps)
            [1]['uuid'] for i in range(0, 5)]

        _, body = self.client.list_deploy_templates(detail=True)

        templates_dict = dict((template['uuid'], template)
                              for template in body['deploy_templates']
                              if template['uuid'] in uuids)

        for uuid in uuids:
            self.assertIn(uuid, templates_dict)
            template = templates_dict[uuid]
            self.assertIn('name', template)
            self.assertEqual(self.steps, template['steps'])
            self.assertIn('uuid', template)
            self.assertEqual({}, template['extra'])
            # Verify self link.
            self.validate_self_link('deploy_templates', template['uuid'],
                                    template['links'][0]['href'])

    @decorators.idempotent_id('a6cf1ade-e19a-41e2-b151-13ecf0d8f08c')
    def test_update_deploy_template_replace(self):
        new_name = _get_random_trait()
        new_steps = [{
            'interface': 'raid',
            'step': 'create_configuration',
            'args': {},
            'priority': 10,
        }]

        patch = [{'path': '/name', 'op': 'replace', 'value': new_name},
                 {'path': '/steps', 'op': 'replace', 'value': new_steps}]

        self.client.update_deploy_template(self.template['uuid'], patch)

        _, body = self.client.show_deploy_template(self.template['uuid'])
        self.assertEqual(new_name, body['name'])
        self.assertEqual(new_steps, body['steps'])

    @decorators.idempotent_id('bb168c63-452b-4065-9a81-77853ca9540a')
    def test_update_deploy_template_add(self):
        new_steps = [
            {
                'interface': 'bios',
                'step': 'cache_bios_settings',
                'args': {},
                'priority': 20
            },
            {
                'interface': 'bios',
                'step': 'factory_reset',
                'args': {},
                'priority': 30
            },
        ]

        patch = [{'path': '/steps/1', 'op': 'add', 'value': new_steps[0]},
                 {'path': '/steps/2', 'op': 'add', 'value': new_steps[1]}]

        self.client.update_deploy_template(self.template['uuid'], patch)

        _, body = self.client.show_deploy_template(self.template['uuid'])
        self.assertEqual(self.steps + new_steps, body['steps'])

    @decorators.idempotent_id('2aa204a2-1d50-48fd-8b76-d2ed15586d50')
    def test_update_deploy_template_mixed_ops(self):
        new_name = _get_random_trait()
        new_steps = [
            {
                'interface': 'bios',
                'step': 'apply_configuration',
                'args': {},
                'priority': 20
            },
            {
                'interface': 'bios',
                'step': 'apply_configuration',
                'args': {},
                'priority': 30
            },
        ]

        patch = [{'path': '/name', 'op': 'replace', 'value': new_name},
                 {'path': '/steps/0', 'op': 'replace', 'value': new_steps[0]},
                 {'path': '/steps/0', 'op': 'remove'},
                 {'path': '/steps/0', 'op': 'add', 'value': new_steps[1]}]

        self.client.update_deploy_template(self.template['uuid'], patch)

        _, body = self.client.show_deploy_template(self.template['uuid'])
        self.assertEqual(new_name, body['name'])
        self.assertEqual([new_steps[1]], body['steps'])


class TestDeployTemplatesOldAPI(base.BaseBaremetalTest):
    """Negative tests for deploy templates using an old API version."""

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('e9481a0d-23e0-4757-bc11-c3c9ab9d3839')
    def test_create_deploy_template_old_api(self):
        # With deploy templates support, ironic returns 404. Without, 405.
        self.assertRaises((lib_exc.NotFound, lib_exc.UnexpectedResponseCode),
                          self.create_deploy_template,
                          name=_get_random_trait(), steps=EXAMPLE_STEPS)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('0d3af2aa-ba53-4c8a-92d4-91f9b4179fe7')
    def test_update_deploy_template_old_api(self):
        patch = [{'path': '/name', 'op': 'replace',
                  'value': _get_random_trait()}]

        # With deploy templates support, ironic returns 404. Without, 405.
        self.assertRaises((lib_exc.NotFound, lib_exc.UnexpectedResponseCode),
                          self.client.update_deploy_template,
                          _get_random_trait(), patch)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('1646b1e5-ab81-45a8-9ea0-30444a4dcaa2')
    def test_delete_deploy_template_old_api(self):
        # With deploy templates support, ironic returns 404. Without, 405.
        self.assertRaises((lib_exc.NotFound, lib_exc.UnexpectedResponseCode),
                          self.client.delete_deploy_template,
                          _get_random_trait())

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('819480ac-f36a-4402-b1d5-504d7cf55b1f')
    def test_list_deploy_templates_old_api(self):
        self.assertRaises(lib_exc.NotFound,
                          self.client.list_deploy_templates)


class TestDeployTemplatesNegative(base.BaseBaremetalTest):
    """Negative tests for deploy templates."""

    min_microversion = '1.55'

    def setUp(self):
        super(TestDeployTemplatesNegative, self).setUp()
        self.useFixture(
            api_microversion_fixture.APIMicroversionFixture(
                self.min_microversion)
        )
        self.steps = EXAMPLE_STEPS

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('a4085c08-e718-4c2f-a796-0e115b659243')
    def test_create_deploy_template_invalid_name(self):
        name = 'invalid-name'
        self.assertRaises(lib_exc.BadRequest,
                          self.create_deploy_template, name=name,
                          steps=self.steps)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('6390acc4-9490-4b23-8b4c-41888a78c9b7')
    def test_create_deploy_template_duplicated_deploy_template_name(self):
        name = _get_random_trait()
        self.create_deploy_template(name=name, steps=self.steps)
        self.assertRaises(lib_exc.Conflict, self.create_deploy_template,
                          name=name, steps=self.steps)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('ed3f0cec-13e8-4175-9fdb-d129e7b7fe10')
    def test_create_deploy_template_no_mandatory_field_name(self):
        self.assertRaises(lib_exc.BadRequest, self.create_deploy_template,
                          name=None, steps=self.steps)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('af5dd0df-d903-463f-9535-9e4e9d6fd576')
    def test_create_deploy_template_no_mandatory_field_steps(self):
        self.assertRaises(lib_exc.BadRequest, self.create_deploy_template,
                          name=_get_random_trait())

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('cbd33bc5-7602-40b7-943e-3e92217567a3')
    def test_create_deploy_template_malformed_steps(self):
        steps = {'key': 'value'}
        self.assertRaises(lib_exc.BadRequest, self.create_deploy_template,
                          name=_get_random_trait(), steps=steps)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('2a562fca-f377-4a6e-b332-37ee82d3a983')
    def test_create_deploy_template_malformed_deploy_template_uuid(self):
        uuid = 'malformed:uuid'
        self.assertRaises(lib_exc.BadRequest, self.create_deploy_template,
                          name=_get_random_trait(), steps=self.steps,
                          uuid=uuid)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('2c006994-88ca-43b7-b605-897d479229d9')
    def test_show_deploy_template_nonexistent(self):
        self.assertRaises(lib_exc.NotFound, self.client.show_deploy_template,
                          data_utils.rand_uuid())

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('5a815f37-f015-4d68-9b22-099504f74805')
    def test_update_deploy_template_remove_mandatory_field_steps(self):
        name = _get_random_trait()
        _, template = self.create_deploy_template(name=name, steps=self.steps)

        # Removing one item from the collection
        self.assertRaises(lib_exc.BadRequest,
                          self.client.update_deploy_template,
                          template['uuid'],
                          [{'path': '/steps/0', 'op': 'remove'}])

        # Removing the collection
        self.assertRaises(lib_exc.BadRequest,
                          self.client.update_deploy_template,
                          template['uuid'],
                          [{'path': '/steps', 'op': 'remove'}])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('ee852ebb-a601-4593-9d59-063fcbc8f964')
    def test_update_deploy_template_remove_mandatory_field_name(self):
        name = _get_random_trait()
        _, template = self.create_deploy_template(name=name, steps=self.steps)
        self.assertRaises(lib_exc.BadRequest,
                          self.client.update_deploy_template,
                          template['uuid'],
                          [{'path': '/name', 'op': 'remove'}])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('e59bf38d-272f-4490-b21e-9db217f11378')
    def test_update_deploy_template_replace_empty_name(self):
        name = _get_random_trait()
        _, template = self.create_deploy_template(name=name, steps=self.steps)
        self.assertRaises(lib_exc.BadRequest,
                          self.client.update_deploy_template,
                          template['uuid'],
                          [{'path': '/name', 'op': 'replace', 'value': ''}])
