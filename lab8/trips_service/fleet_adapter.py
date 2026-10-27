"""Adapter: isolate Trips logic from the external Fleet JSON representation."""
from dataclasses import dataclass
from collections.abc import Mapping

@dataclass(frozen=True)
class VehicleAvailability:
    status: str

@dataclass(frozen=True)
class DriverPermission:
    active: bool
    license_valid: bool

class FleetResponseAdapter:
    def vehicle(self, response: Mapping) -> VehicleAvailability:
        return VehicleAvailability(status=response['status'])

    def driver(self, response: Mapping) -> DriverPermission:
        return DriverPermission(active=response['active'], license_valid=response['license_valid'])
