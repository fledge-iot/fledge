# Introduction

This REST server is implemented with aiohttp. A stand-alone aiohttp server doesn't utilize all cores. There are several options as described here: http://aiohttp.readthedocs.io/en/stable/deployment.html

Gunicorn (Green Unicorn) was chosen.

# Run the server

gunicorn rest:app --bind localhost:8080 --worker-class aiohttp.worker.GunicornWebWorker --reload

# Authentication

A token is acquired by posting to /login a JSON
document with the following:

```
{
    user: 
    password: 
}
```

The provided token must be provided in all other requests via the 'authorization' header.

Tokens expire after ??? minutes of non-use.
