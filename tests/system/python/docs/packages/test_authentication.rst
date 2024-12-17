Test Authentication
~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is specifically designed for basic testing of the `fledge-filter-python35` plugixiv. It incorporates the use of `fledge-south-http-south` for ingesting data into Fledge via Fogbench and `fledge-filter-expression` to verify Fledge's ability to handle multiple filters in a pipeline alongside `fledge-filter-python35`.


This test comprises two classes having multiple test cases functions:

1. **TestTLSDisabled**:
    Following test case function check funcitonality of fledge, when tls is disabled and auth is not mandatory:
    i. **test_on_default_port**: Test to verify if Fledge is properly running on the default port.
    ii. **test_on_custom_port**: Test that changes Fledge's default HTTP port to a custom port, restarts it, and verifies whether Fledge is running correctly on the custom port.
    iii. **test_reset_to_default_port**: Test that changes back Fledge's HTTP port to a default port, i.e. 8081, restarts it, and verifies whether Fledge is running correctly on the custom port.

2. **TestAuthAnyWithoutTLS**: 
    Following test case function check funcitonality of fledge, when tls is disabled but auth is mandatory with any authentication method only:
    i. **test_login_regular_user_using_password**: Test that check if fledge is allowing login of regular user (not admin user) into fledge via username and password.
    ii. **test_logout_me_password_token**: Test that check if fledge is allowing logout of regular user (not admin user) from fledge via password token.
    iii. **test_login_with_invalid_credentials_regular_user_using_password**: Test that check if regular user is able to login into fledge using invalid credentials or not.
    iv. **test_login_username_admin_using_password**: Test that check if fledge is allowing admin user to login into fledge using usernam and password or not.
    v. **test_login_with_invalid_credentials_admin_using_password**: Test that check if admin user is able to login into fledge or not using invalid credentials.
    vi. **test_login_with_user_certificate**: Test that check if regular user (not admin user) is able to login into fledge or not using certificates.
    vii. **test_login_with_admin_certificate**: Test that check if admin user is able to login into fledge or not using certificates.
    viii. **test_login_with_custom_certificate**: Test that creates custom certificates for a regular user and verifies whether the user can log in to Fledge using those custom certificates.
    ix. **test_ping_with_allow_ping_true**: Test that check if `/fledge/ping` is giving response or not, when ping is allowed by fledge.
    x. **test_ingest_with_password_token**: Test that add south service of `http-south` plugin using password token and check if fledge is able to ingest data via fogbench into fledge or not.
    xi. **test_ingest_with_certificate_token**: Test that add south service of `http-south` plugin using certificate token and check if fledge is able to ingest data via fogbench into fledge or not.
    xii. **test_ping_with_allow_ping_false_with_password_token**: Test that check if `/fledge/ping` is giving response or not, when ping is not allowed by fledge and tried with regular user's credentials.
    xiii. **test_ping_with_allow_ping_false_with_certificate_token**: Test that check if `/fledge/ping` is giving response or not, when ping is not allowed by fledge and tried with regular user's certificates.
    xiv. **test_get_users_with_password_token**: Test that checks if differnt users (admin and regular users) are able to list the users of fledge or not, using password token.
    xv. **test_get_users_with_certificate_token**: Test that checks if differnt users (admin and regular users) are able to list the users of fledge or not, using certificate token.
    xvi. **test_get_roles_with_password_token**: Test that checks if admin users is able to list the users of fledge or not, using password token.
    xvii. **test_get_roles_with_certificate_token**: Test that checks if admin users is able to list the users of fledge or not, using certificate token.
    xviii. **test_create_user_with_password_token**: Test that checks if admin users is able to create users of fledge or not, using password token.
    xix. **test_create_user_with_certificate_token**: Test that checks if admin users is able to create users of fledge or not, using certificate token.
    xx. **test_login_of_newly_created_user**: Test that checks if newly created user are able to login into fledge or not using useername and password.
    xxi. **test_update_password_with_password_token**: Test that checks if fledge is allowing regular user to update it password using password token or not.
    xxii. **test_update_password_with_certificate_token**: Test that checks if fledge is allowing regular user to update it password using certificate token or not.
    xxiii. **test_login_with_updated_password**: Test that check if regular user is able to login into fledge using updated password.
    xxiv. **test_reset_user_with_password_token**: Test that checks if admin user is able to reset/update password  of regular user using password token or not.
    xxv. **test_reset_user_with_certificate_token**: Test that checks if admin user is able to reset/update password  of regular user using certificate token or not.
    xxvi. **test_login_with_resetted_password**: Test that check if regular user is able to login into fledge using the password reseted or updated by admin user.
    xxvii. **test_delete_user_with_password_token**: Test that check if admin is able to delete any speccifc user from fledge using the password token or not.
    xxviii. **test_delete_user_with_certificate_token**: Test that check if admin is able to delete any speccifc user from fledge using the certificate token or not.
    xxix. **test_login_of_deleted_user**: Test that check if the deleted user is able to login into fledge or not.
    xxx. **test_logout_all_with_password_token**: Test that check if admin is able to log out all the session of specifc user of fledge or not, using password token.
    xxxi. **test_verify_logout**: Test that check if specifc user is logged out or not.
    xxxii. **test_admin_actions_forbidden_for_regular_user_with_pwd_token**: Test that check if regular user is not able to perform any actions that only an admin can or not, using password token.
    xxxiii. **test_admin_actions_forbidden_for_regular_user_with_cert_token**: Test that check if regular user is not able to perform any actions that only an admin can or not, using certificate token.

3. **TestAuthPasswordWithoutTLS**:
    Following test case function check funcitonality of fledge, when tls is disabled but auth is mandatory with password authentication method:
    i. **test_login_username_regular_user**: Test that check if fledge is allowing login of regular user (not admin user) into fledge via username and password.
    ii. **test_logout_me**: Test that check if fledge is allowing logout of regular user (not admin user) from fledge via password token.
    iii. **test_login_with_invalid_credentials_regular_user**: Test that check if regular user is able to login into fledge using invalid credentials or not.
    iv. **test_login_username_admin**: Test that check if fledge is allowing admin user to login into fledge using usernam and password or not.
    v. **test_login_with_invalid_credentials_admin**: Test that check if admin user is able to login into fledge or not using invalid credentials.
    vi. **test_login_with_admin_certificate**: Test that check admin user should not able to login into fledge or not using certificates.
    vii. **test_ping_with_allow_ping_true**: Test that check if `/fledge/ping` is giving response or not, when ping is allowed by fledge.
    viii. **test_ingest**: Test that add south service of `http-south` plugin using password token and check if fledge is able to ingest data via fogbench into fledge or not.
    ix. **test_ping_with_allow_ping_false**: Test that check if `/fledge/ping` is giving response or not, when ping is not allowed by fledge and tried with regular user's credentials.
    x. **test_get_users**: Test that checks if differnt users (admin and regular users) are able to list the users of fledge or not, using password token.
    xi. **test_get_roles**: Test that checks if admin users is able to list the users of fledge or not, using password token.
    xii. **test_create_user**: Test that checks if admin users is able to create users of fledge or not, using password token.
    xiii. **test_login_of_newly_created_user**: Test that checks if newly created user are able to login into fledge or not using useername and password.
    xiv. **test_update_password**: Test that checks if fledge is allowing regular user to update it password using password token or not.
    xv. **test_login_with_updated_password**: Test that check if regular user is able to login into fledge using updated password.
    xvi. **test_reset_user**: Test that checks if admin user is able to reset/update password  of regular user using password token or not.
    xvii. **test_login_with_resetted_password**: Test that check if regular user is able to login into fledge using the password reseted or updated by admin user.
    xviii. **test_delete_user**: Test that check if admin is able to delete any speccifc user from fledge using the password token or not.
    xix. **test_login_of_deleted_user**: Test that check if the deleted user is able to login into fledge or not.
    xx. **test_logout_all**: Test that check if admin is able to log out all the session of specifc user of fledge or not, using password token.
    xxi. **test_verify_logout**: Test that check if specifc user is logged out or not.
    xxii. **test_admin_actions_forbidden_for_regular_user**: Test that check if regular user is not able to perform any actions that only an admin can or not, using password token.

4. **TestAuthCertificateWithoutTLS**:
    Following test case function check funcitonality of fledge, when tls is disabled but auth is mandatory with certificate authentication method only:
    i. **test_login_with_user_certificate**: Test that check if regular user (not admin user) is able to login into fledge or not using certificates.
    ii. **test_login_with_admin_certificate**: Test that check if admin user is able to login into fledge or not using certificates.
    iii. **test_login_with_custom_certificate**: Test that creates custom certificates for a regular user and verifies whether the user can log in to Fledge using those custom certificates.
    iv. **test_login_with_invalid_credentials**: Test that check if regular user is able to login into fledge using invalid certificate or not.
    v. **test_login_username_admin**: Test that check fledge should not allow admin user to login into fledge using usernam and password or not.
    vi. **test_ping_with_allow_ping_true**: Test that check if `/fledge/ping` is giving response or not, when ping is allowed by fledge.
    vii. **test_ingest**: Test that add south service of `http-south` plugin using certificate token and check if fledge is able to ingest data via fogbench into fledge or not.
    viii. **test_ping_with_allow_ping_false**: Test that check if `/fledge/ping` is giving response or not, when ping is not allowed by fledge and tried with admin user's certificates.
    ix. **test_get_users**: Test that checks if differnt users (admin and regular users) are able to list the users of fledge or not, using certificate token.
    x. **test_get_roles**: Test that checks if admin users is able to list the users of fledge or not, using certificate token.
    xi. **test_create_user**: Test that checks if admin users is able to create users of fledge or not, using certificate token.
    xii. **test_update_password**: Test that checks if fledge is allowing regular user to update it password using certificate token or not.
    xiii. **test_reset_user**: Test that checks if admin user is able to reset/update password  of regular user using certificate token or not.
    xiv. **test_delete_user**: Test that check if admin is able to delete any speccifc user from fledge using the certificate token or not.
    xv. **test_logout_all**: Test that check if admin is able to log out all the session of specifc user of fledge or not, using certificate token.
    xvi. **test_verify_logout**: Test that check if specifc user is logged out or not.
    xvii. **test_admin_actions_forbidden_for_regular_user**: Test that check if regular user is not able to perform any actions that only an admin can or not, using certificate token.

5. **TestTLSEnabled**:
    Following test case function check funcitonality of fledge, when tls is enabled and auth is not mandatory:
    i. **test_on_default_port**: Test to verify if Fledge is properly running on the default port.
    ii. **test_on_custom_port**: Test that changes Fledge's default HTTP port to a custom port, restarts it, and verifies whether Fledge is running correctly on the custom port.

6. **TestAuthAnyWithTLS**:
    Following test case function check funcitonality of fledge, when tls is enabled and auth is mandatory with any authentication method:
    i. **test_login_regular_user_using_password**: Test that check if fledge is allowing login of regular user (not admin user) into fledge via username and password.
    ii. **test_logout_me_password_token**: Test that check if fledge is allowing logout of regular user (not admin user) from fledge via password token.
    iii. **test_login_with_invalid_credentials_regular_user_using_password**: Test that check if regular user is able to login into fledge using invalid credentials or not.
    iv. **test_login_username_admin_using_password**: Test that check if fledge is allowing admin user to login into fledge using usernam and password or not.
    v. **test_login_with_invalid_credentials_admin_using_password**: Test that check if admin user is able to login into fledge or not using invalid credentials.
    vi. **test_login_with_user_certificate**: Test that check if regular user (not admin user) is able to login into fledge or not using certificates.
    vii. **test_login_with_admin_certificate**: Test that check if admin user is able to login into fledge or not using certificates.
    viii. **test_ping_with_allow_ping_false**: Test that check if `/fledge/ping` is giving response or not, when ping is not allowed by fledge and tried with regular user's credentials.
    ix. **test_login_with_custom_certificate**: Test that creates custom certificates for a regular user and verifies whether the user can log in to Fledge using those custom certificates.
    x. **test_ping_with_allow_ping_true**: Test that check if `/fledge/ping` is giving response or not, when ping is allowed by fledge.
    xi. **test_ingest_with_password_token**: Test that add south service of `http-south` plugin using password token and check if fledge is able to ingest data via fogbench into fledge or not.
    xii. **test_ingest_with_certificate_token**: Test that add south service of `http-south` plugin using certificate token and check if fledge is able to ingest data via fogbench into fledge or not.
    xiii. **test_ping_with_allow_ping_false_with_password_token**: Test that check if `/fledge/ping` is giving response or not, when ping is not allowed by fledge and tried with regular user's credentials.
    xiv. **test_ping_with_allow_ping_false_with_certificate_token**: Test that check if `/fledge/ping` is giving response or not, when ping is not allowed by fledge and tried with regular user's certificates.
    xv. **test_get_users_with_password_token**: Test that checks if differnt users (admin and regular users) are able to list the users of fledge or not, using password token.
    xvi. **test_get_users_with_certificate_token**: Test that checks if differnt users (admin and regular users) are able to list the users of fledge or not, using certificate token.
    xvii. **test_get_roles_with_certificate_token**: Test that checks if admin users is able to list the users of fledge or not, using certificate token.
    xviii. **test_create_user_with_password_token**: Test that checks if admin users is able to create users of fledge or not, using password token.
    xix. **test_create_user_with_certificate_token**: Test that checks if admin users is able to create users of fledge or not, using certificate token.
    xx. **test_login_of_newly_created_user**: Test that checks if newly created user are able to login into fledge or not using useername and password.
    xxi. **test_update_password_with_password_token**: Test that checks if fledge is allowing regular user to update it password using password token or not.
    xxii. **test_update_password_with_certificate_token**: Test that checks if fledge is allowing regular user to update it password using certificate token or not.
    xxiii. **test_login_with_updated_password**: Test that check if regular user is able to login into fledge using updated password.
    xxiv. **test_reset_user_with_password_token**: Test that checks if admin user is able to reset/update password  of regular user using password token or not.
    xxv. **test_reset_user_with_certificate_token**: Test that checks if admin user is able to reset/update password  of regular user using certificate token or not.
    xxvi. **test_login_with_resetted_password**: Test that check if regular user is able to login into fledge using the password reseted or updated by admin user.
    xxvii. **test_delete_user_with_password_token**: Test that check if admin is able to delete any speccifc user from fledge using the password token or not.
    xxviii. **test_delete_user_with_certificate_token**: Test that check if admin is able to delete any speccifc user from fledge using the certificate token or not.
    xxix. **test_login_of_deleted_user**: Test that check if the deleted user is able to login into fledge or not.
    xxx. **test_logout_all_with_password_token**: Test that check if admin is able to log out all the session of specifc user of fledge or not, using password token.
    xxxi. **test_verify_logout**: Test that check if specifc user is logged out or not.
    xxxii. **test_admin_actions_forbidden_for_regular_user_with_pwd_token**: Test that check if regular user is not able to perform any actions that only an admin can or not, using password token.
    xxxiii. **test_admin_actions_forbidden_for_regular_user_with_cert_token**: Test that check if regular user is not able to perform any actions that only an admin can or not, using certificate token.

7. **TestAuthPasswordWithTLS**:
    Following test case function check funcitonality of fledge, when tls is enabled and auth is mandatory with password authentication method:
    i. **test_login_username_regular_user**: Test that check if fledge is allowing login of regular user (not admin user) into fledge via username and password.
    ii. **test_logout_me**: Test that check if fledge is allowing logout of regular user (not admin user) from fledge via password token.
    iii. **test_login_with_invalid_credentials_regular_user**: Test that check if regular user is able to login into fledge using invalid credentials or not.
    iv. **test_login_username_admin**: Test that check if fledge is allowing admin user to login into fledge using usernam and password or not.
    v. **test_login_with_invalid_credentials_admin**: Test that check if admin user is able to login into fledge or not using invalid credentials.
    vi. **test_login_with_admin_certificate**: Test that check admin user should not able to login into fledge or not using certificates.
    vii. **test_ping_with_allow_ping_true**: Test that check if `/fledge/ping` is giving response or not, when ping is allowed by fledge.
    viii. **test_ingest**: Test that add south service of `http-south` plugin using password token and check if fledge is able to ingest data via fogbench into fledge or not.
    ix. **test_ping_with_allow_ping_false**: Test that check if `/fledge/ping` is giving response or not, when ping is not allowed by fledge and tried with regular user's credentials.
    x. **test_get_users**: Test that checks if differnt users (admin and regular users) are able to list the users of fledge or not, using password token.
    xi. **test_get_roles**: Test that checks if admin users is able to list the users of fledge or not, using password token.
    xii. **test_create_user**: Test that checks if admin users is able to create users of fledge or not, using password token.
    xiii. **test_login_of_newly_created_user**: Test that checks if newly created user are able to login into fledge or not using useername and password.
    xiv. **test_update_password**: Test that checks if fledge is allowing regular user to update it password using password token or not.
    xv. **test_login_with_updated_password**: Test that check if regular user is able to login into fledge using updated password.
    xvi. **test_reset_user**: Test that checks if admin user is able to reset/update password  of regular user using password token or not.
    xvii. **test_login_with_resetted_password**: Test that check if regular user is able to login into fledge using the password reseted or updated by admin user.
    xviii. **test_delete_user**: Test that check if admin is able to delete any speccifc user from fledge using the password token or not.
    xix. **test_login_of_deleted_user**: Test that check if the deleted user is able to login into fledge or not.
    xx. **test_logout_all**: Test that check if admin is able to log out all the session of specifc user of fledge or not, using password token.
    xxi. **test_verify_logout**: Test that check if specifc user is logged out or not.
    xxii. **test_admin_actions_forbidden_for_regular_user**: Test that check if regular user is not able to perform any actions that only an admin can or not, using password token.

8. **TestAuthCertificateWithTLS**:
    Following test case function check funcitonality of fledge, when tls is enabled and auth is mandatory with certificate authentication method only:
    i. **test_login_with_user_certificate**: Test that check if regular user (not admin user) is able to login into fledge or not using certificates.
    ii. **test_login_with_admin_certificate**: Test that check if admin user is able to login into fledge or not using certificates.
    iii. **test_login_with_custom_certificate**: Test that creates custom certificates for a regular user and verifies whether the user can log in to Fledge using those custom certificates.
    iv. **test_login_with_invalid_credentials**: Test that check if regular user is able to login into fledge using invalid certificate or not.
    v. **test_login_username_admin**: Test that check fledge should not allow admin user to login into fledge using usernam and password or not.
    vi. **test_ping_with_allow_ping_true**: Test that check if `/fledge/ping` is giving response or not, when ping is allowed by fledge.
    vii. **test_ingest**: Test that add south service of `http-south` plugin using certificate token and check if fledge is able to ingest data via fogbench into fledge or not.
    viii. **test_ping_with_allow_ping_false**: Test that check if `/fledge/ping` is giving response or not, when ping is not allowed by fledge and tried with admin user's certificates.
    ix. **test_get_users**: Test that checks if differnt users (admin and regular users) are able to list the users of fledge or not, using certificate token.
    x. **test_get_roles**: Test that checks if admin users is able to list the users of fledge or not, using certificate token.
    xi. **test_create_user**: Test that checks if admin users is able to create users of fledge or not, using certificate token.
    xii. **test_update_password**: Test that checks if fledge is allowing regular user to update it password using certificate token or not.
    xiii. **test_reset_user**: Test that checks if admin user is able to reset/update password  of regular user using certificate token or not.
    xiv. **test_delete_user**: Test that check if admin is able to delete any speccifc user from fledge using the certificate token or not.
    xv. **test_logout_all**: Test that check if admin is able to log out all the session of specifc user of fledge or not, using certificate token.
    xvi. **test_verify_logout**: Test that check if specifc user is logged out or not.
    xvii. **test_admin_actions_forbidden_for_regular_user**: Test that check if regular user is not able to perform any actions that only an admin can or not, using certificate token.


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
                        Generic wait time between processes to run
    --junit-xml=JUNIT_XML
                        Pytest XML report 

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python/
  $ python3 -m pytest -s -vv packages/test_authentication.py --package-build-version="PACKAGE_BUILD_VERSION" --wait-time="WAIT_TIME" --junit-xml="JUNIT_XML"