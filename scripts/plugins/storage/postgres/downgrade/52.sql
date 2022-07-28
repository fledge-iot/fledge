--Remove deprecated_ts column from asset_tracker table
ALTER TABLE fledge.asset_tracker DROP COLUMN IF EXISTS deprecated_ts;