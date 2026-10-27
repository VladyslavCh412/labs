"""Local trust boundary shared by independently enforcing resource owners.

Only bootstrap/login hold account hashes. Services validate exp/iss/aud and
apply their own allowlist. HS256 means mutually trusted local services; see ADR.
"""
import json
import logging
import os
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from threading import Lock

import jwt
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pwdlib import PasswordHash

ISSUER = 'fleetflow-local'
AUDIENCE = 'fleetflow-api'
TTL = 900
PASSWORDS = PasswordHash.recommended()
AUDIT = logging.getLogger('fleetflow.audit')


def secret():
    value = os.environ.get('FLEETFLOW_JWT_SECRET', '')
    if len(value) < 32:
        raise RuntimeError('Run setup_local.py or launch.py: signing key is not configured')
    return value


def issue_token(subject, role, ttl=TTL):
    now = int(time.time())
    return jwt.encode(dict(sub=subject, role=role, iss=ISSUER, aud=AUDIENCE,
                           iat=now, exp=now+ttl, jti=str(uuid.uuid4())), secret(), algorithm='HS256')


def verify_token(token):
    try:
        claims = jwt.decode(token, secret(), algorithms=['HS256'], issuer=ISSUER,
                            audience=AUDIENCE,
                            options={'require': ['sub', 'role', 'iss', 'aud', 'iat', 'exp', 'jti']})
        if claims['role'] not in {'manager', 'dispatcher', 'viewer', 'trips-service', 'bridge'}:
            raise ValueError('unknown role')
        return claims
    except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
        raise HTTPException(401, 'invalid_or_expired_token', headers={'WWW-Authenticate': 'Bearer'}) from exc


def service_headers(role):
    return {'Authorization': 'Bearer '+issue_token(role, role)}


def audit(service, outcome, subject='anonymous', method='', path='', status=0):
    # Never log Authorization, passwords, bodies or URL query values.
    record = dict(time=time.time(), service=service, outcome=outcome,
                  subject=subject, method=method, path=path, status=status)
    line = json.dumps(record, ensure_ascii=True)
    AUDIT.info(line)
    destination = os.getenv('FLEETFLOW_AUDIT_PATH')
    if destination:
        p = Path(destination); p.parent.mkdir(parents=True, exist_ok=True)
        with p.open('a', encoding='utf-8') as stream:
            stream.write(line+'\n')


def allowed(service, method, path, role):
    if service == 'fleet':
        if path.startswith('/fleet-events/'):
            return role == 'bridge' or (method == 'GET' and role in {'manager','dispatcher','viewer'})
        if method == 'GET':
            return role in {'manager','dispatcher','viewer','trips-service'}
        return role == 'manager'
    if service == 'trips':
        if path == '/events/fleet-status':
            return role == 'bridge'
        if method == 'GET':
            return role in {'manager','dispatcher','viewer'}
        return role in {'manager','dispatcher'}
    return False


def install_security(app, service):
    # Middleware protects future routes by default, including direct service calls.
    @app.middleware('http')
    async def resource_owner_guard(request, call_next):
        path=request.url.path
        if path in {'/health', '/docs', '/redoc', '/openapi.json', '/docs/oauth2-redirect'}:
            return await call_next(request)
        header=request.headers.get('authorization','')
        try:
            if not header.startswith('Bearer '):
                raise HTTPException(401,'authentication_required')
            claims=verify_token(header[7:])
            if not allowed(service, request.method, path, claims['role']):
                raise HTTPException(403,'insufficient_permissions')
        except HTTPException as exc:
            audit(service,'denied',method=request.method,path=path,status=exc.status_code)
            return JSONResponse({'detail':exc.detail},status_code=exc.status_code,
                                headers={'WWW-Authenticate':'Bearer'} if exc.status_code==401 else {})
        request.state.principal=claims
        result=await call_next(request)
        if request.method != 'GET':
            audit(service,'mutation',claims['sub'],request.method,path,result.status_code)
        result.headers['X-Content-Type-Options']='nosniff'
        return result


class LoginLimiter:
    def __init__(self):
        self.attempts=defaultdict(deque); self.lock=Lock()

    def check(self, address):
        with self.lock:
            now=time.monotonic(); q=self.attempts[address]
            while q and q[0] < now-60: q.popleft()
            if len(q)>=10: raise HTTPException(429,'login_rate_limit',headers={'Retry-After':'60'})
            q.append(now)


def authenticate(username, password):
    path=Path(os.environ['FLEETFLOW_USERS_PATH'])
    users=json.loads(path.read_text(encoding='utf-8'))
    user=users.get(username)
    # Dummy Argon2 hash avoids a fast path for nonexistent accounts.
    candidate=user or users['manager']
    valid=PASSWORDS.verify(password,candidate['password_hash'])
    if not user or not valid:
        audit('auth','login_failed',status=401)
        raise HTTPException(401,'invalid_credentials')
    audit('auth','login_success',username,status=200)
    return {'access_token':issue_token(username,user['role']), 'token_type':'bearer',
            'expires_in':TTL, 'role':user['role'], 'username':username}
