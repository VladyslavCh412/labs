import time,pytest,yaml
from pathlib import Path
from services.security import issue,verify
from services.patterns import *

def test_token_signature_and_expiry():
    token=issue('d','dispatcher');assert verify(token,['dispatcher'])['sub']=='d'
    with pytest.raises(PermissionError):verify(token+'BAD')
    with pytest.raises(PermissionError):verify(issue('d','dispatcher',-1))

def test_role_restricted():
    with pytest.raises(PermissionError):verify(issue('m','manager'),['dispatcher'])

def test_provider_contract():
    spec=yaml.safe_load((Path(__file__).parents[1]/'contracts/openapi.yaml').read_text())
    op=spec['paths']['/vehicles/{vehicle_id}']['get']
    required=op['responses']['200']['content']['application/json']['schema']['required']
    assert set(required)=={'id','plate','status'}
    assert {'403','404','503'}.issubset(op['responses'])

def test_patterns():
    assert TariffContext(StandardTariff()).quote(10)==200
    assert TariffContext(ExpressTariff()).quote(10)==300
    assert NotificationFactory.make('email').send('ok')=='email:ok'
    class Legacy:
        def get_route(self,p):return {'distance_km':15}
    assert LegacyMapsAdapter(Legacy()).distance('A','B')==15
    received=[];bus=EventBus();bus.subscribe('VehicleUpdated',received.append)
    bus.publish('VehicleUpdated',{'id':'v'});assert received==[{'id':'v'}]
