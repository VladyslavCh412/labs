"""Tests written before refactoring: public behavior must stay the same."""
import httpx
from tests.support import AuthorizedClient as TestClient
from backend.api import create_app
from backend.trips.fleet_client import FleetClient, FleetRejected
from backend.trips.storage import TripsRepository
from backend.trips.domain import Trip
import pytest


def test_gateway_routes_existing_urls_without_changing_responses():
    requests = []
    def respond(request):
        requests.append(str(request.url))
        return httpx.Response(200, json={'path': request.url.path, 'host': request.url.host})
    app = create_app('http://fleet.test', 'http://trips.test', httpx.MockTransport(respond))
    with TestClient(app) as client:
        assert client.get('/api/fleet/vehicles/v-1').json()['host'] == 'fleet.test'
        assert client.get('/api/fleet/drivers/d-1').json()['host'] == 'fleet.test'
        assert client.get('/api/trips/trips/t-1').json()['host'] == 'trips.test'
        assert client.get('/api/trips/events/outbox').json()['host'] == 'trips.test'
        assert client.get('/api/fleet/missing').status_code == 404
        assert client.get('/api/trips/vehicles/v-1').status_code == 404
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
