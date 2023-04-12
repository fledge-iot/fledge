-- Drop control pipeline sequences & tables
DROP TABLE IF EXISTS fledge.control_source;
DROP SEQUENCE IF EXISTS fledge.control_source_id_seq;

DROP TABLE IF EXISTS fledge.control_destination;
DROP SEQUENCE IF EXISTS fledge.control_destination_id_seq;

DROP TABLE IF EXISTS fledge.control_filters;
DROP SEQUENCE IF EXISTS fledge.control_filters_id_seq;

DROP TABLE IF EXISTS fledge.control_pipelines;
DROP SEQUENCE IF EXISTS fledge.control_pipelines_id_seq;
