# Создаёт локальные учётные записи и ключ. Задаёт единое место баз — data.
"""Prepare local accounts, a public demo admin and a unique signing key."""

import json
import os
import secrets
from pathlib import Path
from backend.auth import PASSWORDS

ROOT = Path(__file__).resolve().parents[1]


def configure():
    data = ROOT / "data"
    data.mkdir(exist_ok=True)
    key = data / "jwt.key"
    users = data / "users.json"
    credentials = data / "LOCAL_ACCOUNTS.txt"
    if not key.exists():
        key.write_text(secrets.token_urlsafe(48), encoding="utf-8")
    if not users.exists():
        records = {}
        lines = ["FleetFlow: generated LOCAL accounts. Do not publish this file."]
        for role in ["manager", "dispatcher", "viewer"]:
            password = secrets.token_urlsafe(12)
            records[role] = {"role": role, "password_hash": PASSWORDS.hash(password)}
            lines.append(f"{role}: {password}")
        users.write_text(json.dumps(records, indent=2), encoding="utf-8")
        credentials.write_text("\n".join(lines), encoding="utf-8")
    records = json.loads(users.read_text(encoding="utf-8"))
    if "admin" not in records:
        records["admin"] = {"role": "manager", "password_hash": PASSWORDS.hash("123123")}
        users.write_text(json.dumps(records, indent=2), encoding="utf-8")
        with credentials.open("a", encoding="utf-8") as stream:
            stream.write("\nadmin: 123123\n")
    os.environ.setdefault("FLEETFLOW_JWT_SECRET", key.read_text(encoding="utf-8").strip())
    os.environ.setdefault("FLEETFLOW_USERS_PATH", str(users))
    os.environ.setdefault("FLEETFLOW_AUDIT_PATH", str(data / "audit.jsonl"))
    return credentials


def database_path(service):
    """Both SQLite files live in project/data, regardless of the current folder."""
    variable = {"fleet": "FLEET_DB_PATH", "trips": "TRIPS_DB_PATH"}[service]
    return Path(os.environ.get(variable, str(ROOT / "data" / f"{service}.sqlite"))).resolve()


if __name__ == "__main__":
    configure()
    from backend.fleet.storage import FleetRepository
    from backend.trips.storage import TripsRepository

    FleetRepository(database_path("fleet"), migration_stage=4)
    TripsRepository(database_path("trips"))
    print("Готово: базы данных и локальные учётные записи созданы в папке data.")
