"""Dashboard uses HTTP between contexts; there is no shared database."""
import httpx
from fastapi.testclient import TestClient
from dashboard import create_app as dashboard_app
from fleet_service.app import create_app as fleet_app
from trips_service.app import create_app as trips_app


class LocalServices(httpx.AsyncBaseTransport):
    def __init__(self,fleet,trips):
        self.transports={
            'fleet':httpx.ASGITransport(app=fleet),
            'trips':httpx.ASGITransport(app=trips),
        }
    async def handle_async_request(self,request):
        return await self.transports[request.url.host].handle_async_request(request)


def test_dashboard_endpoints_work_with_independent_services(tmp_path):
    fleet=fleet_app(tmp_path/'fleet.sqlite',migration_stage=4)
    trips=trips_app(tmp_path/'trips.sqlite',fleet_url='http://fleet',
                    fleet_transport=httpx.ASGITransport(app=fleet))
    ui=dashboard_app('http://fleet','http://trips',LocalServices(fleet,trips))
    with TestClient(ui) as client:
        index=client.get('/')
        assert index.status_code==200 and 'FleetFlow' in index.text
        assert client.get('/assets/app.js').status_code==200
        assert client.get('/api/health').json()=={'fleet':True,'trips':True}
        vehicles=client.get('/api/fleet/vehicles').json()
        assert len(vehicles)>=3
        assert any(item['id']=='v-1' for item in vehicles)
        assert client.post('/api/fleet/vehicles',json={'id':'v-test','plate':'BH7777AA','status':'available'}).status_code==201
        assert any(item['id']=='v-test' for item in client.get('/api/fleet/vehicles').json())
        assert client.post('/api/fleet/drivers',json={'id':'d-test','name':'Марія'}).status_code==201
        assert client.post('/api/trips/routes',json={'id':'r-test','stops':['Одеса','Київ']}).status_code==201
        created=client.post('/api/trips/trips',json={'id':'t-test','vehicle_id':'v-1','driver_id':'d-test','route_id':'r-test'})
        assert created.status_code==201,created.text
        assert len(client.get('/api/trips/trips').json())==1
        before=client.get('/api/fleet/cache/stats').json()
        client.get('/api/fleet/vehicles/v-1')
        client.get('/api/fleet/vehicles/v-1')
        after=client.get('/api/fleet/cache/stats').json()
        assert after['hits']>=before['hits']+1
        changed=client.patch('/api/fleet/vehicles/v-1/status',json={'status':'maintenance'})
        assert changed.status_code==200
        assert client.get('/api/fleet/vehicles/v-1').json()['status']=='maintenance'
        outbox=client.get('/api/fleet/fleet-events/outbox').json()
        assert len(outbox)==1 and outbox[0]['payload']['type']=='VehicleStatusChanged'
        event=outbox[0]['payload']
        assert client.post('/api/trips/events/fleet-status',json=event).json()['applied'] is True
        assert client.post('/api/trips/events/fleet-status',json=event).json()['applied'] is False
        snapshots=client.get('/api/trips/snapshots/vehicles').json()
        assert snapshots[0]['status']=='maintenance'
        assert client.get('/api/evil/anything').status_code==404
