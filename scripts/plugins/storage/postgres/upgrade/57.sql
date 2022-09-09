-- Add new column name 'data' for asset_tracker

ALTER TABLE fledge.asset_tracker ADD COLUMN data JSONB DEFAULT '{}'::jsonb;
