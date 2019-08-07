# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# NOTE: When multiple exceptions then enable below and add new exceptions in same list
# __all__ = ('PackageError')


class PackageError(RuntimeError):
    pass
