"""Inject a forbidden import into a disposable copy; run the REAL pipeline gate."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="fleetflow-negative-") as tmp:
        copy = Path(tmp)
        for name in ["backend", "checks"]:
            shutil.copytree(
                ROOT / name,
                copy / name,
                ignore=shutil.ignore_patterns("__pycache__", "*.json", "*.xml", "*.txt"),
            )
        original = (ROOT / "backend/fleet/domain.py").read_bytes()
        f = copy / "backend/fleet/domain.py"
        f.write_text("import sqlite3\n" + f.read_text(encoding="utf-8"), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(copy / "checks/pipeline.py"), "--static-only"],
            cwd=copy,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1 and "forbidden domain import sqlite3" in result.stdout
        assert (ROOT / "backend/fleet/domain.py").read_bytes() == original
        evidence = {
            "command": "python checks/pipeline.py --static-only (disposable source copy)",
            "injected": "backend/fleet/domain.py: import sqlite3",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "original_source_unchanged": True,
        }
        (ROOT / "checks/negative_pipeline.json").write_text(
            json.dumps(evidence, indent=2), encoding="utf-8"
        )
        (ROOT / "checks/negative_pipeline.log").write_text(
            result.stdout + result.stderr, encoding="utf-8"
        )
        print(result.stdout)
        print("PASS: real gate rejected violation; original source unchanged")


if __name__ == "__main__":
    main()
