"""
Extract the audit entries that have a timestamp that starts with
the timestamp string passed in as an argument. The output is
the details/name tag of the audit entry.

The script takes as input the output of the GET /fledge/audit API call
"""

import json
import sys

if __name__ == '__main__':
   json = json.loads(sys.stdin.readline())
   ts = sys.argv[1]
   for audit in json["audit"]:
       if audit["timestamp"].startswith(ts):
           print(audit["details"]["name"])
