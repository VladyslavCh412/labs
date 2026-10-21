"""Atomic Trips write + TripCreated outbox; Fleet DB is never accessed here."""
import json
import sqlite3
from contextlib import closing
import uuid
from pathlib import Path
from .domain import Trip
from .observers import TripEventPublisher

class TripsRepository:
    def __init__(self, path, publisher=None):
        self.publisher = publisher or TripEventPublisher()
        self.path = str(Path(path))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS trips (id TEXT PRIMARY KEY, vehicle_id TEXT NOT NULL, driver_id TEXT NOT NULL, route_id TEXT NOT NULL, status TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS routes (id TEXT PRIMARY KEY, stops_json TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS outbox (event_id TEXT PRIMARY KEY, type TEXT NOT NULL, payload TEXT NOT NULL, delivered INTEGER NOT NULL DEFAULT 0)')
            db.execute('CREATE TABLE IF NOT EXISTS notification_inbox (event_id TEXT PRIMARY KEY, trip_id TEXT NOT NULL, message TEXT NOT NULL)')
            db.execute('''CREATE TABLE IF NOT EXISTS vehicle_snapshot (id TEXT PRIMARY KEY,plate TEXT NOT NULL,status TEXT NOT NULL,version INTEGER NOT NULL,updated_at TEXT NOT NULL)''')
            db.execute('CREATE TABLE IF NOT EXISTS fleet_event_inbox (event_id TEXT PRIMARY KEY, received_at TEXT NOT NULL)')
            for rid,stops in [('r-1',['Одеса','Миколаїв']),('r-2',['Одеса','Київ']),('r-3',['Одеса','Білгород-Дністровський'])]:
                db.execute('INSERT OR IGNORE INTO routes VALUES (?, ?)', (rid, json.dumps(stops, ensure_ascii=False)))

    def trips(self):
        with closing(sqlite3.connect(self.path)) as db:
            rows=db.execute('SELECT id,vehicle_id,driver_id,route_id,status FROM trips ORDER BY rowid DESC').fetchall()
        return [dict(zip(('id','vehicle_id','driver_id','route_id','status'),row)) for row in rows]

    def routes(self):
        with closing(sqlite3.connect(self.path)) as db:
            rows=db.execute('SELECT id,stops_json FROM routes ORDER BY id').fetchall()
        return [{'id':r[0],'stops':json.loads(r[1])} for r in rows]

    def create_route(self, route):
        with closing(sqlite3.connect(self.path,timeout=5)) as db, db:
            db.execute('INSERT INTO routes VALUES (?,?)',(route.id,json.dumps(list(route.stops),ensure_ascii=False)))
        return route

    def snapshots(self):
        with closing(sqlite3.connect(self.path)) as db:
            rows=db.execute('SELECT id,plate,status,version,updated_at FROM vehicle_snapshot ORDER BY id').fetchall()
        return [dict(zip(('id','plate','status','version','updated_at'),r)) for r in rows]

    def route_exists(self, route_id):
        with closing(sqlite3.connect(self.path)) as db, db:
            return db.execute('SELECT 1 FROM routes WHERE id=?', (route_id,)).fetchone() is not None

    def get_trip(self, trip_id):
        with closing(sqlite3.connect(self.path)) as db, db:
            row = db.execute('SELECT id, vehicle_id, driver_id, route_id, status FROM trips WHERE id=?', (trip_id,)).fetchone()
        return Trip(*row) if row else None

    def create_trip_and_publish(self, trip):
        event = {
            'event_id': str(uuid.uuid4()), 'type': 'TripCreated',
            'data': {'id': trip.id, 'vehicle_id': trip.vehicle_id, 'driver_id': trip.driver_id, 'route_id': trip.route_id}
        }
        with closing(sqlite3.connect(self.path, timeout=5)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT INTO trips VALUES (?, ?, ?, ?, ?)', (trip.id, trip.vehicle_id, trip.driver_id, trip.route_id, trip.status))
            db.execute('INSERT INTO outbox (event_id, type, payload) VALUES (?, ?, ?)',
                       (event['event_id'], event['type'], json.dumps(event, ensure_ascii=False)))
        return event

    def outbox(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            rows = db.execute('SELECT event_id, type, payload, delivered FROM outbox ORDER BY rowid').fetchall()
        return [{'event_id': r[0], 'type': r[1], 'payload': json.loads(r[2]), 'delivered': bool(r[3])} for r in rows]

    def notifications(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            rows = db.execute('SELECT event_id, trip_id, message FROM notification_inbox ORDER BY rowid').fetchall()
        return [{'event_id': r[0], 'trip_id': r[1], 'message': r[2]} for r in rows]

    def deliver_pending(self):
        """Local demo subscriber, idempotent via event_id; safe transactional processing."""
        processed = 0
        with closing(sqlite3.connect(self.path, timeout=5)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            for event_id, payload in db.execute('SELECT event_id, payload FROM outbox WHERE delivered=0 ORDER BY rowid').fetchall():
                event = json.loads(payload)
                self.publisher.publish(db, event)
                db.execute('UPDATE outbox SET delivered=1 WHERE event_id=?', (event_id,))
                processed += 1
        return processed

    def vehicle_snapshot(self,vehicle_id):
        """A read-only materialized projection of Fleet fields; not a second source of truth."""
        with closing(sqlite3.connect(self.path)) as db, db:
            row=db.execute('SELECT id,plate,status,version,updated_at FROM vehicle_snapshot WHERE id=?',(vehicle_id,)).fetchone()
        return dict(zip(('id','plate','status','version','updated_at'),row)) if row else None

    def processed_fleet_events(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            return db.execute('SELECT COUNT(*) FROM fleet_event_inbox').fetchone()[0]

    def apply_fleet_event(self,event):
        """At-least-once delivery with idempotency by event_id and monotonic version."""
        from datetime import datetime,timezone
        if event.get('type')!='VehicleStatusChanged':
            raise ValueError('unexpected_event_type')
        data=event['data']
        now=datetime.now(timezone.utc).isoformat()
        with closing(sqlite3.connect(self.path,timeout=5)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            cursor=db.execute('INSERT OR IGNORE INTO fleet_event_inbox(event_id,received_at) VALUES (?,?)',(event['event_id'],now))
            if cursor.rowcount==0:
                return False
            existing=db.execute('SELECT version FROM vehicle_snapshot WHERE id=?',(data['id'],)).fetchone()
            if existing is None or data['version']>existing[0]:
                db.execute('INSERT INTO vehicle_snapshot(id,plate,status,version,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET plate=excluded.plate,status=excluded.status,version=excluded.version,updated_at=excluded.updated_at',
                           (data['id'],data['plate'],data['status'],data['version'],now))
        return True
