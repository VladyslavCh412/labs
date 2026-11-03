"""Trips bounded context. Domain objects do not depend on HTTP or storage."""
from dataclasses import dataclass

class DomainError(ValueError):
    pass

@dataclass(frozen=True)
class Route:
    id: str
    stops: tuple[str, ...]

    def __post_init__(self):
        if len(self.stops) < 2 or any(not stop.strip() for stop in self.stops):
            raise DomainError('Маршрут має не менше двох точок')

@dataclass
class Trip:
    id: str
    vehicle_id: str
    driver_id: str
    route_id: str
    status: str = 'planned'

    def __post_init__(self):
        if not all([self.id, self.vehicle_id, self.driver_id, self.route_id]):
            raise DomainError('Усі ідентифікатори рейсу обов’язкові')

    def start_record(self):
        if self.status != 'planned':
            raise DomainError('only_planned_trip_can_start')
        self.status = 'active'

    def complete_record(self, distance_km):
        if self.status != 'active' or distance_km < 0:
            raise DomainError('invalid_trip_completion')
        self.status = 'completed'

    def activate(self, vehicle, driver):
        if self.status != 'planned':
            raise DomainError('Можна починати лише запланований рейс')
        if not driver.can_drive():
            raise DomainError('Водій не допущений до керування')
        vehicle.begin_trip()
        self.status = 'active'

    def complete(self, vehicle, distance_km):
        if self.status != 'active':
            raise DomainError('Рейс ще не активний')
        vehicle.finish_trip(distance_km)
        self.status = 'completed'


class FleetUnavailable(Exception):
    pass

class FleetRejected(Exception):
    def __init__(self, status_code, message):
        self.status_code, self.message = status_code, message

class MissingResource(LookupError):
    pass

# Ports live with the domain; concrete SQLite/HTTP adapters live outside it.
from typing import Protocol

class TripStore(Protocol):
    def get_trip(self, trip_id: str) -> Trip | None: ...
    def route_exists(self, route_id: str) -> bool: ...
    def create_trip_and_publish(self, trip: Trip) -> dict: ...
    def operation_receipt(self, trip_id: str, operation: str) -> dict | None: ...
    def save_transition(self, trip: Trip, previous: str, operation: str, distance_km: int) -> dict: ...

class FleetGateway(Protocol):
    async def check_vehicle_and_driver(self, vehicle_id: str, driver_id: str): ...
    async def execute_lifecycle(self, trip_id: str, operation: str, vehicle_id: str,
                                driver_id: str, distance_km: int = 0) -> dict: ...
