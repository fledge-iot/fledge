import argparse
from pathlib import Path
import sys
from datetime import datetime

PROJECT_ROOT = Path(__file__).absolute().parent.parent.parent.parent
sys.path.append('{}/tests/system/common'.format(PROJECT_ROOT))

from clean_pi_system import clear_pi_system_pi_web_api

retry_count = 0
data_from_pi = None
retries = 6
wait_time = 10
today = datetime.now().strftime("%Y_%m_%d")

parser = argparse.ArgumentParser(description="PI server",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--pi-host", action="store", default="pi-server",
                    help="PI Server Host Name/IP")
parser.add_argument("--pi-port", action="store", default="5460", type=int,
                    help="PI Server Port")
parser.add_argument("--pi-db", action="store", default="pi-server-db",
                    help="PI Server database")
parser.add_argument("--pi-admin", action="store", default="pi-server-uid",
                    help="PI Server user login")
parser.add_argument("--pi-passwd", action="store", default="pi-server-pwd",
                    help="PI Server user login password")
parser.add_argument("--asset-name", action="store", default="asset-name",
                    help="Asset name")
args = vars(parser.parse_args())

pi_host = args["pi_host"]
pi_admin = args["pi_admin"]
pi_passwd = args["pi_passwd"]
pi_db = args["pi_db"]
asset_name = args["asset_name"]

af_hierarchy_level = "{}_PIlabSinelvl1/PIlabSinelvl2/PIlabSinelvl3".format(today)
af_hierarchy_level_list = af_hierarchy_level.split("/")

clear_pi_system_pi_web_api(pi_host, pi_admin, pi_passwd, pi_db, af_hierarchy_level_list,
                           {asset_name: ['sinusoid', '', 'max', 'square'],
                            'e_accelerometer': ['', 'x', 'y', 'z'],
                            'e_magnetometer': ['', 'x', 'y', 'z'],
                            'e_rgb': ['', 'b', 'g', 'r'],
                            'e_weather': ['', 'altitude', 'temperature', 'pressure', 'temp_fahr'],
                            'randomwalk': ['', 'randomwalk', 'ema'],
                            'randomwalk1': ['', 'randomwalk', 'ema'],
                            'positive_sine': ['', 'description', 'event', 'rule'],
                            'negative_sine': ['', 'description', 'event', 'rule'],
                            'sin0.8': ['', 'description', 'event', 'rule']})
