Notification Service E2E Test with Plugins
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is designed to perform end-to-end testing of the `fledge-service-notification` by using the south service of `fledge-south-coap` plugin, the built-in rule plugin `fledge-rule-threshold`, and the delivery plugin `fledge-notify-python35`.

This test consists of four classes, each consists of multiple test cases functions:

1. **TestNotificationService**:
    a. **test_service**: Verifies that the notification service is correctly installed in Fledge and properly configured.
    b. **test_get_default_notification_plugins**: Verifies whether the built-in rule plugins are available after the notification service is installed.

2. **TestNotificationCRUD**:
    a. **test_create_notification_instances_with_default_rule_and_channel_python35**: Verifies whether Fledge can install the fledge-notify-python35 delivery plugin and create three notification instances using the threshold rule with the python35 delivery plugin, each having a different notification type.
    b. **test_inbuilt_rule_plugin_and_notify_python35_delivery**: Verifies whether the required rule and delivery plugins are available in Fledge.
    c. **test_get_notifications_and_audit_entry**: Verifies that Fledge logs an NTFAD audit entry after adding a notification instance.
    d. **test_update_notification**: Verifies whether Fledge can reconfigure the notification type in an existing notification instance.
    e. **test_delete_notification**: Verifies whether Fledge can delete a notification instance without any issues.

3. **TestSentAndReceiveNotification**:
    a. **test_sent_and_receive_notification**: Creates a notification instance using the threshold rule with the python35 delivery plugin and adds the fledge-south-coap service. Verifies whether the notification service is working properly and creating the corresponding audit logs.


Prerequisite
++++++++++++

1. Fledge must be installed by `make` command
2. The FLEDGE_ROOT environment variable should be exported to the directory where Fledge is installed.
3. Install the prerequisites to run a test:

.. code-block:: console

  $ cd fledge/python
  $ python3 -m pip install -r requirements-test.txt --user

The minimum required parameters to run,

.. code-block:: console

    --wait-time=WAIT_TIME
                        Generic wait time (in seconds) between processes
    --retries=RETIRES
                        Number of tries for polling
    --junit-xml=JUNIT_XML
                        Specifies the file path or directory where the JUnit XML test results should be saved.

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python/ ; 
  $ export FLEDGE_ROOT=<path_to_fledge_installation> 
  $ export PYTHONPATH=$FLEDGE_ROOT/python
  $ python3 -m pytest -s -vv e2e/test_e2e_notification_service_with_plugins.py --wait-time="<WAIT_TIME>" --retries="<RETIRES>" --junit-xml="<JUNIT_XML>"
