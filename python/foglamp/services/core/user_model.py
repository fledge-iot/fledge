
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
from foglamp.common.configuration_manager import ConfigurationManager

__author__ = "Praveen Garg, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# TODO: move to common  / config
JWT_SECRET = 'f0gl@mp'
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 30*60  # 30 minutes
ERROR_MSG = 'Something went wrong'
USED_PASSWORD_HISTORY_COUNT = 3


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

    class PasswordAlreadyUsed(Exception):
        pass

    class PasswordExpired(Exception):
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
                raise ValueError(ERROR_MSG)
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

                payload = PayloadBuilder().SET(enabled="f").WHERE(['id', '=', user_id]).AND_WHERE(['enabled', '=', 't']).payload()
                result = storage_client.update_tbl("users", payload)
            except StorageServerError as ex:
                if ex.error["retryable"]:
                    pass  # retry INSERT
                raise ValueError(ERROR_MSG)
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

            storage_client = connect.get_storage()

            hashed_pwd = None
            pwd_history_list = []
            if 'password' in user_data:
                if len(user_data['password']):
                    hashed_pwd = cls.hash_password(user_data['password'])
                    current_datetime = datetime.now()
                    kwargs.update({"pwd": hashed_pwd, "pwd_last_changed": str(current_datetime)})

                    # get password history list
                    pwd_history_list = cls._get_password_history(storage_client, user_id, user_data)
            try:
                payload = PayloadBuilder().SET(**kwargs).WHERE(['id', '=', user_id]).AND_WHERE(
                    ['enabled', '=', 't']).payload()
                result = storage_client.update_tbl("users", payload)
                if result['rows_affected']:
                    # FIXME: FOGL-1226 active session delete only in case of role_id and password updation

                    # delete all active sessions
                    cls.delete_user_tokens(user_id)

                    if 'password' in user_data:
                        # insert pwd history and delete oldest pwd if USED_PASSWORD_HISTORY_COUNT exceeds
                        cls._insert_pwd_history_with_oldest_pwd_deletion_if_count_exceeds(storage_client, user_id, hashed_pwd, pwd_history_list)

                    return True
            except StorageServerError as ex:
                if ex.error["retryable"]:
                    pass  # retry UPDATE
                raise ValueError(ERROR_MSG)
            except Exception:
                raise

        @classmethod
        def is_user_exists(cls, username, password):
            payload = PayloadBuilder().SELECT("id", "pwd").WHERE(['uname', '=', username]).AND_WHERE(['enabled', '=', 't']).payload()
            storage_client = connect.get_storage()
            result = storage_client.query_tbl_with_payload('users', payload)
            if len(result['rows']) == 0:
                return None

            found_user = result['rows'][0]
            is_valid_pwd = cls.check_password(found_user['pwd'], str(password))
            return result['rows'][0]['id'] if is_valid_pwd else None

        # utility
        @classmethod
        def all(cls):
            storage_client = connect.get_storage()
            payload = PayloadBuilder().SELECT("id", "uname", "role_id").WHERE(['enabled', '=', 't']).payload()
            result = storage_client.query_tbl_with_payload('users', payload)
            return result['rows']

        @classmethod
        def filter(cls, **kwargs):
            user_id = kwargs['uid']
            user_name = kwargs['username']

            q = PayloadBuilder().SELECT("id", "uname", "role_id").WHERE(['enabled', '=', 't'])

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
        async def login(cls, username, password, host):
            """
            Args:
                username: username
                password: password
                host:     IP address
            Returns:
                  return token

            """
            # check password change configuration
            storage_client = connect.get_storage()
            cfg_mgr = ConfigurationManager(storage_client)
            category_item = await cfg_mgr.get_category_item('rest_api', 'passwordChange')
            age = int(category_item['value'])

            # get user info on the basis of username
            payload = PayloadBuilder().SELECT("pwd", "id", "role_id", "pwd_last_changed").WHERE(['uname', '=', username]).\
                AND_WHERE(['enabled', '=', 't']).payload()
            result = storage_client.query_tbl_with_payload('users', payload)
            if len(result['rows']) == 0:
                raise User.DoesNotExist('User does not exist')

            found_user = result['rows'][0]

            # check age of password
            t1 = datetime.now()
            t2 = datetime.strptime(found_user['pwd_last_changed'][:-6], "%Y-%m-%d %H:%M:%S.%f")  # ignore timezone
            delta = t1 - t2
            if age == 0:
                # user will not be forced to change their password.
                pass
            elif age <= delta.days:
                # user will be forced to change their password.
                raise User.PasswordExpired(found_user['id'])

            # validate password
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
                raise ValueError(ERROR_MSG)

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
                raise ValueError(ERROR_MSG)

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
                raise ValueError(ERROR_MSG)

            return res

        @classmethod
        def delete_all_user_tokens(cls):
            storage_client = connect.get_storage()
            storage_client.delete_from_tbl("user_logins")

        @classmethod
        def hash_password(cls, password):
            # uuid is used to generate a random number
            salt = uuid.uuid4().hex
            return hashlib.sha256(salt.encode() + password.encode()).hexdigest() + ':' + salt

        @classmethod
        def check_password(cls, hashed_password, user_password):
            password, salt = hashed_password.split(':')
            return password == hashlib.sha256(salt.encode() + user_password.encode()).hexdigest()

        @classmethod
        def _get_password_history(cls, storage_client, user_id, user_data):
            pwd_history_list = []
            payload = PayloadBuilder().WHERE(['user_id', '=', user_id]).payload()
            result = storage_client.query_tbl_with_payload("user_pwd_history", payload)
            for row in result['rows']:
                if cls.check_password(row['pwd'], user_data['password']):
                    raise User.PasswordAlreadyUsed
                pwd_history_list.append(row['pwd'])
            return pwd_history_list

        @classmethod
        def _insert_pwd_history_with_oldest_pwd_deletion_if_count_exceeds(cls, storage_client, user_id, hashed_pwd, pwd_history_list):
            # delete oldest password for user, as storage result in sorted order so its safe to delete its last index from pwd_history_list
            if len(pwd_history_list) >= USED_PASSWORD_HISTORY_COUNT:
                payload = PayloadBuilder().WHERE(['user_id', '=', user_id]).AND_WHERE(
                    ['pwd', '=', pwd_history_list[-1]]).payload()
                storage_client.delete_from_tbl("user_pwd_history", payload)

            # insert into password history table
            payload = PayloadBuilder().INSERT(user_id=user_id, pwd=hashed_pwd).payload()
            storage_client.insert_into_tbl("user_pwd_history", payload)
