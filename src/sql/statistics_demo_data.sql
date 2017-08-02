delete from foglamp.statistics_history;

update statistics set value = 1234, previous_value = 4567;

\set new_ts now() - 'interval \'20 minute\''
insert into statistics_history (key, history_ts, value, ts) values ( 'READINGS', :new_ts, 91, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'BUFFERED', :new_ts, 110, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'SENT', :new_ts, 111, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSENT', :new_ts, 112, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'PURGED', :new_ts, 113, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSNPURGED', :new_ts, 114, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'DISCARDED', :new_ts, 115, :new_ts );

\set new_ts now() - 'interval \'15 minute\''
insert into statistics_history (key, history_ts, value, ts) values ( 'READINGS', :new_ts, 292, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'BUFFERED', :new_ts, 216, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'SENT', :new_ts, 217, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSENT', :new_ts, 218, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'PURGED', :new_ts, 219, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSNPURGED', :new_ts, 220, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'DISCARDED', :new_ts, 221, :new_ts );

\set new_ts now() - 'interval \'10 minute\''
insert into statistics_history (key, history_ts, value, ts) values ( 'READINGS', :new_ts, 393, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'BUFFERED', :new_ts, 322, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'SENT', :new_ts, 323, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSENT', :new_ts, 324, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'PURGED', :new_ts, 325, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSNPURGED', :new_ts, 326, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'DISCARDED', :new_ts, 327, :new_ts );

\set new_ts now() - 'interval \'5 minute\''
insert into statistics_history (key, history_ts, value, ts) values ( 'READINGS', :new_ts, 494, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'BUFFERED', :new_ts, 428, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'SENT', :new_ts, 429, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSENT', :new_ts, 430, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'PURGED', :new_ts, 431, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSNPURGED', :new_ts, 432, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'DISCARDED', :new_ts, 433, :new_ts );
