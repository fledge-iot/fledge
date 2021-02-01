# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" auth routes """

import re
import json
from collections import OrderedDict

from aiohttp import web
from fledge.services.core.user_model import User
from fledge.common.web.middleware import has_permission
from fledge.common import logger
from fledge.common.web.ssl_wrapper import SSLVerifier

__author__ = "Praveen Garg, Ashish Jabble, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = logger.setup(__name__)

_help = """
    ------------------------------------------------------------------------------------
    | GET                        | /fledge/user                                       |
    | PUT                        | /fledge/user/{id}                                  |
    | PUT                        | /fledge/user/{username}/password                   |     

    | GET                        | /fledge/user/role                                  |
    
    | POST                       | /fledge/login                                      |
    | PUT                        | /fledge/{user_id}/logout                           |
    
    | POST                       | /fledge/admin/user                                 |
    | PUT                        | /fledge/admin/{user_id}/reset                      |
    | DELETE                     | /fledge/admin/{user_id}/delete                     |
    ------------------------------------------------------------------------------------
"""

JWT_SECRET = 'f0gl@mp'
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 30*60  # 30 minutes

MIN_USERNAME_LENGTH = 4
PASSWORD_REGEX_PATTERN = '((?=.*\d)(?=.*[A-Z])(?=.*\W).{6,}$)'
PASSWORD_ERROR_MSG = 'Password must contain at least one digit, one lowercase, one uppercase & one special character ' \
                     'and length of minimum 6 characters'

FORBIDDEN_MSG = 'Resource you were trying to reach is absolutely forbidden for some reason'

# TODO: remove me, use from roles table
ADMIN_ROLE_ID = 1
DEFAULT_ROLE_ID = 2


async def login(request):
    """ Validate user with its username and password

    :Example:
        curl -d '{"username": "user", "password": "fledge"}' -X POST http://localhost:8081/fledge/login
        curl -T data/etc/certs/user.cert -X POST http://localhost:8081/fledge/login --insecure (--insecure or -k)
    """
    auth_method = request.auth_method if 'auth_method' in dir(request) else "any"
    data = await request.text()

    # Check for appropriate payload per auth_method
    if auth_method == 'certificate':
        if not data.startswith("-----BEGIN CERTIFICATE-----"):
            raise web.HTTPBadRequest(reason="Use a valid certificate to login.")
    elif auth_method == 'password':
        try:
            user_data = json.loads(data)
        except json.JSONDecodeError:
            raise web.HTTPBadRequest(reason="Use a valid username and password to login.")

    if data.startswith("-----BEGIN CERTIFICATE-----"):
        peername = request.transport.get_extra_info('peername')
        if peername is not None:
            host, port = peername

        try:
            await User.Objects.verify_certificate(data)
            username = SSLVerifier.get_subject()['commonName']
            uid, token, is_admin = await User.Objects.certificate_login(username, host)
            # set the user to request object
            request.user = await User.Objects.get(uid=uid)
            # set the token to request
            request.token = token
        except (SSLVerifier.VerificationError, User.DoesNotExist, OSError) as e:
            raise web.HTTPUnauthorized(reason="Authentication failed")
        except ValueError as ex:
            raise web.HTTPUnauthorized(reason="Authentication failed: {}".format(str(ex)))
    else:
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            raise web.HTTPBadRequest(reason="Invalid username and/or password.")

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            _logger.warning("Username and password are required to login")
            raise web.HTTPBadRequest(reason="Username or password is missing")

        username = str(username).lower()

        peername = request.transport.get_extra_info('peername')
        host = '0.0.0.0'
        if peername is not None:
            host, port = peername
        try:
            uid, token, is_admin = await User.Objects.login(username, password, host)
        except (User.DoesNotExist, User.PasswordDoesNotMatch, ValueError) as ex:
            _logger.warning(str(ex))
            return web.HTTPNotFound(reason=str(ex))
        except User.PasswordExpired as ex:
            # delete all user token for this user
            await User.Objects.delete_user_tokens(str(ex))

            msg = 'Your password has been expired. Please set your password again'
            _logger.warning(msg)
            return web.HTTPUnauthorized(reason=msg)

    _logger.info("User with username:<{}> has been logged in successfully".format(username))
    return web.json_response({"message": "Logged in successfully", "uid": uid, "token": token, "admin": is_admin})


async def logout_me(request):
    """ log out user

    :Example:
        curl -H "authorization: <token>" -X PUT http://localhost:8081/fledge/logout

    """

    if request.is_auth_optional:
        # no action needed
        return web.json_response({"logout": True})

    result = await User.Objects.delete_token(request.token)

    if not result['rows_affected']:
        _logger.warning("Logout requested with bad user token")
        raise web.HTTPNotFound()

    _logger.info("User has been logged out successfully")
    return web.json_response({"logout": True})


async def logout(request):
    """ log out user's all active sessions

    :Example:
        curl -H "authorization: <token>" -X PUT http://localhost:8081/fledge/{user_id}/logout

    """
    if request.is_auth_optional:
        _logger.warning(FORBIDDEN_MSG)
        raise web.HTTPForbidden

    user_id = request.match_info.get('user_id')

    if int(request.user["role_id"]) == ADMIN_ROLE_ID or int(request.user["id"]) == int(user_id):
        result = await User.Objects.delete_user_tokens(user_id)

        if not result['rows_affected']:
            _logger.warning("Logout requested with bad user")
            raise web.HTTPNotFound()

        _logger.info("User with id:<{}> has been logged out successfully".format(int(user_id)))
    else:
        # requester is not an admin but trying to take action for another user
        raise web.HTTPUnauthorized(reason="admin privileges are required to logout other user")

    return web.json_response({"logout": True})


async def get_roles(request):
    """ get roles

    :Example:
        curl -H "authorization: <token>" -X GET http://localhost:8081/fledge/user/role
    """
    result = await User.Objects.get_roles()
    return web.json_response({'roles': result})


async def get_user(request):
    """ get user info

    :Example:
        curl -H "authorization: <token>" -X GET http://localhost:8081/fledge/user
        curl -H "authorization: <token>" -X GET http://localhost:8081/fledge/user?id=2
        curl -H "authorization: <token>" -X GET http://localhost:8081/fledge/user?username=admin
        curl -H "authorization: <token>" -X GET "http://localhost:8081/fledge/user?id=1&username=admin"
    """
    user_id = None
    user_name = None

    if 'id' in request.query:
        try:
            user_id = int(request.query['id'])
            if user_id <= 0:
                raise ValueError
        except ValueError:
            _logger.warning("Get user requested with bad user id")
            raise web.HTTPBadRequest(reason="Bad user id")

    if 'username' in request.query and request.query['username'] != '':
        user_name = request.query['username'].lower()

    if user_id or user_name:
        try:
            user = await User.Objects.get(user_id, user_name)
            u = OrderedDict()
            u['userId'] = user.pop('id')
            u['userName'] = user.pop('uname')
            u['roleId'] = user.pop('role_id')
            result = u
        except User.DoesNotExist as ex:
            _logger.warning(str(ex))
            raise web.HTTPNotFound(reason=str(ex))
    else:
        users = await User.Objects.all()
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
        curl -H "authorization: <token>" -X POST -d '{"username": "any1", "password": "User@123"}' http://localhost:8081/fledge/admin/user
        curl -H "authorization: <token>" -X POST -d '{"username": "admin1", "password": "F0gl@mp!", "role_id": 1}' http://localhost:8081/fledge/admin/user
    """
    if request.is_auth_optional:
        _logger.warning(FORBIDDEN_MSG)
        raise web.HTTPForbidden
    
    data = await request.json()
    username = data.get('username')
    password = data.get('password')
    role_id = data.get('role_id', DEFAULT_ROLE_ID)

    if not username or not password:
        _logger.warning("Username and password are required to create user")
        raise web.HTTPBadRequest(reason="Username or password is missing")

    if not isinstance(password, str):
        _logger.warning(PASSWORD_ERROR_MSG)
        raise web.HTTPBadRequest(reason=PASSWORD_ERROR_MSG)

    if not re.match(PASSWORD_REGEX_PATTERN, password):
        _logger.warning(PASSWORD_ERROR_MSG)
        raise web.HTTPBadRequest(reason=PASSWORD_ERROR_MSG)

    if not (await is_valid_role(role_id)):
        _logger.warning("Create user requested with bad role id")
        return web.HTTPBadRequest(reason="Invalid or bad role id")

    # TODO: username regex? is email allowed?
    username = username.lower().replace(" ", "")
    if len(username) < MIN_USERNAME_LENGTH:
        msg = "Username should be of minimum 4 characters"
        _logger.warning(msg)
        raise web.HTTPBadRequest(reason=msg)

    try:
        await User.Objects.get(username=username)
    except User.DoesNotExist:
        pass
    else:
        _logger.warning("Can not create a user, username already exists")
        raise web.HTTPConflict(reason="User with the requested username already exists")

    u = dict()
    try:
        result = await User.Objects.create(username, password, role_id)
        if result['rows_affected']:
            # FIXME: we should not do get again!
            # we just need inserted user id; insert call should return that
            user = await User.Objects.get(username=username)
            u['userId'] = user.pop('id')
            u['userName'] = user.pop('uname')
            u['roleId'] = user.pop('role_id')
    except ValueError as ex:
        _logger.warning(str(ex))
        raise web.HTTPBadRequest(reason=str(ex))
    except Exception as exc:
        _logger.exception(str(exc))
        raise web.HTTPInternalServerError(reason=str(exc))

    _logger.info("User has been created successfully")

    return web.json_response({'message': 'User has been created successfully', 'user': u})


async def update_user(request):
    if request.is_auth_optional:
        _logger.warning(FORBIDDEN_MSG)
        raise web.HTTPForbidden

    # TODO: FOGL-1226 we don't have any user profile info yet except password, role
    raise web.HTTPNotImplemented(reason='FOGL-1226')


async def update_password(request):
    """ update password

        :Example:
             curl -X PUT -d '{"current_password": "F0gl@mp!", "new_password": "F0gl@mp1"}' http://localhost:8081/fledge/user/<username>/password
    """
    if request.is_auth_optional:
        _logger.warning(FORBIDDEN_MSG)
        raise web.HTTPForbidden

    username = request.match_info.get('username')
    data = await request.json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    if not current_password or not new_password:
        msg = "Current or new password is missing"
        _logger.warning(msg)
        raise web.HTTPBadRequest(reason=msg)

    if new_password and not isinstance(new_password, str):
        _logger.warning(PASSWORD_ERROR_MSG)
        raise web.HTTPBadRequest(reason=PASSWORD_ERROR_MSG)
    if new_password and not re.match(PASSWORD_REGEX_PATTERN, new_password):
        _logger.warning(PASSWORD_ERROR_MSG)
        raise web.HTTPBadRequest(reason=PASSWORD_ERROR_MSG)

    if current_password == new_password:
        msg = "New password should not be same as current password"
        _logger.warning(msg)
        raise web.HTTPBadRequest(reason=msg)

    user_id = await User.Objects.is_user_exists(username, current_password)
    if not user_id:
        msg = 'Invalid current password'
        _logger.warning(msg)
        raise web.HTTPNotFound(reason=msg)

    try:
        await User.Objects.update(int(user_id), {'password': new_password})
    except ValueError as ex:
        _logger.warning(str(ex))
        raise web.HTTPBadRequest(reason=str(ex))
    except User.DoesNotExist:
        msg = "User with id:<{}> does not exist".format(int(user_id))
        _logger.warning(msg)
        raise web.HTTPNotFound(reason=msg)
    except User.PasswordAlreadyUsed:
        msg = "The new password should be different from previous 3 used"
        _logger.warning(msg)
        raise web.HTTPBadRequest(reason=msg)
    except Exception as exc:
        _logger.exception(str(exc))
        raise web.HTTPInternalServerError(reason=str(exc))

    _logger.info("Password has been updated successfully for user id:<{}>".format(int(user_id)))

    return web.json_response({'message': 'Password has been updated successfully for user id:<{}>'.format(int(user_id))})


@has_permission("admin")
async def reset(request):
    """ reset user (only role and password)
        :Example:
            curl -H "authorization: <token>" -X PUT -d '{"role_id": "1"}' http://localhost:8081/fledge/admin/{user_id}/reset
            curl -H "authorization: <token>" -X PUT -d '{"password": "F0gl@mp!"}' http://localhost:8081/fledge/admin/{user_id}/reset
            curl -H "authorization: <token>" -X PUT -d '{"role_id": 1, "password": "F0gl@mp!"}' http://localhost:8081/fledge/admin/{user_id}/reset
    """
    if request.is_auth_optional:
        _logger.warning(FORBIDDEN_MSG)
        raise web.HTTPForbidden

    user_id = request.match_info.get('user_id')
    if int(user_id) == 1:
        msg = "Restricted for Super Admin user"
        _logger.warning(msg)
        raise web.HTTPNotAcceptable(reason=msg)

    data = await request.json()
    password = data.get('password')
    role_id = data.get('role_id')

    if not role_id and not password:
        msg = "Nothing to update the user"
        _logger.warning(msg)
        raise web.HTTPBadRequest(reason=msg)

    if role_id and not (await is_valid_role(role_id)):
        msg = "Invalid or bad role id"
        _logger.warning(msg)
        return web.HTTPBadRequest(reason=msg)

    if password and not isinstance(password, str):
        _logger.warning(PASSWORD_ERROR_MSG)
        raise web.HTTPBadRequest(reason=PASSWORD_ERROR_MSG)
    if password and not re.match(PASSWORD_REGEX_PATTERN, password):
        _logger.warning(PASSWORD_ERROR_MSG)
        raise web.HTTPBadRequest(reason=PASSWORD_ERROR_MSG)

    user_data = {}
    if 'role_id' in data:
        user_data.update({'role_id': data['role_id']})
    if 'password' in data:
        user_data.update({'password': data['password']})

    try:
        await User.Objects.update(user_id, user_data)
    except ValueError as ex:
        _logger.warning(str(ex))
        raise web.HTTPBadRequest(reason=str(ex))
    except User.DoesNotExist:
        msg = "User with id:<{}> does not exist".format(int(user_id))
        _logger.warning(msg)
        raise web.HTTPNotFound(reason=msg)
    except User.PasswordAlreadyUsed:
        msg = "The new password should be different from previous 3 used"
        _logger.warning(msg)
        raise web.HTTPBadRequest(reason=msg)
    except Exception as exc:
        _logger.exception(str(exc))
        raise web.HTTPInternalServerError(reason=str(exc))

    _logger.info("User with id:<{}> has been updated successfully".format(int(user_id)))

    return web.json_response({'message': 'User with id:<{}> has been updated successfully'.format(user_id)})


@has_permission("admin")
async def delete_user(request):
    """ Delete a user from users table

    :Example:
        curl -H "authorization: <token>" -X DELETE  http://localhost:8081/fledge/admin/{user_id}/delete
    """
    if request.is_auth_optional:
        _logger.warning(FORBIDDEN_MSG)
        raise web.HTTPForbidden

    # TODO: we should not prevent this, when we have at-least 1 admin (super) user
    try:
        user_id = int(request.match_info.get('user_id'))
    except ValueError as ex:
        _logger.warning(str(ex))
        raise web.HTTPBadRequest(reason=str(ex))

    if user_id == 1:
        msg = "Super admin user can not be deleted"
        _logger.warning(msg)
        raise web.HTTPNotAcceptable(reason=msg)
    
    # Requester should not be able to delete her/himself
    if user_id == request.user["id"]:
        msg = "You can not delete your own account"
        _logger.warning(msg)
        raise web.HTTPBadRequest(reason=msg)

    try:
        result = await User.Objects.delete(user_id)
        if not result['rows_affected']:
            raise User.DoesNotExist

    except ValueError as ex:
        _logger.warning(str(ex))
        raise web.HTTPBadRequest(reason=str(ex))
    except User.DoesNotExist:
        msg = "User with id:<{}> does not exist".format(int(user_id))
        _logger.warning(msg)
        raise web.HTTPNotFound(reason=msg)
    except Exception as exc:
        _logger.exception(str(exc))
        raise web.HTTPInternalServerError(reason=str(exc))

    _logger.info("User with id:<{}> has been deleted successfully.".format(int(user_id)))

    return web.json_response({'message': "User has been deleted successfully"})


async def is_valid_role(role_id):
    roles = [int(r["id"]) for r in await User.Objects.get_roles()]
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
