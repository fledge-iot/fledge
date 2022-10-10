"""
Extract the disk usage  percentage and print it if the percentage
is greater than or equal to a value passed in.
The script takes as input the output of the GET /fledge/health/logging
or GET /fledge/health/storage API call
"""
import json
import sys

if __name__ == '__main__':
    json = json.loads(sys.stdin.readline())
    item = json["disk"]
    usage=item["usage"]
    if usage >= int(sys.argv[1]):
         print(usage)
