"""Resource-owner commands, retries, persistence and user-facing use cases."""
from concurrent.futures import ThreadPoolExecutor
import asyncio
import sqlite3
from contextlib import closing

import httpx
import pytest
from fastapi.testclient import TestClient

from fleet_service.app import create_app as fleet_app
from fleet_service.domain import DomainError as FleetError
from fleet_service.repository import FleetRepository
from trips_service.app import create_app as trips_app
from trips_service.application import TripUseCases
from trips_service.domain import Trip, DomainError, MissingResource, FleetUnavailable
from trips_service.repository import TripsRepository
from security import service_headers


def pair(tmp_path, transport=None):
    fleet = fleet_app(tmp_path / 'fleet.sqlite')
    trips = trips_app(tmp_path / 'trips.sqlite', fleet_url='http://fleet',
                      fleet_transport=transport or httpx.ASGITransport(app=fleet))
    return fleet, trips


def plan(client, name='t-1', vehicle='v-1'):
    result = client.post('/trips', json=dict(id=name, vehicle_id=vehicle,
                                           driver_id='d-1', route_id='r-1'),
                         headers=service_headers('dispatcher'))
    assert result.status_code == 201, result.text


def test_complete_lifecycle_persists_and_replays_without_double_mileage(tmp_path):
    fleet, trips = pair(tmp_path)
    with TestClient(trips) as client, TestClient(fleet) as f:
        plan(client)
        auth = service_headers('dispatcher')
        assert client.post('/trips/t-1/complete', json={'distance_km': 10}, headers=auth).status_code == 409
        assert client.post('/trips/t-1/start', headers=auth).json()['status'] == 'active'
        assert client.post('/trips/t-1/start', headers=auth).status_code == 200
        assert f.get('/vehicles/v-1', headers=service_headers('viewer')).json()['status'] == 'in_trip'
        assert f.patch('/vehicles/v-1/status', json={'status': 'maintenance'}, headers=service_headers('manager')).status_code == 409
        assert client.post('/trips/t-1/complete', json={'distance_km': -1}, headers=auth).status_code == 422
        assert client.post('/trips/t-1/complete', json={'distance_km': 25}, headers=auth).json()['status'] == 'completed'
        assert client.post('/trips/t-1/complete', json={'distance_km': 25}, headers=auth).status_code == 200
        assert client.post('/trips/t-1/complete', json={'distance_km': 26}, headers=auth).status_code == 409
        assert f.get('/vehicles/v-1', headers=service_headers('viewer')).json()['mileage_km'] == 25
        assert len(fleet.state.repository.outbox()) == 2
    assert FleetRepository(tmp_path/'fleet.sqlite').vehicle('v-1').mileage_km == 25
    assert TripsRepository(tmp_path/'trips.sqlite').get_trip('t-1').status == 'completed'


def test_viewer_cannot_start_and_human_cannot_impersonate_internal_command(tmp_path):
    fleet, trips = pair(tmp_path)
    command = dict(trip_id='t-1', operation='start', vehicle_id='v-1', driver_id='d-1')
    with TestClient(trips) as client, TestClient(fleet) as f:
        plan(client)
        assert client.post('/trips/t-1/start', headers=service_headers('viewer')).status_code == 403
        for role in ('manager', 'dispatcher', 'viewer', 'bridge'):
            assert f.post('/internal/trip-commands', json=command, headers=service_headers(role)).status_code == 403
        assert f.post('/internal/trip-commands', json=command).status_code == 401
        assert client.post('/trips/t-1/start', headers=service_headers('dispatcher')).status_code == 200


def test_vehicle_is_claimed_atomically_by_only_one_trip(tmp_path):
    repo = FleetRepository(tmp_path/'fleet.sqlite', migration_stage=4)
    def begin(trip_id):
        try:
            repo.execute_lifecycle(trip_id, 'start', 'v-1', 'd-1')
            return True
        except FleetError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(begin, ['first', 'second'])) == [False, True]
    assert len(repo.outbox()) == 1


def test_retry_recovers_after_fleet_commit_and_before_trips_commit(tmp_path, monkeypatch):
    fleet, trips = pair(tmp_path)
    original = trips.state.repository.save_transition
    failed = False
    def fail_once(*args):
        nonlocal failed
        if not failed:
            failed = True
            raise sqlite3.OperationalError('simulated local failure after remote commit')
        return original(*args)
    monkeypatch.setattr(trips.state.repository, 'save_transition', fail_once)
    with TestClient(trips, raise_server_exceptions=False) as client:
        plan(client)
        auth = service_headers('dispatcher')
        assert client.post('/trips/t-1/start', headers=auth).status_code == 500
        assert fleet.state.repository.vehicle('v-1').status.value == 'in_trip'
        assert client.get('/trips/t-1', headers=auth).json()['status'] == 'planned'
        assert client.post('/trips/t-1/start', headers=auth).status_code == 200
        assert len(fleet.state.repository.outbox()) == 1


def test_timeout_does_not_advance_trip_and_retry_after_lost_reply_is_safe(tmp_path):
    class LoseOneReply(httpx.AsyncBaseTransport):
        def __init__(self, app):
            self.inner = httpx.ASGITransport(app=app)
            self.lost = False
        async def handle_async_request(self, request):
            response = await self.inner.handle_async_request(request)
            if request.method == 'POST' and not self.lost:
                self.lost = True
                raise httpx.ReadTimeout('response lost after commit', request=request)
            return response
    fleet = fleet_app(tmp_path/'fleet.sqlite')
    trips = trips_app(tmp_path/'trips.sqlite', fleet_url='http://fleet', fleet_transport=LoseOneReply(fleet))
    with TestClient(trips) as client:
        plan(client)
        auth = service_headers('dispatcher')
        assert client.post('/trips/t-1/start', headers=auth).status_code == 503
        assert trips.state.repository.get_trip('t-1').status == 'planned'
        assert client.post('/trips/t-1/start', headers=auth).status_code == 200
        assert len(fleet.state.repository.outbox()) == 1


def test_driver_is_rechecked_at_actual_departure(tmp_path):
    fleet, trips = pair(tmp_path)
    with TestClient(trips) as client:
        plan(client)
        with closing(sqlite3.connect(tmp_path/'fleet.sqlite')) as db, db:
            db.execute("UPDATE drivers SET license_valid=0 WHERE id='d-1'")
        assert client.post('/trips/t-1/start', headers=service_headers('dispatcher')).status_code == 409
        assert trips.state.repository.get_trip('t-1').status == 'planned'


def test_registration_change_produces_projection_update(tmp_path):
    fleet, trips = pair(tmp_path)
    with TestClient(fleet) as f, TestClient(trips) as t:
        assert f.patch('/vehicles/v-1/registration', json={'plate': 'AA9999BB'}, headers=service_headers('manager')).status_code == 200
        event = fleet.state.repository.outbox()[0]['payload']
        assert t.post('/events/fleet-status', json=event, headers=service_headers('bridge')).json()['applied']
        assert t.get('/snapshots/vehicles/v-1', headers=service_headers('viewer')).json()['plate'] == 'AA9999BB'


@pytest.mark.unit
def test_transition_invariants_without_database():
    t = Trip('t', 'v', 'd', 'r')
    with pytest.raises(DomainError): t.complete_record(10)
    t.start_record()
    with pytest.raises(DomainError): t.start_record()
    with pytest.raises(DomainError): t.complete_record(-1)
    assert t.status == 'active'
    t.complete_record(10)
    assert t.status == 'completed'


@pytest.mark.unit
def test_use_cases_depend_on_in_memory_ports_only():
    class Store:
        def __init__(self): self.items = {}; self.receipts = {}
        def get_trip(self, key):
            item = self.items.get(key)
            return Trip(**item.__dict__) if item else None
        def route_exists(self, key): return key == 'r'
        def create_trip_and_publish(self, trip): self.items[trip.id] = trip; return {'event_id': 'e'}
        def operation_receipt(self, key, op): return self.receipts.get((key, op))
        def save_transition(self, trip, previous, op, distance):
            self.items[trip.id] = trip
            result = {'id': trip.id, 'status': trip.status}
            self.receipts[trip.id, op] = {'distance_km': distance, 'response': result}
            return result
    class Fleet:
        async def check_vehicle_and_driver(self, *args): pass
        async def execute_lifecycle(self, *args): return {}
    store = Store(); cases = TripUseCases(store, Fleet())
    with pytest.raises(MissingResource): asyncio.run(cases.create(Trip('bad', 'v', 'd', 'missing')))
    asyncio.run(cases.create(Trip('t', 'v', 'd', 'r')))
    with pytest.raises(DomainError): asyncio.run(cases.create(Trip('t', 'v', 'd', 'r')))
    with pytest.raises(MissingResource): asyncio.run(cases.transition('missing', 'start'))
    with pytest.raises(DomainError): asyncio.run(cases.transition('t', 'unknown'))
    asyncio.run(cases.transition('t', 'start'))
    assert asyncio.run(cases.transition('t', 'start'))['status'] == 'active'
    asyncio.run(cases.transition('t', 'complete', 10))
    assert store.items['t'].status == 'completed'
    with pytest.raises(DomainError): asyncio.run(cases.transition('t', 'complete', 11))
