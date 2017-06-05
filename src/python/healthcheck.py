import foglamp.env as env

""" checks pre-install and post-install health-check.

pre stage:
 1) foglamp/foglamp-env.yaml created successfully
 2) it consists of all required K => V pairs
 3) env variables exits and loaded properly then those specific if in required parameters in #2 can be ignored
 
post stage:
 1)
 
 each stage should have bucket levels say: red (fatal), yellow(non-fatal / warn)

"""


def init_env():
    env.load_config()


def check_env():
    db_str = env.db_connection_string
    if db_str is None or len(db_str) == 0:
        raise Exception('model.env.db_connection_string is not set')


def check_all():
    init_env()
    check_env()
    print("All Good!")

if __name__ == "__main__":
    check_all()

