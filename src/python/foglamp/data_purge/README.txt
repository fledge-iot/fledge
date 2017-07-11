General Description: FOGL-200 is the responsibility for the purge process, which seats somewhere
between scheduler (calls FOGL-200), and the database layer (recieves requests from FOGL-200)
Link: https://docs.google.com/document/d/1GdMTerNq_-XQuAY0FJNQm09nbYQSjZudKJhY8x5Dq8c/

Right now, the code is missing the following piecies:
- Scheduler --> was replaced by a "main" in sqlalchemy_purge.py that calls the purge process, and returns
    how long to wait until the next purge iteration
- Config Information --> A table (or file) that provides information regarding the purge process, such how far
    back to delete, and when was the last time  Pi System received data. To resolve this problem, there currently
    exists a config.json file, which contains a json object with that information.
- logs table --> A table, or file providing vital information regarding the purge process. Again, to resolve the issue,
    there now is a json file, containing json objects with the needed information


Files:
    - config.json: JSON object with configuration information
        - age
        - retainUnsent
        - enabled
        - lastID
        - wait
        - lastConnection
    - logs.json: A JSON object of objects containing information regarding the purge process. Each object
        is keyed by the start time
        - rowsRemoved
        - complete
        - failedRemovals
        - unsentRowsRemoved
        - startTime
        - rowsRemaining
    - sqlalchemy_insert.py: TEMPORARY file that does INSERTS against database, this is used as a testing tool
      for purces processing
    - sqlalchemy_purge.py: File containing purge script, as well as some extra methods to support reading of configs,
      and writting to logs.
    - tests_data_purge.py: A set of pytest cases that run in parallel to the code, making sure values being sent to
      config and logs files are valid. 