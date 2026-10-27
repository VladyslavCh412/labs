from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock
import time

import httpx
from tests.support import AuthorizedClient
from fleet_service.app import create_app as fleet_app
from trips_service.app import create_app as trips_app
from trips_service.read_cache import TripPageCache


def test_cache_expiry_and_capacity():
    ticks=[0.0];calls=[]
    cache=TripPageCache(ttl=1,capacity=2,clock=lambda:ticks[0])
    def loader():
        calls.append(1);return len(calls)
    assert cache.get(('a',),loader)==1
    assert cache.get(('a',),loader)==1
    ticks[0]=1.01
    assert cache.get(('a',),loader)==2
    assert cache.get(('b',),loader)==3
    assert cache.get(('c',),loader)==4
    assert cache.get(('a',),loader)==5


def test_concurrent_reads_share_one_load():
    cache=TripPageCache();barrier=Barrier(8);count=[0];lock=Lock()
    def loader():
        with lock:count[0]+=1
        time.sleep(.02)
        return [{'id':'same-page'}]
    def worker(_):
        barrier.wait();return cache.get((50,0,True),loader)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(worker,range(8)))
    assert count[0]==1
    assert all(result==[{'id':'same-page'}] for result in results)


def test_trip_write_invalidates_cached_page(tmp_path):
    fleet=fleet_app(tmp_path/'fleet.sqlite')
    trips=trips_app(tmp_path/'trips.sqlite',fleet_url='http://fleet',fleet_transport=httpx.ASGITransport(app=fleet))
    with AuthorizedClient(trips) as client:
        assert client.get('/trips?active=true&limit=50').json()==[]
        assert client.get('/trips?limit=1').json()==[]
        result=client.post('/trips',json={'id':'t-cached','vehicle_id':'v-1','driver_id':'d-1','route_id':'r-1'})
        assert result.status_code==201
        assert client.get('/trips?active=true&limit=50').json()[0]['id']=='t-cached'
        assert client.get('/trips?limit=1').json()[0]['id']=='t-cached'
