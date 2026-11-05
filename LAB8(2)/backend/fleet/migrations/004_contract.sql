-- Stage 4: only after all consumers switch to registration_number.
DROP TRIGGER IF EXISTS trg_plate_to_registration;
DROP TRIGGER IF EXISTS trg_new_vehicle_registration;
ALTER TABLE vehicles DROP COLUMN plate;
