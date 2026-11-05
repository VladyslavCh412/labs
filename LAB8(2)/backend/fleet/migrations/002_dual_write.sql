-- Stage 2: old writers updating plate are mirrored to the new field.
-- New writers in FleetRepository explicitly update BOTH fields at this stage.
CREATE TRIGGER IF NOT EXISTS trg_plate_to_registration
AFTER UPDATE OF plate ON vehicles
BEGIN
    UPDATE vehicles SET registration_number=NEW.plate WHERE id=NEW.id;
END;
CREATE TRIGGER IF NOT EXISTS trg_new_vehicle_registration
AFTER INSERT ON vehicles
WHEN NEW.registration_number IS NULL
BEGIN
    UPDATE vehicles SET registration_number=NEW.plate WHERE id=NEW.id;
END;
