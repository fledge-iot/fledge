# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" auth routes """
from datetime import datetime, timedelta
from collections import OrderedDict

from aiohttp import web
import jwt

from foglamp.services.core.user_model import User

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_help = """
    ------------------------------------------------------------------------------------
    | GET  POST PUT DELETE       | /foglamp/user                                       |
    | POST                       | /foglamp/login                                      |
    | PUT                        | /foglamp/logout                                     |
    ------------------------------------------------------------------------------------
"""

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
    """ get user info

    :Example:
            curl -H "authorization: <token>" -X GET http://localhost:8081/foglamp/user?id=x
            curl -H "authorization: <token>" -X GET http://localhost:8081/foglamp/user?uname=admin
            curl -H "authorization: <token>" -X GET "http://localhost:8081/foglamp/user?id=1&uname=admin"
    """
    user_id = None
    user_name = None

    if 'id' in request.query and request.query['id'] != '':
        try:
            user_id = int(request.query['id'])
            if user_id <= 0:
                raise ValueError
        except ValueError:
            raise web.HTTPBadRequest(reason="Bad user id")

    if 'uname' in request.query and request.query['uname'] != '':
        user_name = request.query['uname']

    if user_id or user_name:
        try:
            user = User.objects.get(user_id, user_name)
            user['userId'] = user.pop('id')
            user['userName'] = user.pop('uname')
            user['roleId'] = user.pop('role_id')
            result = user
        except User.DoesNotExist as ex:
            raise web.HTTPNotFound(reason=str(ex))
    else:
        users = User.objects.all()
        res = []
        for row in users:
            u = OrderedDict()
            u["userId"] = row["id"]
            u["userName"] = row["uname"]
            u["roleId"] = row["role_id"]
            res.append(u)
        result = {'users': res}

    return web.json_response(result)
