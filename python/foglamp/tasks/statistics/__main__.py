#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Statistics history process starter"""

import asyncio
from foglamp.tasks.statistics.statistics_history import StatisticsHistory
from foglamp.common import logger

__author__ = "Terris Linenbach, Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

if __name__ == '__main__':
    _logger = logger.setup("StatisticsHistory")
    statistics_history_process = StatisticsHistory()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(statistics_history_process.run())
