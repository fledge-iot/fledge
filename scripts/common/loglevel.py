"""
Extract the names of services that have the current log level set
to a level passed in as an argument. The script takes as input the
output of the GET /fledge/health/logging API call
"""

import json
import sys

if __name__ == '__main__':
   level = sys.argv[1]
   json = json.loads(sys.stdin.readline())
   for service in json["levels"]:
       if service["level"] == level:
           print(service["name"])
