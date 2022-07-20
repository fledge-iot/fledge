.. 


Repository Configuration
------------------------

``POST /fledge/repository`` - Configure the package repository to use for the Fledge packages.

**Payload**

The payload is a JSON document that can have one or two keys defined in
the JSON object, *url* and *version*. The *url* item is mandatory and
gives the URL of the package repository. This is normally set to the
Dianomic archives for the fledge packages.

.. code-block:: console

   {
       "url":"http://archives.fledge-iot.org",
       "version":"latest"
   }


Update Packages
---------------

``PUT /fledge/update`` - Update all of the packages within the Fledge instance

This call can be used if you have installed some or all of your Fledge
instance using packages via the package installation process or using
the package installer to add extra plugins. It will update all the Fledge
packages that you have installed to the latest version.

**Example**

.. code-block:: console

   $ curl -X PUT http://localhost:8081/fledge/update

The call will return immediately and the package update will occur as a background task.


