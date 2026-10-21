"""Fleet bounded context. Adapted from the LR2 Vehicle/Driver domain model.
No FastAPI, HTTP client or SQLite imports: only business invariants.
"""
from dataclasses import dataclass
from enum import Enum

class DomainError(ValueError):
    pass

class VehicleStatus(str, Enum):
    AVAILABLE = 'available'
    IN_TRIP = 'in_trip'
    MAINTENANCE = 'maintenance'

@dataclass
class Vehicle:
    id: str
    plate: str
    status: VehicleStatus = VehicleStatus.AVAILABLE
    version: int = 1

    def __post_init__(self):
        if not self.id or not self.plate.strip() or self.version < 1:
            raise DomainError('Некоректний автомобіль')

@dataclass
class Driver:
    id: str
    name: str
    active: bool = True
    license_valid: bool = True

    def can_drive(self):
        return self.active and self.license_valid
