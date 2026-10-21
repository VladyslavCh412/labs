"""HTTP adapter, use-case integration and actual SQLite persistence."""
import sqlite3
from fastapi.testclient import TestClient
from fleet.container import build_sqlite_use_cases
from fleet.presentation.api import create_app


def client_for(tmp_path):
    db_path = tmp_path / 'fleet.sqlite'
    return TestClient(create_app(build_sqlite_use_cases(db_path))), db_path


def test_fastapi_trip_lifecycle_and_persistence(tmp_path):
    client, db_path = client_for(tmp_path)
    assert client.get('/health').json() == {'status': 'ok', 'storage': 'SQLite'}
    payload = {'id': 't-101', 'vehicle_id': 'v-1', 'driver_id': 'd-1', 'route_id': 'r-1'}
    response = client.post('/trips', json=payload)
    assert response.status_code == 201
    assert response.json()['status'] == 'planned'
    assert client.post('/trips/t-101/start').json()['status'] == 'active'
    response = client.post('/trips/t-101/complete', json={'distance_km': 25})
    assert response.status_code == 200
    assert response.json()['status'] == 'completed'
    vehicle = client.get('/vehicles/v-1')
    assert vehicle.json()['mileage_km'] == 25
    assert vehicle.json()['status'] == 'available'
    with sqlite3.connect(db_path) as con:
        assert con.execute("SELECT status FROM trips WHERE id='t-101'").fetchone()[0] == 'completed'
    # A new application object can still read persisted vehicle and trip data.
    restarted = TestClient(create_app(build_sqlite_use_cases(db_path)))
    assert restarted.get('/trips/t-101').json()['status'] == 'completed'
    assert restarted.get('/vehicles/v-1').json()['mileage_km'] == 25


def test_fastapi_invariants_and_errors(tmp_path):
    client, _ = client_for(tmp_path)
    payload = {'id': 't-102', 'vehicle_id': 'v-1', 'driver_id': 'd-1', 'route_id': 'r-1'}
    assert client.post('/trips', json=payload).status_code == 201
    assert client.post('/trips', json=payload).status_code == 409
    assert client.post('/trips/missing/start').status_code == 404
    assert client.post('/trips/t-102/complete', json={'distance_km': 1}).status_code == 400
    assert client.post('/trips/t-102/complete', json={'distance_km': -2}).status_code == 422
    assert client.post('/trips/t-102/start').status_code == 200
    assert client.post('/trips/t-102/start').status_code == 400
    other = dict(payload, id='t-103')
    assert client.post('/trips', json=other).status_code == 201
    assert client.post('/trips/t-103/start').status_code == 400


def test_openapi_and_domain_independence(tmp_path):
    client, _ = client_for(tmp_path)
    schema = client.get('/openapi.json').json()
    assert '/trips' in schema['paths']
    assert '/trips/{trip_id}/complete' in schema['paths']
    assert client.get('/docs').status_code == 200


def test_real_layer_dependency_directions():
    """AST check over actual code, not a hard-coded list of allowed layers."""
    import ast
    from pathlib import Path
    source_root = Path(__file__).resolve().parents[1] / 'fleet'
    forbidden = {
        'domain': ('fleet.application', 'fleet.infrastructure', 'fleet.presentation',
                   'fastapi', 'sqlalchemy', 'sqlite3', 'django'),
        'application': ('fleet.infrastructure', 'fleet.presentation',
                        'fastapi', 'sqlite3', 'django'),
        'infrastructure': ('fleet.application', 'fleet.presentation', 'fastapi', 'django'),
        'presentation': ('fleet.infrastructure', 'sqlite3', 'django'),
    }
    for layer, disallowed in forbidden.items():
        for path in (source_root / layer).rglob('*.py'):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                modules = []
                if isinstance(node, ast.ImportFrom) and node.module:
                    modules = [node.module]
                elif isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                for name in modules:
                    assert not name.startswith(disallowed), (path.name, layer, name)
