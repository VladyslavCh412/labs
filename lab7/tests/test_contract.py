import asyncio
import json
from pathlib import Path
import httpx
import pytest
from jsonschema import validate, ValidationError
from fastapi.testclient import TestClient
from security import service_headers
from fleet_service.app import create_app
from trips_service.fleet_client import FleetClient, FleetRejected, FleetUnavailable

CONTRACT=json.loads((Path(__file__).resolve().parents[1]/'contracts/fleet_consumer.json').read_text())


def test_provider_satisfies_independent_consumer_contract(tmp_path):
    with TestClient(create_app(tmp_path/'fleet.sqlite')) as provider:
        for item in CONTRACT['interactions']:
            response=provider.get(item['path'],headers=service_headers('trips-service'))
            assert response.status_code==200
            validate(response.json(),item['schema'])
        assert provider.get('/vehicles/missing',headers=service_headers('trips-service')).status_code==CONTRACT['missing_resource_status']
        assert provider.get('/vehicles/v-1').status_code==401


def test_consumer_uses_contract_without_running_provider():
    calls=[]
    responses={'/vehicles/v-1':{'id':'v-1','plate':'AA','status':'available','version':1},
               '/drivers/d-1':{'id':'d-1','name':'N','active':True,'license_valid':True}}
    def respond(request):
        calls.append(request.url.path)
        assert request.headers['authorization'].startswith('Bearer ')
        body=responses[request.url.path]
        item=next(i for i in CONTRACT['interactions'] if i['path']==request.url.path)
        validate(body,item['schema'])
        return httpx.Response(200,json=body)
    client=FleetClient('http://provider',transport=httpx.MockTransport(respond))
    vehicle,driver=asyncio.run(client.check_vehicle_and_driver('v-1','d-1'))
    assert vehicle['id']=='v-1' and driver['active'] and len(calls)==2


def test_breaking_provider_shape_is_detected():
    schema=CONTRACT['interactions'][0]['schema']
    with pytest.raises(ValidationError):validate({'id':'v-1','status':'available'},schema)


@pytest.mark.parametrize('status',[404,409,503])
def test_consumer_errors_are_bounded(status):
    client=FleetClient('http://provider',transport=httpx.MockTransport(lambda r:httpx.Response(status,json={'detail':'failure'})))
    with pytest.raises(FleetUnavailable if status==503 else FleetRejected):
        asyncio.run(client.get_json('/vehicles/missing'))


def test_consumer_timeout_mapping():
    def timeout(request):raise httpx.ReadTimeout('simulated',request=request)
    client=FleetClient('http://provider',timeout=CONTRACT['availability_timeout_seconds'],transport=httpx.MockTransport(timeout))
    with pytest.raises(FleetUnavailable):asyncio.run(client.get_json('/vehicles/v-1'))
