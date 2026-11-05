# Принимает запросы о маршрутах, рейсах, событиях и копиях статусов автомобилей.
from backend.config import database_path
from .read_cache import TripPageCache
from fastapi.responses import JSONResponse
from backend.auth import install_security

"""Trips API. Run: python -m uvicorn backend.trips.api:app --port 8102"""
import os
import sqlite3
from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field
from .domain import Trip, Route, DomainError, MissingResource
from .use_cases import TripUseCases
from datetime import datetime
from typing import Literal
from .fleet_client import FleetRejected, FleetUnavailable
from .factory import TripsComponentsFactory


class TripInput(BaseModel):
    id: str = Field(min_length=1)
    vehicle_id: str = Field(min_length=1)
    driver_id: str = Field(min_length=1)
    route_id: str = Field(min_length=1)


class CompletionInput(BaseModel):
    distance_km: int = Field(ge=0, strict=True)


class RouteInput(BaseModel):
    id: str = Field(min_length=1)
    stops: list[str] = Field(min_length=2)


class VehicleProjection(BaseModel):
    id: str = Field(min_length=1)
    plate: str = Field(min_length=1)
    status: Literal["available", "in_trip", "maintenance"]
    version: int = Field(ge=1, strict=True)


class FleetStatusEvent(BaseModel):
    event_id: str = Field(min_length=1)
    type: Literal["VehicleStatusChanged"]
    occurred_at: datetime
    data: VehicleProjection


def create_app(db_path=None, fleet_url=None, fleet_transport=None, factory=None):
    components = (factory or TripsComponentsFactory()).build(
        db_path or database_path("trips"),
        fleet_url or os.getenv("FLEET_URL", "http://127.0.0.1:8101"),
        fleet_transport,
    )
    repo, client = components.repository, components.fleet_client
    use_cases = TripUseCases(repo, client)
    app = FastAPI(
        title="Trips — FleetFlow",
        version="1.0.0",
        description="Власник даних про рейси та маршрути",
    )

    app.state.repository = repo
    page_cache = TripPageCache()
    app.state.trip_page_cache = page_cache

    @app.get("/health", tags=["Сервіс"])
    def health():
        return {"service": "trips", "status": "ok"}

    @app.get("/trips", tags=["Рейси"])
    def list_trips(
        response: Response,
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
        active: bool = False,
    ):
        import time

        started = time.perf_counter()
        if os.getenv("TRIPS_READ_MODE", "optimized") == "baseline":
            result = repo.trip_page(limit, offset, active, optimized=False)
        else:
            result = page_cache.get(
                (limit, offset, active),
                lambda: repo.trip_page(limit, offset, active, optimized=True),
            )
        timing = f"repository;dur={(time.perf_counter() - started) * 1000:.3f}"
        if os.getenv("TRIPS_READ_MODE", "optimized") == "baseline":
            response.headers["Server-Timing"] = timing
            return result
        return JSONResponse(result, headers={"Server-Timing": timing})

    @app.get("/routes", tags=["Маршрути"])
    def list_routes():
        return repo.routes()

    @app.post("/routes", status_code=201, tags=["Маршрути"])
    def add_route(body: RouteInput):
        try:
            route = repo.create_route(Route(body.id, tuple(body.stops)))
        except (DomainError, sqlite3.IntegrityError) as exc:
            raise HTTPException(409, detail="route_duplicate_or_invalid") from exc
        return {"id": route.id, "stops": list(route.stops)}

    @app.get("/trips/{trip_id}", tags=["Рейси"])
    def trip(trip_id: str):
        result = repo.get_trip(trip_id)
        if not result:
            raise HTTPException(404, detail="trip_not_found")
        return result.__dict__

    @app.post("/trips", status_code=201, tags=["Рейси"])
    async def create_trip(body: TripInput):
        try:
            result = await use_cases.create(Trip(**body.model_dump()))
        except MissingResource as exc:
            raise HTTPException(404, detail=str(exc)) from exc
        except (DomainError, sqlite3.IntegrityError) as exc:
            raise HTTPException(409, detail=str(exc)) from exc
        except FleetRejected as exc:
            raise HTTPException(exc.status_code, detail=exc.message) from exc
        except FleetUnavailable as exc:
            raise HTTPException(503, detail="fleet_service_unavailable") from exc
        page_cache.invalidate()
        return result

    async def transition(trip_id, operation, distance_km=0):
        try:
            result = await use_cases.transition(trip_id, operation, distance_km)
        except MissingResource as exc:
            raise HTTPException(404, detail=str(exc)) from exc
        except DomainError as exc:
            raise HTTPException(409, detail=str(exc)) from exc
        except FleetRejected as exc:
            raise HTTPException(exc.status_code, detail=exc.message) from exc
        except FleetUnavailable as exc:
            raise HTTPException(503, detail="fleet_service_unavailable_retry_same_command") from exc
        page_cache.invalidate()
        return result

    @app.post("/trips/{trip_id}/start", tags=["Рейси"])
    async def start_trip(trip_id: str):
        return await transition(trip_id, "start")

    @app.post("/trips/{trip_id}/complete", tags=["Рейси"])
    async def complete_trip(trip_id: str, body: CompletionInput):
        return await transition(trip_id, "complete", body.distance_km)

    @app.get("/events/outbox", tags=["Події"])
    def outbox():
        return repo.outbox()

    @app.get("/notifications", tags=["Події"])
    def notifications():
        return repo.notifications()

    @app.post("/events/fleet-status", tags=["Події"])
    def on_vehicle_event(event: FleetStatusEvent):
        return {"applied": repo.apply_fleet_event(event.model_dump(mode="json"))}

    @app.get("/snapshots/vehicles", tags=["Події"])
    def vehicle_snapshots():
        return repo.snapshots()

    @app.get("/snapshots/vehicles/{vehicle_id}", tags=["Події"])
    def vehicle_snapshot(vehicle_id: str):
        snapshot = repo.vehicle_snapshot(vehicle_id)
        if snapshot is None:
            raise HTTPException(404, detail="vehicle_snapshot_not_found")
        return snapshot

    @app.get("/events/fleet-processed-count", tags=["Події"])
    def processed_count():
        return {"processed_events": repo.processed_fleet_events()}

    install_security(app, "trips")
    return app


app = create_app()
