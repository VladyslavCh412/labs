-- Phase 1: expand, old column remains readable.
ALTER TABLE vehicles ADD COLUMN plate_normalized TEXT;
-- Application dual-writes plate and plate_normalized during migration.
