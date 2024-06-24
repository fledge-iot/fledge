# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" auth routes """
import datetime
import re
import json
from collections import OrderedDict
import jwt
from aiohttp import web

from fledge.common.audit_logger import AuditLogger
from fledge.common.logger import FLCoreLogger
from fledge.common.web.middleware import has_permission
from fledge.common.web.ssl_wrapper import SSLVerifier
from fledge.services.core.user_model import User

__author__ = "Praveen Garg, Ashish Jabble, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = FLCoreLogger().get_logger(__name__)

_help = """
    ------------------------------------------------------------------------------------
    | GET                        | /fledge/user                                       |
    | PUT                        | /fledge/user                                       |
    | PUT                        | /fledge/user/{user_id}/password                    |     

    | GET                        | /fledge/user/role                                  |
    
    | POST                       | /fledge/login                                      |
    | PUT                        | /fledge/{user_id}/logout                           |
    
    | GET                        | /fledge/auth/ott                                   |

    | POST                       | /fledge/admin/user                                 |
    | PUT                        | /fledge/admin/{user_id}                            |
    | PUT                        | /fledge/admin/{user_id}/enable                     |
    | PUT                        | /fledge/admin/{user_id}/reset                      |
    | DELETE                     | /fledge/admin/{user_id}/delete                     |
    ------------------------------------------------------------------------------------
"""

JWT_SECRET = 'f0gl@mp'
JWT_ALGORITHM = 'HS512'
JWT_EXP_DELTA_SECONDS = 30*60  # 30 minutes

MIN_USERNAME_LENGTH = 4
USERNAME_REGEX_PATTERN = '^[a-zA-Z0-9_.-]+$'
FORBIDDEN_MSG = 'Resource you were trying to reach is absolutely forbidden for some reason'
DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

# TODO: remove me, use from roles table
ADMIN_ROLE_ID = 1
DEFAULT_ROLE_ID = 2
OTT_TOKEN_EXPIRY_MINUTES = 5


class OTT:
    """
        Manage the One Time Token assigned to log in for single time and within OTT_TOKEN_EXPIRY_MINUTES
    """

    OTT_MAP = {}

    def __init__(self):
        pass


def __remove_ott_for_user(user_id):
    """Helper function that removes given user_id from OTT_MAP if the user exists in the map."""
    try:
        _user_id = int(user_id)
    except ValueError:
        return
    for k, v in OTT.OTT_MAP.items():
        if v[0] == _user_id:
            OTT.OTT_MAP.pop(k)
            break


def __remove_ott_for_token(given_token):
    """Helper function that removes given token from OTT_MAP if that token in the map."""
    for k, v in OTT.OTT_MAP.items():
        if v[1] == given_token:
            OTT.OTT_MAP.pop(k)
            break


async def login(request):
    """ Validate user with its username and password

    :Example:
        curl -d '{"username": "user", "password": "fledge"}' -X POST http://localhost:8081/fledge/login
        curl -T data/etc/certs/user.cert -X POST http://localhost:8081/fledge/login --insecure (--insecure or -k)
        curl -d '{"ott": "ott_token"}' -skX POST http://localhost:8081/fledge/login
    """
    auth_method = request.auth_method if 'auth_method' in dir(request) else "any"
    data = await request.text()

    try:
        # Check ott inside request payload.
        _data = json.loads(data)
        if 'ott' in _data:
            auth_method = "OTT"  # This is for local reference and not a configuration value
    except json.JSONDecodeError:
        if auth_method == 'password':
            raise web.HTTPBadRequest(reason="Use valid username & password to log in.")
        pass

    # Check for appropriate payload per auth_method
    if auth_method == 'certificate':
        if not data.startswith("-----BEGIN CERTIFICATE-----"):
            raise web.HTTPBadRequest(reason="Use a valid certificate to login.")

    if data.startswith("-----BEGIN CERTIFICATE-----"):
        peername = request.transport.get_extra_info('peername')
        if peername is not None:
            host, _ = peername

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
    elif auth_method == "OTT":

        _ott = _data.get('ott')
        if _ott not in OTT.OTT_MAP:
            raise web.HTTPUnauthorized(reason="Authentication failed. Either the given token expired or already used.")

        time_now = datetime.datetime.now()
        user_id, orig_token, is_admin, initial_time = OTT.OTT_MAP[_ott]

        # remove ott from MAP when used or when expired.
        OTT.OTT_MAP.pop(_ott, None)
        if time_now - initial_time <= datetime.timedelta(minutes=OTT_TOKEN_EXPIRY_MINUTES):
            return web.json_response(
                {"message": "Logged in successfully", "uid": user_id, "token": orig_token, "admin": is_admin})
        else:
            raise web.HTTPUnauthorized(reason="Authentication failed! The given token has expired")
    else:

        username = _data.get('username')
        password = _data.get('password')

        if not username or not password:
            raise web.HTTPBadRequest(reason="Username or password is missing")

        username = str(username).lower()

        peername = request.transport.get_extra_info('peername')
        host = '0.0.0.0'
        if peername is not None:
            host, port = peername
        try:
            uid, token, is_admin = await User.Objects.login(username, password, host)
        except (User.DoesNotExist, User.PasswordDoesNotMatch, ValueError) as ex:
            raise web.HTTPNotFound(reason=str(ex))
        except User.PasswordExpired as ex:
            # delete all user token for this user
            await User.Objects.delete_user_tokens(str(ex))
            msg = 'Your password has been expired. Please set your password again.'
            _logger.warning(msg)
            raise web.HTTPUnauthorized(reason=msg)

    _logger.info("User with username:<{}> logged in successfully.".format(username))
    return web.json_response({"message": "Logged in successfully.", "uid": uid, "token": token, "admin": is_admin})


async def get_ott(request):
    """ Get one time use token (OTT) for login.

        :Example:
            curl -H "authorization: <token>" -X GET http://localhost:8081/fledge/auth/ott
    """
    if request.is_auth_optional:
        _logger.warning(FORBIDDEN_MSG)
        raise web.HTTPForbidden

    try:
        # Fetching user_id and role for given token.
        original_token = request.token
        from fledge.services.core import connect
        from fledge.common.storage_client.payload_builder import PayloadBuilder
        payload = PayloadBuilder().SELECT("user_id").WHERE(['token', '=', original_token]).payload()
        storage_client = connect.get_storage_async()
        result = await storage_client.query_tbl_with_payload("user_logins", payload)
        if len(result['rows']) == 0:
            message = "The request token {} does not have a valid user associated with it.".format(original_token)
            raise web.HTTPBadRequest(reason=message)
        user_id = result['rows'][0]['user_id']
        payload_role = PayloadBuilder().SELECT("role_id").WHERE(['id', '=', user_id]).payload()
        storage_client = connect.get_storage_async()
        result_role = await storage_client.query_tbl_with_payload("users", payload_role)
        if len(result_role['rows']) < 1:
            message = "The request token {} does not have a valid role associated with it.".format(original_token)
            raise web.HTTPBadRequest(reason=message)
        # checking if the user is an admin.
        is_admin = False
        if int(result_role['rows'][0]['role_id']) == 1:
            is_admin = True
    except Exception as ex:
        msg = str(ex)
        _logger.error(ex, "OTT token failed.")
        raise web.HTTPBadRequest(reason="The request failed due to {}".format(msg))
    else:
        now_time = datetime.datetime.now()
        p = {'uid': user_id, 'exp': now_time}
        ott_token = jwt.encode(p, JWT_SECRET, JWT_ALGORITHM)
        already_existed_token = False
        key_to_remove = None
        for k, v in OTT.OTT_MAP.items():
            if v[1] == original_token:
                already_existed_token = True
                key_to_remove = k

        if already_existed_token:
            OTT.OTT_MAP.pop(key_to_remove, None)

        ott_info = (user_id, original_token, is_admin, now_time)
        OTT.OTT_MAP[ott_token] = ott_info
        return web.json_response({"ott": ott_token})


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
        raise web.HTTPNotFound()

    __remove_ott_for_token(request.token)
    _logger.info("User has been logged out successfully.")
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
            raise web.HTTPNotFound()
        # Remove OTT token for this user if there.
        __remove_ott_for_user(user_id)
        _logger.info("User with ID:<{}> has been logged out successfully.".format(int(user_id)))
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
            raise web.HTTPBadRequest(reason="Bad user ID")

    if 'username' in request.query and request.query['username'] != '':
        user_name = request.query['username'].lower()
    if user_id or user_name:
        try:
            user = await User.Objects.get(user_id, user_name)
            u = OrderedDict()
            u['userId'] = user.pop('id')
            u['userName'] = user.pop('uname')
            u['roleId'] = user.pop('role_id')
            u["accessMethod"] = user.pop('access_method')
            u["realName"] = user.pop('real_name')
            u["description"] = user.pop('description')
            result = u
        except User.DoesNotExist as ex:
            msg = str(ex)
            raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    else:
        users = await User.Objects.all()
        res = []
        for row in users:
            if row['enabled'] == 't':
                u = OrderedDict()
                u["userId"] = row["id"]
                u["userName"] = row["uname"]
                u["roleId"] = row["role_id"]
                u["accessMethod"] = row["access_method"]
                u["realName"] = row["real_name"]
                u["description"] = row["description"]
                if row["block_until"]:
                    curr_time = datetime.datetime.now(datetime.timezone.utc).strftime(DATE_FORMAT)
                    block_time = row["block_until"].split('.')[0] # strip time after HH:MM:SS for display
                    if datetime.datetime.strptime(row["block_until"], DATE_FORMAT) > datetime.datetime.strptime(curr_time, DATE_FORMAT):
                        u["blockUntil"] = block_time
                res.append(u)
        result = {'users': res}

    return web.json_response(result)


@has_permission("admin")
async def create_user(request):
    """ create user

    :Example:
        curl -H "authorization: <token>" -X POST -d '{"username": "any1", "password": "User@123"}' http://localhost:8081/fledge/admin/user
        curl -H "authorization: <token>" -X POST -d '{"username": "aj.1988", "password": "User@123", "access_method": "any"}' http://localhost:8081/fledge/admin/user
        curl -H "authorization: <token>" -X POST -d '{"username": "aj-1988", "password": "User@123", "access_method": "pwd"}' http://localhost:8081/fledge/admin/user
        curl -H "authorization: <token>" -X POST -d '{"username": "aj_1988", "access_method": "any"}' http://localhost:8081/fledge/admin/user
        curl -H "authorization: <token>" -X POST -d '{"username": "aj1988", "access_method": "cert"}' http://localhost:8081/fledge/admin/user
        curl -H "authorization: <token>" -X POST -d '{"username": "ajnerd", "password": "F0gl@mp!", "role_id": 1, "real_name": "AJ", "description": "Admin user"}' http://localhost:8081/fledge/admin/user
        curl -H "authorization: <token>" -X POST -d '{"username": "nerd", "access_method": "cert", "real_name": "AJ", "description": "Admin user"}' http://localhost:8081/fledge/admin/user
        curl -H "authorization: <token>" -X POST -d '{"username": "nerdapp", "password": "FL)dG3", "access_method": "pwd", "real_name": "AJ", "description": "Admin user"}' http://localhost:8081/fledge/admin/user
    """
    if request.is_auth_optional:
        _logger.warning(FORBIDDEN_MSG)
        raise web.HTTPForbidden
    
    data = await request.json()
    username = data.get('username', '')
    password = data.get('password')
    role_id = data.get('role_id', DEFAULT_ROLE_ID)
    access_method = data.get('access_method', 'any')
    real_name = data.get('real_name', '')
    description = data.get('description', '')

    if not username:
        msg = "Username is required to create user."
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))

    if not isinstance(username, str) or not isinstance(access_method, str) or not isinstance(real_name, str) \
            or not isinstance(description, str):
        msg = "Values should be passed in string."
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))

    username = username.lower().strip().replace(" ", "")
    if len(username) < MIN_USERNAME_LENGTH:
        msg = "Username should be of minimum 4 characters."
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    if not re.match(USERNAME_REGEX_PATTERN, username):
        msg = "Dot, hyphen, underscore special characters are allowed for username."
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))

    if access_method.lower() not in ['any', 'cert', 'pwd']:
        msg = "Invalid access method. Must be 'any' or 'cert' or 'pwd'."
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))

    if access_method == 'pwd' and not password:
        msg = "Password should not be an empty."
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))

    if access_method != 'cert':
        if password is not None:
            error_msg = await validate_password(password)
            if error_msg:
                raise web.HTTPBadRequest(reason=error_msg, body=json.dumps({"message": error_msg}))
    if not (await is_valid_role(role_id)):
        msg = "Invalid role ID."
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    users = await User.Objects.all()
    unames = [u['uname'] for u in users]
    if username in unames:
        msg = "Username already exists."
        _logger.warning(msg)
        raise web.HTTPConflict(reason=msg, body=json.dumps({"message": msg}))
    u = dict()
    try:
        result = await User.Objects.create(username, password, role_id, access_method, real_name, description)
        if result['rows_affected']:
            # FIXME: we should not do get again!
            # we just need inserted user id; insert call should return that
            user = await User.Objects.get(username=username)
            u['userId'] = user.pop('id')
            u['userName'] = user.pop('uname')
            u['roleId'] = user.pop('role_id')
            u["accessMethod"] = user.pop('access_method')
            u["realName"] = user.pop('real_name')
            u["description"] = user.pop('description')
    except ValueError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except Exception as exc:
        msg = str(exc)
        _logger.error(exc, "Failed to create user.")
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    msg = "{} user has been created successfully.".format(username)
    _logger.info(msg)
    return web.json_response({'message': msg, 'user': u})

# FIXME: Need to fix user id dependency in update_me


async def update_me(request):
    """ update user profile

    :Example:
             curl -H "authorization: <token>" -X PUT -d '{"real_name": "AJ"}' http://localhost:8081/fledge/user
    """
    if request.is_auth_optional:
        _logger.warning(FORBIDDEN_MSG)
        raise web.HTTPForbidden
    data = await request.json()
    real_name = data.get('real_name', '')
    if 'real_name' in data:
        if len(real_name.strip()) == 0:
            msg = "Real Name should not be empty."
            raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
        else:
            from fledge.services.core import connect
            from fledge.common.storage_client.payload_builder import PayloadBuilder
            try:
                payload = PayloadBuilder().SELECT("user_id").WHERE(['token', '=', request.token]).payload()
                storage_client = connect.get_storage_async()
                result = await storage_client.query_tbl_with_payload("user_logins", payload)
                if len(result['rows']) == 0:
                    raise User.DoesNotExist
                user_id = result['rows'][0]['user_id']
                payload = PayloadBuilder().SET(real_name=real_name.strip()).WHERE(['id', '=', user_id]).payload()
                message = "Something went wrong."
                result = await storage_client.update_tbl("users", payload)
                if result['response'] == 'updated':
                    # TODO: FOGL-1226 At the moment only real name can update
                    message = "Real name has been updated successfully!"
            except User.DoesNotExist:
                msg = "User does not exist."
                raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
            except ValueError as err:
                msg = str(err)
                raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
            except Exception as exc:
                msg = str(exc)
                _logger.error(exc, "Failed to update the user <{}> profile.".format(int(user_id)))
                raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        msg = "Nothing to update."
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    return web.json_response({"message": message})


@has_permission("admin")
async def update_user(request):
    """ access_method, description, real_name
        :Example:
            curl -H "authorization: <token>" -X PUT -d '{"description": "A new user"}' http://localhost:8081/fledge/admin/{user_id}
            curl -H "authorization: <token>" -X PUT -d '{"real_name": "Admin"}' http://localhost:8081/fledge/admin/{user_id}
            curl -H "authorization: <token>" -X PUT -d '{"access_method": "pwd"}' http://localhost:8081/fledge/admin/{user_id}
            curl -H "authorization: <token>" -X PUT -d '{"description": "A new user", "real_name": "Admin", "access_method": "pwd"}' http://localhost:8081/fledge/admin/{user_id}
    """
    if request.is_auth_optional:
        _logger.warning(FORBIDDEN_MSG)
        raise web.HTTPForbidden

    user_id = request.match_info.get('user_id')
    if int(user_id) == 1:
        msg = "Restricted for Super Admin user."
        _logger.warning(msg)
        raise web.HTTPForbidden(reason=msg, body=json.dumps({"message": msg}))

    data = await request.json()
    access_method = data.get('access_method', '')
    description = data.get('description', '')
    real_name = data.get('real_name', '')
    user_data = {}
    if 'real_name' in data:
        if len(real_name.strip()) == 0:
            msg = "Real Name should not be empty."
            raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
        else:
            user_data.update({"real_name": real_name.strip()})
    if 'access_method' in data:
        if len(access_method.strip()) == 0:
            msg = "Access method should not be empty."
            raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
        else:
            valid_access_method = ('any', 'pwd', 'cert')
            if access_method not in valid_access_method:
                msg = "Accepted access method values are {}.".format(valid_access_method)
                raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
            user_data.update({"access_method": access_method.strip()})
    if 'description' in data:
        user_data.update({"description": description.strip()})
    if not user_data:
        msg = "Nothing to update."
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    try:
        user = await User.Objects.update(user_id, user_data)
        if user:
            user_info = await User.Objects.get(uid=user_id)

        if 'access_method' in data:
            # Remove OTT token for this user only if access method is updated.
            __remove_ott_for_user(user_id)
    except ValueError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=str(err), body=json.dumps({"message": msg}))
    except User.DoesNotExist:
        msg = "User with ID:<{}> does not exist".format(int(user_id))
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as exc:
        msg = str(exc)
        _logger.error(exc, "Failed to update the user ID:<{}>.".format(user_id))
        raise web.HTTPInternalServerError(reason=str(exc), body=json.dumps({"message": msg}))
    return web.json_response({'user_info': user_info})


async def update_password(request):
    """ update password

        :Example:
             curl -X PUT -d '{"current_password": "F0gl@mp!", "new_password": "F0gl@mp1"}' http://localhost:8081/fledge/user/<user_id>/password
    """
    if request.is_auth_optional:
        _logger.warning(FORBIDDEN_MSG)
        raise web.HTTPForbidden

    user_id = request.match_info.get('user_id')
    try:
        int(user_id)
    except ValueError:
        msg = "User ID should be in integer."
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))

    data = await request.json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    if not current_password or not new_password:
        msg = "Current or new password is missing."
        raise web.HTTPBadRequest(reason=msg)

    if new_password and not isinstance(new_password, str):
        err_msg = "New password should be in string format."
        raise web.HTTPBadRequest(reason=err_msg, body=json.dumps({"message": err_msg}))
    error_msg = await validate_password(new_password)
    if error_msg:
        raise web.HTTPBadRequest(reason=error_msg, body=json.dumps({"message": error_msg}))
    if current_password == new_password:
        msg = "New password should not be the same as current password."
        raise web.HTTPBadRequest(reason=msg)

    user_id = await User.Objects.is_user_exists(user_id, current_password)
    if not user_id:
        msg = 'Invalid current password.'
        raise web.HTTPNotFound(reason=msg)

    try:
        await User.Objects.update(int(user_id), {'password': new_password})
        # Remove OTT token for this user if there.
        __remove_ott_for_user(user_id)
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except User.DoesNotExist:
        msg = "User with ID:<{}> does not exist.".format(int(user_id))
        raise web.HTTPNotFound(reason=msg)
    except User.PasswordAlreadyUsed:
        msg = "The new password should be different from previous 3 used."
        raise web.HTTPBadRequest(reason=msg)
    except Exception as exc:
        msg = str(exc)
        _logger.error(exc, "Failed to update the user ID:<{}>.".format(user_id))
        raise web.HTTPInternalServerError(reason=msg)

    msg = "Password has been updated successfully for user ID:<{}>.".format(int(user_id))
    _logger.info(msg)
    return web.json_response({'message': msg})


@has_permission("admin")
async def enable_user(request):
    """ enable/disable user
        :Example:
            curl -H "authorization: <token>" -X PUT -d '{"enabled": "true"}' http://localhost:8081/fledge/admin/{user_id}/enable
            curl -H "authorization: <token>" -X PUT -d '{"enabled": "False"}' http://localhost:8081/fledge/admin/{user_id}/enable
    """
    if request.is_auth_optional:
        _logger.warning(FORBIDDEN_MSG)
        raise web.HTTPForbidden

    user_id = request.match_info.get('user_id')
    if int(user_id) == 1:
        msg = "Restricted for Super Admin user."
        _logger.warning(msg)
        raise web.HTTPForbidden(reason=msg, body=json.dumps({"message": msg}))

    data = await request.json()
    enabled = data.get('enabled')
    try:
        if enabled is not None:
            if str(enabled).lower() in ['true', 'false']:
                from fledge.services.core import connect
                from fledge.common.storage_client.payload_builder import PayloadBuilder
                user_data = {'enabled': 't' if str(enabled).lower() == 'true' else 'f'}
                payload = PayloadBuilder().SELECT("id", "uname", "role_id", "enabled").WHERE(
                    ['id', '=', user_id]).payload()
                storage_client = connect.get_storage_async()
                old_result = await storage_client.query_tbl_with_payload('users', payload)
                if len(old_result['rows']) == 0:
                    raise User.DoesNotExist
                payload = PayloadBuilder().SET(enabled=user_data['enabled']).WHERE(['id', '=', user_id]).payload()
                result = await storage_client.update_tbl("users", payload)
                # Remove ott token for this enabled/disabled user.
                __remove_ott_for_user(user_id)
                if result['response'] == 'updated':
                    _text = 'enabled' if user_data['enabled'] == 't' else 'disabled'
                    payload = PayloadBuilder().SELECT("id", "uname", "role_id", "enabled").WHERE(
                        ['id', '=', user_id]).payload()
                    new_result = await storage_client.query_tbl_with_payload('users', payload)
                    if len(new_result['rows']) == 0:
                        raise User.DoesNotExist
                    # USRCH audit trail entry
                    audit = AuditLogger(storage_client)
                    await audit.information(
                        'USRCH', {'user_id': int(user_id), 'old_value': {'enabled': old_result['rows'][0]['enabled']},
                                  'new_value': {'enabled': new_result['rows'][0]['enabled']},
                                  "message": "'{}' user has been {}.".format(new_result['rows'][0]['uname'], _text)})
                else:
                    raise ValueError('Something went wrong during update. Check Syslogs.')
            else:
                raise ValueError('Accepted values are True/False only.')
        else:
            raise ValueError('Nothing to enable user update.')
    except ValueError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=str(err), body=json.dumps({"message": msg}))
    except User.DoesNotExist:
        msg = "User with ID:<{}> does not exist.".format(int(user_id))
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as exc:
        msg = str(exc)
        _logger.error(exc, "Failed to enable/disable user ID:<{}>.".format(user_id))
        raise web.HTTPInternalServerError(reason=str(exc), body=json.dumps({"message": msg}))
    return web.json_response({'message': 'User with ID:<{}> has been {} successfully.'.format(int(user_id), _text)})

@has_permission("admin")
async def unblock_user(request):
    """ Unblock the user got blocked due to multiple invalid log in attempts
        :Example:
            curl -H "authorization: <token>" -X PUT  http://localhost:8081/fledge/admin/{user_id}/unblock
    """
    if request.is_auth_optional:
        _logger.warning(FORBIDDEN_MSG)
        raise web.HTTPForbidden

    user_id = request.match_info.get('user_id')

    try:
        from fledge.services.core import connect
        storage_client = connect.get_storage_async()
        result = await _unblock_user(user_id,storage_client)
        if 'response' in result:
            if result['response'] == 'updated':
                # USRUB audit trail entry
                audit = AuditLogger(storage_client)
                await audit.information('USRUB', {'user_id': int(user_id),
                                "message": "User with ID:<{}> has been unblocked.".format(user_id)})
        else:
            raise KeyError("Unblock operation for user with ID:<{}> failed".format(user_id))
    except (KeyError, ValueError) as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=str(err), body=json.dumps({"message": msg}))
    except User.DoesNotExist:
        msg = "User with ID:<{}> does not exist.".format(int(user_id))
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as exc:
        msg = str(exc)
        _logger.error(exc, "Failed to unblock user ID:<{}>.".format(user_id))
        raise web.HTTPInternalServerError(reason=str(exc), body=json.dumps({"message": msg}))
    return web.json_response({'message': 'User with ID:<{}> has been unblocked successfully.'.format(int(user_id))})


async def _unblock_user(user_id, storage_client):
    """ implementation for unblock user
    """

    from fledge.common.storage_client.payload_builder import PayloadBuilder

    payload = PayloadBuilder().SELECT("id").WHERE(
        ['id', '=', user_id]).payload()
    old_result = await storage_client.query_tbl_with_payload('users', payload)
    if len(old_result['rows']) == 0:
        raise User.DoesNotExist('User does not exist')

    # Clear the failed_attempts so that maximum allowed attempts can be used correctly
    payload = PayloadBuilder().SET(block_until=None, failed_attempts=0).WHERE(['id', '=', user_id]).payload()
    result = await storage_client.update_tbl("users", payload)
    return result

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
        msg = "Restricted for Super Admin user."
        _logger.warning(msg)
        raise web.HTTPForbidden(reason=msg, body=json.dumps({"message": msg}))

    data = await request.json()
    password = data.get('password')
    role_id = data.get('role_id')

    if not role_id and not password:
        msg = "Nothing to update the user."
        raise web.HTTPBadRequest(reason=msg)

    if role_id and not (await is_valid_role(role_id)):
        msg = "Invalid or bad role id."
        return web.HTTPBadRequest(reason=msg)

    if password and not isinstance(password, str):
        err_msg = "New password should be in string format."
        raise web.HTTPBadRequest(reason=err_msg, body=json.dumps({"message": err_msg}))
    if password:
        error_msg = await validate_password(password)
        if error_msg:
            raise web.HTTPBadRequest(reason=error_msg, body=json.dumps({"message": error_msg}))
    user_data = {}
    if 'role_id' in data:
        user_data.update({'role_id': data['role_id']})
    if 'password' in data:
        user_data.update({'password': data['password']})
    if not user_data:
        msg = "Nothing to update."
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    try:
        await User.Objects.update(user_id, user_data)
        # Remove OTT token for this user if there.
        __remove_ott_for_user(user_id)
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except User.DoesNotExist:
        msg = "User with ID:<{}> does not exist.".format(int(user_id))
        raise web.HTTPNotFound(reason=msg)
    except User.PasswordAlreadyUsed:
        msg = "The new password should be different from previous 3 used."
        _logger.warning(msg)
        raise web.HTTPBadRequest(reason=msg)
    except Exception as exc:
        msg = str(exc)
        _logger.error(exc, "Failed to reset the user ID:<{}>.".format(user_id))
        raise web.HTTPInternalServerError(reason=msg)

    msg = "User with ID:<{}> has been updated successfully.".format(int(user_id))
    _logger.info(msg)
    return web.json_response({'message': msg})


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
        raise web.HTTPBadRequest(reason=str(ex))

    if user_id == 1:
        msg = "Super admin user can not be deleted."
        _logger.warning(msg)
        raise web.HTTPForbidden(reason=msg, body=json.dumps({"message": msg}))
    
    # Requester should not be able to delete her/himself
    if user_id == request.user["id"]:
        msg = "You can not delete your own account."
        _logger.warning(msg)
        raise web.HTTPBadRequest(reason=msg)

    try:
        result = await User.Objects.delete(user_id)
        if not result['rows_affected']:
            raise User.DoesNotExist
        # Remove OTT token for this user if there.
        __remove_ott_for_user(user_id)
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except User.DoesNotExist:
        msg = "User with ID:<{}> does not exist.".format(int(user_id))
        raise web.HTTPNotFound(reason=msg)
    except Exception as exc:
        msg = str(exc)
        _logger.error(exc, "Failed to delete the user ID:<{}>.".format(user_id))
        raise web.HTTPInternalServerError(reason=msg)

    _logger.info("User with ID:<{}> has been deleted successfully.".format(int(user_id)))

    return web.json_response({'message': "User has been deleted successfully."})


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
        # TODO: we may replace with request.user_is_admin
        if int(request.user["role_id"]) != ADMIN_ROLE_ID:
            return False
    return True

async def validate_password(password) -> str:
    from fledge.common.configuration_manager import ConfigurationManager
    from fledge.services.core import connect
    import string

    message = ""
    storage_client = connect.get_storage_async()
    cfg_mgr = ConfigurationManager(storage_client)
    category = await cfg_mgr.get_category_all_items('password')
    policy = category['policy']['value']
    min_chars = category['length']['value']
    max_chars = category['length']['maximum']
    if len(password) < int(min_chars):
        message = "Password length is minimum of {} characters.".format(min_chars)
    if len(password) > int(max_chars):
        message = "Password length is maximum of {} characters.".format(max_chars)
    if not message:
        has_lower = any(pwd.islower() for pwd in password)
        has_upper = any(pwd.isupper() for pwd in password)
        has_numeric = any(pwd.isdigit() for pwd in password)
        has_special = any(pwd in string.punctuation for pwd in password)
        if policy == 'Mixed case Alphabetic':
            mixed_case = has_lower and has_upper
            if not mixed_case:
                message = "Password must contain upper and lower case letters."
        elif policy == 'Mixed case and numeric':
            mixed_numeric_case = has_lower and has_upper and has_numeric
            if not mixed_numeric_case:
                message = "Password must contain upper, lower case, uppercase and numeric values."
        elif policy == 'Mixed case, numeric and special characters':
            mixed_numeric_special_case = has_lower and has_upper and has_numeric and has_special
            if not mixed_numeric_special_case:
                message = "Password must contain atleast one upper and lower case letter, numeric and special characters."
        else:
            # Any characters
            pass
    return message
