"""Isolated test configuration, not a production authentication bypass."""
import os
import secrets
import tempfile
from pathlib import Path

_test_data = tempfile.TemporaryDirectory(prefix='fleetflow-tests-')
os.environ['FLEETFLOW_JWT_SECRET']=secrets.token_urlsafe(48)
os.environ['FLEET_DB_PATH']=str(Path(_test_data.name)/'fleet.sqlite')
os.environ['TRIPS_DB_PATH']=str(Path(_test_data.name)/'trips.sqlite')
os.environ['FLEETFLOW_AUDIT_PATH']=str(Path(_test_data.name)/'audit.jsonl')


def pytest_collection_modifyitems(items):
    import pytest
    for item in items:
        name=item.nodeid
        if 'test_domain' in name or ('test_read_cache' in name and 'test_trip_write' not in name): level='unit'
        elif 'test_contract' in name: level='contract'
        elif 'test_fitness' in name: level='architecture'
        elif 'test_security' in name or 'test_dashboard' in name: level='integration'
        else:
            level='unit' if any(x in name for x in ['domain_invariants','adapter','strategy','fleet_client_keeps','fleet_client_still','cache_hits']) else 'integration'
        item.add_marker(getattr(pytest.mark,level))
