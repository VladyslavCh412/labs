"""Same SQLite database and input across un-cached / cached read measurements.
Timing measures Python repository lookup vs in-process TTL cache, NOT remote HTTP.
"""
import json
import statistics
import sys
import tempfile
from pathlib import Path
from time import perf_counter_ns

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from fleet_service.repository import FleetRepository
from fleet_service.cache import VehicleReadCache


def benchmark(n=1000,output=True):
    with tempfile.TemporaryDirectory(prefix='lab5_bench_') as d:
        repo=FleetRepository(Path(d)/'fleet.sqlite',migration_stage=4)
        cache=VehicleReadCache(ttl_seconds=60.0)
        # warm the OS file cache for a fair repeatable comparison
        for i in range(30):repo.vehicle('v-1')
        uncached=[]
        cached=[]
        for i in range(n):
            start=perf_counter_ns()
            value=repo.vehicle('v-1')
            uncached.append((perf_counter_ns()-start)/1_000_000)
            assert value.id=='v-1'
        cache.get('v-1',repo.vehicle) # warm cache once
        for i in range(n):
            start=perf_counter_ns()
            value=cache.get('v-1',repo.vehicle)
            cached.append((perf_counter_ns()-start)/1_000_000)
            assert value.id=='v-1'
        result={
            'method':'local Python repository lookup vs in-process cache hit (not HTTP RTT)',
            'iterations_per_group':n,
            'without_cache_mean_ms':round(statistics.mean(uncached),6),
            'without_cache_p95_ms':round(sorted(uncached)[int(.95*(n-1))],6),
            'with_cache_mean_ms':round(statistics.mean(cached),6),
            'with_cache_p95_ms':round(sorted(cached)[int(.95*(n-1))],6),
            'speedup_mean':round(statistics.mean(uncached)/statistics.mean(cached),2),
            'cache_stats':cache.stats(),
        }
    if output:
        p=ROOT/'verification'/'cache_benchmark.json'
        p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('CACHE: no-cache',result['without_cache_mean_ms'],'ms; hit',result['with_cache_mean_ms'],
              'ms; factor',result['speedup_mean'],'x')
        print('Metrics:',p.relative_to(ROOT))
    return result

if __name__=='__main__':benchmark()
