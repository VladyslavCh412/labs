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

@dataclass(frozen=True)
class Trip:
    id: str
    vehicle_id: str
    driver_id: str
    route_id: str
    status: str = 'planned'

    def __post_init__(self):
        if not all([self.id, self.vehicle_id, self.driver_id, self.route_id]):
            raise DomainError('Усі ідентифікатори рейсу обов’язкові')
