# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# NOTE: When multiple exceptions then enable below and add new exceptions in same list
# __all__ = ('PackageError')


class PackageError(RuntimeError):
    pass
