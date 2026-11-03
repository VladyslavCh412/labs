"""Old LR3–5 assertions stay intact; this helper supplies new credentials only.

New security tests use the unmodified FastAPI TestClient with explicit tokens.
"""
from fastapi.testclient import TestClient
from security import issue_token


class AuthorizedClient(TestClient):
    def request(self, method, url, **kwargs):
        role='bridge' if str(url).endswith('/events/fleet-status') else 'manager'
        headers=dict(kwargs.pop('headers',None) or {})
        headers.setdefault('Authorization','Bearer '+issue_token('regression-test',role))
        return super().request(method,url,headers=headers,**kwargs)
