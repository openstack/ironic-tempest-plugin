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

from ironic_tempest_plugin.tests.api import base


EXAMPLE_STEPS = [{
    'interface': 'bios',
    'step': 'apply_configuration',
    'args': {},
    'order': 1
}]


def _get_random_trait():
    return data_utils.rand_name('CUSTOM', '').replace('-', '_')


class TestRunbookRBAC(base.BaseBaremetalRBACTest):
    min_microversion = '1.92'
    credentials = ['system_admin',
                   'system_reader',
                   'project_admin',
                   'project_member']

    def setUp(self):
        super(TestRunbookRBAC, self).setUp()
        self.system_admin_client = (
            self.os_system_admin.baremetal.BaremetalClient())

        self.system_reader_client = (
            self.os_system_reader.baremetal.BaremetalClient())

        self.project_admin_client = (
            self.os_project_admin.baremetal.BaremetalClient())

        self.project_member_client = (
            self.os_project_member.baremetal.BaremetalClient())

        _, self.chassis = self.create_chassis()
        _, self.node = self.create_node(self.chassis['uuid'])

        _, self.public_runbook = self.system_admin_client.create_runbook(
            _get_random_trait(), steps=EXAMPLE_STEPS, public=True)

        _, self.private_runbook = self.project_admin_client.create_runbook(
            _get_random_trait(), steps=EXAMPLE_STEPS)

    @decorators.idempotent_id('0410fbed-3454-ded3-6f8b3192abfd3fcd')
    def test_runbook_visibility_and_access_control(self):
        # Project-scoped user can see both public and owned runbooks
        _, project_runbooks = self.project_member_client.list_runbooks()
        self.assertIn(self.public_runbook['uuid'],
                      [r['uuid'] for r in project_runbooks['runbooks']])
        self.assertIn(self.private_runbook['uuid'],
                      [r['uuid'] for r in project_runbooks['runbooks']])

        # System-scoped user can see all runbooks
        _, system_runbooks = self.system_reader_client.list_runbooks()
        self.assertIn(self.public_runbook['uuid'],
                      [r['uuid'] for r in system_runbooks['runbooks']])
        self.assertIn(self.private_runbook['uuid'],
                      [r['uuid'] for r in system_runbooks['runbooks']])

    @decorators.idempotent_id('903d0027-9265-9f87-c86d-09867aa24edd')
    def test_runbook_ownership_and_public_flag(self):
        # Only system-scoped users can set a runbook as public

        patch_public = [{'path': '/public', 'op': 'replace', 'value': True}]
        self.assertRaises(lib_exc.Forbidden,
                          self.project_admin_client.update_runbook,
                          self.private_runbook['uuid'],
                          patch=patch_public)

        # Setting a runbook as public nullifies its owner field
        self.system_admin_client.update_runbook(self.private_runbook['uuid'],
                                                patch=patch_public)
        _, updated_runbook = self.system_admin_client.show_runbook(
            self.private_runbook['uuid'])
        self.assertIsNone(updated_runbook['owner'])

        # Project-scoped user cannot change the owner of a runbook
        patch_owner = [{'path': '/public', 'op': 'replace', 'value': True}]
        self.assertRaises(lib_exc.Forbidden,
                          self.project_admin_client.update_runbook,
                          self.public_runbook['uuid'],
                          patch=patch_owner)
