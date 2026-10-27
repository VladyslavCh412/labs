"""Real HTTP smoke test of login -> gateway -> owners -> outbox bridge."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import httpx
from security import PASSWORDS
from event_bridge import pump_once
from verification.load_test import free_port


def main():
    checks={};processes=[]
    with tempfile.TemporaryDirectory(prefix='fleetflow-smoke-') as tmp:
        env=os.environ.copy();env['FLEETFLOW_JWT_SECRET']=secrets.token_urlsafe(48)
        os.environ['FLEETFLOW_JWT_SECRET']=env['FLEETFLOW_JWT_SECRET']
        users=Path(tmp)/'users.json'; password=secrets.token_urlsafe(18)
        users.write_text(json.dumps({role:{'role':role,'password_hash':PASSWORDS.hash(password)} for role in ['manager','dispatcher','viewer']}))
        env.update(FLEETFLOW_USERS_PATH=str(users),FLEETFLOW_AUDIT_PATH=str(Path(tmp)/'audit.jsonl'),
                   FLEET_DB_PATH=str(Path(tmp)/'fleet.sqlite'),TRIPS_DB_PATH=str(Path(tmp)/'trips.sqlite'))
        urls={name:f'http://127.0.0.1:{free_port()}' for name in ['fleet','trips','dashboard']}
        env.update(FLEET_URL=urls['fleet'],TRIPS_URL=urls['trips'])
        try:
            for name,module in [('fleet','fleet_service.app:app'),('trips','trips_service.app:app'),('dashboard','dashboard:app')]:
                port=urls[name].rsplit(':',1)[1]
                processes.append(subprocess.Popen([sys.executable,'-m','uvicorn',module,'--host','127.0.0.1','--port',port,'--no-access-log','--log-level','error'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
            with httpx.Client(timeout=5,trust_env=False) as client:
                for name in urls:
                    for _ in range(100):
                        try:
                            if client.get(urls[name]+('/api/health' if name=='dashboard' else '/health')).status_code==200:break
                        except httpx.HTTPError:pass
                        time.sleep(.05)
                    else:raise RuntimeError('service unavailable: '+name)
                base=urls['dashboard'];result=client.post(base+'/auth/token',json={'username':'manager','password':password})
                assert result.status_code==200;checks['password_login']=True
                headers={'Authorization':'Bearer '+result.json()['access_token']}
                assert client.get(urls['fleet']+'/vehicles').status_code==401
                assert client.get(base+'/api/fleet/vehicles').status_code==401
                checks['direct_and_proxy_unauthorized_rejected']=True
                created=client.post(base+'/api/trips/trips',headers=headers,json={'id':'smoke-trip','vehicle_id':'v-1','driver_id':'d-1','route_id':'r-1'})
                assert created.status_code==201,created.text;checks['authenticated_trip_with_service_identity']=True
                assert client.patch(base+'/api/fleet/vehicles/v-1/status',headers=headers,json={'status':'maintenance'}).status_code==200
                delivered=pump_once(urls['fleet'],urls['trips'])
                assert delivered['delivered']==1
                snapshot=client.get(base+'/api/trips/snapshots/vehicles/v-1',headers=headers).json()
                assert snapshot['status']=='maintenance';checks['authenticated_bridge_and_projection']=True
                dispatcher=client.post(base+'/auth/token',json={'username':'dispatcher','password':password}).json()
                denied=client.patch(urls['fleet']+'/vehicles/v-1/status',headers={'Authorization':'Bearer '+dispatcher['access_token']},json={'status':'available'})
                assert denied.status_code==403;checks['direct_role_bypass_rejected']=True
                assert client.get(base+'/').status_code==200 and client.get(base+'/assets/app.js').status_code==200
                checks['dashboard_assets']=True
        finally:
            for proc in processes:proc.terminate()
            for proc in processes:
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
    (ROOT/'verification/live_smoke.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    print('PASS',checks)


if __name__=='__main__':main()
