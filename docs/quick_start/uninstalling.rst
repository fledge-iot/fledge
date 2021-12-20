Package Uninstallation
======================

Debian Platform
###############

Use the ``apt`` or the ``apt-get`` command to uninstall Fledge:

.. code-block:: console

  sudo apt -y purge fledge

RPM Platform
############

.. code-block:: console

  sudo yum -y remove fledge

.. note::
    You may notice the warning in the last row of the package removal output:

    dpkg: warning: while removing fledge, directory '/usr/local/fledge' not empty so not removed

This is due to the fact that the data directory (``/usr/local/fledge/data`` by default) has not been removed, in case we might want to analyze or reuse the data further.
So, if you want to remove fledge completely from your system, then do ``rm -rf /usr/local/fledge`` directory.
