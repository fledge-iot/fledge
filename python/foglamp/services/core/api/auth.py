# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" auth routes """

import re
from collections import OrderedDict

from aiohttp import web
from foglamp.services.core.user_model import User
from foglamp.common.web.middleware import has_permission

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_help = """
    ------------------------------------------------------------------------------------
    | GET POST                   | /foglamp/user                                       |
    | PUT DELETE                 | /foglamp/user/{id}                                  |

    | GET                        | /foglamp/user/role                                  |
    
    | POST                       | /foglamp/login                                      |
    | PUT                        | /foglamp/{user_id}/logout                                |
    ------------------------------------------------------------------------------------
"""

JWT_SECRET = 'f0gl@mp'
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 30*60  # 30 minutes

PASSWORD_REGEX_PATTERN = '((?=.*\d)(?=.*[A-Z])(?=.*\W).{6,}$)'
PASSWORD_ERROR_MSG = 'Password must contain at least one digit, one lowercase, one uppercase & one special character ' \
                     'and length of minimum 6 characters'

# TODO: remove me, use from roles table
ADMIN_ROLE_ID = 1
DEFAULT_ROLE_ID = 2


async def login(request):
    """ Validate user with its username and password

    :Example:
        curl -X POST -d '{"username": "user", "password": "foglamp"}' http://localhost:8081/foglamp/login
    """

    data = await request.json()

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        raise web.HTTPBadRequest(reason="Username or password is missing")

    peername = request.transport.get_extra_info('peername')
    host = '0.0.0.0'
    if peername is not None:
        host, port = peername
    try:
        uid, token, is_admin = User.Objects.login(username, password, host)
    except (User.DoesNotExist, User.PasswordDoesNotMatch, ValueError) as ex:
        return web.HTTPBadRequest(reason=str(ex))

    return web.json_response({"message": "Logged in successfully", "uid": uid, "token": token, "admin": is_admin})


async def logout(request):
    """ log out user

    :Example:
        curl -H "authorization: <token>" -X PUT http://localhost:8081/foglamp/{user_id}/logout

    """

    user_id = request.match_info.get('user_id')

    check_authorization(request, user_id, "logout")

    # TODO: logout should be token based only; to allow multiple device session
    result = User.Objects.logout(user_id)

    if not result['rows_affected']:
        raise web.HTTPNotFound()

    return web.json_response({"logout": True})


async def get_roles(request):
    """ get roles

    :Example:
        curl -H "authorization: <token>" -X GET http://localhost:8081/foglamp/user/role
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
        user_name = request.query['username'].lower()

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


@has_permission("admin")
async def create_user(request):
    """ create user

    :Example:
        curl -H "authorization: <token>" -X POST -d '{"username": "any", "password": "User@123"}' http://localhost:8081/foglamp/user
        curl -H "authorization: <token>" -X POST -d '{"username": "admin1", "password": "F0gl@mp!", "role_id": 1}' http://localhost:8081/foglamp/user
    """
    data = await request.json()

    username = data.get('username')
    password = data.get('password')
    role_id = data.get('role_id', DEFAULT_ROLE_ID)

    if not username or not password:
        raise web.HTTPBadRequest(reason="Username or password is missing")

    if not isinstance(password, str):
        raise web.HTTPBadRequest(reason=PASSWORD_ERROR_MSG)

    # TODO: username regex? is email allowed?
    if not re.match(PASSWORD_REGEX_PATTERN, password):
        raise web.HTTPBadRequest(reason=PASSWORD_ERROR_MSG)

    if not is_valid_role(role_id):
        return web.HTTPBadRequest(reason="Invalid or bad role id")

    username = username.lower()
    try:
        User.Objects.get(username=username)
    except User.DoesNotExist:
        pass
    else:
        raise web.HTTPConflict(reason="User with the requested username already exists")

    u = dict()
    try:
        result = User.Objects.create(username, password, role_id)
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
    """ update user

    :Example:
        curl -H "authorization: <token>" -X PUT -d '{"role_id": "1"}' http://localhost:8081/foglamp/user/<id>
        curl -H "authorization: <token>" -X PUT -d '{"password": "F0gl@mp!"}' http://localhost:8081/foglamp/user/<id>
        curl -H "authorization: <token>" -X PUT -d '{"role_id": 1, "password": "F0gl@mp!"}' http://localhost:8081/foglamp/user/<id>
    """

    # we don't have any user profile info yet, let's allow to update role or password only
    user_id = request.match_info.get('id')

    data = await request.json()
    role_id = data.get('role_id')
    password = data.get('password')

    if not role_id and not password:
        raise web.HTTPBadRequest(reason="Nothing to update the user")

    if role_id and not is_valid_role(role_id):
        raise web.HTTPBadRequest(reason="Invalid or bad role id")
    if role_id and not has_admin_permissions(request):
        raise web.HTTPUnauthorized(reason="only admin can update the role for a user")

    if password and not isinstance(password, str):
        raise web.HTTPBadRequest(reason=PASSWORD_ERROR_MSG)
    if password and not re.match(PASSWORD_REGEX_PATTERN, password):
        raise web.HTTPBadRequest(reason=PASSWORD_ERROR_MSG)

    check_authorization(request, user_id, "update")

    try:
        User.Objects.update(user_id, data)
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except User.DoesNotExist:
        raise web.HTTPNotFound(reason="User with id:<{}> does not exist".format(user_id))
    except Exception as exc:
        raise web.HTTPInternalServerError(reason=str(exc))

    return web.json_response({'message': 'User with id:<{}> updated successfully'.format(user_id)})


async def delete_user(request):
    """ Delete a user from users table

    :Example:
        curl -H "authorization: <token>" -X DELETE  http://localhost:8081/foglamp/user/1
    """

    # TODO: do a soft delete, set user->enabled to False
    try:
        user_id = request.match_info.get('id')

        # TODO: we should not prevent this, when we have at-least 1 admin (super) user
        if user_id == 1:
            raise web.HTTPNotAcceptable(reason="super admin can not be deleted")

        # Requester should not be able to delete her/himself
        if request.is_auth_optional is False:
            if user_id == request.user["id"]:
                raise web.HTTPBadRequest(reason="ask admin to disable account")

        check_authorization(request, user_id, "delete")

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


def has_admin_permissions(request):
    if request.is_auth_optional is False:  # auth is mandatory
        if int(request.user["role_id"]) != ADMIN_ROLE_ID:
            return False
    return True


def check_authorization(request, user_id, action):
    # use if has_admin_permissions(request):
    if request.is_auth_optional is False:  # auth is mandatory
        if int(request.user["role_id"]) != ADMIN_ROLE_ID and user_id != request.user["id"]:
            # requester is not an admin but trying to take action for another user
            raise web.HTTPUnauthorized(reason="admin privileges are required to {} other user".format(action))
    return True
