-- Additive feature migration, independent of LR5's four rename stages.
CREATE TABLE IF NOT EXISTS vehicle_usage (
    vehicle_id TEXT PRIMARY KEY,
    mileage_km INTEGER NOT NULL DEFAULT 0 CHECK (mileage_km >= 0),
    active_trip_id TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS command_receipts (
    command_id TEXT PRIMARY KEY,
    request_json TEXT NOT NULL,
    response_json TEXT NOT NULL
);
