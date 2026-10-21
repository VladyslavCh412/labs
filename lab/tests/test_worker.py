import json, sqlite3
from services.events import publish
from services.event_worker import deliver_once

def test_outbox_worker_delivers_once(tmp_path,monkeypatch):
    db=tmp_path/'trips.db'; logfile=tmp_path/'events.jsonl'
    monkeypatch.setattr('services.event_worker.DB',str(db))
    monkeypatch.setattr('services.event_worker.LOG',str(logfile))
    e=publish(db,'TripCreated',{'id':'t1'})
    assert deliver_once()==1
    assert deliver_once()==0
    assert json.loads(logfile.read_text().strip())['event_id']==e['event_id']
