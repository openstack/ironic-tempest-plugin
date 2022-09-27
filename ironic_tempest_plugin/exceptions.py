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

from tempest.lib import exceptions


class IntrospectionFailed(exceptions.TempestException):
    message = "Introspection failed"


class IntrospectionTimeout(exceptions.TempestException):
    message = "Introspection time out"


class HypervisorUpdateTimeout(exceptions.TempestException):
    message = "Hypervisor stats update time out"


class RaidCleaningInventoryValidationFailed(exceptions.TempestException):
    message = "RAID cleaning storage inventory validation failed"


class InsufficientAPIAccess(exceptions.TempestException):
    message = ("Insufficent Access to the API exists. Please use a user "
               "with an elevated level of access to execute this test.")
