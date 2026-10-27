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
    mileage_km: int = 0

    def __post_init__(self):
        if not self.id or not self.plate.strip() or self.version < 1:
            raise DomainError('Некоректний автомобіль')
        if self.mileage_km < 0:
            raise DomainError('Пробіг не може бути від’ємним')

    def begin_trip(self):
        if self.status != VehicleStatus.AVAILABLE:
            raise DomainError('ТЗ не доступний для рейсу')
        self.status = VehicleStatus.IN_TRIP

    def finish_trip(self, added_km):
        if self.status != VehicleStatus.IN_TRIP or added_km < 0:
            raise DomainError('Некоректне завершення рейсу')
        self.mileage_km += added_km
        self.status = VehicleStatus.AVAILABLE

    def start_maintenance(self):
        if self.status == VehicleStatus.IN_TRIP:
            raise DomainError('Не можна почати ТО під час рейсу')
        self.status = VehicleStatus.MAINTENANCE

@dataclass
class Driver:
    id: str
    name: str
    active: bool = True
    license_valid: bool = True

    def can_drive(self):
        return self.active and self.license_valid
