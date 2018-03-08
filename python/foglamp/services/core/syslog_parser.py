# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from pyparsing import Word, alphas, Combine, nums, string, Regex
from time import strftime

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_SYSLOG_FILE = '/var/log/syslog'


class SyslogParser(object):

    def __init__(self):

        ints = Word(nums)

        # timestamp
        month = Word(string.ascii_uppercase, string.ascii_lowercase, exact=3)
        day = ints
        hour = Combine(ints + ":" + ints + ":" + ints)
        timestamp = month + day + hour

        # hostname
        hostname = Word(alphas + nums + "_" + "-" + ".")
        # appname
        appname = Word(" FogLAMP" + alphas + " ")
        # message
        message = Regex(".*")
        # pattern build
        self.__pattern = timestamp + hostname + appname + message

    def parse(self, line):
        parsed = self.__pattern.parseString(line)

        payload = dict()
        payload["timestamp"] = strftime("%Y-%m-%d %H:%M:%S")
        payload["hostname"] = parsed[3]
        payload["appname"] = parsed[4]
        # get [PID] LEVEL: msg from parsed[5]
        payload["message"] = parsed[5]

        return payload


def main(filter_by=None):
    parser = SyslogParser()
    logs = []

    with open(_SYSLOG_FILE) as sys_log_file:
        for line in sys_log_file:
            fields = parser.parse(line)
            if filter_by is not None:
                if filter_by in fields["appname"]:
                    logs.append(fields)
            else:
                logs.append(fields)
    return logs
