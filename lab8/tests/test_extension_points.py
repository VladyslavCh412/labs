"""Supplementary tests for the new abstractions; original LR3 tests are unchanged."""
from gateway_routing import FleetRoutes, TripsRoutes, resolve_target
from trips_service.fleet_adapter import FleetResponseAdapter
from trips_service.factory import TripsComponentsFactory
from trips_service.observers import TripEventPublisher, NotificationObserver
from trips_service.repository import TripsRepository
from trips_service.domain import Trip


def test_strategy_is_extensible():
    assert resolve_target('vehicles/v-1','fleet','trips')=='fleet'
    assert resolve_target('trips','fleet','trips')=='trips'
    assert resolve_target('missing','fleet','trips') is None
    assert FleetRoutes().target('drivers/d-1','F','T')=='F'
    assert TripsRoutes().target('events/outbox','F','T')=='T'


def test_adapter_creates_domain_facing_values():
    adapter=FleetResponseAdapter()
    assert adapter.vehicle({'status':'available'}).status=='available'
    assert adapter.driver({'active':True,'license_valid':False}).license_valid is False


def test_factory_builds_separate_components(tmp_path):
    components=TripsComponentsFactory().build(tmp_path/'t.sqlite','http://localhost:8101')
    assert isinstance(components.repository,TripsRepository)
    assert components.fleet_client.base_url=='http://localhost:8101'


def test_observer_notifies_subscribers_without_duplicate_delivery(tmp_path):
    recorded=[]
    class RecordingObserver:
        def on_trip_created(self, db, event):
            recorded.append(event['data']['id'])
    repo=TripsRepository(tmp_path/'trips.sqlite', publisher=TripEventPublisher([NotificationObserver(),RecordingObserver()]))
    repo.create_trip_and_publish(Trip('t-obs','v-1','d-1','r-1'))
    assert repo.deliver_pending()==1
    assert repo.deliver_pending()==0
    assert recorded==['t-obs']
    assert len(repo.notifications())==1
