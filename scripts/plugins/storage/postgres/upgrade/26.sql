INSERT INTO scheduled_processes ( name, script ) VALUES ( 'south_c',   '["services/south_c"]' ) ON CONFLICT DO NOTHING;
