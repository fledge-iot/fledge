delete from foglamp.statistics_history;

update statistics set value = 1234, previous_value = 4567;

\set new_history_ts now()::timestamp(0) - 'interval \'20 minute\''
insert into statistics_history (key, history_ts, value, ts) values ( 'BUFFERED', :new_history_ts, 10, now() );
insert into statistics_history (key, history_ts, value, ts) values ( 'SENT', :new_history_ts, 11, now() );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSENT', :new_history_ts, 12, now() );
insert into statistics_history (key, history_ts, value, ts) values ( 'PURGED', :new_history_ts, 13, now() );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSNPURGED', :new_history_ts, 14, now() );
insert into statistics_history (key, history_ts, value, ts) values ( 'DISCARDED', :new_history_ts, 15, now() );

\set new_history_ts now()::timestamp(0) - 'interval \'15 minute\''
insert into statistics_history (key, history_ts, value, ts) values ( 'BUFFERED', :new_history_ts, 16, now() );
insert into statistics_history (key, history_ts, value, ts) values ( 'SENT', :new_history_ts, 17, now() );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSENT', :new_history_ts, 18, now() );
insert into statistics_history (key, history_ts, value, ts) values ( 'PURGED', :new_history_ts, 19, now() );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSNPURGED', :new_history_ts, 20, now() );
insert into statistics_history (key, history_ts, value, ts) values ( 'DISCARDED', :new_history_ts, 21, now() );

\set new_history_ts now()::timestamp(0) - 'interval \'10 minute\''
insert into statistics_history (key, history_ts, value, ts) values ( 'BUFFERED', :new_history_ts, 22, now() );
insert into statistics_history (key, history_ts, value, ts) values ( 'SENT', :new_history_ts, 23, now() );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSENT', :new_history_ts, 24, now() );
insert into statistics_history (key, history_ts, value, ts) values ( 'PURGED', :new_history_ts, 25, now() );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSNPURGED', :new_history_ts, 26, now() );
insert into statistics_history (key, history_ts, value, ts) values ( 'DISCARDED', :new_history_ts, 27, now() );

\set new_history_ts now()::timestamp(0) - 'interval \'5 minute\''
insert into statistics_history (key, history_ts, value, ts) values ( 'BUFFERED', :new_history_ts, 28, now() );
insert into statistics_history (key, history_ts, value, ts) values ( 'SENT', :new_history_ts, 29, now() );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSENT', :new_history_ts, 30, now() );
insert into statistics_history (key, history_ts, value, ts) values ( 'PURGED', :new_history_ts, 31, now() );
insert into statistics_history (key, history_ts, value, ts) values ( 'UNSNPURGED', :new_history_ts, 32, now() );
insert into statistics_history (key, history_ts, value, ts) values ( 'DISCARDED', :new_history_ts, 33, now() );
