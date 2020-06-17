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

from oslo_log import log as logging
from tempest.common import utils
from tempest import config
from tempest.lib import decorators

from ironic_tempest_plugin.tests.scenario import \
    baremetal_standalone_manager as bsm

LOG = logging.getLogger(__name__)
CONF = config.CONF


class BaremetalRamdiskBootIso(bsm.BaremetalStandaloneScenarioTest):

    if 'redfish' in CONF.baremetal.enabled_hardware_types:
        driver = 'redfish'
        boot_interface = 'redfish-virtual-media'
    else:
        driver = 'ipmi'
        boot_interface = 'ipxe'
    delete_node = False
    deploy_interface = 'ramdisk'
    api_microversion = '1.66'
    image_ref = CONF.baremetal.ramdisk_iso_image_ref
    wholedisk_image = False

    @classmethod
    def skip_checks(cls):
        super(BaremetalRamdiskBootIso, cls).skip_checks()
        if not cls.image_ref:
            raise cls.skipException('Skipping ramdisk ISO booting as'
                                    'no ramdisk_iso_image_ref is defined.')

    @decorators.idempotent_id('2859d115-9266-4461-9286-79b146e65dc9')
    @utils.services('image', 'network')
    def test_ramdisk_boot(self):
        self.boot_and_verify_ramdisk_node(self.image_ref, iso=True)
