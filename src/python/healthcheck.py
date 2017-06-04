import foglamp.env as env;
import foglamp.model.env as model_env;

def init_env():
    env.read()
    model_env.read()

def check_env():
    db_str = model_env.db_connection_string
    if db_str is None or len(db_str) == 0:
        raise Exception('model.env.db_connection_string is not set')

def check_all():
    init_env()
    check_env()
    print("All Good!")

if __name__ == "__main__":
    check_all()

