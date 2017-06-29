General Description: FOGL-200 is the responsibility for the purge process, which seats somewhere
between schedualer (calls FOGL-200), and the database layer (recieves requests from FOGL-200)
Link: https://docs.google.com/document/d/1GdMTerNq_-XQuAY0FJNQm09nbYQSjZudKJhY8x5Dq8c/

Files:
    - __init__.py: Contains global variables that can be used throughout the directory. In this case,
        the file contaisn connection information, config/log file names, and table information. ]
        Please note that the __init__.py currently has "default" information for connecting to db
         node, and should be updated appropriately if connection fails.

    - sqlalchemy_insert.py: An example of INSERTS being done with SQLAlchemy. This file exists as a tool to
        show how the purge process will be done.

    - sqlalchemy_purge.py: The file contains more information that there would need to be, but shows how
        puring would be done against the database, based on a json object containning configuration information.
        The results of the pruge process are also logged in a JSON object.

How to run:
    A user trying this piece of code should first run INSERTS (sqlalchemy_insert.py) for a few moments before
    beginning the purge process (sqlalchemy_purge.py). Once the purge process has began, the user can feel free
    to begin playing with the config.json. Finally, logged information regarding puring can be seen in logs.json.
    