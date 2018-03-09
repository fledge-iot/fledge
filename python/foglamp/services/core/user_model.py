
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" FogLAMP user entity class with CRUD operations to Storage layer

"""
import uuid
import hashlib

from foglamp.services.core import connect
from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.common.storage_client.exceptions import StorageServerError

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


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
        _storage = []

        @classmethod
        # TODO: remove hard-coded '2' role_id
        def create(cls, username, password, is_admin=2):
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
        def hash_password(cls, password):
            # uuid is used to generate a random number
            salt = uuid.uuid4().hex
            return hashlib.sha256(salt.encode() + password.encode()).hexdigest() + ':' + salt

        @classmethod
        def check_password(cls, hashed_password, user_password):
            password, salt = hashed_password.split(':')
            return password == hashlib.sha256(salt.encode() + user_password.encode()).hexdigest()
