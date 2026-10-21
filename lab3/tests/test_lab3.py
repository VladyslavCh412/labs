import json
import sqlite3
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from fleet_service.app import create_app as fleet_app
from fleet_service.domain import Vehicle, VehicleStatus, DomainError, Driver
from fleet_service.repository import FleetRepository
from trips_service.app import create_app as trips_app
from trips_service.repository import TripsRepository

@pytest.fixture
def env(tmp_path):
    fleet_db = tmp_path/'fleet.sqlite'
    trips_db = tmp_path/'trips.sqlite'
    fleet = fleet_app(fleet_db)
    trips = trips_app(trips_db, fleet_url='http://testfleet', fleet_transport=httpx.ASGITransport(app=fleet))
    return fleet, trips, fleet_db, trips_db

def test_independent_databases_are_distinct(env):
    _, _, fleet_db, trips_db = env
    assert fleet_db != trips_db
    with sqlite3.connect(fleet_db) as db:
        names={x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert 'vehicles' in names and 'trips' not in names
    with sqlite3.connect(trips_db) as db:
        names={x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert 'trips' in names and 'vehicles' not in names

def test_fleet_vehicles_drivers(env):
    fleet, _, _, _ = env
    with TestClient(fleet) as c:
        assert c.get('/vehicles/v-1').json()['status']=='available'
        assert c.get('/drivers/d-1').json()['license_valid'] is True
        assert c.get('/vehicles/not-found').status_code == 404

def test_fleet_domain_invariants():
    with pytest.raises(DomainError): Vehicle('v', '', VehicleStatus.AVAILABLE)
    assert not Driver('d', 'name', active=False).can_drive()

def test_create_trip_sync_and_atomic_outbox(env):
    _, app, _, trips_db = env
    with TestClient(app) as c:
        r=c.post('/trips',json={'id':'t-1','vehicle_id':'v-1','driver_id':'d-1','route_id':'r-1'})
        assert r.status_code == 201, r.text
        assert c.get('/trips/t-1').json()['status']=='planned'
        assert c.post('/trips',json={'id':'t-1','vehicle_id':'v-1','driver_id':'d-1','route_id':'r-1'}).status_code == 409
        events=c.get('/events/outbox').json()
        assert len(events)==1 and events[0]['type']=='TripCreated'
        assert events[0]['payload']['data']['id']=='t-1'
    with sqlite3.connect(trips_db) as db:
        assert db.execute('SELECT COUNT(*) FROM trips').fetchone()[0]==1
        assert db.execute('SELECT COUNT(*) FROM outbox').fetchone()[0]==1

def test_unknown_route_is_404(env):
    _, app, _, _=env
    with TestClient(app) as c:
        r=c.post('/trips', json={'id':'t-x','vehicle_id':'v-1','driver_id':'d-1','route_id':'missing'})
        assert r.status_code==404

def test_unavailable_vehicle_rejected(env):
    fleet, trips, _, _=env
    with TestClient(fleet) as f, TestClient(trips) as t:
        assert f.patch('/vehicles/v-1/status',json={'status':'maintenance'}).status_code==200
        r=t.post('/trips',json={'id':'t-2','vehicle_id':'v-1','driver_id':'d-1','route_id':'r-1'})
        assert r.status_code==409

def test_fleet_down_returns_503_and_no_trip(tmp_path):
    app=trips_app(tmp_path/'trips.sqlite',fleet_url='http://127.0.0.1:1')
    with TestClient(app) as client:
        res=client.post('/trips',json={'id':'t-out','vehicle_id':'v-1','driver_id':'d-1','route_id':'r-1'})
        assert res.status_code==503 and res.json()['detail']=='fleet_service_unavailable'
        assert client.get('/trips/t-out').status_code==404

def test_async_notification_after_fleet_offline(env):
    _, app, _, trips_db=env
    with TestClient(app) as client:
        assert client.post('/trips',json={'id':'t-3','vehicle_id':'v-1','driver_id':'d-1','route_id':'r-1'}).status_code==201
        # No worker yet: HTTP request succeeded but notification is not delivered.
        assert client.get('/notifications').json()==[]
    repo=TripsRepository(trips_db)
    # Event consumer does not call Fleet; equivalent to Fleet outage.
    assert repo.deliver_pending()==1
    assert repo.deliver_pending()==0
    notifications=repo.notifications()
    assert len(notifications)==1 and notifications[0]['trip_id']=='t-3'
    assert repo.outbox()[0]['delivered'] is True

def test_outbox_preserved_while_worker_offline(env):
    _, app, _, trips_db=env
    with TestClient(app) as c:
        assert c.post('/trips',json={'id':'t-4','vehicle_id':'v-1','driver_id':'d-1','route_id':'r-1'}).status_code==201
    reloaded=TripsRepository(trips_db)
    assert reloaded.outbox()[0]['delivered'] is False
    assert reloaded.deliver_pending()==1
    assert reloaded.notifications()[0]['trip_id']=='t-4'

def test_openapi_contract_and_event_schema():
    import yaml
    api=yaml.safe_load(Path('contracts/fleet.openapi.yaml').read_text(encoding='utf-8'))
    trips_contract=yaml.safe_load(Path('contracts/trips.openapi.yaml').read_text(encoding='utf-8'))
    schema=json.loads(Path('contracts/trip_created.schema.json').read_text(encoding='utf-8'))
    assert '200' in api['paths']['/vehicles/{vehicle_id}']['get']['responses']
    assert {'id','plate','status','version'}.issubset(api['paths']['/vehicles/{vehicle_id}']['get']['responses']['200']['content']['application/json']['schema']['required'])
    assert '503' in trips_contract['paths']['/trips']['post']['responses']
    assert '409' in trips_contract['paths']['/trips']['post']['responses']
    assert schema['properties']['type']['const']=='TripCreated'
