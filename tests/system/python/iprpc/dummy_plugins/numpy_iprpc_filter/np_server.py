# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Derived class of server functions for Numpy operations

    take a stream of assets which are raw acceleration values, process them, and return
    a stream of assets representing the results.

"""


__author__ = "Deepanshu Yadav"
__copyright__ = "Copyright (c) 2020 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

import logging

import numpy as np

from fledge.common import logger, iprpc


_LOGGER = logger.setup(__name__, level=logging.INFO)


class NPServer(iprpc.InterProcessRPC):
    """ Class for offloading numpy/scipy operations from filter plugin to a separate process
    """
    def __init__(self, service_name):
        """ Initialize numpy/scipy offloading server
        Args:
            service_name: name of the server
        Returns:
        Raises:
        """
        super().__init__()  # initialize rpc server

    def rms(self, input_array):
        """
        Root mean square of the input array.
        Args:
            input_array: Input numpy array
        Returns:
            root mean square of the input array.
        """
        input_array_np = np.array(input_array)
        return np.sqrt(np.mean(np.square(input_array_np)))

    def plugin_shutdown(self):
        """ Shutdown numpy/scipy offloading server
        Args:
        Returns:
        Raises:
            SystemExit
        """
        _LOGGER.info("PLUGIN SHUTDOWN")
        raise SystemExit


if __name__ == "__main__":
    _LOGGER.error("SERVING...np functions")
    rpc = NPServer('np service')
    rpc.serve()
