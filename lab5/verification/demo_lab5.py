"""Live HTTP demo: two real Uvicorn processes, bridge via HTTP, cache and replay.
Runs entirely on localhost and temporary SQLite files. No third-party servers contacted.
"""
import json
import sqlite3
from contextlib import closing
import os
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from event_bridge import pump_once
from fleet_service.migrations import apply_migrations, schema_columns
from fleet_service.repository import FleetRepository
from verification.benchmark_cache import benchmark


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0))
        return s.getsockname()[1]


def live():
    lines=['ЛР5 - архітектура даних (FastAPI + SQLite), справжні локальні HTTP-сервери']
    processes=[]
    opened=[]
    with tempfile.TemporaryDirectory(prefix='lab5_live_') as d:
        tmp=Path(d)
        fleet_db=tmp/'fleet.sqlite'
        trips_db=tmp/'trips.sqlite'
        stages=[]
        # independent DB used only by Fleet
        FleetRepository(fleet_db)
        for version in range(1,5):
            applied=apply_migrations(fleet_db,version)
            stages.append({'stage':version,'applied':applied})
        with closing(sqlite3.connect(fleet_db)) as db, db:
            assert 'plate' not in schema_columns(db)
            assert 'registration_number' in schema_columns(db)
        lines.append('PASS: 4 етапи expand / dual-write / switch-read / contract застосовано; дані збережено.')
        fleet_port,trips_port=free_port(),free_port()
        fleet=f'http://127.0.0.1:{fleet_port}'
        trips=f'http://127.0.0.1:{trips_port}'
        env=os.environ.copy()
        env.update({'FLEET_DB_PATH':str(fleet_db),'TRIPS_DB_PATH':str(trips_db),'FLEET_URL':fleet,'TRIPS_URL':trips})
        def launch(module,port):
            fp=(tmp/f'{module}.log').open('w',encoding='utf-8');opened.append(fp)
            p=subprocess.Popen([sys.executable,'-m','uvicorn',module+':app','--host','127.0.0.1','--port',str(port),'--log-level','warning'],
                               cwd=ROOT,env=env,stdout=fp,stderr=subprocess.STDOUT)
            processes.append(p)
            return p
        try:
            fleet_proc=launch('fleet_service.app',fleet_port)
            trips_proc=launch('trips_service.app',trips_port)
            for uri,p in ((fleet+'/health',fleet_proc),(trips+'/health',trips_proc)):
                end=time.monotonic()+12
                while time.monotonic()<end:
                    if p.poll() is not None:raise RuntimeError(f'{uri} exited: {p.returncode}')
                    try:
                        if httpx.get(uri,timeout=.5).status_code==200:break
                    except httpx.RequestError:pass
                    time.sleep(.1)
                else:raise RuntimeError(f'{uri} not ready')
            lines.append('PASS: Fleet та Trips запущено окремими процесами, health=200.')
            with httpx.Client(timeout=4.0) as c:
                cold=c.get(fleet+'/vehicles/v-1');warm=c.get(fleet+'/vehicles/v-1')
                assert cold.status_code==200 and warm.status_code==200
                stats1=c.get(fleet+'/cache/stats').json()
                assert stats1['hits']>=1
                lines.append(f"PASS: кеш Fleet: hits={stats1['hits']}, misses={stats1['misses']}, TTL={stats1['ttl_seconds']} с.")
                changed_at=time.monotonic()
                updated=c.patch(fleet+'/vehicles/v-1/status',json={'status':'maintenance'})
                assert updated.status_code==200,(updated.status_code,updated.text)
                again=c.get(fleet+'/vehicles/v-1')
                assert again.json()['status']=='maintenance' and again.json()['version']==2
                stats2=c.get(fleet+'/cache/stats').json()
                assert stats2['misses']==stats1['misses']+1
                lines.append('PASS: PATCH змінює статус; наступний GET бачить новий статус (кеш інвалідовано).')
                assert c.get(trips+'/snapshots/vehicles/v-1').status_code==404
                sent=pump_once(fleet,trips,c)
                assert sent['delivered']==1,sent
                snapshot=c.get(trips+'/snapshots/vehicles/v-1')
                assert snapshot.status_code==200 and snapshot.json()['status']=='maintenance'
                lag_ms=round((time.monotonic()-changed_at)*1000,3)
                lines.append(f'PASS: VehicleStatusChanged доставлено через HTTP: Trips зберіг копію; затримка {lag_ms} мс.')
                record=c.get(fleet+'/fleet-events/outbox').json()[0]
                assert record['delivered'] is True
                replay=c.post(trips+'/events/fleet-status',json=record['payload'])
                assert replay.status_code==200 and replay.json()['applied'] is False
                assert c.get(trips+'/events/fleet-processed-count').json()['processed_events']==1
                lines.append('PASS: повтор тієї ж події: applied=false; дублювання відсутнє.')
                # verify original LR3 synchronous workflow has not been broken after migration
                c.patch(fleet+'/vehicles/v-1/status',json={'status':'available'})
                # Via Trips -> Fleet; uses HTTP (two processes)
                created=c.post(trips+'/trips',json={'id':'t-lab5-live','vehicle_id':'v-1','driver_id':'d-1','route_id':'r-1'})
                assert created.status_code==201,(created.status_code,created.text)
                lines.append('PASS: сценарій ЛР3 збережено: створення рейсу через HTTP повертає 201.')
        finally:
            for p in processes:
                if p.poll() is None:p.terminate()
            for p in processes:
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:p.kill();p.wait(timeout=4)
            for f in opened:f.close()
    bench=benchmark(output=True)
    lines.append(f"CACHE benchmark (Python-level, not HTTP): {bench['without_cache_mean_ms']} мс -> {bench['with_cache_mean_ms']} мс ({bench['speedup_mean']}x).")
    lines.append('ВАЖЛИВО: максимальної гарантованої межі eventual consistency немає під час тривалої відмови worker або мережі.')
    result={'migration_stages':stages,'observed_event_lag_ms':lag_ms,'cache_measurement':bench,'checks':lines}
    (ROOT/'verification'/'lab5_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'verification'/'lab5_results.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines))
    print('Log: verification/lab5_results.txt')
    return result

if __name__=='__main__':live()
