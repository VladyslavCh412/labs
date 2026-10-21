import sqlite3
from fleet.infrastructure.repositories import SQLiteVehicleRepository
from fleet.domain.models import Vehicle
from services.events import consume_vehicle_update,initialize
from services.cache import TTLCache

def test_repository_roundtrip(tmp_path):
    repo=SQLiteVehicleRepository(tmp_path/'fleet.sqlite');repo.save(Vehicle('v','AA1020AA'))
    assert repo.get('v').plate=='AA1020AA'

def test_event_is_idempotent_and_monotonic(tmp_path):
    db=tmp_path/'trips.sqlite';initialize(db)
    event={'event_id':'e-1','data':{'id':'v-1','plate':'XX1000YY','status':'available','version':2}}
    assert consume_vehicle_update(db,event)
    assert not consume_vehicle_update(db,event)
    stale={'event_id':'e-2','data':{'id':'v-1','plate':'WRONG','status':'maintenance','version':1}}
    assert consume_vehicle_update(db,stale)
    with sqlite3.connect(db) as con:result=con.execute('SELECT plate,version FROM vehicle_projection').fetchone()
    assert result==('XX1000YY',2)

def test_cache_invalidation():
    c=TTLCache(60);data={'value':1};assert c.get('all',lambda:data['value'])==1
    data['value']=2;assert c.get('all',lambda:data['value'])==1
    c.invalidate('all');assert c.get('all',lambda:data['value'])==2
