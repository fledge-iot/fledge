-- Remove asset_tracker sequence, index and table
DROP SEQUENCE IF EXISTS fledge.asset_tracker_id_seq;
DROP TABLE IF EXISTS fledge.asset_tracker;
DROP INDEX IF EXISTS fledge.asset_tracker_ix1;
DROP INDEX IF EXISTS fledge.asset_tracker_ix2;
