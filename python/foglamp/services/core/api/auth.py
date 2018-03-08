# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" auth routes """
from datetime import datetime, timedelta

from aiohttp import web
import jwt

from foglamp.services.core.user_model import User

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_help = """
    ------------------------------------------------------------------------------------
    | GET             | /foglamp/user                                                  |
    | POST            | /foglamp/login                                                 |
    | PUT             | /foglamp/logout                                                |
    ------------------------------------------------------------------------------------
"""

# do it via init.sql
#User.objects.create_admin()

# move to common  / config
JWT_SECRET = 'f0gl@mp'
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 30*60  # 30 minutes


async def login(request):
    """

    :param request:
    :return:

    curl -X POST -d '{"username": "admin", "password": "foglamp"}' http://localhost:8081/foglamp/login
    """

    req = await request.json()

    try:
        user = User.objects.get(username=req.get("username"))
        user.match_password(req.get("password"))

    except (User.DoesNotExist, User.PasswordDoesNotMatch):
        return web.HTTPBadRequest()

    payload = {
        'uid': user.uid,
        'exp': datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
    }
    jwt_token = jwt.encode(payload, JWT_SECRET, JWT_ALGORITHM)

    # save this token, login time, expiration in DB
    return web.json_response({'token': jwt_token.decode('utf-8')})


async def logout(request):
    """

    :param request:
    :return:

        curl -H "authorization: <token>" -X PUT http://localhost:8081/foglamp/logout

    """
    # invalidate token in DB
    return web.json_response({"logout": True})


async def get_user(request):
    """

    :param request:
    :return:

    curl -H "authorization: <token>" -X GET http://localhost:8081/foglamp/user?id=x
    """
    # if id, return single user
    # else all
    users = User.objects.all()

    temp = [str(u) for u in users]

    return web.json_response({'users': temp})
