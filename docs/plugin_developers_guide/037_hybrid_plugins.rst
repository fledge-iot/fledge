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
  	"connection" : "ModbusC",
  	"defaults" : {
  		"pin" : {
  			"default" : "4"
                        }
                     }
  }

This creates a new hybrid plugin called DHT11-4 that is installed by copying this file into the plugins/south/DHT11-4 directory of your installation. Once installed it can be treated as any other south plugin within Fledge.

It may not be difficult to enter the GPIO pin in each case in this example, where it becomes more useful is for plugins such as *Modbus* where a complex map is required to be entered in a JSON document. By using a hybrid plugin we can define the map we need once and then add new sensors of the same type without having to repeat the map. An example of this would be the Flir AX8 camera that require a total of 176 Modbus registers to be mapped into 88 different values in an asset. A hybrid plugin *fledge-south-FlirAX8* defines that mapping once and as a result adding a new Flir AX8 camera is as simple as selecting the FlirAX8 hybrid plugin and entering the IP address of the camera.
