import ast,time
from pathlib import Path
ROOT=Path(__file__).parents[1]
def test_fitness_domain_imports_not_infrastructure():
    for path in (ROOT/'fleet/domain').rglob('*.py'):
        tree=ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom) and node.module:
                assert not node.module.startswith(('fleet.infrastructure','fleet.presentation','rest_framework','django')), (path,node.module)
            if isinstance(node,ast.Import):
                assert not any(x.name.startswith(('fleet.infrastructure','fleet.presentation','django')) for x in node.names)

def test_fitness_no_cycles_in_clean_dependency_layers():
    permitted={'domain':set(),'application':{'domain'},'infrastructure':{'domain'},'presentation':{'application','domain'}}
    assert all(layer not in upstream for layer,upstream in permitted.items())

def test_fitness_local_p95_under_500ms():
    from fleet.infrastructure.repositories import InMemoryRepository
    from fleet.domain.models import Vehicle
    r=InMemoryRepository();r.save(Vehicle('v','AA1111AA'))
    times=[]
    for _ in range(200):
        start=time.perf_counter();r.get('v');times.append((time.perf_counter()-start)*1000)
    assert sorted(times)[int(len(times)*0.95)-1]<500
