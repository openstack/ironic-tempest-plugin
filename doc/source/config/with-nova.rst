Full cloud with the Compute service and flat networking
=======================================================

This section documents running tempest on a full OpenStack cloud with the
Compute, Image and Networking services enabled. The Bare Metal Introspection
service (ironic-inspector) is not enabled. Flat networking is used.

Prerequisite
------------

* `Create a bare metal flavor`_ in the Compute service in advance
  and record its ID (``<flavor uuid>`` below).

* `Create an image`_ to use for instances and record its ID (``<image uuid>``).
  It can be either a whole disk or a partition image.

* Create and record the name or UUID of a flat network to use for bare metal
  instances (``<network name>``).

* Get the minimum and maximum API versions that you want to test against.
  Check the `API version history`_ to find the appropriate versions for
  your deployment.

  .. note:: The minimum version can usually be set to ``1.1``.

* Enroll_ at least one node and make it ``available``.

.. _Create a bare metal flavor: https://docs.openstack.org/ironic/latest/install/configure-nova-flavors.html
.. _Create an image: https://docs.openstack.org/ironic/latest/install/configure-glance-images.html
.. _API version history: https://docs.openstack.org/ironic/latest/contributor/webapi-version-history.html
.. _Enroll: https://docs.openstack.org/ironic/latest/install/enrollment.html

Configuration
-------------

.. code-block:: ini

    [service_available]
    # Enable ironic tests.
    ironic = True

    # Disable ironic-inspector tests.
    ironic-inspector = False

    [baremetal]
    # Minimum and maximum API versions to test against.
    min_microversion = <min API version as X.Y>
    max_microversion = <max API version as X.Y>
    # Driver to use for API tests for Queens and newer:
    driver = fake-hardware

    [compute]
    # Configure the bare metal flavor so that the Compute services provisions
    # bare metal instances during the tests.
    flavor_ref = <flavor uuid>
    flavor_ref_alt = <flavor uuid>

    # Configure the image to use.
    image_ref = <image uuid>
    image_ref_alt = <image uuid>

    # Configure the network to use.
    fixed_network_name = <network name>

    [compute-feature-enabled]
    # Ironic does not support this feature.
    disk_config = False

    # Not supported with flat networking.
    interface_attach = False

    [auth]
    # Not supported with flat networking.
    create_isolated_networks = False

    [network]
    # Required for flat networking.
    shared_physical_network = True
