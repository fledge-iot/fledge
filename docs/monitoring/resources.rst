.. |MonitorDiskUsge| image:: ../images/MonitorDiskUsge.jpg

Resources
=========

Monitoring resource usage within a Fledge instance can be achieved by using the south plugin that is designed to monitor the Linux resources of the machine on which Fledge is running, this is the systeminfo south plugin.

This plugin creates a number of assets with a configurable prefix on the asset name. This include

  - The aggregate CPU usage for all the CPUs within the machine.

  - The disk traffic for that disk for each disk connected to the machine.

  - The load average of the machine.

  - The memory usage information for the machine.

  - The network usage for each network interface on the machine.

  - The paging and swapping events for the machine.

  - Platform information for the machine.

  - A summary of the processes running on the machine.

There are some other things that are also monitored that of not of particular interest for monitoring resource usage.

Example
-------

In this example we will assume we want to use the notification service to monitor the percentage of space remaining on a particular disk within the Fledge machine. We use the systeminfo plugin to get the data we want, in this case we will look at the disk device sda1, using the defaults of the plugin this will create an asset called *system/diskUsage_dev/sda1* with a datapoint called *Use_prcntg*.

.. note::

   The systeminfo plugin imposes a significant load when it collects data, since the data we are interested in does not change at a very high rate we should reduce the polling rate of this plugin in order to not take unnecessary resources from the machine in order to monitor resource usage.

Since we are looking for a numeric value to go above a certain vale, say 85%, we can simply use the threshold notification rule to detect the disk usage going above this value and deliver a notification using any of the Fledge notification delivery mechanisms.

+====================+
| |MonitorDiskUsage| |
+====================+

Database Disk Usage
===================

Fledge has a built in mechanism that will monitor and predict when the disk hosting the internal storage buffer will become full. It will write predictions to the error log and will additionally raise alerts when the disk usage becomes critical.
