"""
Utility to extract the names of services in a particular state given the output of
the API call GET /fledge/services
"""

import json
import sys

if __name__ == '__main__':
    json = json.loads(sys.stdin.readline())
    state = sys.argv[1]
    for service in json["services"]:
         if service["status"] == state:
              print(service["name"])
