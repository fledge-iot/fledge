# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" auth routes """

import re
from collections import OrderedDict

from aiohttp import web
from foglamp.services.core.user_model import User

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_help = """
    ------------------------------------------------------------------------------------
    | GET  POST PUT              | /foglamp/user                                       |
    | DELETE                     | /foglamp/user/{id}                                  |
    
    | POST                       | /foglamp/login                                      |
    | PUT                        | /foglamp/logout                                     |
    ------------------------------------------------------------------------------------
"""

# move to common  / config
JWT_SECRET = 'f0gl@mp'
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 30*60  # 30 minutes

PASSWORD_REGEX_PATTERN = '((?=.*\d)(?=.*[A-Z])(?=.*\W).{6,}$)'


async def login(request):
    """ Validate user with its username and password

    :Example:
            curl -X POST -d '{"username": "user", "password": "User@123"}' http://localhost:8081/foglamp/login
    """

    data = await request.json()

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        raise web.HTTPBadRequest(reason="Username or password is missing")

    try:
        token, is_admin = User.Objects.login(username, password)
    except (User.DoesNotExist, User.PasswordDoesNotMatch) as ex:
        return web.HTTPBadRequest(reason=str(ex))
    except ValueError as exc:
        return web.HTTPBadRequest(reason=str(exc))

    return web.json_response({"message": "Logged in successfully", "token": token, "admin": is_admin})


async def logout(request):
    """

    :param request:
    :return:

        curl -H "authorization: <token>" -X PUT http://localhost:8081/foglamp/logout

    """
    # TODO: request.user is only available when auth is mandatory
    # or we can have uid in request as query param in optional case
    # e.g. curl PUT http://localhost:8081/foglamp/<user_id>/logout

    logged_in_user = request.user
    print(logged_in_user)

    if logged_in_user:
        result = User.Objects.logout(logged_in_user["id"])
        if not result['rows_affected']:
            raise web.HTTPBadRequest()

    return web.json_response({"logout": True})


async def get_roles(request):
    """ get roles

       :Example:
            curl -X GET http://localhost:8081/foglamp/user/role
    """
    result = User.Objects.get_roles()
    return web.json_response({'roles': result})


async def get_user(request):
    """ get user info

    :Example:
            curl -H "authorization: <token>" -X GET http://localhost:8081/foglamp/user
            curl -H "authorization: <token>" -X GET http://localhost:8081/foglamp/user?id=2
            curl -H "authorization: <token>" -X GET http://localhost:8081/foglamp/user?username=admin
            curl -H "authorization: <token>" -X GET "http://localhost:8081/foglamp/user?id=1&username=admin"
    """
    user_id = None
    user_name = None

    if 'id' in request.query:
        try:
            user_id = int(request.query['id'])
            if user_id <= 0:
                raise ValueError
        except ValueError:
            raise web.HTTPBadRequest(reason="Bad user id")

    if 'username' in request.query and request.query['username'] != '':
        user_name = request.query['username']

    if user_id or user_name:
        try:
            user = User.Objects.get(user_id, user_name)
            u = OrderedDict()
            u['userId'] = user.pop('id')
            u['userName'] = user.pop('uname')
            u['roleId'] = user.pop('role_id')
            result = u
        except User.DoesNotExist as ex:
            raise web.HTTPNotFound(reason=str(ex))
    else:
        users = User.Objects.all()
        res = []
        for row in users:
            u = OrderedDict()
            u["userId"] = row["id"]
            u["userName"] = row["uname"]
            u["roleId"] = row["role_id"]
            res.append(u)
        result = {'users': res}

    return web.json_response(result)


async def create_user(request):
    """ create user

    :Example:
        curl -X POST -d '{"username": "admin", "password": "F0gl@mp!"}' http://localhost:8081/foglamp/user
        curl -X POST -d '{"username": "ajadmin", "password": "User@123", "role": 1}' http://localhost:8081/foglamp/user
    """
    data = await request.json()

    username = data.get('username')
    password = data.get('password')
    role_id = data.get('role', 2)

    if not username or not password:
        raise web.HTTPBadRequest(reason="Username or password is missing")

    # TODO:
    # 1) username regex? is email allowed?
    if not re.match(PASSWORD_REGEX_PATTERN, password):
        raise web.HTTPBadRequest(reason="Password must contain at least one digit, "
                                        "one lowercase, one uppercase & one special character and "
                                        "length of minimum 6 characters")

    if not is_valid_role(role_id):
        return web.HTTPBadRequest(reason="Invalid or bad role id")

    try:
        User.Objects.get(username=username)
    except User.DoesNotExist:
        pass
    else:
        raise web.HTTPConflict(reason="User with the requested username already exists")

    u = dict()
    try:
        is_admin = True if int(role_id) == 1 else False
        result = User.Objects.create(username, password, is_admin)
        if result['rows_affected']:
            # FIXME: we should not do get again!
            # we just need inserted user id; insert call should return that
            user = User.Objects.get(username=username)
            u['userId'] = user.pop('id')
            u['userName'] = user.pop('uname')
            u['roleId'] = user.pop('role_id')
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except Exception as exc:
        raise web.HTTPInternalServerError(reason=str(exc))

    return web.json_response({'message': 'User has been created successfully', 'user': u})


async def update_user(request):
    data = await request.json()

    # we don't have any profile yet, let's allow to update role or password only

    role_id = data.get('role')
    if not is_valid_role(role_id):
        return web.HTTPBadRequest(reason="Invalid or bad role id")

    password = data.get('password')
    if not re.match(PASSWORD_REGEX_PATTERN, password):
        raise web.HTTPBadRequest(reason="Password must contain at least one digit, "
                                        "one lowercase, one uppercase & one special character and "
                                        "length of minimum 6 characters")

    logged_in_user = request.user
    print(logged_in_user)

    updated_user = logged_in_user
    updated_user["role_id"] = int(role_id)
    updated_user["password"] = User.Objects.hash_password(password)

    User.Objects.update(user_id=logged_in_user["id"], user=updated_user)

    u = dict()
    u['userId'] = updated_user.pop('id')
    u['userName'] = updated_user.pop('uname')
    u['roleId'] = updated_user('role_id')

    return web.json_response({'message': 'User has been updated successfully', 'user': u})


async def delete_user(request):
    """ Delete a user from users table

    :Example:
            curl -X DELETE  http://localhost:8081/foglamp/user/1
    """

    # TODO: soft delete?
    try:
        # Requester should not be able to delete her/himself
        # Requester should have role admin
        # raise web.HTTPUnauthorized(reason="Only admin can delete the user")

        user_id = request.match_info.get('id')
        result = User.Objects.delete(user_id)
        if not result['rows_affected']:
            raise User.DoesNotExist

    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except User.DoesNotExist:
        raise web.HTTPNotFound(reason="User with id:<{}> does not exist".format(user_id))
    except Exception as exc:
        raise web.HTTPInternalServerError(reason=str(exc))

    return web.json_response({'message': "User has been deleted successfully"})


def is_valid_role(role_id):
    roles = [int(r["id"]) for r in User.Objects.get_roles()]
    try:
        role = int(role_id)
        if role not in roles:
            raise ValueError
    except ValueError:
        return False
    return True
