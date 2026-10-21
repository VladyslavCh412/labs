"""Fleet owns its SQLite database, migrations, and vehicle change outbox."""
import json
import sqlite3
from contextlib import closing
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .domain import Vehicle, VehicleStatus, Driver
from .migrations import apply_migrations, schema_columns, current_stage

class FleetRepository:
    def __init__(self, path, migration_stage=None):
        self.path=str(Path(path))
        Path(self.path).parent.mkdir(parents=True,exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS vehicles (id TEXT PRIMARY KEY, plate TEXT NOT NULL, status TEXT NOT NULL, version INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS drivers (id TEXT PRIMARY KEY, name TEXT NOT NULL, active INTEGER NOT NULL, license_valid INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS vehicle_outbox (event_id TEXT PRIMARY KEY, type TEXT NOT NULL, payload TEXT NOT NULL, delivered INTEGER NOT NULL DEFAULT 0)')
            cols=schema_columns(db)
            if 'plate' in cols and 'registration_number' in cols:
                db.execute('INSERT OR IGNORE INTO vehicles (id,plate,registration_number,status,version) VALUES (?,?,?,?,?)',('v-1','BH1234AA','BH1234AA','available',1))
            else:
                plate_col='registration_number' if 'registration_number' in cols else 'plate'
                db.execute(f'INSERT OR IGNORE INTO vehicles (id,{plate_col},status,version) VALUES (?,?,?,?)',('v-1','BH1234AA','available',1))
            db.execute('INSERT OR IGNORE INTO drivers VALUES (?,?,?,?)',('d-1','Олена',1,1))
            db.execute('INSERT OR IGNORE INTO drivers VALUES (?,?,?,?)',('d-2','Максим',1,1))
            db.execute('INSERT OR IGNORE INTO drivers VALUES (?,?,?,?)',('d-3','Ірина',1,1))
            for vid, plate, status in [('v-2','BH2100AA','available'), ('v-3','BH3300AA','maintenance')]:
                if 'plate' in cols and 'registration_number' in cols:
                    db.execute('INSERT OR IGNORE INTO vehicles (id,plate,registration_number,status,version) VALUES (?,?,?,?,?)',
                               (vid,plate,plate,status,1))
                else:
                    db.execute(f'INSERT OR IGNORE INTO vehicles (id,{plate_col},status,version) VALUES (?,?,?,?)',
                               (vid,plate,status,1))
        if migration_stage is not None:
            apply_migrations(self.path,migration_stage)


    def vehicles(self):
        """List owned vehicles for the dashboard without touching the read-cache counters."""
        with closing(sqlite3.connect(self.path)) as db:
            cols=schema_columns(db)
            plate_col='registration_number' if 'registration_number' in cols else 'plate'
            rows=db.execute(f'SELECT id,{plate_col},status,version FROM vehicles ORDER BY id').fetchall()
        return [dict(id=r[0],plate=r[1],status=r[2],version=r[3]) for r in rows]

    def drivers(self):
        with closing(sqlite3.connect(self.path)) as db:
            rows=db.execute('SELECT id,name,active,license_valid FROM drivers ORDER BY id').fetchall()
        return [dict(id=r[0],name=r[1],active=bool(r[2]),license_valid=bool(r[3])) for r in rows]

    def create_vehicle(self, vehicle):
        with closing(sqlite3.connect(self.path,timeout=5)) as db, db:
            cols=schema_columns(db)
            if 'plate' in cols and 'registration_number' in cols:
                db.execute('INSERT INTO vehicles (id,plate,registration_number,status,version) VALUES (?,?,?,?,?)',
                           (vehicle.id,vehicle.plate,vehicle.plate,vehicle.status.value,vehicle.version))
            else:
                plate_col='registration_number' if 'registration_number' in cols else 'plate'
                db.execute(f'INSERT INTO vehicles (id,{plate_col},status,version) VALUES (?,?,?,?)',
                           (vehicle.id,vehicle.plate,vehicle.status.value,vehicle.version))
        return vehicle

    def create_driver(self, driver):
        with closing(sqlite3.connect(self.path,timeout=5)) as db, db:
            db.execute('INSERT INTO drivers VALUES (?,?,?,?)',
                       (driver.id,driver.name,int(driver.active),int(driver.license_valid)))
        return driver

    def vehicle(self, item_id):
        with closing(sqlite3.connect(self.path)) as db, db:
            cols=schema_columns(db)
            stage=current_stage(db)
            plate_col='registration_number' if stage>=3 else 'plate'
            if plate_col not in cols:
                plate_col='registration_number' if 'registration_number' in cols else 'plate'
            row=db.execute(f'SELECT id, {plate_col}, status, version FROM vehicles WHERE id=?',(item_id,)).fetchone()
        return Vehicle(row[0],row[1],VehicleStatus(row[2]),row[3]) if row else None

    def driver(self, item_id):
        with closing(sqlite3.connect(self.path)) as db, db:
            row=db.execute('SELECT id,name,active,license_valid FROM drivers WHERE id=?',(item_id,)).fetchone()
        return Driver(row[0],row[1],bool(row[2]),bool(row[3])) if row else None

    def change_status(self, item_id, status):
        with closing(sqlite3.connect(self.path,timeout=5)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            cursor=db.execute('UPDATE vehicles SET status=?,version=version+1 WHERE id=?',(status.value,item_id))
            if cursor.rowcount==0:
                return None
            cols=schema_columns(db)
            stage=current_stage(db)
            plate_col='registration_number' if stage>=3 else 'plate'
            if plate_col not in cols:
                plate_col='plate' if 'plate' in cols else 'registration_number'
            row=db.execute(f'SELECT id,{plate_col},status,version FROM vehicles WHERE id=?',(item_id,)).fetchone()
            vehicle=Vehicle(row[0],row[1],VehicleStatus(row[2]),row[3])
            event={'event_id':str(uuid.uuid4()),'type':'VehicleStatusChanged','occurred_at':datetime.now(timezone.utc).isoformat(),
                   'data':{'id':vehicle.id,'plate':vehicle.plate,'status':vehicle.status.value,'version':vehicle.version}}
            db.execute('INSERT INTO vehicle_outbox (event_id,type,payload) VALUES (?,?,?)',
                       (event['event_id'],event['type'],json.dumps(event,ensure_ascii=False)))
        return vehicle

    def outbox(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            rows=db.execute('SELECT event_id,payload,delivered FROM vehicle_outbox ORDER BY rowid').fetchall()
        return [{'event_id':eid,'payload':json.loads(payload),'delivered':bool(delivered)} for eid,payload,delivered in rows]

    def ack_event(self,event_id):
        with closing(sqlite3.connect(self.path)) as db, db:
            result=db.execute('UPDATE vehicle_outbox SET delivered=1 WHERE event_id=?',(event_id,))
            return bool(result.rowcount)

    def change_registration(self, item_id, new_plate):
        """Dual-write during expansion; use new field only after contract."""
        new_plate = new_plate.strip()
        if not new_plate:
            raise ValueError('empty_registration')
        with closing(sqlite3.connect(self.path, timeout=5)) as db, db:
            cols = schema_columns(db)
            if 'plate' in cols and 'registration_number' in cols:
                statement = 'UPDATE vehicles SET plate=?, registration_number=?, version=version+1 WHERE id=?'
                args = (new_plate, new_plate, item_id)
            elif 'registration_number' in cols:
                statement = 'UPDATE vehicles SET registration_number=?, version=version+1 WHERE id=?'
                args = (new_plate, item_id)
            else:
                statement = 'UPDATE vehicles SET plate=?, version=version+1 WHERE id=?'
                args = (new_plate, item_id)
            if not db.execute(statement, args).rowcount:
                return None
        return self.vehicle(item_id)
