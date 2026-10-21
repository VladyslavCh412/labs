"""HTTP presentation adapter (FastAPI); no direct SQLite calls or domain rules."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fleet.application.use_cases import FleetUseCases
from fleet.domain.models import DomainError, Trip, Vehicle


class PlanTripRequest(BaseModel):
    id: str = Field(min_length=1)
    vehicle_id: str = Field(min_length=1)
    driver_id: str = Field(min_length=1)
    route_id: str = Field(min_length=1)


class CompleteTripRequest(BaseModel):
    distance_km: int = Field(ge=0)


class TripResponse(BaseModel):
    id: str
    vehicle_id: str
    driver_id: str
    route_id: str
    status: str


class VehicleResponse(BaseModel):
    id: str
    plate: str
    mileage_km: int
    status: str


def _trip_response(item: Trip) -> TripResponse:
    return TripResponse(
        id=item.id, vehicle_id=item.vehicle_id, driver_id=item.driver_id,
        route_id=item.route_id, status=item.status
    )


def _vehicle_response(item: Vehicle) -> VehicleResponse:
    return VehicleResponse(
        id=item.id, plate=item.plate, mileage_km=item.mileage_km,
        status=item.status.value
    )


def _fail(error: DomainError) -> None:
    message = str(error)
    if 'уже існує' in message:
        raise HTTPException(status_code=409, detail=message)
    if 'не знайдено' in message:
        raise HTTPException(status_code=404, detail=message)
    raise HTTPException(status_code=400, detail=message)


def create_app(use_cases: FleetUseCases) -> FastAPI:
    app = FastAPI(
        title='Автопарк та маршрути — ЛР2',
        description='Навчальне багатошарове ядро: FastAPI + SQLite (варіант 12).',
        version='2.0.0'
    )

    @app.get('/health', tags=['Система'])
    def health():
        return {'status': 'ok', 'storage': 'SQLite'}

    @app.get('/vehicles/{vehicle_id}', response_model=VehicleResponse, tags=['Автопарк'])
    def get_vehicle(vehicle_id: str):
        item = use_cases.vehicles.get(vehicle_id)
        if item is None:
            raise HTTPException(404, detail='ТЗ не знайдено')
        return _vehicle_response(item)

    @app.get('/trips/{trip_id}', response_model=TripResponse, tags=['Рейси'])
    def get_trip(trip_id: str):
        item = use_cases.trips.get(trip_id)
        if item is None:
            raise HTTPException(404, detail='Рейс не знайдено')
        return _trip_response(item)

    @app.post('/trips', status_code=201, response_model=TripResponse, tags=['Рейси'])
    def plan_trip(data: PlanTripRequest):
        try:
            item = use_cases.plan_trip(data.id, data.vehicle_id, data.driver_id, data.route_id)
            return _trip_response(item)
        except DomainError as exc:
            _fail(exc)

    @app.post('/trips/{trip_id}/start', response_model=TripResponse, tags=['Рейси'])
    def start_trip(trip_id: str):
        try:
            return _trip_response(use_cases.start_trip(trip_id))
        except DomainError as exc:
            _fail(exc)

    @app.post('/trips/{trip_id}/complete', response_model=TripResponse, tags=['Рейси'])
    def complete_trip(trip_id: str, data: CompleteTripRequest):
        try:
            return _trip_response(use_cases.finish_trip(trip_id, data.distance_km))
        except DomainError as exc:
            _fail(exc)

    return app
