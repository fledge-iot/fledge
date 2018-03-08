
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" FogLAMP user entity class with CRUD operations to Storage layer

"""

#  import storage, payload builder

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

    class objects:

        _storage = []
        _max_id = 0

        @classmethod
        def create_admin(cls):
            cls.create("admin", "foglamp", is_admin=True)
            cls.create("admin2", "foglamp2", is_admin=True)

        @classmethod
        def create(cls, username, password, is_admin=False):
            cls._max_id += 1
            cls._storage.append(User(cls._max_id, username, password, is_admin))

        @classmethod
        def delete(cls, user_id=None, username=None):
            if not user_id and not username:
                raise ValueError("Either user id or name is required")

            if user_id and username:
                raise ValueError("Only one of user id or name is required")

            if user_id == 1 or username == "foglamp":
                raise ValueError("Admin user can not be deleted")

            cls.get(uid=user_id, username=username)
            # remove from storage
            pass

        # utility
        @classmethod
        def all(cls):
            return cls._storage

        @classmethod
        def filter(cls, **kwargs):
            users = cls._storage
            for k, v in kwargs.items():
                if v:
                    users = [u for u in users if getattr(u, k, None) == v]
            return users

        @classmethod
        def get(cls, uid=None, username=None):
            users = cls.filter(uid=uid, username=username)
            if len(users) == 0:
                raise User.DoesNotExist
            return users[0]
