Admin API
=========

Introduction
------------
This code originated from `JWT AUTHORIZATION IN PYTHON, PART 1 <http://steelkiwi.com/blog/jwt-authorization-python-part-1-practise>`_


Starting the server
-------------------
The foglamp start script starts the server on port 8080. There is currently no https option.

Authentication
--------------
POSTing to auth/login accepts user credentials and responds with a JSON document containing 'access' and 'refresh' tokens.

An access token must be provided in the 'authorization' header for all other requests except auth/refresh-token.

Access tokens expire after 15 minutes. Refresh tokens are valid for up to 7 days.

When a token has expired, requests fail with status code 401. When a token has not been provided or if the token is invalid, requests fail with status code 400.

auth/login is an expensive operation. POSTing to auth/refresh-token is faster and also responds with a JSON document containing access_token (but no refresh_token). The refresh token must be provided in the 'authorization' header.

Base URI
--------
/api

Methods
-------

POST auth/login
^^^^^^^^^^^^^^^

  - There is currently only one user named 'user' with password 'password.'
  - Request:
  - .. code-block:: python

      {
        "username": "user",
        "password": "password"
      }

  - Response:
  - .. code-block:: python

      {
        "access_token": "33fece..",
        "refresh_token": "93adfd.."
      }

POST auth/refresh-token
^^^^^^^^^^^^^^^^^^^^^^^

  - Provide a refresh token in the 'authorization' header
  - Response:
  - .. code-block:: python

      {
        "access_token": "33fece..",
      }

GET example/whoami
^^^^^^^^^^^^^^^^^^

  - This is an example method that returns details about the currently logged in user
  - Provide an access token in the 'authorization' header
  - Response:
  - .. code-block:: python

      {
        "username" : "user"
      }

Usage Example
-------------

.. code-block:: bash

    foglamp$ curl -X POST -d '{"username":"user", "password": "password"}' \
    localhost:8080/api/auth/login

    {"refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJhY2Nlc3MiOjAsImV4cCI6MTQ5NzQ5OTI1NH0.WXgSegU4AZtucLh1HbbEZmufCAE81ntR-XLOKEYPzE8", 
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJhY2Nlc3MiOjEsImV4cCI6MTQ5NjkyMDU1NC4xMDM1OTF9.HlFo1ABpmSLmJocUFjQyH0Y8v4z-3kujvbmC77RZMkg"}

    foglamp$ curl -H authorization:eyJhbGciOiJIUzI1NiIsInRY5MTgxNTkuNDc4NzQ1LCJhY2Nlc3MiOjEsInVzZXJfaWQiOjF9.c3zS_EXm1YXsgPMxkyO3sIgDmDWOsx8tZYV512XlV7I \
    localhost:8080/api/example/whoami

    {"username": "user"}

    foglamp$ curl -X POST -H authorization:eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJhY2Nlc3MiOjAsImV4cCI6MTQ5NzQ5OTI1NH0.WXgSegU4AZtucLh1HbbEZmufCAE81ntR-XLOKEYPzE8 \
    localhost:8080/api/auth/refresh-token

    {"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE0OTY5MjA3NTguMjAwNjIxLCJ1c2VyX2lkIjoxLCJhY2Nlc3MiOjF9.cgv348fsNjqYrocmPvJbCgUIqJWoJGaUpVaBIxREJPc"}
