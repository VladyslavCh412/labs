"""LR2 business-rule coverage: no database, HTTP or filesystem fixtures."""
import pytest
from fleet_service.domain import Vehicle, VehicleStatus, Driver, DomainError as FleetError
from trips_service.domain import Trip, Route, DomainError


@pytest.mark.parametrize('identifier,plate,km',[('','AA',0),('v',' ',0),('v','AA',-1)])
def test_vehicle_identity_plate_mileage(identifier,plate,km):
    with pytest.raises(FleetError):Vehicle(identifier,plate,mileage_km=km)


@pytest.mark.parametrize('status',[VehicleStatus.IN_TRIP,VehicleStatus.MAINTENANCE])
def test_only_available_vehicle_can_start(status):
    with pytest.raises(FleetError):Vehicle('v','AA',status).begin_trip()


def test_maintenance_cannot_interrupt_trip():
    v=Vehicle('v','AA');v.begin_trip()
    with pytest.raises(FleetError):v.start_maintenance()
    assert v.status==VehicleStatus.IN_TRIP


@pytest.mark.parametrize('active,valid,allowed',[(True,True,True),(True,False,False),(False,True,False),(False,False,False)])
def test_driver_permission(active,valid,allowed):
    assert Driver('d','Name',active=active,license_valid=valid).can_drive() is allowed


@pytest.mark.parametrize('stops',[(),('A',),('A',' ')])
def test_route_requires_two_nonempty_stops(stops):
    with pytest.raises(DomainError):Route('r',stops)


def test_trip_lifecycle_and_mileage():
    v=Vehicle('v','AA',mileage_km=10);d=Driver('d','Name');t=Trip('t','v','d','r')
    t.activate(v,d);assert t.status=='active' and v.status==VehicleStatus.IN_TRIP
    t.complete(v,25);assert t.status=='completed' and v.mileage_km==35 and v.status==VehicleStatus.AVAILABLE


def test_trip_rejects_invalid_transitions_without_side_effects():
    v=Vehicle('v','AA');d=Driver('d','Name');t=Trip('t','v','d','r')
    with pytest.raises(DomainError):t.complete(v,10)
    with pytest.raises(DomainError):t.activate(v,Driver('d','Name',active=False))
    assert v.status==VehicleStatus.AVAILABLE and t.status=='planned'
    t.activate(v,d)
    with pytest.raises(DomainError):t.activate(v,d)
    with pytest.raises(FleetError):t.complete(v,-1)
    assert t.status=='active' and v.mileage_km==0


@pytest.mark.parametrize('position',range(4))
def test_trip_requires_all_identifiers(position):
    ids=['t','v','d','r'];ids[position]=''
    with pytest.raises(DomainError):Trip(*ids)


def test_vehicle_finish_requires_active_trip_and_nonnegative_distance():
    v=Vehicle('v','AA')
    with pytest.raises(FleetError):v.finish_trip(1)
    v.start_maintenance();assert v.status==VehicleStatus.MAINTENANCE


def test_valid_route_preserves_stop_order():
    assert Route('r',('A','B')).stops==('A','B')
