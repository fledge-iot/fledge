Set Point Control
-----------------

South plugins can also be used to exert control on the underlying device to which they are connected. This is not intended for use as a substitute for real time control systems, but rather as a mechanism to make non-time critical changes to a device or to trigger an operation on the device.

To make a south plugin support control features there are two steps that need to be taken

  - Tag the plugin as supporting control

  - Add the entry points for control


Enable Control
~~~~~~~~~~~~~~

A plugin enables control features by means of the mode field in the plugin information dict which is returned by the *plugin_info* entry point of the plugin. The flag value *control* should be added to the mode field of the plugin. Multiple flag values are separated by the pipe symbol '|'.

.. code-block:: console

    # plugin information dict
    {
        'name': 'Sinusoid Poll plugin',
        'version': '1.9.2',
        'mode': 'poll|control',
        'type': 'south',
        'interface': '1.0',
        'config': _DEFAULT_CONFIG
    }


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

.. code-block:: python

     def plugin_write(handle, name, value)

Where the parameters are;

  - **handle** the handle of the plugin instance

  - **name** the name of the item to be changed

  - **value** a string presentation of the new value to assign to the item

The return value defines if the write was successful or not. True is returned for a successful write.

.. code-block:: python

  def plugin_write(handle, name, value):
    """ Setpoint write operation

    Args:
        handle: handle returned by the plugin initialisation call
        name: Name of parameter to write
        value: Value to be written to that parameter
    Returns:
        bool: Result of the write operation
    """
    _LOGGER.info("plugin_write(): name={}, value={}".format(name, value))
    return True


In this case we are merely printing the parameter name and the value to be set for this parameter. Normally control would be used for making a change with the connected device itself, such as changing a PLC register value. This is simply an example to demonstrate the API.

Operation Entry Point
^^^^^^^^^^^^^^^^^^^^^

The plugin will support an operation entry point. This will execute the given operation synchronously, it is expected that this operation entry point will be called using a separate thread, therefore the plugin should implement operations in a thread safe environment.

The plugin write operation entry point is defined as follows

.. code-block:: python

     def plugin_operation(handle, operation, params)

Where the parameters are;

  - **handle** the handle of the plugin instance

  - **operation** the name of the operation to be executed

  - **params** a list of name/value tuples that are passed to the operation

The *operation* parameter should be used by the plugin to determine which operation is to be performed. The actual parameters are passed in a list of key/value tuples as strings.

The return from the call is a boolean result of the operation, a failure of the operation or a call to an unrecognized operation should be indicated by returning a false value. If the operation succeeds a value of true should be returned.

The following example shows the implementation of the plugin operation entry point.

.. code-block:: python

  def plugin_operation(handle, operation, params):
    """ Setpoint control operation

    Args:
        handle: handle returned by the plugin initialisation call
        operation: Name of operation
        params: Parameter list
    Returns:
        bool: Result of the operation
    """
    _LOGGER.info("plugin_operation(): operation={}, params={}".format(operation, params))
    return True

In the case of a real machine the operation would most likely cause an action on a machine, for example a request to the machine to re-calibrate itself. Above example is just a demonstration of the API.
