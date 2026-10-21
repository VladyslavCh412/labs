"""Composition root: only here are concrete dependencies assembled."""
from pathlib import Path
from fleet.infrastructure.repositories import (
    InMemoryRepository, SQLiteVehicleRepository, SQLiteTripRepository
)
from fleet.domain.models import Driver, Route, Vehicle
from fleet.application.use_cases import FleetUseCases

# Retained for existing isolated domain tests from labs 2-8.
vehicles = InMemoryRepository()
trips = InMemoryRepository()
vehicles.save(Vehicle('v-1', 'BH1234AA'))
drivers = {'d-1': Driver('d-1', 'Олена')}
routes = {'r-1': Route('r-1', ('Одеса', 'Миколаїв'))}


def build_use_cases():
    return FleetUseCases(vehicles, trips, drivers, routes)


def build_sqlite_use_cases(path: str | Path) -> FleetUseCases:
    """Build persistent adapters while keeping business rules framework-agnostic."""
    vehicle_repo = SQLiteVehicleRepository(path)
    trip_repo = SQLiteTripRepository(path)
    if vehicle_repo.get('v-1') is None:
        vehicle_repo.save(Vehicle('v-1', 'BH1234AA'))
    return FleetUseCases(
        vehicle_repo,
        trip_repo,
        {'d-1': Driver('d-1', 'Олена')},
        {'r-1': Route('r-1', ('Одеса', 'Миколаїв'))}
    )
