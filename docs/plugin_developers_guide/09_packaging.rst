.. Documentation of package for a Plugin

Packaging Documentation
=======================

Below are the prerequisite files which we need them in Plugin repository itself.

Common files
------------

- Description
   Summary of a plugin. Also make sure description of plugin must be in a single line as we do not support multiline yet.

- Package
   This is the main file where we define set of variables.

   - plugin_name
      Name of the Plugin.
   - plugin_type
      Type of the plugin.
   - plugin_install_dirname
      Installed directory name.
   - plugin_package_name (OPTIONAL)
      Name of the Package and also fullname is required. If not given or variable is not set then the package name should be same as plugin name.
   - requirements
      Runtime Architecture specific packages list in comma separated without any space.

   .. note::
      For C-based plugins if a plugin requires some additional libraries to install with then set additional_libs variable inside Package file. And the value must be with following contract:

      additional_libs="DIRECTORY_NAME:FILE_NAME" - in case of single
      additional_libs="DIRECTORY_NAME:FILE_NAME1,DIRECTORY_NAME:FILE_NAME2" - in case of multiple use comma separated with both directory & file name


- service_notification.version
   This file only requires if plugin is notification rule or delivery based.

C based Plugins
---------------

- VERSION
   Plugin version number.
- fledge.version
   Fledge version number.
- requirements.sh (OPTIONAL)
   If a plugin requires some additional libraries to install with. Also make sure file should be in executable format.

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
        rpm)
            requirements="${requirements},epel-release,libmodbus,libmodbus-devel"
            ;;
    esac

.. note::
    If your package is not supported for a specific platform then you must exit with exitcode 1

6. service_notification.version

.. code-block:: console

    $ cat service_notification.version
    service_notification_version>=1.9.2

Common Additional Libraries Package
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
At the moment we have only two package exists.

- **fledge-mqtt** which is packed with libpaho-mqtt library.
- **fledge-gcp** which is packed with libjwt and libjansson libraries.

If your plugin depends upon then update **requirements** variable in Package file instead of using *additional_libs* variable.

Python based Plugins
--------------------

- VERSION.{PLUGIN_TYPE}.{PLUGIN_NAME}
   Fledge and Plugin version number.
- install_notes.txt (OPTIONAL)
   If plugin requires any manual intervention like reboot or any setting which is required on the device directly. Therefore we need some notes to let user know what else is required to complete the installation of a plugin. And notes will be appeared at the end of plugin installation.
- extras_install.sh (OPTIONAL)
   This is just another shell script file to avoid package lock errors during package installation. We can write those steps here. Also make sure file should be in executable format.

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
        rpm)
            ;;
    esac

.. note::
    If your package is not supported for a specific platform then you must exit with exitcode 1

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
      *"Red Hat"*)
        source scl_source enable rh-python36
        ;;

      *"CentOS"*)
        source scl_source enable rh-python36
        ;;

      *"Ubuntu"*)
        if [ ${arch} = "aarch64" ]; then
          python3 -m pip install --upgrade pip
        fi
        ;;

      esac
    fi

Build Package
-------------

Firstly you need to clone the repository `fledge-pkg <https://github.com/fledge-iot/fledge-pkg>`_. Now do the following steps

.. code-block:: console

    $ cd plugins
    $ ./make_deb -b <BRANCH_NAME> <REPOSITORY_NAME>

    if everything goes well with above command then you can find your package inside archive directory.

    $ ls archive
