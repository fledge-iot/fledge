"""Environment"""
import os

class Env(object):
    connection_string = None
    """Connection string to primary database"""

def __init__():
    cs = os.environ.get('FOGLAMP_DB')

    if cs is None:
        # See http://docs.sqlalchemy.org/en/latest/core/engines.html
        cs = 'postgresql://postgres:postgres@localhost:5432/foglamp'

    Env.connection_string = cs

__init__()


