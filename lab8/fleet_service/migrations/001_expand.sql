-- Stage 1: old code still SELECTs/writes plate.
ALTER TABLE vehicles ADD COLUMN registration_number TEXT;
UPDATE vehicles SET registration_number = plate WHERE registration_number IS NULL;
