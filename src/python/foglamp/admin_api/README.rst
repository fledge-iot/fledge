# Introduction

This code originated from work described at http://steelkiwi.com/blog/jwt-authorization-python-part-1-practise/

# Running the server 

./build.sh -r

# Authentication

Posting to /api/auth/login with query strings user= and password= returns a token.

The token should be provided in the 'authorization' header for all other API calls. 

The token expires after 15 minutes. Post to /api/auth/refresh_token to reset the expiration time. The token can be refreshed only for up to 7 days.

# Methods

## whoami

This is an example method that returns details about the currently logged in user

# Usage Example

 bash-3.2$ curl -X POST localhost:8080/api/auth/login user=username password=password

    HTTP/1.1 200 OK
    Content-Length: 177
    Content-Type: text/json
    Date: Mon, 22 May 2017 05:23:33 GMT
    Server: Python/3.6 aiohttp/2.0.7

    {
        "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE0OTYwMzU1MjYsInJlZnJlc2hfZXhwIjoxNDk1NDU2ODI2LjMwMTE5M30.LRDw1wnfoDluSMBfghUJB2e4Iy8jSlLkQmIlKMet9mo"
    }

 bash-3.2$ curl localhost:8080/api/auth/whoami --header authorization:eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE0OTYwMzU1MjYsInJlZnJlc2hfZXhwIjoxNDk1NDU2ODI2LjMwMTE5M30.LRDw1wnfoDluSMBfghUJB2e4Iy8jSlLkQmIlKMet9mo

    HTTP/1.1 200 OK
    Content-Length: 49
    Content-Type: text/json
    Date: Mon, 22 May 2017 05:23:45 GMT
    Server: Python/3.6 aiohttp/2.0.7

    {
        "user": "User id=1: <username, is_admin=False>"
    }

    bash-3.2$ curl -X POST localhost:8080/api/auth/refresh-token --header authorization:eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE0OTYwMzU1MjYsInJlZnJlc2hfZXhwIjoxNDk1NDU2ODI2LjMwMTE5M30.LRDw1wnfoDluSMBfghUJB2e4Iy8jSlLkQmIlKMet9mo

    HTTP/1.1 200 OK
    Content-Length: 177
    Content-Type: text/json
    Date: Mon, 22 May 2017 05:24:05 GMT
    Server: Python/3.6 aiohttp/2.0.7

    {
        "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE0OTYwMzU1MjYsInJlZnJlc2hfZXhwIjoxNDk1NDU2ODkwLjkzMDMyM30.V4Eye1eCzZXiGmLzvZ5vRvXMWd9xVS9tneY52YTeFo4"
    }

