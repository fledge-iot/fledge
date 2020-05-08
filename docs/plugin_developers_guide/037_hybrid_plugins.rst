.. |br| raw:: html

   <br />

.. Images

.. Links

.. =============================================

Hybrid Plugins
==============

In addition to plugins written in Python and C/C++ it is possible to have a hybrid plugin that is a combination of an existing plugin and configuration for that plugin. This is useful in a situation whereby there are multiple sensors or devices that you connect to Fledge that have common configuration. It allows devices to be added without repeating the common configuration.

Using our example of a *DHT11* sensor connected to a GPIO pin, if we wanted to create a new plugin for a *DHT11* that was always connected to pin 4 then we could do this by creating a JSON file as below that supplies a fixed default value for the GPIO pin.

.. code-block:: JSON

  {
        "description" : "A DHT11 sensor connected to GPIO pin 4",
  	"name" : "DHT11-4",
  	"connection" : "DHT11",
  	"defaults" : {
  		"pin" : {
  			"default" : "4"
                        }
                     }
  }

This creates a new hybrid plugin called DHT11-4 that is installed by copying this file into the plugins/south/DHT11-4 directory of your installation. Once installed it can be treated as any other south plugin within Fledge. The effect of this hybrid plugin is to load the *DHT11* plugin and always set the configuration parameter called "pin" to the value "4". The item "pin" will hidden from the user in the Fledge GUI when they create the instance of the plugin. This allows for a simpler and more streamlined user experience when adding plugins with common configuration.

The items in the JSON file are;

.. list-table::
    :widths: 20 80
    :header-rows: 1

    * - Name
      - Description
    * - description
      - A description of the hybrid plugin. This will appear the right of the selection list in the Fledge user interface when the plugin is selected.
    * - name
      - The name of the plugin itself. This must match the filename of the JSON file and also the name of the directory the file is placed in.
    * - connection
      - The name of the underlying plugin that will be used as the basis for this hybrid plugin. This must be a C/C++ or Python plugin, it can not be another hybrid plugin.
    * - defaults
      - The set of values to default in this hybrid plugin. These are configuration parameters of the underlying plugin that will be fixed in the hybrid plugin. Each hybrid plugin can have one or my values here.

It may not be difficult to enter the GPIO pin in each case in this example, where it becomes more useful is for plugins such as *Modbus* where a complex map is required to be entered in a JSON document. By using a hybrid plugin we can define the map we need once and then add new sensors of the same type without having to repeat the map. An example of this would be the Flir AX8 camera that require a total of 176 Modbus registers to be mapped into 88 different values in an asset. A hybrid plugin *fledge-south-FlirAX8* defines that mapping once and as a result adding a new Flir AX8 camera is as simple as selecting the FlirAX8 hybrid plugin and entering the IP address of the camera.
