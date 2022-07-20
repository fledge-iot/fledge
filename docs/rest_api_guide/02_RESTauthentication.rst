..



***********************************
* REST API Users & Authentication *
***********************************

Fledge supports a number of different authentication schemes for use of the REST API

  - Unauthenticated or Optional authentication. There is no requirement for any authnetication to occur with the Fledge system to use the API. A user may authenticate if they desire, but it is not required.

  - Username/Password authentication. Authentication is required and the user chooses to authenticate usign a username and password.

  - Certificate based authentication. Authentication is required and the user presents a token issued using a certificate in order to authenticate.

Authentication API
==================

Login
-----

``POST /fledge/login`` - Create a login session token that can be used for future calls to the API


**Request Payload** 

The request payload is an authentication payload that must match one of the payloads that an authentication provider can interrupt. Note the payload does not explicitly state which provider should authenticate the request, it is the responsibility of the code to try each provider in turn until authentication is successful.

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

.. code-block:: console 

    {
      "message": "Logged in successfully",
      "uid": 1,
      "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1aWQiOjEsImV4cCI6MTY1ODIzOTIyMH0.ptpvvJtbPx9glG27SkJ3HNpvo0UWUchHe5VGk4S4eoU",
      "admin": true
    }

Subsequenct calls should carry an HTTP header with the authorization token given in this response.

.. code-block:: console

   curl -H "authorization: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1aWQiOjEsImV4cCI6MTY1ODIzOTIyMH0.ptpvvJtbPx9glG27SkJ3HNpvo0UWUchHe5VGk4S4eoU" http://localhost:8081/fledge/ping

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

``PUT /fledge/{user_id}/logout`` - Terminate the login session for another user.

The administrator may terminate the login session of another user.

.. code-block:: console

   curl -H "authorization: <token>" -X PUT http://localhost:8081/fledge/{user_id}/logout

Users
=====

Fledge supports two levels of user, administration users and normal users. A set of API calls exsits to allow users to be created, queried, modified and destroyed. 

Add User
--------

``POST /fledge/user`` - add a new user to Fledge’s user database

**Request Payload**

A JSON document which describes the user to add.

.. list-table::
    :widths: 20 20 50 30
    :header-rows: 1

    * - Name
      - Type
      - Description
      - Example
    * - username
      - string
      - The username of the new user to add
      - david
    * - password
      - string
      - The password to assign to the new user. If not given then a certificate must be included in the payload.
      - 1nv1nc1ble
    * - certificate
      - string
      - The name of a certificate in the certificate store. May only be used when a password is not given.
      -
    * - permissions
      - string
      - The permissions that new user should be given
      - admin
    * - realname
      - string
      - The real name of the user. This is used for display purposes only.
      - David Brent

**Response Payload**

The response payload is a JSON document containing the username of the newly created user.

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

   curl -X POST /fledge/user -d'
   {
    "username"    : "david",
    "password"    : "1nv1nc1ble",
    "permissions" : "admin",
    "realname"    : "David Brent"
   }

Get All Users
-------------

``GET /fledge/user`` - Retrieve data on all users

**Response Payload**

A JSON document which all users in a JSON array.

.. list-table::
    :widths: 20 20 50 30
    :header-rows: 1

    * - Name
      - Type
      - Description
      - Example
    * - [].username
      - string
      - The username of the new user to add
      - david
    * - [].permissions
      - string
      - The permissions that new user should be given
      - admin
    * - [].realname
      - string
      - The real name of the user. This is used for display purposes only.
      - David Brent

.. note::

   This payload does not include the password of the user.

**Example**

.. code-block:: console

   curl -X GET /fledge/user


Returns the response payload

.. code-block:: console
    {
        "users" : [
                    {
                       "username"    : "david",
                       "permissions" : "admin",
                       "realname"    : "David Brent"
                    },
                    {
                       "username"    : "paul",
                       "permissions" : "user",
                       "realname"    : "Paul Smith"
                    }
                  ]
    }



Get User
--------

``GET /fledge/user/{username}`` - Retrieve data on a user

**Response Payload**

A JSON document which describes the user.

.. list-table::
    :widths: 20 50
    :header-rows: 1

    * - Name
      - Type
      - Description
      - Example
    * - username
      - string
      - The username of the new user to add
      - david
    * - permissions
      - string
      - The permissions that new user should be given
      - admin
    * - realname
      - string
      - The real name of the user. This is used for display purposes only.
      - David Brent


..note::

    This payload does not include the password of the user.

**Example**

.. code-block:: console

  GET /fledge/user/david**

Returns the response payload

.. code-block:: console

    {
        "username"    : "david",
        "permissions" : "admin",
        "realname"    : "David Brent"
    }

Update User
-----------

``PUT /fledge/user/{username}`` - update a user

**Request Payload**

A JSON document which describes the updates to the user record.

.. list-table::
    :widths: 20 20 50 30
    :header-rows: 1

    * - Name
      - Type
      - Description
      - Example
    * - username
      - string
      - The username of the new user to add
      - david
    * - password
      - string
      - The password to assign to the new user
      - 1nv1nc1ble
    * - permissions
      - string
      - The permissions that new user should be given
      - admin
    * - realname
      - string
      - The real name of the user. This is used for display purposes only.
      - David Brent


.. note::

    The inclusion of username in the payload allows for usernames to be changed.

**Response Payload**

The response payload is a JSON document containing the username of the newly created user.

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

   curl -X PUT /foglamp/user/david -d'
    {
        "username"    : "dave",
        "password"    : "1nv1nc1ble",
        "permissions" : "admin",
        "realname"    : "Dave Brent"
    }'

Delete User
-----------

``DELETE /foglamp/user/{username}`` - delete a user

.. note::

    It is not possible to remove the user that is currently logged in to the system.

**Example**

.. code-block:: console 

	DELETE /foglamp/user/paul

