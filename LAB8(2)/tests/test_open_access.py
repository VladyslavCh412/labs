"""Default local use needs no account; the optional security profile still works."""
import httpx
from fastapi.testclient import TestClient

from backend.api import create_app as dashboard_app
from backend.fleet.api import create_app as fleet_app
from backend.trips.api import create_app as trips_app
from tests.test_dashboard import LocalServices


def test_default_anonymous_gateway_lifecycle_has_no_login(tmp_path, monkeypatch):
    monkeypatch.delenv('FLEETFLOW_AUTH_REQUIRED')
    fleet = fleet_app(tmp_path/'fleet.sqlite', migration_stage=4)
    trips = trips_app(tmp_path/'trips.sqlite', fleet_url='http://fleet',
                      fleet_transport=httpx.ASGITransport(app=fleet))
    ui = dashboard_app('http://fleet', 'http://trips', LocalServices(fleet, trips))
    with TestClient(ui) as client:
        assert client.get('/api/config').json() == {'auth_required': False}
        index = client.get('/')
        assert 'loginPanel' not in index.text and 'loginForm' not in index.text
        assert 'loginPassword' not in index.text and 'logoutBtn' not in index.text
        assert index.headers['cache-control'] == 'no-store'
        assert '/assets/app.js?v=' in index.text
        assert client.get('/assets/app.js').headers['cache-control'] == 'no-store'
        assert client.post('/api/fleet/vehicles', json={'id':'open-v', 'plate':'BH1234OP'}).status_code == 201
        assert client.post('/api/fleet/drivers', json={'id':'open-d', 'name':'Local driver'}).status_code == 201
        assert client.post('/api/trips/routes', json={'id':'open-r', 'stops':['Odesa','Kyiv']}).status_code == 201
        body = dict(id='open-t', vehicle_id='open-v', driver_id='open-d', route_id='open-r')
        assert client.post('/api/trips/trips', json=body).status_code == 201
        assert client.post('/api/trips/trips/open-t/start').json()['status'] == 'active'
        for _ in range(2):
            assert client.post('/api/trips/trips/open-t/complete', json={'distance_km':25}).json()['status'] == 'completed'
        vehicle = client.get('/api/fleet/vehicles/open-v').json()
        assert vehicle['status'] == 'available' and vehicle['mileage_km'] == 25
        assert client.get('/api/trips/trips/open-t').json()['status'] == 'completed'


def test_open_api_and_internal_command_boundaries_match(tmp_path, monkeypatch):
    monkeypatch.delenv('FLEETFLOW_AUTH_REQUIRED')
    with TestClient(fleet_app(tmp_path/'fleet.sqlite')) as fleet, TestClient(trips_app(tmp_path/'trips.sqlite')) as trips:
        spec = fleet.get('/openapi.json').json()['paths']
        assert not spec['/vehicles']['get'].get('security')
        assert not spec['/vehicles']['post'].get('security')
        assert not spec['/fleet-events/outbox']['get'].get('security')
        assert spec['/internal/trip-commands']['post']['security']
        assert fleet.post('/internal/trip-commands', json={}).status_code == 401
        assert fleet.post('/fleet-events/ack/unknown').status_code == 401
        assert trips.post('/events/fleet-status', json={}).status_code == 401
        assert trips.get('/trips').status_code == 200
        assert not trips.get('/openapi.json').json()['paths']['/trips']['get'].get('security')


def test_opt_in_profile_advertises_and_requires_login(tmp_path, monkeypatch):
    monkeypatch.setenv('FLEETFLOW_AUTH_REQUIRED', '1')
    with TestClient(dashboard_app()) as ui, TestClient(fleet_app(tmp_path/'fleet.sqlite')) as fleet:
        assert ui.get('/api/config').json() == {'auth_required': True}
        assert 'loginForm' not in ui.get('/').text
        assert fleet.get('/vehicles').status_code == 401
        assert fleet.get('/openapi.json').json()['paths']['/vehicles']['get']['security']


def test_open_user_actions_do_not_need_account_files_or_jwt_key(tmp_path, monkeypatch):
    monkeypatch.delenv('FLEETFLOW_AUTH_REQUIRED')
    monkeypatch.delenv('FLEETFLOW_USERS_PATH', raising=False)
    monkeypatch.delenv('FLEETFLOW_JWT_SECRET')
    with TestClient(fleet_app(tmp_path/'fleet.sqlite')) as client:
        assert client.get('/vehicles', headers={'Authorization':'Bearer stale-token'}).status_code == 200
        result = client.post('/drivers', json={'id':'no-account', 'name':'Local driver'})
        assert result.status_code == 201
