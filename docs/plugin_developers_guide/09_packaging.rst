.. Plugin as a Package

Plugin Packaging
================

There are as set of files that must exist within the repository of a plugin that are used to create the package for that plugin on the various supported platforms. The following documents what those files are and what they should contain.

Common files
------------

- **Description** - It should contain a brief description of the plugin and will be used as the description for the package that is created. Also make sure description of plugin must be in a single line as of now we do not have support multi lines yet.
- **Package** - This is the main file where we define set of variables.

   - **plugin_name** - Name of the Plugin.
   - **plugin_type** - Type of the Plugin.
   - **plugin_install_dirname** - Installed Directory name.
   - **plugin_package_name (Optional)** - Name of the Package. If it is not given then the package name should be same as plugin name.
   - **requirements** - Runtime Architecture specific packages list and should have comma separated values without any space.

   .. note::
      For C-based plugins if a plugin requires some additional libraries to install with then set additional_libs variable inside Package file. And the value must be with following contract:

      additional_libs="DIRECTORY_NAME:FILE_NAME" - in case of single
      additional_libs="DIRECTORY_NAME:FILE_NAME1,DIRECTORY_NAME:FILE_NAME2" - in case of multiple use comma separated with both directory & file name

- **service_notification.version** - It is only required if the plugin is a notification rule or notification delivery plugin. It contains the minimum version of the notification service which the plugin requires.

C based Plugins
---------------

- **VERSION** - It contains the version number of the plugin and is used by the build process to include the version number within the code and also within the name of the package file created.
- **fledge.version** - It contains the minimum version number of Fledge required by the plugin.
- **requirements.sh (Optional)** - It is used to install any additional libraries or other artifacts that are need to build the plugin. It takes the form of a shell script. This script, if it exists, will be run as a part of the process of building the plugin before the cmake command is issued in the build process.
- **extras_install.sh (Optional)** - It is a shell script that is added to the package to allow for extra commands to be executed as part of the package installation. Not all plugins will require this file to be present and it can be omitted if there are no extra steps required on the installation.

Examples of filename along with content
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. VERSION

.. code-block:: console

    $ cat VERSION
    1.9.2

2. fledge.version

.. code-block:: console

    $ cat fledge.version
    fledge_version>=1.9

3. requirements.sh

.. code-block:: console

    $ cat requirements.sh
    #!/usr/bin/env bash
    which apt >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        sudo apt install -y libmodbus-dev
    else
        which yum >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            sudo yum -y install epel-release libmodbus libmodbus-devel
        fi
    fi

4. Description

.. code-block:: console

    $ cat Description
    Fledge modbus plugin. Supports modbus RTU and modbus TCP.

5. Package

.. code-block:: console

    $ cat Package
    # A set of variables that define how we package this repository
    #
    plugin_name=modbus
    plugin_type=south
    plugin_install_dirname=ModbusC
    plugin_package_name=fledge-south-modbus
    additional_libs="usr/local/lib:/usr/local/lib/libsmod.so*"

    # Now build up the runtime requirements list. This has 3 components
    #   1. Generic packages we depend on in all architectures and package managers
    #   2. Architecture specific packages we depend on
    #   3. Package manager specific packages we depend on
    requirements="fledge"

    case "$arch" in
        x84_64)
            ;;
        armv7l)
            ;;
        aarch64)
            ;;
    esac
    case "$package_manager" in
        deb)
            requirements="${requirements},libmodbus-dev"
            ;;
    esac

.. note::
    If your package is not supported for a specific platform then you must exit with exitcode 1.

6. service_notification.version

.. code-block:: console

    $ cat service_notification.version
    service_notification_version>=1.9.2

Common Additional Libraries Package
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Below are the packages which created a part of the process of building Fledge that are commonly used in plugins.

- **fledge-mqtt** which is a packaged version of the libpaho-mqtt library.
- **fledge-gcp** which is a packaged version of the libjwt and libjansson libraries.
- **fledge-iec** which is a packaged version of the IEC 60870 and IEC 61850 libraries.
- **fledge-s2opcua** which is a packaged version of libexpat and libs2opc libraries.


If your plugin depends on any of these libraries they should be added to the *requirements* variable in the **Package** file rather than adding them as *additional_libs* since the version of these is managed by the Fledge build and packaging process. Below is the example

.. code-block:: console

    requirements="fledge,fledge-s2opcua"

Python based Plugins
--------------------

- **VERSION.{PLUGIN_TYPE}.{PLUGIN_NAME}** - It contains the packaged version of the plugin and also the minimum fledge version that the plugin requires.
- **install_notes.txt (Optional)** - It is a simple text file that can be included if there are specific instructions required to be given during the installation of the plugin. These notes will be displayed at the end of the installation process for the package.
- **extras_install.sh (Optional)** - It is a shell script that is added to the package to allow for extra commands to be executed as part of the package installation. Not all plugins will require this file to be present and it can be omitted if there are no extra steps required on the installation.
- **requirements-{PLUGIN_NAME}.txt (Optional)** - It is a simple text file that can be included if there are pip dependencies required to be given during the installation of the plugin. Also make sure file should be placed inside *python* directory.

Examples of filename along with content
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Description

.. code-block:: console

    $ cat Description
    Fledge South Sinusoid plugin

2. Package

.. code-block:: console

    $ cat Package
    # A set of variables that define how we package this repository
    #
    plugin_name=sinusoid
    plugin_type=south
    plugin_install_dirname=sinusoid

    # Now build up the runtime requirements list. This has 3 components
    #   1. Generic packages we depend on in all architectures and package managers
    #   2. Architecture specific packages we depend on
    #   3. Package manager specific packages we depend on
    requirements="fledge"

    case "$arch" in
        x86_64)
            ;;
        armv7l)
            ;;
        aarch64)
            ;;
    esac
    case "$package_manager" in
        deb)
            ;;
    esac

.. note::
    If your package is not supported for a specific platform then you must exit with exitcode 1.

3. VERSION.{PLUGIN_TYPE}.{PLUGIN_NAME}

.. code-block:: console

    $ cat VERSION.south.sinusoid
    fledge_south_sinusoid_version=1.9.2
    fledge_version>=1.9

4. install_notes.txt

.. code-block:: console

    $ cat install_notes.txt
    It is required to reboot the RPi, please do the following steps:
    1) sudo reboot

5. extras_install.sh

.. code-block:: console

    #!/usr/bin/env bash

    os_name=$(grep -o '^NAME=.*' /etc/os-release | cut -f2 -d\" | sed 's/"//g')
    os_version=$(grep -o '^VERSION_ID=.*' /etc/os-release | cut -f2 -d\" | sed 's/"//g')
    echo "Platform is ${os_name}, Version: ${os_version}"
    arch=`arch`
    ID=$(cat /etc/os-release | grep -w ID | cut -f2 -d"=")
    if [ ${ID} != "mendel" ]; then
    case $os_name in
      *"Ubuntu"*)
        if [ ${arch} = "aarch64" ]; then
          python3 -m pip install --upgrade pip
        fi
        ;;

      esac
    fi

6. requirements-{PLUGIN_NAME}.txt

.. code-block:: console

    $ cat python/requirements-modbustcp.txt
    pymodbus3==1.0.0


Building A Package
------------------

Firstly you need to clone the repository `fledge-pkg <https://github.com/fledge-iot/fledge-pkg>`_. Now do the following steps

.. code-block:: console

    $ cd plugins
    $ ./make_deb -b <BRANCH_NAME> <REPOSITORY_NAME>

    if everything goes well with above command then you can find your package inside archive directory.

    $ ls archive
