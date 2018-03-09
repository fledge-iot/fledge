
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

    def match_password(self, password):
        if password != self.password:
            raise User.PasswordDoesNotMatch

    class DoesNotExist(BaseException):
        pass

    class UserAlreadyExists(BaseException):
        pass

    class PasswordDoesNotMatch(BaseException):
        pass

    class Objects:

        @classmethod
        def roles(cls):
            storage_client = connect.get_storage()
            result = storage_client.query_tbl('roles')
            return result

        @classmethod
        # TODO: remove hard-coded '2' role_id
        def create(cls, username, password, is_admin=2):
            """
            Args:
                username: user name
                password: Password must contain at least one digit, one lowercase, one uppercase,
                          one special symbol and length is exactly of 8 characters
                is_admin: Role (by default normal 'user' role whose id is 2)

            Returns:
                   user json info
            """
            storage_client = connect.get_storage()
            payload = PayloadBuilder().INSERT(uname=username, pwd=cls.hash_password(password),
                                              role_id=is_admin).payload()
            result = {}
            try:
                result = storage_client.insert_into_tbl("users", payload)
            except StorageServerError as ex:
                err_response = ex.error
                if not err_response["retryable"]:
                    raise ValueError(err_response['message'])
            return result

        @classmethod
        def delete(cls, user_id=None):
            """
            Args:
                user_id: user id to delete

            Returns:
                  json response
            """
            # TODO: any admin role?
            if int(user_id) == 1:
                raise ValueError("Admin user can not be deleted")

            payload = PayloadBuilder().DELETE("users").WHERE(['id', '=', user_id]).payload()
            storage_client = connect.get_storage()
            result = {}
            try:
                result = storage_client.delete_from_tbl("users", payload)
            except StorageServerError as ex:
                err_response = ex.error
                if not err_response["retryable"]:
                    raise ValueError(err_response['message'])
            return result

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

            payload = PayloadBuilder().SELECT("id", "uname", "role_id").WHERE(['1', '=', '1'])
            if user_id is not None:
                payload.AND_WHERE(['id', '=', user_id])

            if user_name is not None:
                payload.AND_WHERE(['uname', '=', user_name])

            _and_where_payload = payload.chain_payload()

            storage_client = connect.get_storage()
            payload = PayloadBuilder(_and_where_payload).payload()
            result = storage_client.query_tbl_with_payload('users', payload)
            return result['rows']

        @classmethod
        def get(cls, uid=None, username=None):
            users = cls.filter(uid=uid, username=username)
            if len(users) == 0:
                raise User.DoesNotExist
            return users[0]

        @classmethod
        def login(cls, username, password):
            """
            Args:
                username: username
                password: password

            Returns:
                  user json info with jwt token and expiration token

            """
            payload = PayloadBuilder().SELECT("pwd", "id").WHERE(['uname', '=', username]).payload()
            storage_client = connect.get_storage()
            result = storage_client.query_tbl_with_payload('users', payload)
            if result['rows']:
                # Validate password
                is_valid_pwd = cls.check_password(result['rows'][0]['pwd'], password)
                if is_valid_pwd:
                    # fetch user info
                    u = cls.get(uid=result['rows'][0]['id'])
                    if u['id']:
                        # jwt token
                        p = {'uid': u['id'],
                             'exp': str(datetime.now() + timedelta(seconds=JWT_EXP_DELTA_SECONDS))}
                        jwt_token = jwt.encode(p, JWT_SECRET, JWT_ALGORITHM)
                        payload = PayloadBuilder().INSERT(user_id=p['uid'], token=jwt_token.decode("utf-8"),
                                                          token_expiration=p['exp']).payload()

                        # Insert token, uid, expiration into user_login table
                        try:
                            # TODO: allow multiple user login?
                            r = storage_client.insert_into_tbl("user_logins", payload)
                            d = {"token": jwt_token.decode("utf-8"), "expiration": p['exp']}
                            if r['rows_affected']:
                                result = cls.get(username=username)
                                result.update(d)
                        except StorageServerError as ex:
                            err_response = ex.error
                            if not err_response["retryable"]:
                                raise ValueError(err_response['message'])
                else:
                    raise User.PasswordDoesNotMatch('Username and Password do not match')
            else:
                raise User.DoesNotExist('User does not exist')
            return result

        @classmethod
        def hash_password(cls, password):
            # uuid is used to generate a random number
            salt = uuid.uuid4().hex
            return hashlib.sha256(salt.encode() + password.encode()).hexdigest() + ':' + salt

        @classmethod
        def check_password(cls, hashed_password, user_password):
            password, salt = hashed_password.split(':')
            return password == hashlib.sha256(salt.encode() + user_password.encode()).hexdigest()
