--Remove data column from asset_tracker table
ALTER TABLE fledge.asset_tracker DROP COLUMN IF EXISTS data;
