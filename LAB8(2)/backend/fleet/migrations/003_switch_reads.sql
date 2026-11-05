-- Stage 3: application reads registration_number if present.
-- Validate all backfilled entries before considering the old column removable.
UPDATE vehicles SET registration_number=plate WHERE registration_number IS NULL;
CREATE INDEX IF NOT EXISTS ix_vehicle_registration ON vehicles(registration_number);
