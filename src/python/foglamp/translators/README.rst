OMF Translator
==============

Starting the OMF Translator
---------------------------
- it could be executed as is without parameters :
    python -m foglamp.translators.omf_translator

Note
----
- OMF information available at - http://omf-docs.readthedocs.io/en/v1.0/Data_Msg_Sample.html#data-example

- logs : tail -f /var/log/syslog | grep omf_translator

- block_size identifies the number of rows to send for each execution

- it uses foglamp.streams to track the information to send

- Temporary/Useful SQL code for development testing:

    - the configuration table should be updated using for example (the row will be recreated) to being able the create a new producerToken  :
        - DELETE FROM foglamp.configuration WHERE key='OMF_TRANS ';

    - set the staring point using :
        - identify the correct id, using for example :
            SELECT MAX(ID) FROM foglamp.readings;

        - update last_object properly :
            - UPDATE foglamp.streams SET last_object=0, ts=now() WHERE id=1;

    SELECT MAX(ID) FROM foglamp.readings;

    UPDATE foglamp.streams SET last_object=0, ts=now() WHERE id=1;

    SELECT * FROM foglamp.streams;

    SELECT * FROM foglamp.readings WHERE id > 0 ORDER by id;
    SELECT * FROM foglamp.readings WHERE id > 0 ORDER by USER_ts;

    SELECT * FROM foglamp.readings WHERE id > 0 and id <= 0+50 and asset_code like '%gyrosc%' ORDER by USER_ts;

    SELECT * FROM foglamp.readings WHERE id > 0 and id <= 0+50 and asset_code  like '%mag%' ORDER by USER_ts;
