=====
Usage
=====

Configuring
-----------

Update your `Tempest configuration`_ to enable support for ironic:

.. code-block:: ini

    [service_available]
    ironic = True

If introspection tests are needed, also enable support for ironic-inspector:

.. code-block:: ini

    [service_available]
    ironic_inspector = True

See the following example configurations for more details:

.. toctree::
   :maxdepth: 1

   config/with-nova

.. TODO(dtantsur): cover standalone tests

.. _Tempest configuration: https://docs.openstack.org/tempest/latest/configuration.html

Running
-------

Run tests as described in the `Tempest documentation`_. The following patterns
can be used with ``--regex`` option to only run bare metal tests:

``ironic``
    all bare metal tests
``ironic_tempest_plugin.tests.api``
    only API tests using fake hardware, without other OpenStack services (these
    tests are run by jobs starting with ``ironic-tempest-functional-python3``)
``ironic_tempest_plugin.tests.scenario``
    all integration tests, excluding the API tests with fake hardware (these
    tests are run by most of the jobs)
``ironic_standalone``
    standalone bare metal tests that do not use the Compute service
    (these tests are run by the jobs ``ironic-standalone`` and
    ``ironic-standalone-redfish``)
``InspectorBasicTest``
    basic introspection tests (these tests are run by most of the jobs with
    ``ironic-inspector`` in their name)
``InspectorDiscoveryTest``
    introspection auto-discovery tests (these tests are run by the job
    ``ironic-inspector-tempest-discovery`` and require additional set up)

.. _Tempest documentation: https://docs.openstack.org/tempest/latest/run.html
