"""Entry point: python -m uvicorn main:app --reload"""
import os
from fleet.container import build_sqlite_use_cases
from fleet.presentation.api import create_app

app = create_app(build_sqlite_use_cases(os.getenv('FLEET_DB_PATH', 'data/fleet.sqlite')))
