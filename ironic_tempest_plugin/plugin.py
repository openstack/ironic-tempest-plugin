# Copyright 2015 NEC Corporation
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


import os

from tempest import config
from tempest.test_discover import plugins

from ironic_tempest_plugin import config as project_config

_opts = [
    (project_config.baremetal_group, project_config.BaremetalGroup),
    (project_config.baremetal_features_group,
     project_config.BaremetalFeaturesGroup),
    (project_config.baremetal_introspection_group,
     project_config.BaremetalIntrospectionGroup),
]


class IronicTempestPlugin(plugins.TempestPlugin):
    def load_tests(self):
        base_path = os.path.split(os.path.dirname(
            os.path.abspath(__file__)))[0]
        test_dir = "ironic_tempest_plugin/tests"
        full_test_dir = os.path.join(base_path, test_dir)
        return full_test_dir, base_path

    def register_opts(self, conf):
        conf.register_opt(project_config.ironic_service_option,
                          group='service_available')
        conf.register_opt(project_config.inspector_service_option,
                          group='service_available')
        conf.register_opt(project_config.ironic_scope_enforcement,
                          group='enforce_scope')
        conf.register_opt(project_config.inspector_scope_enforcement,
                          group='enforce_scope')
        for group, option in _opts:
            config.register_opt_group(conf, group, option)

    def get_opt_lists(self):
        return [(group.name, option) for group, option in _opts]

    def get_service_clients(self):
        ironic_config = config.service_client_config(
            project_config.baremetal_group.name
        )
        baremetal_client = {
            'name': 'baremetal',
            'service_version': 'baremetal.v1',
            'module_path': 'ironic_tempest_plugin.services.baremetal.v1.'
                           'json.baremetal_client',
            'client_names': [
                'BaremetalClient',
            ],
        }
        baremetal_client.update(ironic_config)

        inspector_config = config.service_client_config(
            project_config.baremetal_introspection_group.name
        )
        inspector_client = {
            'name': 'introspection',
            'service_version': 'baremetal_introspection.v1',
            'module_path': 'ironic_tempest_plugin.services.'
                           'introspection_client',
            'client_names': [
                'BaremetalIntrospectionClient',
            ],
        }
        inspector_client.update(inspector_config)

        return [baremetal_client, inspector_client]
