.. Images
.. |filter_south| image:: images/filter_1.jpg
.. |filter_add| image:: images/filter_2.jpg
.. |filter_expression| image:: images/filter_3.jpg
.. |filter_data| image:: images/filter_4.jpg
.. |filter_pipeline| image:: images/filter_5.jpg
.. |filter_reorder| image:: images/filter_6.jpg
.. |filter_edit| image:: images/filter_7.jpg
.. |filter_north| image:: images/filter_8.jpg
.. |filter_select| image:: images/filter_9.jpg
.. |filter_floor| image:: images/filter_10.jpg

.. Links
.. |filter_plugins| raw:: html

   <a href="fledge_plugins.html#filter-plugins">Filter Plugins</a>


***************
Processing Data
***************

We have already seen that Fledge can collect data from a variety of sources, buffer it locally and send it on to one or more destination systems. It is also possible to process the data within Fledge to edit, augment or remove data as it traverses the Fledge system. In the same way Fledge makes extensive use of plugin components to add new sources of data and new destinations for that data, Fledge also uses plugins to add processing filters to the Fledge system.

Why Use Filters?
================

The concept behind filters is to create a set of small, useful pieces of
functionality that can be inserted into the data flow from the south data
ingress side to the north data egress side. By making these elements
small and dedicated to a single task it increases the re-usability of
the filters and greatly improves the chances when a new requirement
is encountered that it can be satisfied by creating a filter pipeline
from existing components or by augmenting existing components with the
addition of any incremental processing required. The ultimate aim being
to be able to create new applications within Fledge by merely configuring
filters from the existing pool of available filters into a suitable pipeline
without the need to write any new code.

What Can Be Done?
=================

Data processing is done via plugins that are known as *filters* in Fledge, therefore it is not possible to give a definitive list of all the different processing that can occur, the design intent is that it is expandable by the user. The general types of things that can be done are;

  - **Modify a value in a reading**. This could be as simple as applying a scale factor to convert from one measurement scale to another or more complex mathematical operation.
  - **Modify asset or datapoint names**. Perform a simple textual substitution in order to change the name of an asset or a data point within that asset.
  - **Add a new calculated value**. A new value can be calculated from a set of values, either based over a time period or based on a combination of different values, e.g. calculate power from voltage and current.
  - **Add metadata to an asset**. This allows data such as units of measurement or information about the data source to be added to the data.
  - **Compress data**. Only send data forward when the data itself shows significant change from previous values. This can be a useful technique to save bandwidth in low bandwidth or high cost network connections.
  - **Conditionally forward data**. Only send data when a condition is satisfied or send low rate data unless some *interesting* condition is met.
  - **Data conditioning**. Remove data from the data stream if the values are suspect or outside of reasonable conditions.

Where Can it Be Done?
=====================

Filters can be applied in two locations in the Fledge system;

  - In the south service as data arrives in Fledge and before it is added to the storage subsystem for buffering.
  - In the north tasks as the data is sent out to the upstream systems that receive data from the Fledge system.

More than one filter can be added to a single south or north within a Fledge instance. Filters are placed in an ordered pipeline of filters that are applied to the data in the order of the pipeline. The output of the first filter becomes the input to the second. Filters can thus be combined to perform complex sets of operations on a particular data stream into Fledge or out of Fledge.

The same filter plugin can appear in multiple places within a filter pipeline, a different instance is created for each and each one has its own configuration.

Adding a South Filter
---------------------

In the following example we will add a filter to a south service. The filter we will use is the *expression* filter and we will convert the incoming value to a logarithmic scale. The south plugin used in this simple example is the *sinusoid* plugin that creates a simulated sine wave.

The process starts by selecting the *South* services in the Fledge GUI from the left-hand menu bar. Then click on the south service of interest. This will display a dialog that allows the south service to be edited.

+----------------+
| |filter_south| |
+----------------+

Towards the bottom of this dialog is a section labeled *Applications* with a + icon to the right, select the + icon to add a filter to the south service. A filter wizard is now shown that allows you to select the filter you wish to add and give that filter a name.

+--------------+
| |filter_add| |
+--------------+

Select the *expression* filter and enter a name in the dialog. Now click on the *Next* button. A new page in the wizard appears that allows the configuration of the filter.

+---------------------+
| |filter_expression| |
+---------------------+

In the case of our expression filter we should add the expression we wish to execute *log(sinusoid)* and the name of the datapoint we wish to put the result in, *LogSine*. We can also choose to enable or disable the execution of this filter. We will enable it and click on *Done* to complete adding the filter.

Click on *Save* in the south edit dialog and our filter is now installed and running.

If we select the *Assets & Readings* option from the menu bar we can examine the sinusoid asset and view a graph of that asset. We will now see a second datapoint has been added, *LogSine* which is the result of executing our expression in the filter.

+---------------+
| |filter_data| |
+---------------+

A second filter can be added in the same way, for example a *metadata* filter to create a pipeline. Now when we go back and view the south service we see two applications in the dialog.

+-------------------+
| |filter_pipeline| |
+-------------------+

Reordering Filters
~~~~~~~~~~~~~~~~~~

The order in which the filters are applied can be changed in the south service dialog by clicking and dragging one filter above another in the *Applications* section of dialog.

+------------------+
| |filter_reorder| |
+------------------+

Filters are executed in a top to bottom order always. It may not matter in some cases what order a filter is executed in, in others it can have significant effect on the result.

Editing Filter Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A filters configuration can be altered from the south service dialog by selecting the down arrow to the right of the filter name. This will open the edit area for that filter and show the configuration that can be altered.

+---------------+
| |filter_edit| |
+---------------+

You can also remove a filter from the pipeline of filters by select the trash can icon at the bottom right of the edit area for the filter.

Adding Filters To The North
---------------------------

Filters can also be added to the north in the same way as the south. The same set of filters can be applied, however some may be less useful in the north than in the south as they apply to all assets that are sent north.

In this example we will use the metadata filter to label all the data that goes north as coming via a particular Fledge instance. As with the *South* service we start by selecting our north task from the *North* menu item in the left-hand menu bar.

+----------------+
| |filter_north| |
+----------------+

At the bottom of the dialog there is a *Applications* area, you may have to scroll the dialog to find it, click on the + icon. A selection dialog appears that allows you to select the filter to use. Select the *metadata* filter.

+-----------------+
| |filter_select| |
+-----------------+

After clicking *Next* you will be shown the configuration page for the particular filter you have chosen. We will edit the JSON that defines the metadata tags to add and set a name of *floor* and a value of *1*.

+----------------+
| |filter_floor| |
+----------------+

After enabling and clicking on *Done* we save the north changes. All assets sent to this PI Server connection will now be tagged with the tag "floor" and value "1".

Although this is a simple example of labeling data other things can be done here, such as limiting the rate we send data to the PI Server until an *interesting* condition becomes true, perhaps to save costs on an expensive link or prevent a network becoming loaded until normal operating conditions. Another option might be to block particular assets from being sent on this link, this could be useful if you have two destinations and you wish to send a subset of assets to each.

This example used a PI Server as the destination, however the same mechanism and filters may be used for any north destination.


Some Useful Filters
===================

A number of simple filters are worthy of mention here, a complete list of the currently available filters in Fledge can be found in the section |filter_plugins|.

Scale
-----

The filter *fledge-filter-scale* applies a scale factor and offset to the numeric values within an asset. This is useful for operations such as changing the unit of measurement of a value. An example might be to convert a temperature reading from Centigrade to Fahrenheit.

Metadata
--------

The filter *fledge-filter-metadata* will add metadata to an asset. This could be used to add information such as unit of measurement, machine data (make, model, serial no)  or the location of the asset to the data.

Delta
-----

The filter *fledge-filter-delta* allows duplicate data to be removed, only forwarding data that changes by more than a configurable percentage. This can be useful if a value does not change often and there is a desire not to forward all the *similar* values in order to save network bandwidth or reduce storage requirements.

Rate
----

The filter *fledge-filter-rate* is similar to the delta filter above, however it forwards data at a fixed rate that is lower the rate of the oncoming data but can send full rate data should an *interesting* condition be detected. The filter is configured with a rate to send data, the values sent at that rate are an average of the values seen since the last value was sent.

A rate of one reading per minute for example would average all the values for 1 minute and then send that average as the reading at the end of that minute. A condition can be added, when that condition is triggered all data is forwarded at full rate of the incoming data until a further condition is triggered that causes the reduced rate to be resumed.

