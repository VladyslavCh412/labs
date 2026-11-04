"""Measure the four actual refactorings using bundled before/current sources."""

import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BEFORE = ROOT / "docs/refactoring/before"


def method(root, filename, name, owner=None):
    source = (root / filename).read_text(encoding="utf-8")
    tree = ast.parse(source)
    scope = (
        next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == owner)
        if owner
        else tree
    )
    node = next(
        n
        for n in ast.walk(scope)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name
    )
    return node, hashlib.sha256(source.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def value(kind, node):
    if kind == "proxy_branches":
        # Compare only service-selection branches. Query forwarding, input
        # validation and other HTTP concerns are unrelated to this Strategy.
        return sum(
            isinstance(n, ast.If)
            and any(
                isinstance(child, ast.Name) and child.id in {"rest", "owner"}
                for child in ast.walk(n.test)
            )
            for n in ast.walk(node)
        )
    if kind == "external_json_reads":
        return sum(
            isinstance(n, ast.Subscript)
            and isinstance(n.value, ast.Name)
            and n.value.id in {"vehicle", "driver"}
            for n in ast.walk(node)
        )
    if kind == "concrete_constructors":
        return sum(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id in {"TripsRepository", "FleetClient"}
            for n in ast.walk(node)
        )
    if kind == "notification_sql_writes":
        return sum(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "execute"
            and bool(n.args)
            and isinstance(n.args[0], ast.Constant)
            and isinstance(n.args[0].value, str)
            and "INSERT" in n.args[0].value.upper()
            and "notification_inbox" in n.args[0].value
            for n in ast.walk(node)
        )
    raise ValueError(kind)


def measure():
    cases = [
        (
            "Strategy",
            "gateway.py",
            "proxy",
            None,
            "proxy_branches",
            "Розгалуження вибору сервісу; без валідації та HTTP-обробки",
        ),
        (
            "Adapter",
            "trips_service/fleet_client.py",
            "check_vehicle_and_driver",
            "FleetClient",
            "external_json_reads",
            "Прямі звернення до JSON полів vehicle/driver у споживачі",
        ),
        (
            "Factory",
            "trips_service/app.py",
            "create_app",
            None,
            "concrete_constructors",
            "Прямі конструктори конкретних repo/client у create_app",
        ),
        (
            "Observer",
            "trips_service/repository.py",
            "deliver_pending",
            "TripsRepository",
            "notification_sql_writes",
            "Прямі SQL-вставки notification_inbox у продуцента",
        ),
    ]
    result = []
    current_files = {
        "Strategy": ("backend/api.py", "forward"),
        "Adapter": ("backend/trips/fleet_client.py", "check_vehicle_and_driver"),
        "Factory": ("backend/trips/api.py", "create_app"),
        "Observer": ("backend/trips/storage.py", "deliver_pending"),
    }
    for pattern, filename, name, owner, kind, description in cases:
        before, before_hash = method(BEFORE, filename, name, owner)
        current_file, current_method = current_files[pattern]
        after, after_hash = method(ROOT, current_file, current_method, owner)
        old, new = value(kind, before), value(kind, after)
        if not new < old:
            raise AssertionError(f"{pattern}: expected coupling reduction, got {old} -> {new}")
        result.append(
            dict(
                pattern=pattern,
                file=current_file,
                method=f"{owner + '.' if owner else ''}{current_method}",
                metric=description,
                before=old,
                after=new,
                before_source_sha256=before_hash,
                current_source_sha256=after_hash,
            )
        )
    return dict(
        baseline_commit="46aa488",
        method="AST counts for named methods; not whole-system cyclomatic complexity",
        metrics=result,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    target = ROOT / "docs/evidence/pattern-metrics.json"
    result = measure()
    if args.check:
        assert json.loads(target.read_text(encoding="utf-8")) == result, (
            "Pattern evidence is stale; run checks/pattern_metrics.py"
        )
    else:
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for item in result["metrics"]:
        print(f"{item['pattern']}: {item['before']} -> {item['after']}")


if __name__ == "__main__":
    main()
