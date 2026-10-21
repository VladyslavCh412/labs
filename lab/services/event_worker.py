"""Trips-owned outbox consumer: independent process; writes demo notifications once."""
import json,sqlite3,time,os
from pathlib import Path
from services.events import initialize
DB=os.environ.get('TRIPS_DB','trips.db')
LOG=os.environ.get('NOTIFY_LOG','notifications.jsonl')
def deliver_once():
    initialize(DB)
    with sqlite3.connect(DB) as db:
        db.execute('BEGIN IMMEDIATE')
        rows=db.execute('SELECT event_id,payload FROM outbox WHERE delivered=0 ORDER BY rowid LIMIT 100').fetchall()
        for event_id,payload in rows:
            # Demo-only sink; external delivery must use an idempotency key in production.
            with Path(LOG).open('a',encoding='utf8') as out:out.write(payload+'\n')
            db.execute('UPDATE outbox SET delivered=1 WHERE event_id=?',(event_id,))
        db.commit()
    return len(rows)
if __name__=='__main__':
    print('Outbox worker started; CTRL+C to exit',flush=True)
    while True:
        deliver_once();time.sleep(.5)
