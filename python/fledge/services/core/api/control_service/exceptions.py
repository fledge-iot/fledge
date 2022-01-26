# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2021 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__all__ = ('DuplicateNameError', 'NameNotFoundError')


class DuplicateNameError(RuntimeError):
    pass


class NameNotFoundError(ValueError):
    pass
