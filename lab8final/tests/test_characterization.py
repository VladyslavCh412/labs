"""Tests written before refactoring: public behavior must stay the same."""
import httpx
from tests.support import AuthorizedClient as TestClient
import gateway
from trips_service.fleet_client import FleetClient, FleetRejected
from trips_service.repository import TripsRepository
from trips_service.domain import Trip
import pytest


def test_gateway_routes_existing_urls_without_changing_responses(monkeypatch):
    monkeypatch.setattr(gateway, 'FLEET_URL', 'http://fleet.test')
    monkeypatch.setattr(gateway, 'TRIPS_URL', 'http://trips.test')
    requests = []
    def respond(request):
        requests.append(str(request.url))
        return httpx.Response(200, json={'path':request.url.path,'host':request.url.host})
    real_client = gateway.httpx.AsyncClient
    def mocked_client(*args, **kwargs):
        return real_client(*args, transport=httpx.MockTransport(respond), **kwargs)
    monkeypatch.setattr(gateway.httpx, 'AsyncClient', mocked_client)
    with TestClient(gateway.app) as client:
        assert client.get('/vehicles/v-1').json()['host'] == 'fleet.test'
        assert client.get('/drivers/d-1').json()['host'] == 'fleet.test'
        assert client.get('/trips/t-1').json()['host'] == 'trips.test'
        assert client.get('/events/outbox').json()['host'] == 'trips.test'
        assert client.get('/missing').status_code == 404
    assert len(requests) == 4


@pytest.mark.anyio
async def test_fleet_client_keeps_existing_response_contract():
    def respond(request):
        if request.url.path.startswith('/vehicles/'):
            return httpx.Response(200, json={'id':'v-1','plate':'BH1234AA','status':'available','version':1})
        return httpx.Response(200, json={'id':'d-1','name':'Olena','active':True,'license_valid':True})
    client=FleetClient('http://fleet',transport=httpx.MockTransport(respond))
    vehicle,driver=await client.check_vehicle_and_driver('v-1','d-1')
    assert vehicle['status']=='available'
    assert driver['license_valid'] is True


@pytest.mark.anyio
async def test_fleet_client_still_rejects_maintenance():
    def respond(request):
        if request.url.path.startswith('/vehicles/'):
            return httpx.Response(200, json={'id':'v-1','plate':'BH1234AA','status':'maintenance','version':1})
        return httpx.Response(200, json={'id':'d-1','name':'Olena','active':True,'license_valid':True})
    client=FleetClient('http://fleet',transport=httpx.MockTransport(respond))
    with pytest.raises(FleetRejected) as err:
        await client.check_vehicle_and_driver('v-1','d-1')
    assert err.value.status_code==409


def test_trip_event_notification_text_and_idempotence(tmp_path):
    repo=TripsRepository(tmp_path/'trips.sqlite')
    trip=Trip('t-before','v-1','d-1','r-1')
    event=repo.create_trip_and_publish(trip)
    assert repo.deliver_pending()==1
    assert repo.deliver_pending()==0
    assert repo.notifications()==[{'event_id':event['event_id'],'trip_id':'t-before','message':'Заплановано рейс t-before'}]

@pytest.fixture
def anyio_backend():
    return "asyncio"
