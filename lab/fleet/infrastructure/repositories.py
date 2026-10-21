"""SQLite adapters. Domain knows only Repository protocols, never SQLite."""
import sqlite3
from pathlib import Path
from fleet.domain.models import Vehicle, Trip, VehicleStatus


class InMemoryRepository:
    def __init__(self):
        self.items = {}

    def get(self, identifier):
        return self.items.get(identifier)

    def save(self, item):
        self.items[item.id] = item


def _db_path(path):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    return str(target)


class SQLiteVehicleRepository:
    def __init__(self, path):
        self.path = _db_path(path)
        with sqlite3.connect(self.path) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS vehicles (
                id TEXT PRIMARY KEY,
                plate TEXT NOT NULL,
                mileage_km INTEGER NOT NULL CHECK (mileage_km >= 0),
                status TEXT NOT NULL
            )''')

    def save(self, item: Vehicle) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute('''INSERT INTO vehicles (id, plate, mileage_km, status)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  plate=excluded.plate,
                  mileage_km=excluded.mileage_km,
                  status=excluded.status''',
                (item.id, item.plate, item.mileage_km, item.status.value))

    def get(self, identifier: str) -> Vehicle | None:
        with sqlite3.connect(self.path) as db:
            row = db.execute(
                'SELECT id, plate, mileage_km, status FROM vehicles WHERE id=?',
                (identifier,)
            ).fetchone()
        return Vehicle(row[0], row[1], row[2], VehicleStatus(row[3])) if row else None


class SQLiteTripRepository:
    def __init__(self, path):
        self.path = _db_path(path)
        with sqlite3.connect(self.path) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS trips (
                id TEXT PRIMARY KEY,
                vehicle_id TEXT NOT NULL,
                driver_id TEXT NOT NULL,
                route_id TEXT NOT NULL,
                status TEXT NOT NULL
            )''')

    def save(self, item: Trip) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute('''INSERT INTO trips (id, vehicle_id, driver_id, route_id, status)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  vehicle_id=excluded.vehicle_id,
                  driver_id=excluded.driver_id,
                  route_id=excluded.route_id,
                  status=excluded.status''',
                (item.id, item.vehicle_id, item.driver_id, item.route_id, item.status))

    def get(self, identifier: str) -> Trip | None:
        with sqlite3.connect(self.path) as db:
            row = db.execute(
                'SELECT id, vehicle_id, driver_id, route_id, status FROM trips WHERE id=?',
                (identifier,)
            ).fetchone()
        return Trip(*row) if row else None
