from fleet.domain.models import Trip, Vehicle, Driver, Route, DomainError
from fleet.domain.repositories import VehicleRepository, TripRepository
class FleetUseCases:
    def __init__(self,vehicles:VehicleRepository,trips:TripRepository,drivers:dict[str,Driver],routes:dict[str,Route]):
        self.vehicles=vehicles;self.trips=trips;self.drivers=drivers;self.routes=routes
    def plan_trip(self,trip_id:str,vehicle_id:str,driver_id:str,route_id:str)->Trip:
        if self.trips.get(trip_id): raise DomainError('Рейс з таким id уже існує')
        if not self.vehicles.get(vehicle_id): raise DomainError('ТЗ не знайдено')
        if driver_id not in self.drivers or not self.drivers[driver_id].can_drive(): raise DomainError('Водій не допущений')
        if route_id not in self.routes: raise DomainError('Маршрут не знайдено')
        item=Trip(trip_id,vehicle_id,driver_id,route_id)
        self.trips.save(item);return item
    def start_trip(self,trip_id:str)->Trip:
        trip=self.trips.get(trip_id)
        if trip is None: raise DomainError('Рейс не знайдено')
        vehicle=self.vehicles.get(trip.vehicle_id)
        trip.activate(vehicle,self.drivers[trip.driver_id])
        self.vehicles.save(vehicle);self.trips.save(trip);return trip
    def finish_trip(self,trip_id:str,distance:int)->Trip:
        trip=self.trips.get(trip_id)
        if trip is None: raise DomainError('Рейс не знайдено')
        vehicle=self.vehicles.get(trip.vehicle_id)
        trip.complete(vehicle,distance)
        self.vehicles.save(vehicle);self.trips.save(trip);return trip
