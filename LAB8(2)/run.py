"""Один запускной файл: установка, запуск приложения и проверки."""

import argparse
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent


def build_frontend(env, install=False):
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        raise SystemExit("Установите Node.js 24 с npm, затем откройте VS Code заново.")
    if install:
        subprocess.run(
            [npm, "ci", "--no-audit", "--no-fund"], cwd=ROOT / "frontend", env=env, check=True
        )
    subprocess.run([npm, "run", "build"], cwd=ROOT / "frontend", env=env, check=True)


def start(python, env, open_browser=True):
    from backend.config import configure

    configure()
    env.update(
        {
            name: os.environ[name]
            for name in ["FLEETFLOW_JWT_SECRET", "FLEETFLOW_USERS_PATH", "FLEETFLOW_AUDIT_PATH"]
        }
    )
    servers = [
        ("Fleet", 8101, "backend.fleet.api:app"),
        ("Trips", 8102, "backend.trips.api:app"),
        ("Панель", 8000, "backend.api:app"),
    ]
    busy = []
    for _, port, _ in servers:
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                busy.append(port)
    if busy:
        print("Порты уже заняты:", ", ".join(map(str, busy)))
        print("Если FleetFlow уже запущен, откройте http://127.0.0.1:8000")
        print("Для перезапуска остановите предыдущий запуск: Shift+F5 или Ctrl+C.")
        return 1
    children = []
    try:
        for name, port, module in servers:
            children.append(
                subprocess.Popen(
                    [
                        str(python),
                        "-m",
                        "uvicorn",
                        module,
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(port),
                        "--no-access-log",
                        "--log-level",
                        "warning",
                    ],
                    cwd=ROOT,
                    env=env,
                )
            )
            suffix = "" if port == 8000 else "/docs"
            print(f"{name}: http://127.0.0.1:{port}{suffix}", flush=True)
        for _ in range(100):
            if any(child.poll() is not None for child in children):
                raise RuntimeError("Сервис завершился при запуске. Ошибка указана выше.")
            try:
                for _, port, _ in servers:
                    path = "/api/health" if port == 8000 else "/health"
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}{path}", timeout=0.6
                    ) as response:
                        if response.status != 200:
                            raise OSError("Сервис ещё запускается")
                break
            except (OSError, urllib.error.URLError):
                time.sleep(0.15)
        else:
            raise RuntimeError("Сервисы не ответили за отведённое время.")
        for module in ["backend.event_bridge", "backend.event_worker"]:
            children.append(subprocess.Popen([str(python), "-m", module], cwd=ROOT, env=env))
        print("FleetFlow запущен. Базы данных находятся в папке data.", flush=True)
        print("Остановка: Shift+F5 или Ctrl+C.", flush=True)
        if open_browser:
            webbrowser.open("http://127.0.0.1:8000")
        while all(child.poll() is None for child in children):
            time.sleep(0.5)
        raise RuntimeError("Один из процессов завершился. Остальные остановлены.")
    except KeyboardInterrupt:
        return 0
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
        for child in reversed(children):
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="FleetFlow: setup / start / test / verify / benchmark"
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="start",
        choices=["setup", "start", "test", "verify", "benchmark"],
    )
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if (
        args.command != "setup"
        and python.exists()
        and Path(sys.executable).resolve() != python.resolve()
    ):
        return subprocess.call([str(python), str(ROOT / "run.py")] + sys.argv[1:], cwd=ROOT)
    env = os.environ.copy()
    env.update(PYTHONUTF8="1", PYTHONUNBUFFERED="1")
    if args.command == "setup":
        if not python.exists():
            subprocess.run([sys.executable, "-m", "venv", str(ROOT / ".venv")], check=True, env=env)
        subprocess.run(
            [str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")],
            check=True,
            env=env,
        )
        build_frontend(env, install=True)
        return subprocess.call([str(python), "-m", "backend.config"], cwd=ROOT, env=env)
    if not python.exists():
        parser.error("Сначала выполните: python run.py setup")
    if args.command in {"start", "test", "verify"}:
        build_frontend(env)
    if args.command == "start":
        return start(python, env, open_browser=not args.no_browser)
    commands = {
        "test": ["-m", "pytest", "-q"],
        "verify": ["checks/pipeline.py"],
        "benchmark": ["checks/load_test.py"],
    }
    return subprocess.call([str(python)] + commands[args.command], cwd=ROOT, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
