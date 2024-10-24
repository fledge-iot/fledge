*******************************
REST API Users & Authentication
*******************************

Fledge supports a number of different authentication schemes for use of the REST API

  - Unauthenticated or Optional authentication. There is no requirement for any authentication to occur with the Fledge system to use the API. A user may authenticate if they desire, but it is not required.

  - Username/Password authentication. Authentication is required and the user chooses to authenticate using a username and password.

  - Certificate based authentication. Authentication is required and the user presents a token issued using a certificate in order to authenticate.

Authentication API
==================

Login
-----

``POST /fledge/login`` - Create a login session token that can be used for future calls to the API


**Request Payload** 

If the user is connecting with a user name and a password then a JSON structure should be passed as the payload providing the following key/value pairs.

.. list-table::
    :widths: 20 20 50 30
    :header-rows: 1

    * - Key Name
      - Type
      - Description
      - Example
    * - username
      - string
      - The username of the user attempting to login
      - admin
    * - password
      - string
      - The plain text password of the user attempting to login
      - fledge

**Response Payload**

The response payload is an authentication token that should be included in all future calls to the API. This token will be included in the header of the subsequent requests as the value of the property authorization.

**Example**

Assuming the authentication provider is a username and password provider.

.. code-block:: console

    curl -X POST http://localhost:8081/fledge/login -d'
    {
      "username" : "admin",
      "password" : "fledge"
    }'

Would return an authentication token

.. code-block:: json 

    {
      "message": "Logged in successfully",
      "uid": 1,
      "token": "********************",
      "admin": true
    }

Subsequent calls should carry an HTTP header with the authorization token given in this response.

.. code-block:: console

   curl -H "authorization: <token>" http://localhost:8081/fledge/ping

Alternatively a certificate based authentication can be used with the user presenting a certificate instead of the JSON payload shown above to the ``/fledge/login`` endpoint.

.. code-block:: console

   curl -T user.cert -X POST http://localhost:8081/fledge/login --insecure

The payload returned is the same as for username and password based authentication.

.. note::

   The examples above have been shown using HTTP as the transport, however if authentication is in use then it would normally be expected to use HTTPS to encrypt the communication.

Logout
------

``PUT /fledge/logout`` - Terminate the current login session and invalidate the authentication token

Ends to login session for the current user and invalidates the token given in the header.

``PUT /fledge/{user_id}/logout`` - Terminate the login session for user's all active sessions.

The administrator may terminate the login session of another user.

.. code-block:: console

   curl -H "authorization: <token>" -X PUT http://localhost:8081/fledge/{user_id}/logout

Users
=====

Fledge supports two levels of user, administration users and normal users. A set of API calls exists to allow users to be created, queried, modified and destroyed. 

Add User
--------

``POST /fledge/admin/user`` - add a new user to Fledge’s user database

.. note::

   Only admin users are able to create other users.


**Request Payload**

A JSON document which describes the user to add.

.. list-table::
    :widths: 20 20 50 30
    :header-rows: 1

    * - Key Name
      - Type
      - Description
      - Example
    * - username
      - string
      - The username of the new user to add. It is a required field.
      - david
    * - password
      - string
      - The password to assign to the new user. It is a required field.
      - Inv1nc!ble
    * - access_method
      - string
      - Access of a user. It is an optional field.
      - Possible values are cert, any, cert.
    * - real_name
      - string
      - The real name of the user. This is used for display purposes only. It is an optional field.
      - David Brent
    * - role_id
      - integer
      - The role id of the new user. It is an optional field.
      - 1 for Admin user and 2 for normal user. If not given it will be treated as normal user.
    * - description
      - string
      - Description of the user. It is an optional field.
      - 1 for Admin and 2 for normal user. If not given it will be treated as normal user.


**Response Payload**

The response payload is a JSON document containing the full details of the newly created user.

**Errors**

The following error responses may be returned

.. list-table::
    :widths: 20 50
    :header-rows: 1

    * - HTTP Code
      - Reason
    * - 400
      - Incomplete or badly formed request payload
    * - 403
      - A user without admin permissions tried to add a new user
    * - 409
      - The username is already in use


**Example**

.. code-block:: console

    curl -H "authorization: <token>" -X POST -d '{"username": "david", "password": "Inv1nc!ble", "role_id": 1, "real_name": "David Brent"}' http://localhost:8081/fledge/admin/user


Get All Users
-------------

``GET /fledge/user`` - Retrieve data on all users

**Response Payload**

A JSON document which all users in a JSON array.

.. list-table::
    :widths: 20 20 50 30
    :header-rows: 1

    * - JSON Key
      - Type
      - Description
      - Example
    * - .users[].userName
      - string
      - The username of the user
      - david
    * - .users[].roleId
      - integer
      - The permissions level of the user
      - 1
    * - .users[].realName
      - string
      - The real name of the user. This is used for display purposes only.
      - David Brent
    * - .users[].description
      - string
      - The description of the user.
      - This is an admin user.

.. note::

   This payload does not include the password of the user.

**Example**

.. code-block:: console

   curl -H "authorization: <token>" -X GET http://localhost:8081/fledge/user


Returns the response payload

.. code-block:: json

    {
        "users" : [
                    {
                       "userId"       : 1,
                       "userName"     : "admin",
                       "roleId"       : 1,
                       "accessMethod" : "any",
                       "realName"     : "Admin user",
                       "description"  : "admin user"
                    },
                    {
                       "userId"       : 2,
                       "userName"     : "david",
                       "realName"     : "David Brent",
                       "accessMethod" : "any",
                       "roleId"       : 1,
                       "description"  : "OT Department Head"
                    },
                    {
                       "userId"       : 3,
                       "userName"     : "paul",
                       "realName"     : "Paul Smith"
                       "roleId"       : 2,
                       "accessMethod" : "any",
                       "description"  : "OT Supervisor"
                    }
                  ]
    }

Update User
-----------

``PUT /fledge/user`` - Allows a user to update their own user information

**Request Payload**

A JSON document which describes the updates to the user record.

.. list-table::
    :widths: 20 20 50 30
    :header-rows: 1

    * - Key Name
      - string
      - description
      - Example
    * - real_name
      - string
      - The real name of the user. This is used for display purposes only.
      - David Brent


.. note::

    A user can only update their own real name, other information must be updated by an admin user.

**Response Payload**

The response payload is a JSON document containing a message as to the success of the operation.

**Errors**

The following error responses may be returned

.. list-table::
    :widths: 20 50 
    :header-rows: 1

    * - HTTP Code
      - Reason
    * - 400
      - Incomplete or badly formed request payload

**Example**

.. code-block:: console

   curl -H "authorization: <token>" -X PUT /fledge/user -d '{"real_name": "Dave Brent"}'

Change Password
---------------

``PUT /fledge/user/{userid}/password`` - change the password for the current user

**Request Payload**

A JSON document that contains the old and new passwords.

.. list-table::
    :widths: 20 20 50 30
    :header-rows: 1

    * - Key Name
      - string
      - description
      - Example
    * - current_password
      - string
      - The current password of the user
      - Inv1nc!ble
    * - new_password
      - string
      - The new password of the user
      - F0gl!mp1

**Response Payload**

A message as to the success of the operation

**Example**

.. code-block:: console

    curl -X PUT -d '{"current_password": "Inv1nc!ble", "new_password": "F0gl!mp1"}' http://localhost:8081/fledge/user/{user_id}/password

Admin Update User
-----------------

``PUT /fledge/admin/user`` - An admin user can update any user's information

**Request Payload**

A JSON document which describes the updates to the user record.

.. list-table::
    :widths: 20 20 50 30
    :header-rows: 1

    * - Name
      - Type
      - Description
      - Example
    * - description
      - string
      - The description of a user
      - david
    * - access_method
      - string
      - The permissions that new user should be given
      - Possible values are cert, any, cert.
    * - real_name
      - string
      - The real name of the user. This is used for display purposes only.
      - David Brent

**Response Payload**

The response payload is a JSON document containing the user information.

**Errors**

The following error responses may be returned

.. list-table::
    :widths: 20 50 
    :header-rows: 1

    * - HTTP Code
      - Reason
    * - 400
      - Incomplete or badly formed request payload
    * - 403
      - A user without admin permissions tried to add a new user
    * - 409
      - The username is already in use

**Example**

.. code-block:: console

   curl -H "authorization: <token>" -X PUT -d '{"description": "OT Department Head", "real_name": "David Brent", "access_method": "pwd"}' http://localhost:8081/fledge/admin/{user_id}

Delete User
-----------

``DELETE /fledge/admin/user/{userID}/delete`` - delete a user


The delete user call can only be made by users with administrator privileges. If a user that is currently logged in is removed then that user will be forcibly logged out of the system.

.. note::

   The user with the user name admin can not be removed from the system.

**Example**

.. code-block:: console 

	curl -H "authorization: <token>" -X DELETE  http://localhost:8081/fledge/admin/{user_id}/delete
