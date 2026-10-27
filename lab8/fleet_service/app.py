from security import install_security
"""Fleet owns its data; /fleet-events exposes outbox to external delivery worker."""
import os
import sqlite3
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel, Field
from .domain import VehicleStatus, Vehicle, Driver
from .repository import FleetRepository
from .cache import VehicleReadCache

class VehicleCreateBody(BaseModel):
    id: str = Field(min_length=1)
    plate: str = Field(min_length=1)
    status: VehicleStatus = VehicleStatus.AVAILABLE

class DriverCreateBody(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    active: bool = True
    license_valid: bool = True

class RegistrationBody(BaseModel):
    plate: str

class StatusBody(BaseModel):
    status: VehicleStatus

def create_app(db_path=None, cache_ttl=30.0, cache_clock=None, migration_stage=4):
    repo=FleetRepository(db_path or os.getenv('FLEET_DB_PATH','data/fleet.sqlite'),migration_stage=migration_stage)
    cache=VehicleReadCache(cache_ttl,clock=cache_clock)
    app=FastAPI(title='Fleet — ЛР5',version='1.1.0',description='Fleet SQLite; міграції, кешування, outbox')
    app.state.repository=repo
    app.state.vehicle_cache=cache

    @app.get('/health',tags=['Сервіс'])
    def health():return {'service':'fleet','status':'ok'}

    @app.get('/vehicles',tags=['Автопарк'])
    def list_vehicles():return repo.vehicles()

    @app.get('/drivers',tags=['Автопарк'])
    def list_drivers():return repo.drivers()

    @app.post('/vehicles',status_code=201,tags=['Автопарк'])
    def add_vehicle(body:VehicleCreateBody):
        try:
            vehicle=repo.create_vehicle(Vehicle(body.id,body.plate,body.status))
        except (ValueError,sqlite3.IntegrityError) as exc:
            raise HTTPException(409,detail='vehicle_duplicate_or_invalid') from exc
        return {'id':vehicle.id,'plate':vehicle.plate,'status':vehicle.status.value,'version':vehicle.version}

    @app.post('/drivers',status_code=201,tags=['Автопарк'])
    def add_driver(body:DriverCreateBody):
        try:
            driver=repo.create_driver(Driver(**body.model_dump()))
        except (ValueError,sqlite3.IntegrityError) as exc:
            raise HTTPException(409,detail='driver_duplicate_or_invalid') from exc
        return {'id':driver.id,'name':driver.name,'active':driver.active,'license_valid':driver.license_valid}

    @app.get('/vehicles/{vehicle_id}',tags=['Автопарк'])
    def get_vehicle(vehicle_id:str):
        vehicle=cache.get(vehicle_id,repo.vehicle)
        if vehicle is None:raise HTTPException(404,detail='vehicle_not_found')
        return {'id':vehicle.id,'plate':vehicle.plate,'status':vehicle.status.value,'version':vehicle.version}

    @app.get('/drivers/{driver_id}',tags=['Автопарк'])
    def get_driver(driver_id:str):
        d=repo.driver(driver_id)
        if not d:raise HTTPException(404,detail='driver_not_found')
        return {'id':d.id,'name':d.name,'active':d.active,'license_valid':d.license_valid}

    @app.patch('/vehicles/{vehicle_id}/status',tags=['Автопарк'])
    def change_vehicle_status(vehicle_id:str,body:StatusBody):
        v=repo.change_status(vehicle_id,body.status)
        if not v:raise HTTPException(404,detail='vehicle_not_found')
        cache.invalidate(vehicle_id)
        return {'id':v.id,'plate':v.plate,'status':v.status.value,'version':v.version}

    @app.patch('/vehicles/{vehicle_id}/registration',tags=['Автопарк'])
    def change_registration(vehicle_id: str,body: RegistrationBody):
        try: v=repo.change_registration(vehicle_id,body.plate)
        except ValueError as exc:raise HTTPException(422,detail=str(exc)) from exc
        if not v:raise HTTPException(404,detail='vehicle_not_found')
        cache.invalidate(vehicle_id)
        return {'id':v.id,'plate':v.plate,'status':v.status.value,'version':v.version}

    @app.get('/fleet-events/outbox',tags=['Події'])
    def fleet_outbox():return repo.outbox()

    @app.post('/fleet-events/ack/{event_id}',tags=['Події'])
    def ack(event_id:str):
        if not repo.ack_event(event_id):raise HTTPException(404,detail='event_not_found')
        return {'acknowledged':True}

    @app.get('/cache/stats',tags=['Сервіс'])
    def stats():return cache.stats()

    install_security(app, 'fleet')
    return app

app=create_app()
