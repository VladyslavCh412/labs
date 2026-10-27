"""Inject a forbidden import into a disposable copy; run the REAL pipeline gate."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix='fleetflow-negative-') as tmp:
        copy=Path(tmp)
        for name in ['fleet_service','trips_service','verification']:
            shutil.copytree(ROOT/name,copy/name,ignore=shutil.ignore_patterns('__pycache__','*.json','*.xml','*.txt'))
        original=(ROOT/'fleet_service/domain.py').read_bytes()
        f=copy/'fleet_service/domain.py';f.write_text('import sqlite3\n'+f.read_text(encoding='utf-8'),encoding='utf-8')
        result=subprocess.run([sys.executable,str(copy/'verification/pipeline.py'),'--static-only'],cwd=copy,capture_output=True,text=True)
        assert result.returncode==1 and 'forbidden domain import sqlite3' in result.stdout
        assert (ROOT/'fleet_service/domain.py').read_bytes()==original
        evidence={'command':'python verification/pipeline.py --static-only (disposable source copy)',
                  'injected':'fleet_service/domain.py: import sqlite3','returncode':result.returncode,
                  'stdout':result.stdout,'stderr':result.stderr,'original_source_unchanged':True}
        (ROOT/'verification/negative_pipeline.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
        (ROOT/'verification/negative_pipeline.log').write_text(result.stdout+result.stderr,encoding='utf-8')
        print(result.stdout);print('PASS: real gate rejected violation; original source unchanged')


if __name__=='__main__':main()
