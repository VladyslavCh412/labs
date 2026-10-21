"""Only Fleet accesses its SQLite database."""
import sqlite3
from pathlib import Path
from .domain import Vehicle, VehicleStatus, Driver

class FleetRepository:
    def __init__(self, path):
        self.path = str(Path(path))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS vehicles (id TEXT PRIMARY KEY, plate TEXT NOT NULL, status TEXT NOT NULL, version INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS drivers (id TEXT PRIMARY KEY, name TEXT NOT NULL, active INTEGER NOT NULL, license_valid INTEGER NOT NULL)')
            db.execute('INSERT OR IGNORE INTO vehicles VALUES (?, ?, ?, ?)', ('v-1', 'BH1234AA', 'available', 1))
            db.execute('INSERT OR IGNORE INTO drivers VALUES (?, ?, ?, ?)', ('d-1', 'Олена', 1, 1))

    def vehicle(self, item_id):
        with sqlite3.connect(self.path) as db:
            row = db.execute('SELECT id, plate, status, version FROM vehicles WHERE id=?', (item_id,)).fetchone()
        return Vehicle(row[0], row[1], VehicleStatus(row[2]), row[3]) if row else None

    def driver(self, item_id):
        with sqlite3.connect(self.path) as db:
            row = db.execute('SELECT id, name, active, license_valid FROM drivers WHERE id=?', (item_id,)).fetchone()
        return Driver(row[0], row[1], bool(row[2]), bool(row[3])) if row else None

    def change_status(self, item_id, status):
        with sqlite3.connect(self.path) as db:
            cursor = db.execute('UPDATE vehicles SET status=?, version=version+1 WHERE id=?', (status.value, item_id))
            if not cursor.rowcount:
                return None
        return self.vehicle(item_id)
