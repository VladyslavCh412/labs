"""Lab 5 tests on an isolated temp directory; no credentials, cloud, or database sharing."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import httpx
from tests.support import AuthorizedClient as TestClient

from fleet_service.app import create_app as fleet_app
from fleet_service.cache import VehicleReadCache
from fleet_service.domain import VehicleStatus
from fleet_service.migrations import apply_migrations, schema_columns
from fleet_service.repository import FleetRepository
from trips_service.app import create_app as trips_app
from trips_service.repository import TripsRepository
from event_bridge import pump_once


def test_all_four_migrations_and_backward_compatibility(tmp_path):
    path=tmp_path/'fleet.sqlite'
    repo=FleetRepository(path)
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT plate FROM vehicles WHERE id=?',('v-1',)).fetchone()[0]=='BH1234AA'
    assert apply_migrations(path,1)==[1]
    assert apply_migrations(path,2)==[1,2]
    updated=repo.change_registration('v-1','BH9999AA')
    assert updated.plate=='BH9999AA'
    with sqlite3.connect(path) as db:
        row=db.execute('SELECT plate,registration_number FROM vehicles WHERE id=?',('v-1',)).fetchone()
        assert row==('BH9999AA','BH9999AA')  # parallel write
        assert db.execute('SELECT plate FROM vehicles WHERE id=?',('v-1',)).fetchone()[0]=='BH9999AA'  # old consumer
    assert apply_migrations(path,3)==[1,2,3]
    assert repo.vehicle('v-1').plate=='BH9999AA'
    with sqlite3.connect(path) as db:
        assert 'plate' in schema_columns(db) # old code still works through switch
    assert apply_migrations(path,4)==[1,2,3,4]
    assert apply_migrations(path,4)==[1,2,3,4]  # idempotent migration runner
    with sqlite3.connect(path) as db:
        assert 'plate' not in schema_columns(db)
        assert 'registration_number' in schema_columns(db)
    assert repo.vehicle('v-1').plate=='BH9999AA'
    assert repo.change_registration('v-1','BH1111AA').plate=='BH1111AA'
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT registration_number FROM vehicles WHERE id=?',('v-1',)).fetchone()[0]=='BH1111AA'


def test_cache_hits_ttl_expiration():
    ticks=[100.0]
    cache=VehicleReadCache(30.0,clock=lambda:ticks[0])
    loaded=[]
    def loader(key):loaded.append(key);return {'id':key}
    assert cache.get('v-1',loader)=={'id':'v-1'}
    assert cache.get('v-1',loader)=={'id':'v-1'}
    assert len(loaded)==1 and cache.stats()['hits']==1
    ticks[0]+=31
    assert cache.get('v-1',loader)=={'id':'v-1'}
    assert len(loaded)==2 and cache.stats()['misses']==2


def test_cache_explicit_invalidation_on_write(tmp_path):
    app=fleet_app(tmp_path/'fleet.sqlite',migration_stage=4)
    with TestClient(app) as c:
        assert c.get('/vehicles/v-1').json()['status']=='available'
        assert c.get('/vehicles/v-1').json()['status']=='available'
        before=c.get('/cache/stats').json()
        assert before['hits']==1
        assert c.patch('/vehicles/v-1/status',json={'status':'maintenance'}).status_code==200
        response=c.get('/vehicles/v-1').json()
        assert response['status']=='maintenance' and response['version']==2
        stats=c.get('/cache/stats').json()
        assert stats['misses']==2
        assert c.patch('/vehicles/v-1/registration',json={'plate':'BH5555AA'}).status_code==200
        assert c.get('/vehicles/v-1').json()['plate']=='BH5555AA'


def test_local_vehicle_copy_and_idempotent_replay(tmp_path):
    f=fleet_app(tmp_path/'fleet.sqlite',migration_stage=4)
    t=trips_app(tmp_path/'trips.sqlite')
    with TestClient(f) as fleet, TestClient(t) as trips:
        assert trips.get('/snapshots/vehicles/v-1').status_code==404
        assert fleet.patch('/vehicles/v-1/status',json={'status':'maintenance'}).status_code==200
        event=fleet.get('/fleet-events/outbox').json()[0]['payload']
        first=trips.post('/events/fleet-status',json=event)
        assert first.status_code==200 and first.json()['applied'] is True
        snapshot=trips.get('/snapshots/vehicles/v-1').json()
        assert snapshot['status']=='maintenance' and snapshot['version']==2
        again=trips.post('/events/fleet-status',json=event)
        assert again.json()['applied'] is False
        assert trips.get('/events/fleet-processed-count').json()['processed_events']==1
        # Another old event ID does not roll back a newer projection
        stale={**event,'event_id':'older-than-current',
               'data':{**event['data'],'status':'available','version':1}}
        assert trips.post('/events/fleet-status',json=stale).json()['applied'] is True
        assert trips.get('/snapshots/vehicles/v-1').json()['status']=='maintenance'
        assert trips.get('/events/fleet-processed-count').json()['processed_events']==2
    with sqlite3.connect(tmp_path/'fleet.sqlite') as db:
        assert 'vehicle_snapshot' not in {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    with sqlite3.connect(tmp_path/'trips.sqlite') as db:
        assert 'vehicles' not in {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_bridge_ack_after_confirmed_event_delivery():
    posted=[]
    event={'event_id':'ev-1','type':'VehicleStatusChanged','occurred_at':datetime.now(timezone.utc).isoformat(),
           'data':{'id':'v-1','plate':'BH1234AA','status':'maintenance','version':2}}
    def responder(req):
        if req.method=='GET':
            return httpx.Response(200,json=[{'event_id':'ev-1','payload':event,'delivered':False}])
        posted.append((req.method,req.url.path))
        return httpx.Response(200,json={'applied':True})
    with httpx.Client(transport=httpx.MockTransport(responder)) as c:
        out=pump_once('http://fleet','http://trips',c)
    assert out=={'delivered':1,'pending':1}
    assert posted==[('POST','/events/fleet-status'),('POST','/fleet-events/ack/ev-1')]


def test_bridge_does_not_ack_if_receiver_fails():
    posted=[]
    def responder(req):
        posted.append(req.url.path)
        if req.method=='GET':
            return httpx.Response(200,json=[{'event_id':'ev-1','payload':{'event_id':'ev-1'},'delivered':False}])
        return httpx.Response(503)
    import pytest
    with httpx.Client(transport=httpx.MockTransport(responder)) as c:
        with pytest.raises(httpx.HTTPStatusError):pump_once('http://fleet','http://trips',c)
    assert '/fleet-events/ack/ev-1' not in posted


def test_post_migration_old_lab_3_trip_still_operates(tmp_path):
    f=fleet_app(tmp_path/'fleet.sqlite',migration_stage=4)
    t=trips_app(tmp_path/'trips.sqlite',fleet_url='http://fleet',fleet_transport=httpx.ASGITransport(app=f))
    with TestClient(t) as trips:
        response=trips.post('/trips',json={'id':'t-lab5','vehicle_id':'v-1','driver_id':'d-1','route_id':'r-1'})
        assert response.status_code==201,response.text
        assert trips.get('/trips/t-lab5').status_code==200
