"""Trips API. Run: python -m uvicorn trips_service.app:app --port 8102"""
import os
import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .domain import Trip
from .repository import TripsRepository
from .fleet_client import FleetClient, FleetRejected, FleetUnavailable

class TripInput(BaseModel):
    id: str = Field(min_length=1)
    vehicle_id: str = Field(min_length=1)
    driver_id: str = Field(min_length=1)
    route_id: str = Field(min_length=1)

def create_app(db_path=None, fleet_url=None, fleet_transport=None):
    repo = TripsRepository(db_path or os.getenv('TRIPS_DB_PATH', 'data/trips.sqlite'))
    client = FleetClient(fleet_url or os.getenv('FLEET_URL', 'http://127.0.0.1:8101'), timeout=0.35, transport=fleet_transport)
    app = FastAPI(title='Trips — ЛР3', version='1.0.0', description='Власник даних про рейси та маршрути')

    @app.get('/health', tags=['Сервіс'])
    def health():
        return {'service': 'trips', 'status': 'ok'}

    @app.get('/trips/{trip_id}', tags=['Рейси'])
    def trip(trip_id: str):
        result = repo.get_trip(trip_id)
        if not result:
            raise HTTPException(404, detail='trip_not_found')
        return result.__dict__

    @app.post('/trips', status_code=201, tags=['Рейси'])
    async def create_trip(body: TripInput):
        if repo.get_trip(body.id):
            raise HTTPException(409, detail='duplicate_trip_id')
        if not repo.route_exists(body.route_id):
            raise HTTPException(404, detail='route_not_found')
        try:
            await client.check_vehicle_and_driver(body.vehicle_id, body.driver_id)
        except FleetRejected as exc:
            raise HTTPException(exc.status_code, detail=exc.message) from exc
        except FleetUnavailable as exc:
            raise HTTPException(503, detail='fleet_service_unavailable') from exc
        trip = Trip(**body.model_dump())
        try:
            event = repo.create_trip_and_publish(trip)
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409, detail='duplicate_trip_id') from exc
        return {'id': trip.id, 'status': trip.status, 'event_id': event['event_id']}

    @app.get('/events/outbox', tags=['Події'])
    def outbox():
        return repo.outbox()

    @app.get('/notifications', tags=['Події'])
    def notifications():
        return repo.notifications()

    return app

app = create_app()
