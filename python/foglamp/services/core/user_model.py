
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" FogLAMP user entity class with CRUD operations to Storage layer

"""
import uuid
import hashlib

from datetime import datetime, timedelta
import jwt

from foglamp.services.core import connect
from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.common.storage_client.exceptions import StorageServerError

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# TODO: move to common  / config
JWT_SECRET = 'f0gl@mp'
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 30*60  # 30 minutes


class User:

    __slots__ = ['uid', 'username', 'password', 'is_admin']

    def __init__(self, uid, username, password, is_admin=False):
        self.uid = uid
        self.username = username
        self.password = password
        self.is_admin = is_admin

    def __repr__(self):
        template = 'User id={s.uid}: <{s.username}, is_admin={s.is_admin}>'
        return template.format(s=self)

    def __str__(self):
        return self.__repr__()

    class DoesNotExist(Exception):
        pass

    class UserAlreadyExists(Exception):
        pass

    class PasswordDoesNotMatch(Exception):
        pass

    class InvalidToken(Exception):
        pass

    class TokenExpired(Exception):
        pass

    class Objects:

        @classmethod
        def get_roles(cls):
            storage_client = connect.get_storage()
            result = storage_client.query_tbl('roles')
            return result["rows"]

        @classmethod
        def get_role_id_by_name(cls, name):
            storage_client = connect.get_storage()
            payload = PayloadBuilder().SELECT("id").WHERE(['name', '=', name]).payload()
            result = storage_client.query_tbl_with_payload('roles', payload)
            return result["rows"]

        @classmethod
        def create(cls, username, password, role_id):
            """
            Args:
                username: user name
                password: Password must contain at least one digit, one lowercase, one uppercase &
                          one special character and length of minimum 6 characters
                role_id: Role (by default normal 'user' role whose id is 2)

            Returns:
                   user json info
            """

            storage_client = connect.get_storage()
            payload = PayloadBuilder().INSERT(uname=username, pwd=cls.hash_password(password),
                                              role_id=role_id).payload()
            try:
                result = storage_client.insert_into_tbl("users", payload)
            except StorageServerError as ex:
                if ex.error["retryable"]:
                    pass  # retry INSERT
                raise ValueError(ex.error['message'])
            return result

        @classmethod
        def delete(cls, user_id):
            """
            Args:
                user_id: user id to delete

            Returns:
                  json response
            """

            # either keep 1 admin user or just reserve id:1 for superuser
            if int(user_id) == 1:
                raise ValueError("Super admin user can not be deleted")

            storage_client = connect.get_storage()
            try:
                # first delete the active login references
                cls.delete_user_tokens(user_id)

                payload = PayloadBuilder().SET(enabled="False").WHERE(['id', '=', user_id]).AND_WHERE(['enabled', '=', 'True']).payload()
                result = storage_client.update_tbl("users", payload)
            except StorageServerError as ex:
                if ex.error["retryable"]:
                    pass  # retry INSERT
                raise ValueError(ex.error['message'])
            return result

        @classmethod
        def update(cls, user_id, user_data):
            """
            Args:
                 user_id: logged user id
                 user_data: user dict

            Returns:
                  updated user info dict
            """

            kwargs = dict()
            if 'role_id' in user_data:
                kwargs.update({"role_id": user_data['role_id']})

            if 'password' in user_data:
                if len(user_data['password']):
                    hashed_pwd = cls.hash_password(user_data['password'])
                    kwargs.update({"pwd": hashed_pwd})

            payload = PayloadBuilder().SET(**kwargs).WHERE(['id', '=', user_id]).AND_WHERE(['enabled', '=', 'True']).payload()
            storage_client = connect.get_storage()
            try:
                result = storage_client.update_tbl("users", payload)
                if result['rows_affected']:
                    return True
            except StorageServerError as ex:
                if ex.error["retryable"]:
                    pass  # retry UPDATE
                raise ValueError(ex.error['message'])
            except Exception:
                raise

        # utility
        @classmethod
        def all(cls):
            storage_client = connect.get_storage()
            payload = PayloadBuilder().SELECT("id", "uname", "role_id").WHERE(['enabled', '=', 'True']).payload()
            result = storage_client.query_tbl_with_payload('users', payload)
            return result['rows']

        @classmethod
        def filter(cls, **kwargs):
            user_id = kwargs['uid']
            user_name = kwargs['username']

            q = PayloadBuilder().SELECT("id", "uname", "role_id").WHERE(['enabled', '=', 'True'])

            if user_id is not None:
                q = q.AND_WHERE(['id', '=', user_id])

            if user_name is not None:
                q = q.AND_WHERE(['uname', '=', user_name])

            storage_client = connect.get_storage()
            q_payload = PayloadBuilder(q.chain_payload()).payload()
            result = storage_client.query_tbl_with_payload('users', q_payload)
            return result['rows']

        @classmethod
        def get(cls, uid=None, username=None):
            users = cls.filter(uid=uid, username=username)
            if len(users) == 0:
                msg = ''
                if uid:
                    msg = "User with id:<{}> does not exist".format(uid)
                if username:
                    msg = "User with name:<{}> does not exist".format(username)
                if uid and username:
                    msg = "User with id:<{}> and name:<{}> does not exist".format(uid, username)

                raise User.DoesNotExist(msg)
            return users[0]

        @classmethod
        def refresh_token_expiry(cls, token):
            storage_client = connect.get_storage()
            exp = datetime.now() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
            payload = PayloadBuilder().SET(token_expiration=str(exp)).WHERE(['token', '=', token]).payload()
            storage_client.update_tbl("user_logins", payload)

        @classmethod
        def validate_token(cls, token):
            """ check existence and validity of token
                    * exists in user_logins table
                    * its not expired
            :param token:
            :return:
            """

            storage_client = connect.get_storage()
            payload = PayloadBuilder().SELECT("token_expiration").WHERE(['token', '=', token]).payload()
            result = storage_client.query_tbl_with_payload('user_logins', payload)

            if len(result['rows']) == 0:
                raise User.InvalidToken("Token appears to be invalid")

            r = result['rows'][0]
            token_expiry = r["token_expiration"][:-6]

            curr_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

            fmt = "%Y-%m-%d %H:%M:%S.%f"
            diff = datetime.strptime(token_expiry, fmt) - datetime.strptime(curr_time, fmt)

            if diff.seconds < 0:
                raise User.TokenExpired("The token has expired, login again")

            # verification of expiry set to false,
            # as we want to refresh token on each successful request
            # and extend it to keep session alive
            user_payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={'verify_exp': False})
            return user_payload["uid"]

        @classmethod
        def login(cls, username, password, host):
            """
            Args:
                username: username
                password: password
                host:     host address
            Returns:
                  return token

            """
            payload = PayloadBuilder().SELECT("pwd", "id", "role_id").WHERE(['uname', '=', username]).\
                AND_WHERE(['enabled', '=', 'True']).payload()
            storage_client = connect.get_storage()

            result = storage_client.query_tbl_with_payload('users', payload)

            if len(result['rows']) == 0:
                raise User.DoesNotExist('User does not exist')

            found_user = result['rows'][0]

            is_valid_pwd = cls.check_password(found_user['pwd'], str(password))

            if not is_valid_pwd:
                raise User.PasswordDoesNotMatch('Username or Password do not match')

            # fetch user info
            exp = datetime.now() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
            uid = found_user['id']
            p = {'uid': uid, 'exp': exp}
            jwt_token = jwt.encode(p, JWT_SECRET, JWT_ALGORITHM).decode("utf-8")

            payload = PayloadBuilder().INSERT(user_id=p['uid'], token=jwt_token,
                                              token_expiration=str(exp), ip=host).payload()

            # Insert token, uid, expiration into user_login table
            try:
                storage_client.insert_into_tbl("user_logins", payload)
            except StorageServerError as ex:
                if ex.error["retryable"]:
                    pass  # retry INSERT
                raise ValueError(ex.error['message'])

            # TODO remove hard code role id to return is_admin info
            if int(found_user['role_id']) == 1:
                return uid, jwt_token, True

            return uid, jwt_token, False

        @classmethod
        def delete_user_tokens(cls, user_id):
            storage_client = connect.get_storage()
            payload = PayloadBuilder().WHERE(['user_id', '=', user_id]).payload()
            try:
                res = storage_client.delete_from_tbl("user_logins", payload)
            except StorageServerError as ex:
                if not ex.error["retryable"]:
                    pass
                raise ValueError(ex.error['message'])

            return res

        @classmethod
        def delete_token(cls, token):
            storage_client = connect.get_storage()
            payload = PayloadBuilder().WHERE(['token', '=', token]).payload()
            try:
                res = storage_client.delete_from_tbl("user_logins", payload)
            except StorageServerError as ex:
                if not ex.error["retryable"]:
                    pass
                raise ValueError(ex.error['message'])

            return res

        @classmethod
        def hash_password(cls, password):
            # uuid is used to generate a random number
            salt = uuid.uuid4().hex
            return hashlib.sha256(salt.encode() + password.encode()).hexdigest() + ':' + salt

        @classmethod
        def check_password(cls, hashed_password, user_password):
            password, salt = hashed_password.split(':')
            return password == hashlib.sha256(salt.encode() + user_password.encode()).hexdigest()
