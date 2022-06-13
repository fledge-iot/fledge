
Building Notification Service
-----------------------------

As with *Fledge* itself there is always the option to build the notification service from the source code repository. This is only recommended if you also built your *Fledge* from source code, if you did not then you should first do this before building the notification, otherwise you should install a binary package of the notification service.

The steps involved in building the notification service, assuming you have already built Fledge itself and the environment variable *FLEDGE_ROOT* points to where you built your *Fledge*, are;

.. code-block:: console

   $ git clone https://github.com/fledge-iot/fledge-service-notification.git
   ...
   $ cd fledge-service-notification
   $ ./requirements.sh
   ...
   $ mkdir build
   $ cd build
   $ cmake ..
   ...
   $ make
   ...

This will result in the creation of a notification service binary, you now need to copy that binary into the *Fledge* installation. There are two options here, one if you used *make install* to create your installation and the other if you are running directly form the build environment.

If you used *make install* to create your *Fledge* installation then simply run *make install* to install your notification service. This should be run from the *build* directory under the *fledge-service-notification* directory.

.. code-block:: console

   $ make install

.. note::

   You may need to run *make install* under a sudo command if your user does not have permissions to write to the installation directory. If you use a DESTDIR=... option to the *make install* of *Fledge* then you should use the same DESTDIR=... option here also.

If you are running your *Fledge* directly from the build environment, then execute the command

.. code-block:: console

   $ cp ./C/services/notification/fledge.services.notification $FLEDGE_ROOT/services
