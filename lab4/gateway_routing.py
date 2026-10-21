"""Strategy: each routing rule decides which bounded context owns a URL."""
from dataclasses import dataclass
from typing import Protocol

class RoutingStrategy(Protocol):
    def target(self, endpoint: str, fleet_url: str, trips_url: str) -> str | None: ...

@dataclass(frozen=True)
class FleetRoutes:
    """Use the Fleet API for vehicle and driver resources."""
    def target(self, endpoint, fleet_url, trips_url):
        return fleet_url if endpoint.startswith(('vehicles/', 'drivers/')) else None

@dataclass(frozen=True)
class TripsRoutes:
    """Use the Trips API for trip planning and event data."""
    def target(self, endpoint, fleet_url, trips_url):
        if endpoint == 'trips' or endpoint.startswith(('trips/', 'events/', 'notifications')):
            return trips_url
        return None

STRATEGIES: tuple[RoutingStrategy, ...] = (FleetRoutes(), TripsRoutes())

def resolve_target(endpoint: str, fleet_url: str, trips_url: str) -> str | None:
    """Extend routing by adding a new strategy; proxy need not change."""
    for strategy in STRATEGIES:
        selected = strategy.target(endpoint, fleet_url, trips_url)
        if selected:
            return selected
    return None
