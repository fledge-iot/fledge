import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).absolute().parent.parent.parent.parent
sys.path.append('{}/tests/system/common'.format(PROJECT_ROOT))

from clean_pi_system import clear_pi_system_pi_web_api

retry_count = 0
data_from_pi = None
retries = 6
wait_time = 10

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

af_hierarchy_level = "PIlab/PIlablvl1/PIlablvl2"
af_hierarchy_level_list = af_hierarchy_level.split("/")

clear_pi_system_pi_web_api(pi_host, pi_admin, pi_passwd, pi_db, af_hierarchy_level_list,
                           {asset_name: [asset_name, '']})
