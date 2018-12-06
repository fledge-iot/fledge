DELETE FROM foglamp.statistics WHERE key IN (
    'NORTH_READINGS_TO_PI',
    'NORTH_STATISTICS_TO_PI',
    'NORTH_READINGS_TO_HTTP',
    'North Readings to PI',
    'North Statistics to PI',
    'North Readings to OCS'
    ) AND value = 0;
