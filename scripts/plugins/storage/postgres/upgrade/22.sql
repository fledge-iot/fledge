CREATE INDEX readings_ix3
    ON fledge.readings USING btree (user_ts);
