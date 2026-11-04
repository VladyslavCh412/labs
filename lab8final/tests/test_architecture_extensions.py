import json
from pathlib import Path

from fastapi.testclient import TestClient
from backend.auth import service_headers
from backend.trips.api import create_app
from checks.fitness import check_cycles, check_application_dependencies


def test_relative_from_package_import_cannot_hide_a_cycle(tmp_path):
    package = tmp_path/'fleet_service'
    package.mkdir()
    (package/'domain.py').write_text('from . import repository\n')
    (package/'repository.py').write_text('from . import domain\n')
    assert check_cycles(tmp_path)


def test_application_imports_only_domain_ports(tmp_path):
    package = tmp_path/'trips_service'
    package.mkdir()
    target = package/'application.py'
    target.write_text('from .domain import Trip\n')
    assert check_application_dependencies(tmp_path) == []
    target.write_text('from .repository import TripsRepository\n')
    assert check_application_dependencies(tmp_path)


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
