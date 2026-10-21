from dataclasses import dataclass
from enum import Enum

class DomainError(ValueError):
    pass

class VehicleStatus(str, Enum):
    AVAILABLE = "available"
    IN_TRIP = "in_trip"
    MAINTENANCE = "maintenance"

@dataclass
class Vehicle:
    id: str
    plate: str
    mileage_km: int = 0
    status: VehicleStatus = VehicleStatus.AVAILABLE
    def __post_init__(self):
        if not self.id or not self.plate.strip():
            raise DomainError("Номер і id транспортного засобу обов'язкові")
        if self.mileage_km < 0:
            raise DomainError("Пробіг не може бути від'ємним")
    def begin_trip(self):
        if self.status != VehicleStatus.AVAILABLE:
            raise DomainError("ТЗ не доступний для рейсу")
        self.status = VehicleStatus.IN_TRIP
    def finish_trip(self, added_km:int):
        if self.status != VehicleStatus.IN_TRIP or added_km < 0:
            raise DomainError("Некоректне завершення рейсу")
        self.mileage_km += added_km
        self.status = VehicleStatus.AVAILABLE
    def start_maintenance(self):
        if self.status == VehicleStatus.IN_TRIP:
            raise DomainError("Не можна почати ТО під час рейсу")
        self.status = VehicleStatus.MAINTENANCE

@dataclass
class Driver:
    id: str
    name: str
    license_valid: bool = True
    active: bool = True
    def can_drive(self):
        return self.active and self.license_valid

@dataclass
class Route:
    id: str
    stops: tuple[str, ...]
    def __post_init__(self):
        if len(self.stops) < 2 or any(not p.strip() for p in self.stops):
            raise DomainError("Маршрут має містити щонайменше дві точки")

@dataclass
class Trip:
    id: str
    vehicle_id: str
    driver_id: str
    route_id: str
    status: str = "planned"
    def activate(self, vehicle:Vehicle, driver:Driver):
        if self.status != "planned":
            raise DomainError("Можна починати лише запланований рейс")
        if not driver.can_drive():
            raise DomainError("Водій не допущений до керування")
        vehicle.begin_trip()
        self.status = "active"
    def complete(self, vehicle:Vehicle, distance_km:int):
        if self.status != "active":
            raise DomainError("Рейс ще не активний")
        vehicle.finish_trip(distance_km)
        self.status = "completed"
