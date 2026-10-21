"""Local real-process demonstration of failure, sync timeout, and authorization."""
import subprocess,os,time,urllib.request,urllib.error,json,tempfile,sys
from pathlib import Path
from services.security import issue
root=Path(__file__).parent

def request(method,path,token=None,data=None):
    payload=json.dumps(data).encode() if data is not None else None
    headers={'Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    req=urllib.request.Request('http://127.0.0.1:8100'+path,payload,headers,method=method)
    t=time.perf_counter()
    try:
        with urllib.request.urlopen(req,timeout=2) as r:code=r.status;body=json.load(r)
    except urllib.error.HTTPError as e:code=e.code;body=json.load(e)
    return {'code':code,'body':body,'elapsed_ms':round((time.perf_counter()-t)*1000,2)}

def run():
    with tempfile.TemporaryDirectory() as td:
        env=os.environ.copy();env['PYTHONPATH']=str(root);env['FLEET_DB']=str(Path(td)/'fleet.db');env['TRIPS_DB']=str(Path(td)/'trips.db');env['FLEET_TOKEN_KEY']='test-only-change-me'
        procs=[]
        def spawn(module):
            p=subprocess.Popen([sys.executable,'-m',module],cwd=root,env=env,stdout=open(str(Path(td)/(module.split(".")[-1]+".log")),"w"),stderr=subprocess.STDOUT)
            procs.append(p);time.sleep(.55);print(module,p.poll(),file=sys.stderr)
            return p
        try:
            fleet=spawn('services.fleet_service');spawn('services.trips_service');spawn('services.gateway')
            disp=issue('demo','dispatcher');manager=issue('demo','manager')
            result={'healthy':request('GET','/vehicles/v-1',disp),'no_token':request('GET','/vehicles/v-1'),'manager_cannot_create_trip':request('POST','/trips',manager,{'id':'t-1','vehicle_id':'v-1'}),'trip_created':request('POST','/trips',disp,{'id':'t-1','vehicle_id':'v-1'})}
            fleet.terminate();fleet.wait(timeout=3)
            result['fleet_offline_trip_attempt']=request('POST','/trips',disp,{'id':'t-2','vehicle_id':'v-1'})
            return result
        finally:
            for p in reversed(procs):
                if p.poll() is None:p.terminate()
            for p in procs:
                try:p.wait(timeout=2)
                except subprocess.TimeoutExpired:p.kill()
if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False,indent=2))
