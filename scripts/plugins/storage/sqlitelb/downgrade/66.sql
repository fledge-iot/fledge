-- From: http://www.sqlite.org/faq.html:
--    SQLite has limited ALTER TABLE support that you can use to change type of column.
--    If you want to change the type of any column you will have to recreate the table.
--    You can save existing data to a temporary table and then drop the old table
--    Now, create the new table, then copy the data back in from the temporary table


-- Remove priority column in fledge.scheduled_processes

-- Rename existing table into a temp one
ALTER TABLE fledge.scheduled_processes RENAME TO scheduled_processes_old;

-- Create new table
CREATE TABLE fledge.scheduled_processes (
             name        character varying(255)  NOT NULL,             -- Name of the process
             script      JSON,                                         -- Full path of the process
             CONSTRAINT scheduled_processes_pkey PRIMARY KEY ( name ) );

-- Copy data
INSERT INTO fledge.scheduled_processes ( name, script) SELECT name, script FROM fledge.scheduled_processes_old;

-- Remote old table
DROP TABLE IF EXISTS fledge.scheduled_processes_old;
