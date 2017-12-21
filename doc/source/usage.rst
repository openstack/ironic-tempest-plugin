=====
Usage
=====

Configuring
-----------

Update your `Tempest configuration`_ to enable support for ironic:

.. code-block:: ini

    [service_enabled]
    ironic = True

If introspection tests are needed, also enable support for ironic-inspector:

.. code-block:: ini

    [service_enabled]
    ironic_inspector = True

.. TODO(dtantsur): I'm pretty sure more configuration is required, fill it in

.. _Tempest configuration: https://docs.openstack.org/tempest/latest/configuration.html

Running
-------

Run tests as described in the `Tempest documentation`_. The following patterns
can be used with ``--regex`` option to only run bare metal tests:

``ironic``
    all bare metal tests
``ironic_standalone``
    standalone bare metal tests that do not use the Compute service
``InspectorBasicTest``
    basic introspection tests
``InspectorDiscoveryTest``
    introspection auto-discovery tests

.. _Tempest documentation: https://docs.openstack.org/tempest/latest/run.html
