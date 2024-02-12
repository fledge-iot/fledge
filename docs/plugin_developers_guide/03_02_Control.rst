.. Links in new tabs

.. |fledge South Random| raw:: html

   <a href="https://github.com/fledge-iot/fledge-south-random" target="_blank">https://github.com/fledge-iot/fledge-south-random</a>
   <br />


Set Point Control
-----------------

South plugins can also be used to exert control on the underlying device to which they are connected. This is not intended for use as a substitute for real time control systems, but rather as a mechanism to make non-time critical changes to a device or to trigger an operation on the device.

To make a south plugin support control features there are two steps that need to be taken

  - Tag the plugin as supporting control

  - Add the entry points for control


Enable Control
~~~~~~~~~~~~~~

A plugin enables control features by means of the flags in the plugin information data structure which is returned by the *plugin_info* entry point of the plugin. The flag value *SP_CONTROL* should be added to the flags of the plugin.

.. code-block:: console

      /**
       * The plugin information structure
       */
      static PLUGIN_INFORMATION info = {
              PLUGIN_NAME,              // Name
              VERSION,                  // Version
              SP_CONTROL,   	    // Flags - add control
              PLUGIN_TYPE_SOUTH,        // Type
              "1.0.0",                  // Interface version
              CONFIG                    // Default configuration
      };

Adding this flag will cause the south service to do a number of things when it loads the plugin;

  - The south service will attempt to resolve the two control entry points.

  - A toggle will be added to the advanced configuration category of the service that will permit the disabling of control services.

  - A security category will be added to the south service that contains the access control lists and permissions associated with the service.

Control Entry Points
~~~~~~~~~~~~~~~~~~~~

Two entry points are supported for control operations in the south plugin

  - **plugin_write**: which is used to set the value of a parameter within the plugin or device

  - **plugin_operation**: which is used to perform an operation on the plugin or device

The south plugin can support one or both of these entry points as appropriate for the plugin.

Write Entry Point
^^^^^^^^^^^^^^^^^

The write entry point is used to set data in the plugin or write data into the device.

The plugin write entry point is defined as follows

.. code-block:: C

     bool plugin_write(PLUGIN_HANDLE handle, string name, string value)

Where the parameters are;

  - **handle** the handle of the plugin instance

  - **name** the name of the item to be changed

  - **value** a string presentation of the new value to assign top the item

The return value defines if the write was successful or not. True is returned for a successful write.

.. code-block:: C

  bool plugin_write(PLUGIN_HANDLE handle, string& name, string& value)
  {
  	Random *random = static_cast<Random *>(handle);

  	return random->write(operation, name, value);
  }

In this case the main logic of the write operation is implemented in a class that contains all the plugin logic. Note that the assumption here, and a design pattern often used by plugin writers, is that the *PLUGIN_HANDLE* is actually a pointer to a C++ class instance.

In this case the implementation in the plugin class is as follows:

.. code-block:: C

  bool Random::write(string& name, string& value)
  {
        if (name.compare("mode") == 0)
        {
                if (value.compare("relative") == 0)
                {
                        m_mode = RELATIVE_MODE;
                }
                else if (value.compare("absolute") == 0)
                {
                        m_mode = ABSOLUTE_MODE;
                }
                Logger::getLogger()->error("Unknown mode requested '%s' ignored.", value.c_str());
                return false;
        }
        else
        {
                Logger::getLogger()->error("Unknown control item '%s' ignored.", name.c_str());
                return false;
        }
        return true;
  }

In this case the code is relatively simple as we assume there is a single control parameter that can be written, the mode of operation. We look for the known name and if a different name is passed an error is logged and false is returned. If the correct name is passed in we then check the value and take the appropriate action. If the value is not a recognized value then an error is logged and we again return false.

In this case we are merely setting a value within the plugin, this could equally well be done via configuration and would in that case be persisted between restarted. Normally control would not be used for this, but rather for making a change with the connected device itself, such as changing a PLC register value. This is simply an example to demonstrate the mechanism.

Operation Entry Point
^^^^^^^^^^^^^^^^^^^^^

The plugin will support an operation entry point. This will execute the given operation synchronously, it is expected that this operation entry point will be called using a separate thread, therefore the plugin should implement operations in a thread safe environment.

The plugin write operation entry point is defined as follows

.. code-block:: C

     bool plugin_operation(PLUGIN_HANDLE handle, string& operation, int count, PLUGIN_PARAMETER **params)

Where the parameters are;

  - **handle** the handle of the plugin instance

  - **operation** the name of the operation to be executed

  - **count** the number of parameters

  - **params** a set of name/value pairs that are passed to the operation

The *operation* parameter should be used by the plugin to determine which operation is to be performed, that operation may also be passed a number of parameters. The count of these parameters are passed to the plugin in the *count* argument and the actual parameters are passed in an array of key/value pairs as strings.

The return from the call is a boolean result of the operation, a failure of the operation or a call to an unrecognized operation should be indicated by returning a false value. If the operation succeeds a value of true should be returned.

The following example shows the implementation of the plugin operation entry point.

.. code-block:: C

  bool plugin_operation(PLUGIN_HANDLE handle, string& operation, int count, PLUGIN_PARAMETER **params)
  {
  	Random *random = static_cast<Random *>(handle);

  	return random->operation(operation, count, params);
  }

In this case the main logic of the operation is implemented in a class that contains all the plugin logic. Note that the assumption here, and a design pattern often used by plugin writers, is that the *PLUGIN_HANDLE* is actually a pointer to a C++ class instance.

In this case the implementation in the plugin class is as follows:

.. code-block:: C

  /**
   * SetPoint operation. We support reseeding the random number generator
   */
  bool Random::operation(const std::string& operation, int count, PLUGIN_PARAMETER **params)
  {
          if (operation.compare("seed") == 0)
          {
                  if (count)
                  {
                          if (params[0]->name.compare("seed"))
                          {
                                  long seed = strtol(params[0]->value.c_str(), NULL, 10);
                                  srand(seed);
                          }
                          else
                          {
                                  return false;
                          }
                  }
                  else
                  {
                          srand(time(0));
                  }
                  Logger::getLogger()->info("Reseeded random number generator");
                  return true;
          }
          Logger::getLogger()->error("Unrecognised operation %s", operation.c_str());
          return false;
  }

In this example, the operation method checks the name of the operation to perform, only a single operation is supported by this plugin. If this operation name differs the method will log an error and return false. If the operation is recognized it will check for any arguments passed in, retrieve and use it. In this case an optional *seed* argument may be passed.

The full source code, including the *Random* class can be found in GitHub |fledge South Random|

There is no actual machine connected here, therefore the operation occurs within the plugin. In the case of a real machine the operation would most likely cause an action on a machine, for example a request to the machine to re-calibrate itself.
