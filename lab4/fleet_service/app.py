"""Fleet HTTP adapter. Run: python -m uvicorn fleet_service.app:app --port 8101"""
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .domain import VehicleStatus
from .repository import FleetRepository

class StatusBody(BaseModel):
    status: VehicleStatus

def create_app(db_path=None):
    repo = FleetRepository(db_path or os.getenv('FLEET_DB_PATH', 'data/fleet.sqlite'))
    app = FastAPI(title='Fleet — ЛР3', version='1.0.0', description='Власник даних про транспорт і водіїв')

    @app.get('/health', tags=['Сервіс'])
    def health():
        return {'service': 'fleet', 'status': 'ok'}

    @app.get('/vehicles/{vehicle_id}', tags=['Автопарк'])
    def get_vehicle(vehicle_id: str):
        vehicle = repo.vehicle(vehicle_id)
        if not vehicle:
            raise HTTPException(404, detail='vehicle_not_found')
        return {'id': vehicle.id, 'plate': vehicle.plate, 'status': vehicle.status.value, 'version': vehicle.version}

    @app.get('/drivers/{driver_id}', tags=['Автопарк'])
    def get_driver(driver_id: str):
        driver = repo.driver(driver_id)
        if not driver:
            raise HTTPException(404, detail='driver_not_found')
        return {'id': driver.id, 'name': driver.name, 'active': driver.active, 'license_valid': driver.license_valid}

    @app.patch('/vehicles/{vehicle_id}/status', tags=['Автопарк'])
    def change_vehicle_status(vehicle_id: str, request: StatusBody):
        vehicle = repo.change_status(vehicle_id, request.status)
        if not vehicle:
            raise HTTPException(404, detail='vehicle_not_found')
        return {'id': vehicle.id, 'plate': vehicle.plate, 'status': vehicle.status.value, 'version': vehicle.version}

    return app

app = create_app()
