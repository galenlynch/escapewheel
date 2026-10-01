"""The package's one tier of public names, and what each module exports to the others.

The tier is the entry points `pyproject.toml` registers, and `README.md` documents the source kinds
among them. Nothing is imported from the package by name, so `__init__` exports nothing, and a
module's `__all__` holds the names this package's own modules and tests import from it.
"""

import ast
import importlib
import inspect
import pkgutil
import re
import tomllib
from pathlib import Path

import escapewheel_aind

PROJECT = Path(__file__).resolve().parents[1]
PACKAGE = escapewheel_aind.__name__
ENTRY_POINTS = tomllib.loads((PROJECT / "pyproject.toml").read_text())["project"]["entry-points"]

#: The entry-point group whose names are the source kinds `README.md` lists.
SOURCES = "escapewheel.sources"


def _modules():
    """Every module of the package but its `__init__`, by dotted name relative to the package."""
    found = pkgutil.walk_packages(escapewheel_aind.__path__, f"{PACKAGE}.")
    return {info.name.removeprefix(f"{PACKAGE}."): importlib.import_module(info.name) for info in found}


def _defined(module):
    """The names a module binds at top level by a definition or an assignment, imports excluded."""
    names = set()
    for node in ast.parse(inspect.getsource(module)).body:
        if isinstance(node, ast.FunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.TypeAlias):
            names.add(node.name.id)
        elif isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                elements = target.elts if isinstance(target, ast.Tuple) else [target]
                names.update(element.id for element in elements if isinstance(element, ast.Name))
    return names


def _imports(path, importer=None):
    """Each `from <module of this package> import <name>` in a file, as (module, name).

    `importer` is the importing module's dotted name and whether it is a package, which a relative
    import resolves against.
    """
    for node in ast.walk(ast.parse(path.read_text())):
        if not isinstance(node, ast.ImportFrom):
            continue
        named = node.module.split(".") if node.module else []
        if node.level:
            if importer is None:
                continue
            name, is_package = importer
            parts = name.split(".") if name else []
            base = parts if is_package else parts[:-1]
            module = ".".join([*base[: len(base) - (node.level - 1)], *named])
        elif named[:1] == [PACKAGE]:
            module = ".".join(named[1:])
        else:
            continue
        for alias in node.names:
            yield module, alias.name


def test_every_module_declares_what_it_exports():
    for name, module in {"": escapewheel_aind, **_modules()}.items():
        exported = getattr(module, "__all__", None)
        assert isinstance(exported, list), f"{name or PACKAGE} declares no __all__"
        assert len(exported) == len(set(exported)), name
        for member in exported:
            assert hasattr(module, member), f"{name}.{member}"


def test_a_module_exports_only_what_it_defines():
    for name, module in _modules().items():
        assert set(module.__all__) <= _defined(module) - {"__all__"}, name


def test_the_package_exports_nothing():
    """An adapter is reached by its entry point, so no name is imported from the package."""
    assert escapewheel_aind.__all__ == []
    assert not [
        node for node in ast.parse(inspect.getsource(escapewheel_aind)).body if isinstance(node, ast.ImportFrom)
    ]


def test_every_entry_point_names_an_exported_object():
    for group, entries in ENTRY_POINTS.items():
        for name, target in entries.items():
            module, _, member = target.partition(":")
            assert member in importlib.import_module(module).__all__, f"{group}: {name} = {target}"


def test_the_readme_lists_exactly_the_registered_source_kinds():
    section = (PROJECT / "README.md").read_text().split("## Source kinds", 1)[1].split("\n## ", 1)[0]
    assert set(re.findall(r"^\| `(\w+)` \|", section, flags=re.MULTILINE)) == set(ENTRY_POINTS[SOURCES])


def test_a_module_or_a_test_imports_from_a_module_only_what_it_exports():
    """So a module's `__all__` is the whole of what moving it can break."""
    modules = _modules()
    files = [(Path(module.__file__), (name, hasattr(module, "__path__"))) for name, module in modules.items()]
    files += [(path, None) for path in sorted((PROJECT / "tests").glob("*.py"))]
    for path, importer in files:
        for module, name in _imports(path, importer):
            if name.startswith("_") or f"{module}.{name}".lstrip(".") in modules:
                continue
            assert name in modules[module].__all__, f"{path.name} imports {module or PACKAGE}.{name}"


def test_a_test_imports_an_underscore_name_only_from_the_module_it_is_named_for():
    for path in sorted((PROJECT / "tests").glob("*.py")):
        for module, name in _imports(path):
            if name.startswith("_") and not name.startswith("__"):
                assert path.name == f"test_{module.rpartition('.')[2]}.py", f"{path.name} imports {module}.{name}"
