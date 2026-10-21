"""Reproducible SQLite single-host lab bench; NOT HTTP/DRF/100-client production benchmark."""
import tempfile,sqlite3,time,statistics,json,concurrent.futures
from pathlib import Path
from services.cache import TTLCache

def percentile(samples,p):
    s=sorted(samples)
    return round(s[max(0,min(len(s)-1,int((len(s)-1)*p)))],3)

def prepare(db):
    with sqlite3.connect(db) as cn:
        cn.execute('CREATE TABLE trips(id INTEGER PRIMARY KEY, vehicle_id TEXT, status TEXT, started_at INTEGER)')
        cn.executemany('INSERT INTO trips(vehicle_id,status,started_at) VALUES (?,?,?)',[(f'v-{i%220}',('active' if i%3 else 'planned'),i) for i in range(12000)])

def query(db):
    with sqlite3.connect(db) as cn:
        return cn.execute("SELECT id,vehicle_id,status FROM trips WHERE status='active' ORDER BY started_at DESC LIMIT 50").fetchall()

def run():
    with tempfile.TemporaryDirectory() as td:
        db=Path(td)/'trips.db';prepare(db)
        cache=TTLCache(300)
        def measure(fn,n=200):
            out=[]
            for _ in range(n):
                t=time.perf_counter();fn();out.append((time.perf_counter()-t)*1000)
            return {'n':n,'p50_ms':percentile(out,.5),'p95_ms':percentile(out,.95),'p99_ms':percentile(out,.99)}
        before=measure(lambda:query(db))
        cached=measure(lambda:cache.get('active:50',lambda:query(db)))
        with sqlite3.connect(db) as cn:
            cn.execute('CREATE INDEX idx_trips_status_started ON trips(status,started_at DESC)')
        indexed=measure(lambda:query(db))
        # Concurrent *local SQLite calls*, not HTTP users.
        concurrent_results=[]
        for workers in [1,10,30,50]:
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                fut=[pool.submit(lambda:measure(lambda:query(db),1)['p50_ms']) for _ in range(100)]
                vals=[f.result() for f in fut]
            concurrent_results.append({'workers':workers,'n':100,'p50_ms':percentile(vals,.5),'p95_ms':percentile(vals,.95)})
        return {'without_cache':before,'with_cache':cached,'indexed':indexed,'concurrency_local':concurrent_results}
if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False,indent=2))
