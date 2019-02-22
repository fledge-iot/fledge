CREATE INDEX readings_ix3
    ON foglamp.readings USING btree (user_ts);
