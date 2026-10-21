# Launch: python -m services.trips_service (port 8102). Separate Trips DB.
import os,json,sqlite3,urllib.request,urllib.error
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from services.security import verify
from services.events import publish
DB=os.environ.get('TRIPS_DB','trips.db');FLEET_URL=os.environ.get('FLEET_URL','http://127.0.0.1:8101')
class Handler(BaseHTTPRequestHandler):
    def send(self,code,data):
        raw=json.dumps(data,ensure_ascii=False).encode();self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)))
        self.end_headers();self.wfile.write(raw)
    def do_POST(self):
        if self.path!='/trips':return self.send(404,{'error':'not_found'})
        try:verify(self.headers.get('Authorization','').removeprefix('Bearer '),['dispatcher'])
        except PermissionError:return self.send(403,{'error':'forbidden'})
        try:
            body=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
            req=urllib.request.Request(FLEET_URL+'/vehicles/'+body['vehicle_id'],headers={'Authorization':self.headers.get('Authorization','')})
            with urllib.request.urlopen(req,timeout=0.35) as response: vehicle=json.load(response)
            if vehicle['status']!='available':return self.send(409,{'error':'vehicle_not_available'})
        except (urllib.error.URLError,TimeoutError,ConnectionError):return self.send(503,{'error':'fleet_service_unavailable'})
        except (KeyError,ValueError):return self.send(400,{'error':'bad_request'})
        with sqlite3.connect(DB) as db:
            db.execute('CREATE TABLE IF NOT EXISTS trips(id TEXT PRIMARY KEY,vehicle_id TEXT NOT NULL,status TEXT NOT NULL)')
            try:db.execute('INSERT INTO trips VALUES (?,?,?)',(body['id'],body['vehicle_id'],'planned'))
            except sqlite3.IntegrityError:return self.send(409,{'error':'duplicate_id'})
        publish(DB,'TripCreated',{'id':body['id'],'vehicle_id':body['vehicle_id']})
        return self.send(201,{'id':body['id'],'status':'planned'})
if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',8102),Handler).serve_forever()
