"""Same entry point locally and in GitHub Actions; nonzero stops the build."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from verification.fitness import check_domain_purity, check_cycles


def main():
    p=argparse.ArgumentParser();p.add_argument('--static-only',action='store_true');a=p.parse_args()
    errors=check_domain_purity(ROOT)+check_cycles(ROOT)
    if errors:
        print('ARCHITECTURE FAILED\n'+'\n'.join(errors),flush=True);return 1
    print('Static fitness: PASS',flush=True)
    if a.static_only:return 0
    result=subprocess.call([sys.executable,'-m','pytest','-q','--durations=0',
                            '-k','not test_dynamic_http_p95_at_100_users',
                            '--junitxml=verification/test_results.xml',
                            '--cov=fleet_service.domain','--cov=trips_service.domain',
                            '--cov-report=term-missing','--cov-report=json:verification/coverage.json',
                            '--cov-fail-under=95'],cwd=ROOT)
    if result:return result
    return subprocess.call([sys.executable,'-m','pytest','-q','-s',
                            'tests/test_fitness.py::test_dynamic_http_p95_at_100_users',
                            '--junitxml=verification/fitness_results.xml'],cwd=ROOT)


if __name__=='__main__':raise SystemExit(main())
