-- Add new column name 'deprecated_ts' for asset_tracker

ALTER TABLE fledge.asset_tracker ADD COLUMN deprecated_ts timestamp(6) with time zone;
