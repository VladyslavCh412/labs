# Launch: python -m services.fleet_service (port 8101). Independent Fleet DB.
import os,sqlite3,json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit
from services.security import verify
DB=os.environ.get('FLEET_DB','fleet.db')
class Handler(BaseHTTPRequestHandler):
    def send(self,code,data):
        raw=json.dumps(data,ensure_ascii=False).encode();self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)))
        self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        try:verify(self.headers.get('Authorization','').removeprefix('Bearer '),['dispatcher','manager'])
        except PermissionError:return self.send(403,{'error':'forbidden'})
        if urlsplit(self.path).path.startswith('/vehicles/'):
            ident=self.path.split('/')[-1]
            with sqlite3.connect(DB) as db:
                db.execute('CREATE TABLE IF NOT EXISTS vehicles(id TEXT PRIMARY KEY, plate TEXT NOT NULL,status TEXT NOT NULL)')
                row=db.execute('SELECT id,plate,status FROM vehicles WHERE id=?',(ident,)).fetchone()
            return self.send(200,dict(zip(('id','plate','status'),row))) if row else self.send(404,{'error':'not_found'})
        return self.send(404,{'error':'not_found'})
if __name__=='__main__':
    with sqlite3.connect(DB) as db:db.execute("CREATE TABLE IF NOT EXISTS vehicles(id TEXT PRIMARY KEY,plate TEXT NOT NULL,status TEXT NOT NULL)");db.execute("INSERT OR IGNORE INTO vehicles VALUES ('v-1','BH1234AA','available')")
    ThreadingHTTPServer(('127.0.0.1',8101),Handler).serve_forever()
