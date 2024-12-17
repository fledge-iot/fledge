Test E2E Notification Service with Plugins
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is designed to perform end-to-end testing of the `fledge-service-notification` by using the south service of `fledge-south-coap` plugin, the built-in rule plugin `fledge-rule-threshold`, and the delivery plugin `fledge-notify-python35`.


This test comprises of four classes having multiple test cases functions:

1. **TestNotificationService**:
    a. **test_service**: Test that install notification service into Fledge and check if it is properly installed or not.
    b. **test_get_default_notification_plugins**: Test whether the built-in rules are available after installing the notification service or not.

2. **TestNotificationCRUD**:
    a. **test_create_notification_instances_with_default_rule_and_channel_python35**: Test whether Fledge can install the `fledge-notify-python35` delivery plugin and then creates  three notification instance using the threshold rule with the `python35` delivery plugin, each haing differnt notification type.
    b. **test_inbuilt_rule_plugin_and_notify_python35_delivery**: Test whether the required rule and delivery plugins are available in Fledge.
    c. **test_get_notifications_and_audit_entry**: Test whether Fledge has logged NTFAD audit entry after adding notification insatnce.
    d. **test_update_notification**: Test whether Fledge is able to reconfigure the notification type in a notification instance.
    e. **test_delete_notification**: Test whther Fledge is able to delete notification instance wihtout any issue.

3. **TestSentAndReceiveNotification**:
    a. **test_sent_and_receive_notification**: Test that creates notification instance using the threshold rule with the `python35` delivery plugin, also add service of fledge-south-coap.  Then, verify if the notification service is working properly and creating audit logs.


Prerequisite
++++++++++++

1. Fledge must be installed by `make` command
2. FLEDGE_ROOT environment variable should be exported to location where Fledge is installed.
3. Install the prerequisites to run a test:

.. code-block:: console

  $ cd fledge/python
  $ python3 -m pip install -r requirements-test.txt

The minimum required parameters to run,

.. code-block:: console

    --wait-time=WAIT_TIME
                        Generic wait time between processes to run
    --retries=RETIRES
                        Number of tries for polling
    --junit-xml=JUNIT_XML
                        Pytest XML report 

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python/ ; 
  $ export FLEDGE_ROOT=FLEDGE_ROOT_PATH 
  $ export PYTHONPATH=$FLEDGE_ROOT/python
  $ python3 -m pytest -s -vv e2e/test_e2e_notification_service_with_plugins.py  --wait-time="WAIT_TIME" --retries="RETIRES" --junit-xml="JUNIT_XML"
