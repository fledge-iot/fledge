# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from foglamp import logger

from foglamp.storage.payload_builder import PayloadBuilder
from foglamp.storage.storage import Storage


__author__ = "Ashwin Gopalakrishnan, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_logger = logger.setup(__name__)


class Statistics(object):
    """ Statistics interface of the API to gather the available statistics counters,
        calculate the deltas from the previous run of the process and write the deltas
        to a statistics record.
    """

    def __init__(self, storage):
        if not isinstance(storage, Storage):
            raise TypeError('Must be a valid Storage object')

        self._storage = storage

    async def update(self, key, value_increment):
        """ UPDATE the value column only of a statistics row based on key

        Args:
            key: statistics key value (required)
            value_increment: amount to increment the value by

        Returns:
            None
        """
        try:
            payload = PayloadBuilder()\
                .WHERE(["key", "=", key])\
                .EXPR(["value", "+", value_increment])\
                .payload()
            self._storage.update_tbl("statistics", payload)
        except:
            _logger.exception(
                'Unable to update statistics value based on statistics_key %s and value_increment %s'
                , key, value_increment)
            raise


# TODO: FOGL-484 Move below commented code to tests directory
# async def _main():
#     _storage = Storage(core_management_host="0.0.0.0", core_management_port=33881)
#
#     _stats = Statistics(_storage)
#     await _stats.update(key='READINGS', value_increment=10)
#
#
# if __name__ == '__main__':
#     import asyncio
#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(_main())
