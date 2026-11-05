"""Atomic Trips write + TripCreated outbox; Fleet DB is never accessed here."""
import json
import sqlite3
import uuid
from pathlib import Path
from .domain import Trip

class TripsRepository:
    def __init__(self, path):
        self.path = str(Path(path))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS trips (id TEXT PRIMARY KEY, vehicle_id TEXT NOT NULL, driver_id TEXT NOT NULL, route_id TEXT NOT NULL, status TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS routes (id TEXT PRIMARY KEY, stops_json TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS outbox (event_id TEXT PRIMARY KEY, type TEXT NOT NULL, payload TEXT NOT NULL, delivered INTEGER NOT NULL DEFAULT 0)')
            db.execute('CREATE TABLE IF NOT EXISTS notification_inbox (event_id TEXT PRIMARY KEY, trip_id TEXT NOT NULL, message TEXT NOT NULL)')
            db.execute('INSERT OR IGNORE INTO routes VALUES (?, ?)', ('r-1', json.dumps(['Одеса', 'Миколаїв'], ensure_ascii=False)))

    def route_exists(self, route_id):
        with sqlite3.connect(self.path) as db:
            return db.execute('SELECT 1 FROM routes WHERE id=?', (route_id,)).fetchone() is not None

    def get_trip(self, trip_id):
        with sqlite3.connect(self.path) as db:
            row = db.execute('SELECT id, vehicle_id, driver_id, route_id, status FROM trips WHERE id=?', (trip_id,)).fetchone()
        return Trip(*row) if row else None

    def create_trip_and_publish(self, trip):
        event = {
            'event_id': str(uuid.uuid4()), 'type': 'TripCreated',
            'data': {'id': trip.id, 'vehicle_id': trip.vehicle_id, 'driver_id': trip.driver_id, 'route_id': trip.route_id}
        }
        with sqlite3.connect(self.path, timeout=5) as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT INTO trips VALUES (?, ?, ?, ?, ?)', (trip.id, trip.vehicle_id, trip.driver_id, trip.route_id, trip.status))
            db.execute('INSERT INTO outbox (event_id, type, payload) VALUES (?, ?, ?)',
                       (event['event_id'], event['type'], json.dumps(event, ensure_ascii=False)))
        return event

    def outbox(self):
        with sqlite3.connect(self.path) as db:
            rows = db.execute('SELECT event_id, type, payload, delivered FROM outbox ORDER BY rowid').fetchall()
        return [{'event_id': r[0], 'type': r[1], 'payload': json.loads(r[2]), 'delivered': bool(r[3])} for r in rows]

    def notifications(self):
        with sqlite3.connect(self.path) as db:
            rows = db.execute('SELECT event_id, trip_id, message FROM notification_inbox ORDER BY rowid').fetchall()
        return [{'event_id': r[0], 'trip_id': r[1], 'message': r[2]} for r in rows]

    def deliver_pending(self):
        """Local demo subscriber, idempotent via event_id; safe transactional processing."""
        processed = 0
        with sqlite3.connect(self.path, timeout=5) as db:
            db.execute('BEGIN IMMEDIATE')
            for event_id, payload in db.execute('SELECT event_id, payload FROM outbox WHERE delivered=0 ORDER BY rowid').fetchall():
                event = json.loads(payload)
                db.execute('INSERT OR IGNORE INTO notification_inbox (event_id, trip_id, message) VALUES (?, ?, ?)',
                           (event_id, event['data']['id'], 'Заплановано рейс ' + event['data']['id']))
                db.execute('UPDATE outbox SET delivered=1 WHERE event_id=?', (event_id,))
                processed += 1
        return processed
