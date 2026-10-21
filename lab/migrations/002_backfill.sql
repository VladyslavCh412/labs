-- Phase 2: populate new column; still compatible with old application.
UPDATE vehicles SET plate_normalized = UPPER(REPLACE(plate, ' ', '')) WHERE plate_normalized IS NULL;
-- Switch reads to plate_normalized after all instances updated.
