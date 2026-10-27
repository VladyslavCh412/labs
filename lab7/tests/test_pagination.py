import sqlite3
from contextlib import closing
from trips_service.repository import TripsRepository


def test_optimization_preserves_page_projection_order_and_filter(tmp_path):
    repo=TripsRepository(tmp_path/'trips.sqlite')
    with closing(sqlite3.connect(repo.path)) as db,db:
        db.executemany('INSERT INTO trips VALUES(?,?,?,?,?)',
                       [(f't-{i}','v-1','d-1','r-1','completed' if i%3==0 else 'planned') for i in range(300)])
    for active in [True,False]:
        for offset in [0,50,250,1000]:
            assert repo.trip_page(50,offset,active,True)==repo.trip_page(50,offset,active,False)
    assert len(repo.trip_page())==50
