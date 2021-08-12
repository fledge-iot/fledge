.. Images
.. |setpoint_1| image:: images/setpoint_1.jpg
.. |setpoint_2| image:: images/setpoint_2.jpg
.. |setpoint_3| image:: images/setpoint_3.jpg


*****************
Set Point Control
*****************

Fledge supports facilities that allows control of devices via the south service and plugins. This control in known as *set point control* as it is not intended for real time critical control of devices but rather to modify the behavior of a device based on one of many different information flows. The latency involved in these control operations is highly dependent on the control path itself and also the scheduling limitations of the underlying operating system. Hence the caveat that the control functions are not real time or guaranteed to be actioned within a specified time window.

Control Functions
=================

The are two type of control function supported

  - Modify the value in a device via the south service and plugin.

  - Request the device to perform an action.

Set Point
---------

Setting the value within the device is known as a set point action in Fledge. This can be as simple as setting a speed variable within a controller for a fan or it may be more complete. Typically a south plugin would provide a set of values that can be manipulated, giving each a symbolic name that would be available for a set point command. The exact nature of these is defined by the south plugin.

Operation
---------

Operations, as the name implies provides a means for the south service to request a device to perform an operation, such as reset or re-calibrate. The names of these operations and any arguments that can be given are defined within the south plugin and are specific to that south plugin.

Control Paths
=============

Set point control may be invoked via a number of paths with Fledge

  - As the result of a notification within Fledge itself.

  - As a result of a request via the Fledge public REST API.

  - As a result of a control message flowing from a north side system into a north plugin and being routed onward to the south service.

Currently only the notification method is fully implemented within Fledge.

The use of a notification in the Fledge instance itself provides the fastest response for an edge notification. All the processing for this is done on the edge by Fledge itself.

Edge Based Control
------------------

As an example of how edge based control might work lets consider the following example.

We have a machine tool that is being monitored by Fledge using the OPC/UA south plugin to read data from the machine tools controlling PLC. As part of that data we receive an asset which contains the temperature of the motor which is running the tool. We can assume this asset is called *MotorTemperature* and it contains a single data point called *temperature*. 

We also have a fan unit that is able to cool that motor which is controlled via a Modbus interface. The modbus contains one a coil that toggles the fan on and off and a register that controls the speed of the fan. We configure the *fledge-south-modbus* as a service called *MotorFan* with a control map that will map the coil and register to a pair of set points. 

.. code-block:: JSON

   {
       "values" : [
                      {
                          "name" : "run",
                          "coil" : 1
                      },
                      {
                          "name"     : "speed",
                          "register" : 1
                      }
                  ]
   }

+--------------+
| |setpoint_1| |
+--------------+

If the measured temperature of the motor going above 35 degrees centigrade we want to turn the fan on at 1200 RPM. We create a new notification to do this. The notification uses the *threshold* rule and triggers if the asset *MotorTemperature*, data point *temperature* is greater than 35.

+--------------+
| |setpoint_2| |
+--------------+

We select the *setpoint* delivery plugin from the list and configure it.


    +--------------+
    | |setpoint_3| |
    +--------------+

  - In *Service* we set the name of the service we are going to use to control the fan, in this case *MotorFan* 

  - In *Trigger Value* we set the control message we are going to send to the service. This will turn the fan on and set the speed to 1200RPM

  - In *Cleared Value* we set the control message we are going to send to turn off the fan when the value falls below 35 degrees.

The plugin is enabled and we go on to set the notification type to toggled, since we want to turn off the fan if the motor cools down, and set a retrigger time to prevent the fan switching on and off too quickly.

If we required the fan to speed up at a higher temperature then this could be achieved with a second notification. In this case it would have a higher threshold value and would set the speed to a higher value in the trigger condition and set it back to 1200 in the cleared condition. Since the notification type is *toggled* the notification service will ensure that these are called in the correct order.
