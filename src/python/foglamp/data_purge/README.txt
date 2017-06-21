General Description: FOGL-200 is the responsibility for purge processing, which I began to look in the past few days.
The work done in this in this the data_purge configuration (thus far) is based on the simple purge process
(https://docs.google.com/document/d/1GdMTerNq_-XQuAY0FJNQm09nbYQSjZudKJhY8x5Dq8c/edit#).

Code Description:
1. Before testing Inserts there exists a creation of table and continuous inserts
2. Once the purging process is called (currently needs to initiated), it looks at the config file (config.yaml)
    Since the config file is called each time, a user can update it on the fly
3. Based on the config.yaml files the purge process prepares the DELETE statement, and COUNT
4. It then sends the respective queries to the the database node to be executed.
5. The database node returns the following
    - Number of rows less than or equal to the WHERE condition for delete (prior to DELETE execution)
    - Number of rows less than or equal to the WHERE condition for delete (after DELETE execution) - Expect 0
    - Number of rows more than or equal to the WHERE condition for delete (after DELETE execution)
6. Provided these 3 numbers, as well as current timestamp are stored in a logs file (called logs.db)
7. Finally, based on the configuration file (config.yaml) the purge process sends the schedualer how long to
    wait, until recalling it.

 Files:
 - config.yaml: configuration file
 - logs.db: Data logs
 - pg_insert.py: psycopg2 version of the INSERT process
 - pg_purge.py: psycopg2 version of the PURGE process
 - sqlalchemy_insert.py: SQLAlchemy version of the INSERT process
 - sqlalchemy_purge.py: SQLAlchemy version of the PURGE process

Review: When using psycopg2 for the INSERT process, I "hang" (meaning wait) for all other executions to finish.
Whereas with SQLAlchemy, both the  INSERT and PURGE processes can co-exist as if running on parallel threads.

Note: I'm honestly NOT trying to by dependent on SQLAlchemy, but rather trying to convey the point that it makes like easier than I had initially thought.
