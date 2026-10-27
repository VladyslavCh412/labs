from pathlib import Path
from verification.fitness import check_domain_purity, check_cycles

ROOT=Path(__file__).resolve().parents[1]


def test_static_domain_imports():
    assert check_domain_purity(ROOT)==[]


def test_static_no_cycles():
    assert check_cycles(ROOT)==[]


def test_rule_detects_injected_import_and_cycle(tmp_path):
    service=tmp_path/'fleet_service';service.mkdir()
    (service/'domain.py').write_text('import sqlite3\nfrom . import repository\n')
    assert check_domain_purity(tmp_path)
    (service/'domain.py').write_text('from .repository import Store\n')
    (service/'repository.py').write_text('from .domain import Vehicle\n')
    assert check_cycles(tmp_path)


def test_dynamic_http_p95_at_100_users():
    from verification.load_test import run
    # Actual socket HTTP: independent server process and temporary SQLite.
    result=run(levels=(100,),duration=3,rows=5000, modes=('optimized',))
    measurement=result['results']['optimized'][0]
    import json
    (ROOT/'verification/fitness_measurement.json').write_text(json.dumps(measurement,indent=2))
    assert measurement['errors']==0
    assert measurement['requests']>=100
    assert measurement['p95_ms']<=500,measurement
