"""Run dashboard + Fleet + Trips + bridge from one command on Windows/Linux.

All HTTP servers bind to loopback only; no external network exposure.
"""
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVERS = [
    ('Fleet', 8101, 'fleet_service.app:app'),
    ('Trips', 8102, 'trips_service.app:app'),
    ('Dashboard', 8000, 'dashboard:app'),
]


def port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1',port)) != 0


def main():
    busy=[port for _,port,_ in SERVERS if not port_free(port)]
    if busy:
        print('Порти зайняті:', ', '.join(map(str,busy)), flush=True)
        print('Зупиніть старі сервери в терміналах (Ctrl+C), потім повторіть запуск.',flush=True)
        return 1
    from setup_local import configure
    credentials=configure()
    print('Облікові дані:',credentials,flush=True)
    children=[]
    env=os.environ.copy()
    env.setdefault('PYTHONUNBUFFERED','1')
    try:
        for name,port,module in SERVERS:
            args=[sys.executable,'-m','uvicorn',module,'--host','127.0.0.1',
                  '--port',str(port),'--no-access-log','--log-level','warning']
            children.append(subprocess.Popen(args,cwd=ROOT,env=env))
            print(f'{name}: http://127.0.0.1:{port}',flush=True)
        def services_ready():
            for _,port,_ in SERVERS:
                endpoint='/api/health' if port==8000 else '/health'
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}{endpoint}',timeout=0.6) as response:
                        if response.status!=200:return False
                except (OSError,urllib.error.URLError):
                    return False
            return True
        for _ in range(75):
            if any(proc.poll() is not None for proc in children):
                raise RuntimeError('Один із серверів завершився під час запуску; дивіться помилку вище.')
            if services_ready():break
            time.sleep(.15)
        else:raise RuntimeError('Сервіси не відповідають на HTTP-запити.')
        children.append(subprocess.Popen([sys.executable,'event_bridge.py'],cwd=ROOT,env=env))
        print('\n✅ FleetFlow запущено. Відкрийте http://127.0.0.1:8000',flush=True)
        print('Для зупинки натисніть Ctrl+C у цьому терміналі.\n',flush=True)
        if '--no-browser' not in sys.argv:
            webbrowser.open('http://127.0.0.1:8000')
        while True:
            if any(proc.poll() is not None for proc in children):
                print('Один із процесів завершився. Зупиняю решту.',flush=True)
                return 1
            time.sleep(.5)
    except KeyboardInterrupt:
        print('\nЗупинка сервісів...',flush=True)
        return 0
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
        for child in reversed(children):
            try:child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == '__main__':
    raise SystemExit(main())
