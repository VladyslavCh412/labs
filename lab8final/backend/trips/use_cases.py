# Сценарии создания, начала и завершения рейса. Координирует правила и обращения к Fleet.
"""Application use cases depend only on domain entities and ports."""

from .domain import Trip, TripStore, FleetGateway, DomainError, MissingResource


class TripUseCases:
    def __init__(self, repository: TripStore, fleet: FleetGateway):
        self.repository, self.fleet = repository, fleet

    async def create(self, trip: Trip):
        if self.repository.get_trip(trip.id):
            raise DomainError("duplicate_trip_id")
        if not self.repository.route_exists(trip.route_id):
            raise MissingResource("route_not_found")
        await self.fleet.check_vehicle_and_driver(trip.vehicle_id, trip.driver_id)
        event = self.repository.create_trip_and_publish(trip)
        return {"id": trip.id, "status": trip.status, "event_id": event["event_id"]}

    async def transition(self, trip_id, operation, distance_km=0):
        receipt = self.repository.operation_receipt(trip_id, operation)
        if receipt:
            if receipt["distance_km"] != distance_km:
                raise DomainError("idempotency_payload_conflict")
            return receipt["response"]
        trip = self.repository.get_trip(trip_id)
        if trip is None:
            raise MissingResource("trip_not_found")
        previous = trip.status
        if operation == "start":
            trip.start_record()
        elif operation == "complete":
            trip.complete_record(distance_km)
        else:
            raise DomainError("unknown_operation")
        # A lost response is recovered by retry: Fleet persists command receipts.
        await self.fleet.execute_lifecycle(
            trip.id, operation, trip.vehicle_id, trip.driver_id, distance_km
        )
        return self.repository.save_transition(trip, previous, operation, distance_km)
