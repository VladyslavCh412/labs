"""Check API contracts and run functional tests."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    result = subprocess.call([sys.executable, "checks/export_contracts.py"], cwd=ROOT)
    if result:
        return result
    return subprocess.call(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=ROOT,
    )


if __name__ == "__main__":
    raise SystemExit(main())
