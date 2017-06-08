Introduction
------------
This code originated from work described at http://steelkiwi.com/blog/jwt-authorization-python-part-1-practise/

Starting the server
-------------------
The foglamp start script starts the server on port 8080. There is currently no https option.

Authentication
--------------
POST to /api/auth/login with username: and password: in JSON format.

A JSON document is returned with two keys, refresh_token and access_token.

The access token should be provided in the 'authorization' header for all API calls except /api/auth/refresh_token. It expires after 15 minutes.

POST the refresh token to /api/auth/refresh_token to get a new access token. The refresh token expires after 7 days.

Methods
-------
- whoami

  - This is an example method that returns details about the currently logged in user

Usage Example
-------------
.. code-block::

    foglamp$ curl -X POST -d '{"username":"user", "password": "password"}' localhost:8080/api/auth/login
    {"refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJhY2Nlc3MiOjAsImV4cCI6MTQ5NzQ5OTI1NH0.WXgSegU4AZtucLh1HbbEZmufCAE81ntR-XLOKEYPzE8", 
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJhY2Nlc3MiOjEsImV4cCI6MTQ5NjkyMDU1NC4xMDM1OTF9.HlFo1ABpmSLmJocUFjQyH0Y8v4z-3kujvbmC77RZMkg"}

    foglamp$ curl -X GET -H authorization:eyJhbGciOiJIUzI1NiIsInRY5MTgxNTkuNDc4NzQ1LCJhY2Nlc3MiOjEsInVzZXJfaWQiOjF9.c3zS_EXm1YXsgPMxkyO3sIgDmDWOsx8tZYV512XlV7I localhost:8080/api/example/whoami
    {"username": "user"}

    foglamp$ curl -X POST -H authorization:eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJhY2Nlc3MiOjAsImV4cCI6MTQ5NzQ5OTI1NH0.WXgSegU4AZtucLh1HbbEZmufCAE81ntR-XLOKEYPzE8 localhost:8080/api/auth/refresh-token
    {"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE0OTY5MjA3NTguMjAwNjIxLCJ1c2VyX2lkIjoxLCJhY2Nlc3MiOjF9.cgv348fsNjqYrocmPvJbCgUIqJWoJGaUpVaBIxREJPc"}
