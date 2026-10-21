"""Factory: the application composition root creates swappable dependencies."""
from dataclasses import dataclass
from collections.abc import Callable
from .repository import TripsRepository
from .fleet_client import FleetClient

@dataclass(frozen=True)
class TripsComponents:
    repository: TripsRepository
    fleet_client: FleetClient

class TripsComponentsFactory:
    def __init__(self, repository_factory: Callable = TripsRepository,
                 fleet_client_factory: Callable = FleetClient):
        self.repository_factory = repository_factory
        self.fleet_client_factory = fleet_client_factory

    def build(self, db_path, fleet_url, fleet_transport=None):
        return TripsComponents(
            repository=self.repository_factory(db_path),
            fleet_client=self.fleet_client_factory(fleet_url, timeout=0.35, transport=fleet_transport),
        )
