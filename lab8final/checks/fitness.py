"""AST fitness rules used by tests and CI; no string-only import matching."""

import ast
from pathlib import Path

PURE_IMPORTS = {"dataclasses", "enum", "typing", "collections", "datetime", "decimal", "__future__"}


def imports(source):
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                yield name.name
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                yield "." * node.level + (node.module or "")
            else:
                yield node.module or ""


def check_domain_purity(root):
    errors = []
    source = Path(root) / "backend" if (Path(root) / "backend").is_dir() else Path(root)
    for path in source.glob("*/domain.py"):
        for name in imports(path.read_text(encoding="utf-8")):
            if name.split(".")[0] not in PURE_IMPORTS:
                errors.append(f"{path.relative_to(root)}: forbidden domain import {name}")
    return errors


def check_cycles(root):
    root = Path(root)
    source = root / "backend" if (root / "backend").is_dir() else root
    paths = list(source.glob("*/*.py")) + list(source.glob("*.py"))
    modules = {".".join(p.relative_to(root).with_suffix("").parts): p for p in paths}
    graph = {name: set() for name in modules}
    for name, path in modules.items():
        package = name.rsplit(".", 1)[0] if "." in name else ""
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            candidates = []
            if isinstance(node, ast.Import):
                candidates = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                prefix = (
                    package.split(".")[: len(package.split(".")) - node.level + 1]
                    if node.level
                    else []
                )
                base = ".".join(prefix + ([node.module] if node.module else [])).strip(".")
                candidates = [base] + [base + "." + alias.name for alias in node.names]
            for target in candidates:
                if target in modules:
                    graph[name].add(target)
    errors = []
    active = []
    done = set()

    def visit(name):
        if name in active:
            errors.append(" -> ".join(active[active.index(name) :] + [name]))
            return
        if name in done:
            return
        active.append(name)
        for child in sorted(graph[name]):
            visit(child)
        active.pop()
        done.add(name)

    for name in graph:
        visit(name)
    return errors


def check_application_dependencies(root):
    errors = []
    source = Path(root) / "backend" if (Path(root) / "backend").is_dir() else Path(root)
    for path in list(source.glob("*/use_cases.py")) + list(source.glob("*/application.py")):
        for name in imports(path.read_text(encoding="utf-8")):
            if name not in {".domain"} and name.split(".")[0] not in PURE_IMPORTS:
                errors.append(f"{path.relative_to(root)}: forbidden application import {name}")
    return errors


if __name__ == "__main__":
    import sys

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    errors = check_domain_purity(root) + check_cycles(root) + check_application_dependencies(root)
    print("\n".join(errors) if errors else "PASS: pure domain, no cyclic imports")
    raise SystemExit(bool(errors))
