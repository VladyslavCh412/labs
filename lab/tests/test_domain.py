import pytest
from fleet.domain.models import Vehicle,Driver,Route,Trip,DomainError,VehicleStatus
from fleet.container import build_use_cases

def test_vehicle_has_valid_plate():
    with pytest.raises(DomainError):Vehicle('v','')
def test_negative_mileage_is_rejected():
    with pytest.raises(DomainError):Vehicle('v','AB1',-1)
def test_trip_cannot_begin_twice():
    v=Vehicle('v','AB1');v.begin_trip()
    with pytest.raises(DomainError):v.begin_trip()
def test_maintenance_blocks_trip():
    v=Vehicle('v','AB1');v.start_maintenance()
    with pytest.raises(DomainError):v.begin_trip()
def test_mileage_accumulates():
    v=Vehicle('v','AB1');v.begin_trip();v.finish_trip(18)
    assert v.mileage_km==18 and v.status==VehicleStatus.AVAILABLE
def test_invalid_license():
    v=Vehicle('v','AB1');d=Driver('d','Тест',False);t=Trip('t','v','d','r')
    with pytest.raises(DomainError):t.activate(v,d)
def test_bad_route():
    with pytest.raises(DomainError):Route('r',('Одеса',))
def test_use_case_end_to_end_in_memory():
    c=build_use_cases();item=c.plan_trip('test-end-to-end','v-1','d-1','r-1');assert item.status=='planned'
    assert c.start_trip(item.id).status=='active'
    assert c.finish_trip(item.id,20).status=='completed'
