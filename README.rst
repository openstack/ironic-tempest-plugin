==============================================
Tempest plugin for ironic and ironic-inspector
==============================================

This repository contains a Tempest_ plugin for OpenStack `Bare Metal`_ and
`Bare Metal Introspection`_ projects.

* Free software: Apache license
* Documentation: https://docs.openstack.org/ironic-tempest-plugin
* Source: https://git.openstack.org/cgit/openstack/ironic-tempest-plugin
* Bugs: https://storyboard.openstack.org/#!/project/951

.. _Tempest: https://docs.openstack.org/tempest/latest/
.. _Bare Metal: https://docs.openstack.org/ironic/latest/
.. _Bare Metal Introspection: https://docs.openstack.org/ironic-inspector/latest/


1.mkdir tempest2
创建虚拟化环境
2.virtualenv venv
3. source venv/bin/activate
4. git clone https://github.com/zhoumingang/tempest-pike.git
进入extension目录下安装ironic tempest的plugin
https://github.com/zhoumingang/ironic-tempest-plugin
5根据具体环境修改tempest配置/etc/tempest/tempest.conf
[identity]
uri =  http://10.152.35.89/identity/v2.0

# Full URI of the OpenStack Identity API (Keystone), v3 (string value)
uri_v3 = http://10.152.35.89/identity/v3

# Identity API version to be used for authentication for API tests.
# (string value)
auth_version = v3

[network]
public_network_id = d2352c0a-9c4c-4398-ac54-0c4af6892204


[service_available]
ironic = True
ironic-inspector = False

[baremetal]
# Minimum and maximum API versions to test against.
min_microversion = 1.1
max_microversion = 1.34
# Driver to use for API tests for Queens and newer:
#driver = fake-hardwae

6.cd tempest-pike/extention/ironic-tempest-plugin
pip install .
pip install tox

7.tox -eapi



======
Totals
======
Ran: 151 tests in 86.0000 sec.
 - Passed: 147
 - Skipped: 4
 - Expected Fail: 0
 - Unexpected Success: 0
 - Failed: 0
Sum of execute time for each test: 104.8137 sec.
