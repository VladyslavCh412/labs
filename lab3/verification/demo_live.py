"""Real subprocess and HTTP lab demo, including Fleet outage and delayed event delivery.
Run: python verification/demo_live.py; generated report verification/live_demo_results.txt.
"""
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def wait_for(url, process, timeout=12):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f'Process exited early: {url}')
        try:
            r = httpx.get(url, timeout=0.5)
            if r.status_code == 200:
                return
        except httpx.RequestError:
            pass
        time.sleep(0.15)
    raise RuntimeError(f'Service did not start: {url}')


def run():
    processes = []
    lines = ['ЛР3 — реальний HTTP-експеримент (FastAPI + SQLite)', 'Запуск: незалежні процеси Fleet, Trips, Gateway; подію доставляє окремий worker.']
    log_files = []
    with tempfile.TemporaryDirectory(prefix='lab3_live_') as temp:
        tmp = Path(temp)
        fleet_port, trips_port, gate_port = free_port(), free_port(), free_port()
        fleet = f'http://127.0.0.1:{fleet_port}'
        trips = f'http://127.0.0.1:{trips_port}'
        gate = f'http://127.0.0.1:{gate_port}'
        env = os.environ.copy()
        env.update({'FLEET_DB_PATH': str(tmp / 'fleet.sqlite'), 'TRIPS_DB_PATH': str(tmp / 'trips.sqlite'), 'FLEET_URL': fleet, 'TRIPS_URL': trips})

        def launch(module, port):
            log = (tmp / f'{module.replace(".", "_")}.log').open('w', encoding='utf-8')
            log_files.append(log)
            proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', f'{module}:app', '--host', '127.0.0.1', '--port', str(port), '--log-level', 'warning'],
                                    cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            processes.append(proc)
            return proc
        try:
            fleet_proc=launch('fleet_service.app', fleet_port)
            trips_proc=launch('trips_service.app', trips_port)
            gateway_proc=launch('gateway', gate_port)
            for url,proc in [(fleet+'/health',fleet_proc), (trips+'/health',trips_proc), (gate+'/health',gateway_proc)]:
                wait_for(url,proc)
            lines.append('PASS: три незалежні процеси запущено; health=200 на всіх.')
            request={'id':'t-live-ok','vehicle_id':'v-1','driver_id':'d-1','route_id':'r-1'}
            ok=httpx.post(gate+'/trips',json=request,timeout=3)
            assert ok.status_code==201,(ok.status_code,ok.text)
            lines.append(f'PASS: POST /trips через gateway при доступному Fleet => HTTP {ok.status_code}, status={ok.json()["status"]}.')
            queued=httpx.get(gate+'/events/outbox',timeout=3).json()
            assert len(queued)==1 and queued[0]['delivered'] is False
            lines.append('PASS: подію TripCreated записано в outbox (delivered=false); notification поки немає.')
            fleet_proc.terminate()
            try: fleet_proc.wait(timeout=5)
            except subprocess.TimeoutExpired: fleet_proc.kill();fleet_proc.wait(timeout=3)
            try:
                failed=httpx.post(gate+'/trips',json={**request,'id':'t-live-fail'},timeout=4)
            except httpx.RequestError as exc:
                raise RuntimeError(f'POST failed at gateway: {exc}')
            assert failed.status_code==503,(failed.status_code,failed.text)
            assert httpx.get(gate+'/trips/t-live-fail').status_code==404
            lines.append('PASS: Fleet зупинено; POST /trips => HTTP 503, незавершений рейс не створено.')
            worker=subprocess.run([sys.executable,'-m','event_worker','--once'],cwd=ROOT,env=env,
                                  stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=12)
            assert worker.returncode==0,(worker.returncode,worker.stdout)
            notifications=httpx.get(gate+'/notifications',timeout=3).json()
            assert len(notifications)==1 and notifications[0]['trip_id']=='t-live-ok'
            assert httpx.get(gate+'/events/outbox').json()[0]['delivered'] is True
            lines.append('PASS: при зупиненому Fleet окремий worker доставив TripCreated; notification збережено.')
            lines.append('PASS: асинхронна подія не залежить від доступності Fleet після створення рейсу.')
            lines.append('Обмеження: це локальний інтеграційний експеримент, не навантажувальний тест та не зовнішній брокер.')
        finally:
            for proc in processes:
                if proc.poll() is None:
                    proc.terminate()
            for proc in processes:
                try: proc.wait(timeout=4)
                except subprocess.TimeoutExpired: proc.kill();proc.wait(timeout=4)
            for lf in log_files: lf.close()
    output = ROOT/'verification'/'live_demo_results.txt'
    output.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines))
    print('Log:',output.relative_to(ROOT))

if __name__ == '__main__':
    run()
