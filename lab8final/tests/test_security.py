import json
import time

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient
from fleet_service.app import create_app as fleet_app
from trips_service.app import create_app as trips_app
from security import issue_token, secret, ISSUER, AUDIENCE, PASSWORDS
from dashboard import create_app as dashboard_app


def auth(role):
    return {'Authorization':'Bearer '+issue_token('test-'+role,role)}


@pytest.mark.parametrize('service,path', [('fleet','/vehicles/v-1'),('trips','/trips')])
def test_direct_owner_rejects_missing_forged_and_expired_tokens(tmp_path,service,path):
    app=(fleet_app if service=='fleet' else trips_app)(tmp_path/(service+'.sqlite'))
    with TestClient(app) as c:
        assert c.get(path).status_code==401
        token=issue_token('x','manager')
        assert c.get(path,headers={'Authorization':'Bearer '+token[:-8]+'forgedxx'}).status_code==401
        assert c.get(path,headers={'Authorization':'Bearer '+issue_token('x','manager',ttl=-1)}).status_code==401
        assert c.get(path,headers=auth('viewer')).status_code==200


@pytest.mark.parametrize('claim,value',[('aud','other'),('iss','other'),('role','root')])
def test_invalid_claims_rejected(tmp_path,claim,value):
    payload=dict(sub='x',role='manager',iss=ISSUER,aud=AUDIENCE,iat=int(time.time()),exp=int(time.time())+60,jti='test')
    payload[claim]=value
    token=jwt.encode(payload,secret(),algorithm='HS256')
    with TestClient(fleet_app(tmp_path/'f.sqlite')) as c:
        assert c.get('/vehicles',headers={'Authorization':'Bearer '+token}).status_code==401


def test_roles_at_both_owners_and_internal_event_boundary(tmp_path):
    with TestClient(fleet_app(tmp_path/'f.sqlite')) as f, TestClient(trips_app(tmp_path/'t.sqlite')) as t:
        body={'status':'maintenance'}
        assert f.patch('/vehicles/v-1/status',json=body,headers=auth('dispatcher')).status_code==403
        assert f.patch('/vehicles/v-1/status',json=body,headers=auth('manager')).status_code==200
        route={'id':'r-new','stops':['A','B']}
        assert t.post('/routes',json=route,headers=auth('viewer')).status_code==403
        assert t.post('/routes',json=route,headers=auth('dispatcher')).status_code==201
        event=f.get('/fleet-events/outbox',headers=auth('bridge')).json()[0]['payload']
        assert t.post('/events/fleet-status',json=event,headers=auth('manager')).status_code==403
        assert t.post('/events/fleet-status',json=event,headers=auth('bridge')).json()['applied']
        assert t.post('/events/fleet-status',json=event,headers=auth('bridge')).json()['applied'] is False
        assert f.get('/vehicles',headers=auth('bridge')).status_code==403


def test_login_hashing_and_rate_limit(tmp_path,monkeypatch):
    users=tmp_path/'users.json'; users.write_text(json.dumps({'manager':{'role':'manager','password_hash':PASSWORDS.hash('a-test-password')}}))
    monkeypatch.setenv('FLEETFLOW_USERS_PATH',str(users))
    with TestClient(dashboard_app()) as c:
        result=c.post('/auth/token',json={'username':'manager','password':'a-test-password'})
        assert result.status_code==200 and result.headers['cache-control']=='no-store'
        assert result.json()['expires_in']==900
        assert 'a-test-password' not in users.read_text()
        for _ in range(9):assert c.post('/auth/token',json={'username':'unknown','password':'bad'}).status_code==401
        assert c.post('/auth/token',json={'username':'manager','password':'bad'}).status_code==429


def test_denial_is_audited_without_token_or_password(tmp_path,monkeypatch):
    path=tmp_path/'audit.jsonl';monkeypatch.setenv('FLEETFLOW_AUDIT_PATH',str(path))
    with TestClient(fleet_app(tmp_path/'f.sqlite')) as c:
        before=time.time();assert c.get('/vehicles?password=do-not-log',headers={'Authorization':'Bearer supersecret'}).status_code==401
    event=json.loads(path.read_text().splitlines()[-1])
    assert event['outcome']=='denied' and event['time']-before<2
    assert 'supersecret' not in path.read_text() and 'do-not-log' not in path.read_text()


def test_proxy_forwards_identity_and_does_not_bypass_ownership(tmp_path):
    from tests.test_dashboard import LocalServices
    fleet=fleet_app(tmp_path/'f.sqlite');trips=trips_app(tmp_path/'t.sqlite')
    with TestClient(dashboard_app('http://fleet','http://trips',LocalServices(fleet,trips))) as c:
        assert c.get('/api/fleet/vehicles').status_code==401
        assert c.get('/api/fleet/vehicles',headers=auth('dispatcher')).status_code==200
        assert c.patch('/api/fleet/vehicles/v-1/status',json={'status':'maintenance'},headers=auth('dispatcher')).status_code==403
