"""Sync service boundary: Trips sees Fleet only through its public HTTP API."""
import httpx

class FleetUnavailable(Exception):
    pass

class FleetRejected(Exception):
    def __init__(self, status_code, message):
        self.status_code, self.message = status_code, message

class FleetClient:
    def __init__(self, base_url, timeout=0.35, transport=None):
        self.base_url, self.timeout, self.transport = base_url.rstrip('/'), timeout, transport

    async def get_json(self, path):
        try:
            async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
                response = await client.get(self.base_url + path)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise FleetUnavailable('fleet_service_unavailable') from exc
        if response.status_code in (404, 409):
            raise FleetRejected(response.status_code, 'not_found_or_conflict')
        if response.status_code >= 500:
            raise FleetUnavailable('fleet_service_unavailable')
        if response.status_code >= 400:
            raise FleetRejected(response.status_code, 'fleet_request_rejected')
        return response.json()

    async def check_vehicle_and_driver(self, vehicle_id, driver_id):
        vehicle = await self.get_json('/vehicles/' + vehicle_id)
        driver = await self.get_json('/drivers/' + driver_id)
        if vehicle['status'] != 'available':
            raise FleetRejected(409, 'vehicle_not_available')
        if not driver['active'] or not driver['license_valid']:
            raise FleetRejected(409, 'driver_not_allowed')
        return vehicle, driver
