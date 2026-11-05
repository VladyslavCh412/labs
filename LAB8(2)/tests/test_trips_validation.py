from fastapi.testclient import TestClient
from backend.auth import service_headers
from backend.trips.api import create_app


def test_malformed_projection_is_rejected_before_inbox_write(tmp_path):
    app = create_app(tmp_path/'trips.sqlite')
    with TestClient(app) as client:
        response = client.post('/events/fleet-status', headers=service_headers('bridge'),
            json={'event_id':'bad', 'type':'VehicleStatusChanged',
                  'occurred_at':'2026-11-03T10:00:00Z',
                  'data':{'id':'v-1','plate':'AA','status':'unknown','version':-1}})
        assert response.status_code == 422
        assert app.state.repository.processed_fleet_events() == 0


def test_start_of_missing_trip_returns_404(tmp_path):
    with TestClient(create_app(tmp_path/'trips.sqlite')) as client:
        assert client.post('/trips/missing/start', headers=service_headers('dispatcher')).status_code == 404
