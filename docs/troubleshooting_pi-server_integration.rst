.. Images
.. |img_001| image:: images/tshooting_pi_001.jpg
.. |img_002| image:: images/tshooting_pi_002.jpg
.. |img_003| image:: images/tshooting_pi_003.jpg
.. |img_004| image:: images/tshooting_pi_004.jpg
.. |img_005| image:: images/tshooting_pi_005.jpg
.. |img_006| image:: images/tshooting_pi_006.jpg

Troubleshooting the PI-Server integration
=========================================

This section describes how to trouble shoot issues with the PI-Server integration
using Fledge version >= 1.9.1 and PI Web API 2019 SP1 1.13.0.6518

- Log files
- How to check the PI Web API is installed and running
- Commands to check the PI Web API
- Error messages and possible solutions

Log files
---------

Fledge logs into the system syslog, mainly warnings and errors and in some circumstances rows of severity information.
The name of the north instance should be used to extract just the logs about the PI-Server integration, as in this example
showed by the Fledge GUI:

  +-----------+
  | |img_003| |
  +-----------+

.. code-block:: console

    sudo cat /var/log/syslog | grep North_Readings_to_PI

.. code-block:: console

    user.info, 6,1,Mar 15 08:29:57,localhost,Fledge, North_Readings_to_PI[15506]: INFO: SendingProcess is starting

another sample message:

.. code-block:: console

    North_Readings_to_PI[20884]: WARNING: Error in retrieving the PIWebAPI version, The PI Web API server is not reachable, verify the network reachability

How to check the PI Web API is installed and running
----------------------------------------------------

Open the URL *https://piserver_1/piwebapi* in the browser, substituting *piserver_1* with the name/address of your PI Server, to
verify the reachability and proper installation of PI Web API, if PI Web API is configured for *Basic* authentication
a prompt asking user name/password like the following one will appear:

  +-----------+
  | |img_002| |
  +-----------+

**NOTE:**

- *The same user name/password configured in Fledge should be used.*

The *PI Web API OMF* plugin must be installed to allow the integration with Fledge, in this screen shot the 4th row shows the
proper installation of the plugin:

  +-----------+
  | |img_001| |
  +-----------+

Commands to check the PI WEB API
--------------------------------

Drill drown in PI Web API to verify the proper configuration on the PI-Server side, also in terms of granted permission,
going down to the path *DataServers* - *Points*

  +-----------+
  | |img_004| |
  +-----------+

  +-----------+
  | |img_005| |
  +-----------+

you should be able to browse the *PI Point* page and see your pi points if some data was already sent:

  +-----------+
  | |img_006| |
  +-----------+

Error messages an possible solutions
------------------------------------

Same sample messages and the related cause:

.. code-block:: console

    North_Readings_to_PI[20884]: WARNING: Error in retrieving the PIWebAPI version, The PI Web API server is not reachable, verify the network reachability

Fledge is not able to reach the machine in which PI-Server is running due to a network problem of a firewall restriction.

.. code-block:: console

    North_Readings_to_PI[5838]: WARNING: Error in retrieving the PIWebAPI version, 503 Service Unavailable

Fledge is capable to reach the machine in which PI-Server is running but the PI Web API is not running.

.. code-block:: console

    North_Readings_to_PI[24485]: ERROR: Sending JSON data error : Container not found. 4273005507977094880_1measurement_sin_4816_asset_1 - WIN-4M7ODKB0RH2:443 /piwebapi/omf

Fledge is able to interact with PI Web API but there is an attempt to store data in a PI Point that is not existing.


