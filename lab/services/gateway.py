# Gateway: forwards requests, hides service topology, authenticates every request locally as well.
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib import request,error
from services.security import verify,issue
import json
class Gateway(BaseHTTPRequestHandler):
    def respond(self,code,obj):
        raw=json.dumps(obj).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(raw)
    def do_POST(self):
        if self.path=='/auth/demo':
            body=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
            if body.get('username')=='demo' and body.get('password')=='change-me':return self.respond(200,{'access_token':issue('demo','dispatcher')})
            return self.respond(401,{'error':'invalid_credentials'})
        self.proxy('POST')
    def do_GET(self):self.proxy('GET')
    def proxy(self,method):
        try:verify(self.headers.get('Authorization','').removeprefix('Bearer '))
        except PermissionError:return self.respond(401,{'error':'invalid_token'})
        host='http://127.0.0.1:'+('8101' if self.path.startswith('/vehicles/') else '8102')
        body=self.rfile.read(int(self.headers.get('Content-Length','0'))) if method=='POST' else None
        req=request.Request(host+self.path,data=body,method=method,headers={'Authorization':self.headers.get('Authorization',''),'Content-Type':'application/json'})
        try:
            with request.urlopen(req,timeout=0.6) as r:out=r.read();code=r.status
        except error.HTTPError as e:out=e.read();code=e.code
        except (error.URLError,TimeoutError):return self.respond(503,{'error':'downstream_unavailable'})
        self.send_response(code);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(out)
if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',8100),Gateway).serve_forever()
