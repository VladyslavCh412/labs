import sqlite3,json,uuid
from pathlib import Path

def initialize(db_path):
    with sqlite3.connect(db_path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS inbox(event_id TEXT PRIMARY KEY)')
        db.execute('CREATE TABLE IF NOT EXISTS vehicle_projection(vehicle_id TEXT PRIMARY KEY,plate TEXT,status TEXT,version INTEGER)')
        db.execute('CREATE TABLE IF NOT EXISTS outbox(event_id TEXT PRIMARY KEY,payload TEXT,delivered INTEGER DEFAULT 0)')

def publish(db_path,kind,body):
    event={'event_id':str(uuid.uuid4()),'type':kind,'data':body}
    initialize(db_path)
    with sqlite3.connect(db_path) as db:
        db.execute('INSERT INTO outbox(event_id,payload) VALUES (?,?)',(event['event_id'],json.dumps(event)))
    return event

def consume_vehicle_update(db_path,event):
    initialize(db_path)
    with sqlite3.connect(db_path) as db:
        try:
            db.execute('INSERT INTO inbox(event_id) VALUES (?)',(event['event_id'],))
        except sqlite3.IntegrityError:
            return False
        body=event['data']
        old=db.execute('SELECT version FROM vehicle_projection WHERE vehicle_id=?',(body['id'],)).fetchone()
        if old is None or body['version']>old[0]:
            db.execute('INSERT INTO vehicle_projection VALUES (?,?,?,?) ON CONFLICT(vehicle_id) DO UPDATE SET plate=excluded.plate,status=excluded.status,version=excluded.version',(body['id'],body['plate'],body['status'],body['version']))
    return True
