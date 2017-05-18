#!/usr/bin/env python3.5

from subprocess import call

call(["pip3", "install"
    , "aiocoap"
    , "aiopg"
    , "cbor2"
    , "sqlalchemy"
    , "linkheader" # Needed by aiocoap
    , "python-daemon"
    ])
