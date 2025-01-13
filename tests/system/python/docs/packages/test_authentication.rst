Test Authentication
~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is specifically designed for basic testing of the `fledge-filter-python35` plugixiv. It incorporates the use of `fledge-south-http-south` for ingesting data into Fledge via Fogbench and `fledge-filter-expression` to verify Fledge's ability to handle multiple filters in a pipeline alongside `fledge-filter-python35`.

This test consists of eight classes, each containing multiple test case functions:

1. **TestTLSDisabled**:
    Following test case function check funcitonality of Fledge, when tls is disabled and auth is not mandatory:
    i. **test_on_default_port**: Verify if Fledge is properly running on the default port.
    ii. **test_on_custom_port**: Verify that Fledge's default HTTP port is successfully changed to a custom port, the service is restarted, and that Fledge is functioning correctly by confirming it is running on the new custom port.
    iii. **test_reset_to_default_port**: Verify that Fledge's HTTP port is changed back to the default port (8081), the service is restarted, and that Fledge is functioning correctly by confirming it is running on the default port.

2. **TestAuthAnyWithoutTLS**: 
    Following test case function check funcitonality of Fledge, when tls is disabled but auth is mandatory with any authentication method only:
    i. **test_login_regular_user_using_password**: Checks if Fledge is allowing login of regular user (not admin user) via username and password.
    ii. **test_logout_me_password_token**: Checks if Fledge is allowing logout of regular user (not admin user) via password token.
    iii. **test_login_with_invalid_credentials_regular_user_using_password**: Checks if regular user is able to login into Fledge using invalid credentials.
    iv. **test_login_username_admin_using_password**: Checks if Fledge is allowing admin u using username and password.
    v. **test_login_with_invalid_credentials_admin_using_password**: Checks if admin user is able to login into Fledge using invalid credentials.
    vi. **test_login_with_user_certificate**: Checks if regular user (not admin user) is able to login into Fledge using certificates.
    vii. **test_login_with_admin_certificate**: Checks if admin user is able to login into Fledge using certificates.
    viii. **test_login_with_custom_certificate**: Creatses custom certificates for a regular user and verifies whether the user can log in to Fledge using those custom certificates.
    ix. **test_ping_with_allow_ping_true**: Checks if `/fledge/ping` is giving response, when ping is allowed by Fledge.
    x. **test_ingest_with_password_token**: Verify that the `http-south` plugin is successfully added as a south service using a password token, and check whether Fledge can ingest data via Fogbench into Fledge.
    xi. **test_ingest_with_certificate_token**: Verify that the `http-south` plugin is successfully added as a south service using a certificate token, and check whether Fledge can ingest data via Fogbench into Fledge.
    xii. **test_ping_with_allow_ping_false_with_password_token**: Checks if `/fledge/ping` is giving response, when ping is not allowed by Fledge and tried with regular user's credentials.
    xiii. **test_ping_with_allow_ping_false_with_certificate_token**: Checks if `/fledge/ping` is giving response, when ping is not allowed by Fledge and tried with regular user's certificates.
    xiv. **test_get_users_with_password_token**: Checks if differnt users (admin and regular users) are able to list the users of Fledge, using password token.
    xv. **test_get_users_with_certificate_token**: Checks if differnt users (admin and regular users) are able to list the users of Fledge, using certificate token.
    xvi. **test_get_roles_with_password_token**: Checks if admin users is able to list the users of Fledge, using password token.
    xvii. **test_get_roles_with_certificate_token**: Checks if admin users is able to list the users of Fledge, using certificate token.
    xviii. **test_create_user_with_password_token**: Checks if admin users is able to create users of Fledge, using password token.
    xix. **test_create_user_with_certificate_token**: Checks if admin users is able to create users of Fledge, using certificate token.
    xx. **test_login_of_newly_created_user**: Checks if newly created user are able to login into Fledge using useername and password.
    xxi. **test_update_password_with_password_token**: Checks if Fledge is allowing regular user to update password using password token.
    xxii. **test_update_password_with_certificate_token**: Checks if Fledge is allowing regular user to update password using certificate token.
    xxiii. **test_login_with_updated_password**: Checks if regular user is able to login into Fledge using updated password.
    xxiv. **test_reset_user_with_password_token**: Checks if admin user is able to reset/update password  of regular user using password token.
    xxv. **test_reset_user_with_certificate_token**: Checks if admin user is able to reset/update password  of regular user using certificate token.
    xxvi. **test_login_with_resetted_password**: Checks if regular user is able to login into Fledge using resetted password or password updated by admin user.
    xxvii. **test_delete_user_with_password_token**: Checks if admin is able to delete any specific user from Fledge using the password token.
    xxviii. **test_delete_user_with_certificate_token**: Checks if admin is able to delete any specific user from Fledge using the certificate token.
    xxix. **test_login_of_deleted_user**: Checks if the deleted user is able to login into Fledge.
    xxx. **test_logout_all_with_password_token**: Checks if admin is able to log out all the session of specifc user of Fledge, using password token.
    xxxi. **test_verify_logout**: Checks if specifc user is logged out.
    xxxii. **test_admin_actions_forbidden_for_regular_user_with_pwd_token**: Checks if regular user is not able to perform any actions that only an admin can, using password token.
    xxxiii. **test_admin_actions_forbidden_for_regular_user_with_cert_token**: Checks if regular user is not able to perform any actions that only an admin can, using certificate token.

3. **TestAuthPasswordWithoutTLS**:
    Following test case function check funcitonality of Fledge, when tls is disabled but auth is mandatory with password authentication method:
    i. **test_login_username_regular_user**: Checks if Fledge is allowing login of regular user (not admin user) via username and password.
    ii. **test_logout_me**: Checks if Fledge is allowing logout of regular user (not admin user) via password token.
    iii. **test_login_with_invalid_credentials_regular_user**: Checks if regular user is able to login into Fledge using invalid credentials.
    iv. **test_login_username_admin**: Checks if Fledge is allowing admin u using username and password.
    v. **test_login_with_invalid_credentials_admin**: Checks if admin user is able to login into Fledge using invalid credentials.
    vi. **test_login_with_admin_certificate**: Checks admin user should not able to login into Fledge using certificates.
    vii. **test_ping_with_allow_ping_true**: Checks if `/fledge/ping` is giving response, when ping is allowed by Fledge.
    viii. **test_ingest**: Verify that the `http-south` plugin is successfully added as a south service using a password token, and confirm whether Fledge is able to ingest data via Fogbench into the system
    ix. **test_ping_with_allow_ping_false**: Checks if `/fledge/ping` is giving response, when ping is not allowed by Fledge and tried with regular user's credentials.
    x. **test_get_users**: Checks if differnt users (admin and regular users) are able to list the users of Fledge, using password token.
    xi. **test_get_roles**: Checks if admin users is able to list the users of Fledge, using password token.
    xii. **test_create_user**: Checks if admin users is able to create users of Fledge, using password token.
    xiii. **test_login_of_newly_created_user**: Checks if newly created user are able to login into Fledge using useername and password.
    xiv. **test_update_password**: Checks if Fledge is allowing regular user to update password using password token.
    xv. **test_login_with_updated_password**: Checks if regular user is able to login into Fledge using updated password.
    xvi. **test_reset_user**: Checks if admin user is able to reset/update password  of regular user using password token.
    xvii. **test_login_with_resetted_password**: Checks if regular user is able to login into Fledge using resetted password or password updated by admin user.
    xviii. **test_delete_user**: Checks if admin is able to delete any specific user from Fledge using the password token.
    xix. **test_login_of_deleted_user**: Checks if the deleted user is able to login into Fledge.
    xx. **test_logout_all**: Checks if admin is able to log out all the session of specifc user of Fledge, using password token.
    xxi. **test_verify_logout**: Checks if specifc user is logged out.
    xxii. **test_admin_actions_forbidden_for_regular_user**: Checks if regular user is not able to perform any actions that only an admin can, using password token.

4. **TestAuthCertificateWithoutTLS**:
    Following test case function check funcitonality of Fledge, when tls is disabled but auth is mandatory with certificate authentication method only:
    i. **test_login_with_user_certificate**: Checks if regular user (not admin user) is able to login into Fledge using certificates.
    ii. **test_login_with_admin_certificate**: Checks if admin user is able to login into Fledge using certificates.
    iii. **test_login_with_custom_certificate**: Creatses custom certificates for a regular user and verifies whether the user can log in to Fledge using those custom certificates.
    iv. **test_login_with_invalid_credentials**: Checks if regular user is able to login into Fledge using invalid certificate.
    v. **test_login_username_admin**: Checks Fledge should not allow admin user to login using username and password.
    vi. **test_ping_with_allow_ping_true**: Checks if `/fledge/ping` is giving response, when ping is allowed by Fledge.
    vii. **test_ingest**: Verify that the `http-south` plugin is successfully added as a south service using a certificate token, and confirm whether Fledge is able to ingest data via Fogbench into the system
    viii. **test_ping_with_allow_ping_false**: Checks if `/fledge/ping` is giving response, when ping is not allowed by Fledge and tried with admin user's certificates.
    ix. **test_get_users**: Checks if differnt users (admin and regular users) are able to list the users of Fledge, using certificate token.
    x. **test_get_roles**: Checks if admin users is able to list the users of Fledge, using certificate token.
    xi. **test_create_user**: Checks if admin users is able to create users of Fledge, using certificate token.
    xii. **test_update_password**: Checks if Fledge is allowing regular user to update password using certificate token.
    xiii. **test_reset_user**: Checks if admin user is able to reset/update password  of regular user using certificate token.
    xiv. **test_delete_user**: Checks if admin is able to delete any specific user from Fledge using the certificate token.
    xv. **test_logout_all**: Checks if admin is able to log out all the session of specifc user of Fledge, using certificate token.
    xvi. **test_verify_logout**: Checks if specifc user is logged out.
    xvii. **test_admin_actions_forbidden_for_regular_user**: Checks if regular user is not able to perform any actions that only an admin can, using certificate token.

5. **TestTLSEnabled**:
    Following test case function check funcitonality of Fledge, when tls is enabled and auth is not mandatory:
    i. **test_on_default_port**: Verifies if Fledge is properly running on the default port.
    ii. **test_on_custom_port**: Verify that Fledge's default HTTP port is changed to a custom port, restart the service, and check if Fledge is running correctly on the custom port

6. **TestAuthAnyWithTLS**:
    Following test case function check funcitonality of Fledge, when tls is enabled and auth is mandatory with any authentication method:
    i. **test_login_regular_user_using_password**: Checks if Fledge is allowing login of regular user (not admin user) via username and password.
    ii. **test_logout_me_password_token**: Checks if Fledge is allowing logout of regular user (not admin user) via password token.
    iii. **test_login_with_invalid_credentials_regular_user_using_password**: Checks if regular user is able to login into Fledge using invalid credentials.
    iv. **test_login_username_admin_using_password**: Checks if Fledge is allowing admin u using username and password.
    v. **test_login_with_invalid_credentials_admin_using_password**: Checks if admin user is able to login into Fledge using invalid credentials.
    vi. **test_login_with_user_certificate**: Checks if regular user (not admin user) is able to login into Fledge using certificates.
    vii. **test_login_with_admin_certificate**: Checks if admin user is able to login into Fledge using certificates.
    viii. **test_ping_with_allow_ping_false**: Checks if `/fledge/ping` is giving response, when ping is not allowed by Fledge and tried with regular user's credentials.
    ix. **test_login_with_custom_certificate**: Creatses custom certificates for a regular user and verifies whether the user can log in to Fledge using those custom certificates.
    x. **test_ping_with_allow_ping_true**: Checks if `/fledge/ping` is giving response, when ping is allowed by Fledge.
    xi. **test_ingest_with_password_token**: Verify that the `http-south` plugin is successfully added as a south service using a password token, and check whether Fledge can ingest data via Fogbench into Fledge.
    xii. **test_ingest_with_certificate_token**: Verify that the `http-south` plugin is successfully added as a south service using a certificate token, and check whether Fledge can ingest data via Fogbench into Fledge.
    xiii. **test_ping_with_allow_ping_false_with_password_token**: Checks if `/fledge/ping` is giving response, when ping is not allowed by Fledge and tried with regular user's credentials.
    xiv. **test_ping_with_allow_ping_false_with_certificate_token**: Checks if `/fledge/ping` is giving response, when ping is not allowed by Fledge and tried with regular user's certificates.
    xv. **test_get_users_with_password_token**: Checks if differnt users (admin and regular users) are able to list the users of Fledge, using password token.
    xvi. **test_get_users_with_certificate_token**: Checks if differnt users (admin and regular users) are able to list the users of Fledge, using certificate token.
    xvii. **test_get_roles_with_certificate_token**: Checks if admin users is able to list the users of Fledge, using certificate token.
    xviii. **test_create_user_with_password_token**: Checks if admin users is able to create users of Fledge, using password token.
    xix. **test_create_user_with_certificate_token**: Checks if admin users is able to create users of Fledge, using certificate token.
    xx. **test_login_of_newly_created_user**: Checks if newly created user are able to login into Fledge using useername and password.
    xxi. **test_update_password_with_password_token**: Checks if Fledge is allowing regular user to update password using password token.
    xxii. **test_update_password_with_certificate_token**: Checks if Fledge is allowing regular user to update password using certificate token.
    xxiii. **test_login_with_updated_password**: Checks if regular user is able to login into Fledge using updated password.
    xxiv. **test_reset_user_with_password_token**: Checks if admin user is able to reset/update password  of regular user using password token.
    xxv. **test_reset_user_with_certificate_token**: Checks if admin user is able to reset/update password  of regular user using certificate token.
    xxvi. **test_login_with_resetted_password**: Checks if regular user is able to login into Fledge using resetted password or password updated by admin user.
    xxvii. **test_delete_user_with_password_token**: Checks if admin is able to delete any specific user from Fledge using the password token.
    xxviii. **test_delete_user_with_certificate_token**: Checks if admin is able to delete any specific user from Fledge using the certificate token.
    xxix. **test_login_of_deleted_user**: Checks if the deleted user is able to login into Fledge.
    xxx. **test_logout_all_with_password_token**: Checks if admin is able to log out all the session of specifc user of Fledge, using password token.
    xxxi. **test_verify_logout**: Checks if specifc user is logged out.
    xxxii. **test_admin_actions_forbidden_for_regular_user_with_pwd_token**: Checks if regular user is not able to perform any actions that only an admin can, using password token.
    xxxiii. **test_admin_actions_forbidden_for_regular_user_with_cert_token**: Checks if regular user is not able to perform any actions that only an admin can, using certificate token.

7. **TestAuthPasswordWithTLS**:
    Following test case function check funcitonality of Fledge, when tls is enabled and auth is mandatory with password authentication method:
    i. **test_login_username_regular_user**: Checks if Fledge is allowing login of regular user (not admin user) via username and password.
    ii. **test_logout_me**: Checks if Fledge is allowing logout of regular user (not admin user) via password token.
    iii. **test_login_with_invalid_credentials_regular_user**: Checks if regular user is able to login into Fledge using invalid credentials.
    iv. **test_login_username_admin**: Checks if Fledge is allowing admin u using username and password.
    v. **test_login_with_invalid_credentials_admin**: Checks if admin user is able to login into Fledge using invalid credentials.
    vi. **test_login_with_admin_certificate**: Checks admin user should not able to login into Fledge using certificates.
    vii. **test_ping_with_allow_ping_true**: Checks if `/fledge/ping` is giving response, when ping is allowed by Fledge.
    viii. **test_ingest**: Verify that the 'http-south' plugin is added as a south service using a password token, and check if Fledge is able to ingest data via Fogbench into the system.
    ix. **test_ping_with_allow_ping_false**: Checks if `/fledge/ping` is giving response, when ping is not allowed by Fledge and tried with regular user's credentials.
    x. **test_get_users**: Checks if differnt users (admin and regular users) are able to list the users of Fledge, using password token.
    xi. **test_get_roles**: Checks if admin users is able to list the users of Fledge, using password token.
    xii. **test_create_user**: Checks if admin users is able to create users of Fledge, using password token.
    xiii. **test_login_of_newly_created_user**: Checks if newly created user are able to login into Fledge using useername and password.
    xiv. **test_update_password**: Checks if Fledge is allowing regular user to update password using password token.
    xv. **test_login_with_updated_password**: Checks if regular user is able to login into Fledge using updated password.
    xvi. **test_reset_user**: Checks if admin user is able to reset/update password  of regular user using password token.
    xvii. **test_login_with_resetted_password**: Checks if regular user is able to login into Fledge using resetted password or password updated by admin user.
    xviii. **test_delete_user**: Checks if admin is able to delete any specific user from Fledge using the password token.
    xix. **test_login_of_deleted_user**: Checks if the deleted user is able to login into Fledge.
    xx. **test_logout_all**: Checks if admin is able to log out all the session of specifc user of Fledge, using password token.
    xxi. **test_verify_logout**: Checks if specifc user is logged out.
    xxii. **test_admin_actions_forbidden_for_regular_user**: Checks if regular user is not able to perform any actions that only an admin can, using password token.

8. **TestAuthCertificateWithTLS**:
    Following test case function check funcitonality of Fledge, when tls is enabled and auth is mandatory with certificate authentication method only:
    i. **test_login_with_user_certificate**: Checks if regular user (not admin user) is able to login into Fledge using certificates.
    ii. **test_login_with_admin_certificate**: Checks if admin user is able to login into Fledge using certificates.
    iii. **test_login_with_custom_certificate**: Creatses custom certificates for a regular user and verifies whether the user can log in to Fledge using those custom certificates.
    iv. **test_login_with_invalid_credentials**: Checks if regular user is able to login into Fledge using invalid certificate.
    v. **test_login_username_admin**: Checks Fledge should not allow admin user to login using username and password.
    vi. **test_ping_with_allow_ping_true**: Checks if `/fledge/ping` is giving response, when ping is allowed by Fledge.
    vii. **test_ingest**: Verify that the 'http-south' plugin is added as a south service using a certificate token, and check if Fledge is able to ingest data via Fogbench into the system.
    viii. **test_ping_with_allow_ping_false**: Checks if `/fledge/ping` is giving response, when ping is not allowed by Fledge and tried with admin user's certificates.
    ix. **test_get_users**: Checks if differnt users (admin and regular users) are able to list the users of Fledge, using certificate token.
    x. **test_get_roles**: Checks if admin users is able to list the users of Fledge, using certificate token.
    xi. **test_create_user**: Checks if admin users is able to create users of Fledge, using certificate token.
    xii. **test_update_password**: Checks if Fledge is allowing regular user to update password using certificate token.
    xiii. **test_reset_user**: Checks if admin user is able to reset/update password  of regular user using certificate token.
    xiv. **test_delete_user**: Checks if admin is able to delete any specific user from Fledge using the certificate token.
    xv. **test_logout_all**: Checks if admin is able to log out all the session of specifc user of Fledge, using certificate token.
    xvi. **test_verify_logout**: Checks if specifc user is logged out.
    xvii. **test_admin_actions_forbidden_for_regular_user**: Checks if regular user is not able to perform any actions that only an admin can, using certificate token.


Prerequisite
++++++++++++

Install the prerequisites to run a test:

.. code-block:: console

   $ cd fledge/python
   $ python3 -m pip install -r requirements-tesxixtxt


The minimum required parameters to run,

.. code-block:: console

    --package-build-version=PACKAGE_BUILD_VERSION
                        Package build version for http://archives.fledge-iot.org/
    --wait-time=WAIT_TIME
                        Generic wait time (in seconds) between processes
    --junit-xml=JUNIT_XML
                        Specifies the file path or directory where the JUnit XML test results should be saved.

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python/
  $ python3 -m pytest -s -vv packages/test_authentication.py --package-build-version="<PACKAGE_BUILD_VERSION>" --wait-time="<WAIT_TIME>" --junit-xml="<JUNIT_XML>"
