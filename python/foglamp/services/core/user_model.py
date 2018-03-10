
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
        def create(cls, username, password, is_admin=False):
            """
            Args:
                username: user name
                password: Password must contain at least one digit, one lowercase, one uppercase,
                          one special symbol and length is exactly of 8 characters
                is_admin: Role (by default normal 'user' role whose id is 2)

            Returns:
                   user json info
            """

            # be careful
            role_id = 2 if is_admin is False else 1

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
        def delete(cls, user_id=None):
            """
            Args:
                user_id: user id to delete

            Returns:
                  json response
            """

            # either keep 1 admin user or just reserve id:1 for superuser
            if int(user_id) == 1:
                raise ValueError("Admin user can not be deleted")

            storage_client = connect.get_storage()
            try:
                # first delete the active login references
                payload = PayloadBuilder().DELETE("user_logins").WHERE(['user_id', '=', user_id]).payload()
                res_del_user_active_login_ref = storage_client.delete_from_tbl("user_logins", payload)

                payload = PayloadBuilder().DELETE("users").WHERE(['id', '=', user_id]).payload()
                res_del_user = storage_client.delete_from_tbl("users", payload)
            except StorageServerError as ex:
                if ex.error["retryable"]:
                    pass  # retry INSERT
                raise ValueError(ex.error['message'])
            return res_del_user

        # utility
        @classmethod
        def all(cls):
            storage_client = connect.get_storage()
            payload = PayloadBuilder().SELECT("id", "uname", "role_id").payload()
            result = storage_client.query_tbl_with_payload('users', payload)
            return result['rows']

        @classmethod
        def filter(cls, **kwargs):
            user_id = kwargs['uid']
            user_name = kwargs['username']

            q = PayloadBuilder().SELECT("id", "uname", "role_id").WHERE(['1', '=', '1'])

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
                raise User.DoesNotExist
            return users[0]

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

            user_payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return user_payload["uid"]

        @classmethod
        def login(cls, username, password):
            """
            Args:
                username: username
                password: password

            Returns:
                  return token

            """
            payload = PayloadBuilder().SELECT("pwd", "id").WHERE(['uname', '=', username]).payload()
            storage_client = connect.get_storage()

            result = storage_client.query_tbl_with_payload('users', payload)

            if len(result['rows']) == 0:
                raise User.DoesNotExist('User does not exist')

            found_user = result['rows'][0]

            is_valid_pwd = cls.check_password(found_user['pwd'], password)

            if not is_valid_pwd:
                raise User.PasswordDoesNotMatch('Username or Password do not match')

            # fetch user info
            exp = datetime.now() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
            # jwt token
            p = {'uid': found_user['id'],
                 'exp': exp
                 }

            jwt_token = jwt.encode(p, JWT_SECRET, JWT_ALGORITHM).decode("utf-8")

            payload = PayloadBuilder().INSERT(user_id=p['uid'], token=jwt_token,
                                              token_expiration=str(exp)).payload()

            # Insert token, uid, expiration into user_login table
            try:
                storage_client.insert_into_tbl("user_logins", payload)
            except StorageServerError as ex:
                if ex.error["retryable"]:
                    pass  # retry INSERT
                raise ValueError(ex.error['message'])

            return jwt_token

        @classmethod
        def hash_password(cls, password):
            # uuid is used to generate a random number
            salt = uuid.uuid4().hex
            return hashlib.sha256(salt.encode() + password.encode()).hexdigest() + ':' + salt

        @classmethod
        def check_password(cls, hashed_password, user_password):
            password, salt = hashed_password.split(':')
            return password == hashlib.sha256(salt.encode() + user_password.encode()).hexdigest()
