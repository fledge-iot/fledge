delete from foglamp.statistics_history;

update statistics set value = 1234, previous_value = 4567;

\set new_ts now() - 'interval \'20 minute\''
insert into statistics_history (key, history_ts, value, ts) values ( 'BUFFERED', :new_ts, 10, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'SENT', :new_ts, 11, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSENT', :new_ts, 12, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'PURGED', :new_ts, 13, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSNPURGED', :new_ts, 14, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'DISCARDED', :new_ts, 15, :new_ts );

\set new_ts now() - 'interval \'15 minute\''
insert into statistics_history (key, history_ts, value, ts) values ( 'BUFFERED', :new_ts, 16, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'SENT', :new_ts, 17, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSENT', :new_ts, 18, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'PURGED', :new_ts, 19, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSNPURGED', :new_ts, 20, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'DISCARDED', :new_ts, 21, :new_ts );

\set new_ts now() - 'interval \'10 minute\''
insert into statistics_history (key, history_ts, value, ts) values ( 'BUFFERED', :new_ts, 22, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'SENT', :new_ts, 23, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSENT', :new_ts, 24, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'PURGED', :new_ts, 25, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSNPURGED', :new_ts, 26, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'DISCARDED', :new_ts, 27, :new_ts );

\set new_ts now() - 'interval \'5 minute\''
insert into statistics_history (key, history_ts, value, ts) values ( 'BUFFERED', :new_ts, 28, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'SENT', :new_ts, 29, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSENT', :new_ts, 30, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'PURGED', :new_ts, 31, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSNPURGED', :new_ts, 32, :new_ts );
insert into statistics_history (key, history_ts, value, ts) values ( 'DISCARDED', :new_ts, 33, :new_ts );
