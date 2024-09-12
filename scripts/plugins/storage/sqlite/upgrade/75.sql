ALTER TABLE fledge.streams ADD COLUMN last_objects JSON  NOT NULL DEFAULT '{"Readings":0,"Stats":0,"Audit":0}';
