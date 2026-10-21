# Educational HMAC token; in production use audited Django authentication/JWT library and key rotation.
import hmac,hashlib,base64,json,time,os
SECRET=os.environ.get('FLEET_TOKEN_KEY','test-only-change-me').encode()
def _b64(raw):return base64.urlsafe_b64encode(raw).rstrip(b'=')
def issue(subject,role,ttl=900):
    payload=_b64(json.dumps({'sub':subject,'role':role,'exp':int(time.time())+ttl},separators=(',',':')).encode())
    signature=_b64(hmac.new(SECRET,payload,hashlib.sha256).digest())
    return payload.decode()+'.'+signature.decode()
def verify(token,roles=None):
    try:
        payload,signature=token.split('.')
        signed=_b64(hmac.new(SECRET,payload.encode(),hashlib.sha256).digest()).decode()
        if not hmac.compare_digest(signature,signed):raise ValueError('bad signature')
        claims=json.loads(base64.urlsafe_b64decode(payload+'='*(-len(payload)%4)))
        if claims['exp']<=int(time.time()):raise ValueError('expired')
        if roles and claims['role'] not in roles:raise PermissionError('forbidden')
        return claims
    except (ValueError,KeyError,TypeError) as e:raise PermissionError('invalid token') from e
