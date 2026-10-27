"""Reproducible real loopback HTTP benchmark; never uses working data/.

Closed-loop clients, identical DB, payload and authentication before/after.
Reports HTTP p50/p95, repository timing and failures, not an in-memory proxy.
"""
from contextlib import closing
import argparse
import asyncio
import json
import math
import os
import platform
import secrets
import socket
import ssl
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from security import issue_token
from trips_service.repository import TripsRepository


def percentile(values, p):
    return sorted(values)[max(0,math.ceil(len(values)*p)-1)] if values else None


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]


async def stage(url, headers, users, duration):
    import httpx
    latencies=[];segments=[];errors=0;statuses={}
    tls=ssl.create_default_context()
    clients=[httpx.AsyncClient(verify=tls,headers=headers,timeout=20,limits=httpx.Limits(max_connections=1,max_keepalive_connections=1),trust_env=False) for _ in range(users)]
    try:
        await asyncio.gather(*(client.get(url) for client in clients),return_exceptions=True)
        deadline=time.perf_counter()+duration
        async def worker(client):
            nonlocal errors
            while time.perf_counter()<deadline:
                start=time.perf_counter()
                try:
                    r=await client.get(url)
                    statuses[str(r.status_code)]=statuses.get(str(r.status_code),0)+1
                    if r.status_code!=200 or len(r.json())!=50:errors+=1
                    if 'server-timing' in r.headers:
                        segments.append(float(r.headers['server-timing'].split('dur=')[-1]))
                except (httpx.HTTPError,ValueError):errors+=1
                latencies.append((time.perf_counter()-start)*1000)
        start=time.perf_counter();await asyncio.gather(*(worker(client) for client in clients))
        elapsed=time.perf_counter()-start
    finally:
        await asyncio.gather(*(client.aclose() for client in clients))
    return dict(users=users,duration_s=round(elapsed,3),requests=len(latencies),errors=errors,
                error_rate=errors/len(latencies),p50_ms=round(percentile(latencies,.50),3),
                p95_ms=round(percentile(latencies,.95),3),repository_p95_ms=round(percentile(segments,.95),3) if segments else None,
                requests_per_s=round(len(latencies)/elapsed,2),statuses=statuses,
                target_met=percentile(latencies,.95)<=500 and errors==0)


def run(levels=(1,10,50,100,200),duration=3,rows=20000,modes=('baseline','optimized')):
    import httpx
    results={}
    key=secrets.token_urlsafe(48);os.environ['FLEETFLOW_JWT_SECRET']=key
    headers={'Authorization':'Bearer '+issue_token('load-test','dispatcher')}
    with tempfile.TemporaryDirectory(prefix='fleetflow-load-') as tmp:
        db=Path(tmp)/'trips.sqlite';TripsRepository(db)
        with closing(sqlite3.connect(db)) as conn, conn:
            conn.executemany('INSERT INTO trips VALUES(?,?,?,?,?)',
                             ((f't-{i}','v-1','d-1','r-1','planned') for i in range(rows)))
        for mode in modes:
            port=free_port();env=os.environ.copy()
            env.update(FLEETFLOW_JWT_SECRET=key,TRIPS_DB_PATH=str(db),TRIPS_READ_MODE=mode,
                       FLEETFLOW_AUDIT_PATH=str(Path(tmp)/'audit.jsonl'))
            proc=subprocess.Popen([sys.executable,'-m','uvicorn','trips_service.app:app',
                                   '--host','127.0.0.1','--port',str(port),'--no-access-log','--log-level','error'],
                                  cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            try:
                base=f'http://127.0.0.1:{port}'
                for _ in range(100):
                    try:
                        if httpx.get(base+'/health',timeout=.3,trust_env=False).status_code==200:break
                    except httpx.HTTPError:pass
                    if proc.poll() is not None:raise RuntimeError(proc.stderr.read().decode())
                    time.sleep(.05)
                else:raise RuntimeError('HTTP server did not start')
                results[mode]=[]
                for users in levels:
                    measurement=asyncio.run(stage(base+'/trips?active=true&limit=50',headers,users,duration))
                    results[mode].append(measurement)
                    print(mode,json.dumps(measurement),flush=True)
            finally:
                proc.terminate()
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
                proc.stderr.close()
    return dict(environment=dict(python=sys.version.split()[0],platform=platform.platform(),
                                 cpu=platform.processor(),logical_cpus=os.cpu_count(),rows=rows,
                                 users=list(levels),stage_seconds=duration,workers=1,
                                 profile='closed-loop, no think time, one warm-up request per concurrent user',
                                 target='LR1: first 50 active trips, HTTP p95 <= 500 ms at 100 users',
                                 optimization='SQL LIMIT/OFFSET instead of fetchall and Python projection of all rows'),
                results=results)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--duration',type=float,default=3)
    p.add_argument('--levels',default='1,10,50,100,200');p.add_argument('--rows',type=int,default=20000)
    p.add_argument('--output',default='verification/load_results.json');a=p.parse_args()
    result=run(tuple(map(int,a.levels.split(','))),a.duration,a.rows)
    target=ROOT/a.output;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2),encoding='utf-8')
