"""Standalone entry point for the final FleetFlow product."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import shutil

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT


def build_frontend(env, install=False):
    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    if not npm:
        raise SystemExit('Install Node.js 24 LTS (including npm) to build the TypeScript frontend.')
    frontend = PROJECT / 'frontend'
    if install:
        subprocess.run([npm, 'ci', '--no-audit', '--no-fund'], cwd=frontend, env=env, check=True)
    subprocess.run([npm, 'run', 'build'], cwd=frontend, env=env, check=True)


def main():
    parser = argparse.ArgumentParser(description='FleetFlow: labs 1-8')
    parser.add_argument('command', nargs='?', default='start',
                        choices=['setup', 'start', 'test', 'verify', 'benchmark'])
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    python = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    env = os.environ.copy()
    # Keep temporary files on the same drive as the checkout (C: may be full).
    temporary = ROOT / '.runtime' / 'tmp'
    temporary.mkdir(parents=True, exist_ok=True)
    env.update(TEMP=str(temporary), TMP=str(temporary), TMPDIR=str(temporary),
               PIP_CACHE_DIR=str(ROOT / '.runtime' / 'pip-cache'),
               npm_config_cache=str(ROOT / '.runtime' / 'npm-cache'), PYTHONUTF8='1')
    if args.command == 'setup':
        if not python.exists():
            subprocess.run([sys.executable, '-m', 'venv', str(ROOT/'.venv')], check=True, env=env)
        result = subprocess.call([str(python), '-m', 'pip', 'install', '-r', str(PROJECT/'requirements-lock.txt')], env=env)
        if result: return result
        build_frontend(env, install=True)
        return 0
    if not python.exists():
        parser.error('Run python run.py setup first.')
    if args.command in {'start', 'test', 'verify'}:
        build_frontend(env)
    commands = {
        'start': ['launch.py'] + (['--no-browser'] if args.no_browser else []),
        'test': ['-m', 'pytest', '-q', '-k', 'not test_dynamic_http_p95_at_100_users'],
        'verify': ['verification/pipeline.py'],
        'benchmark': ['verification/load_test.py'],
    }
    result = subprocess.call([str(python)] + commands[args.command], cwd=PROJECT, env=env)
    if result == 0 and args.command == 'verify':
        result = subprocess.call([str(python), 'verification/negative_pipeline.py'], cwd=PROJECT, env=env)
    return result


if __name__ == '__main__':
    raise SystemExit(main())
