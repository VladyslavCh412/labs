"""Rebuild/check the checked-in provider specifications without working databases."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='fleetflow-contracts-') as temp:
        # These files describe the explicitly enabled JWT/RBAC profile.
        os.environ['FLEETFLOW_AUTH_REQUIRED'] = '1'
        os.environ['FLEET_DB_PATH'] = str(Path(temp)/'fleet.sqlite')
        os.environ['TRIPS_DB_PATH'] = str(Path(temp)/'trips.sqlite')
        from fleet_service.app import app as fleet
        from trips_service.app import app as trips
        for name, app in [('fleet', fleet), ('trips', trips)]:
            path = ROOT/'contracts'/f'{name}.secured.openapi.json'
            schema = app.openapi()
            if args.write:
                path.write_text(json.dumps(schema, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
            elif json.loads(path.read_text(encoding='utf-8')) != schema:
                raise SystemExit(f'{path.name} is stale; run verification/export_contracts.py --write')
    print('OpenAPI provider contracts: PASS')


if __name__ == '__main__':
    main()
