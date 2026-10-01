"""The package's two tiers of public names, and what each module exports to the others.

The user tier is `escapewheel_writer.__all__`. The adapter tier is `escapewheel_writer.adapter.__all__`,
for a source adapter in another distribution. `api.rst` documents both and nothing else. Every other
module's `__all__` holds the names this package's own modules and tests import from it.
"""

import ast
import importlib
import inspect
import pkgutil
from pathlib import Path

import escapewheel_writer
from escapewheel_writer import adapter, errors

PROJECT = Path(__file__).resolve().parents[1]
API = PROJECT / "docs" / "source" / "api.rst"
PACKAGE = escapewheel_writer.__name__

#: The module holding the adapter tier, which defines nothing and exports other modules' names.
ADAPTER = "adapter"

#: The section of `api.rst` listing module pages rather than names.
MODULE_PAGES = "Modules"


def _modules():
    """Every module of the package but its `__init__`, by dotted name relative to the package."""
    found = pkgutil.walk_packages(escapewheel_writer.__path__, f"{PACKAGE}.")
    return {info.name.removeprefix(f"{PACKAGE}."): importlib.import_module(info.name) for info in found}


def _defining():
    """The modules that export what they define."""
    return {name: module for name, module in _modules().items() if name != ADAPTER}


def _user():
    return set(escapewheel_writer.__all__) - {"__version__"}


def _holders(name, value):
    """The modules exporting this object under this name; two modules may each define a `build`."""
    return [module for module in _defining().values() if name in module.__all__ and getattr(module, name) is value]


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


def _documented():
    """The entries of each `autosummary` in `api.rst`, by the section they are under."""
    sections, section, listing = {}, None, False
    lines = API.read_text().splitlines()
    for position, line in enumerate(lines):
        following = lines[position + 1] if position + 1 < len(lines) else ""
        if line and following and set(following) <= set("=-~") and len(following) >= len(line):
            section, listing = line, False
        elif line.startswith(".. autosummary::"):
            listing = True
        elif listing and line.startswith("   ") and not line.strip().startswith(":"):
            sections.setdefault(section, []).append(line.strip())
        elif line and not line.startswith(" "):
            listing = False
    return sections


def test_every_module_declares_what_it_exports():
    for name, module in {"": escapewheel_writer, **_modules()}.items():
        exported = getattr(module, "__all__", None)
        assert isinstance(exported, list), f"{name or PACKAGE} declares no __all__"
        assert len(exported) == len(set(exported)), name
        for member in exported:
            assert hasattr(module, member), f"{name}.{member}"


def test_a_module_exports_only_what_it_defines():
    """A name has one module, so no module but `adapter` passes on another's."""
    for name, module in _defining().items():
        assert set(module.__all__) <= _defined(module), name


def test_the_adapter_module_defines_nothing():
    """Each of its names is the one another module exports, so the tier is a list and not a copy."""
    assert not {name for name in _defined(adapter) if not name.startswith("__")}
    for name in adapter.__all__:
        assert len(_holders(name, getattr(adapter, name))) == 1, name


def test_the_package_imports_from_its_modules_exactly_the_user_tier():
    """A name `__init__` imported and did not export would be importable from the package by accident."""
    imported = {
        alias.asname or alias.name
        for node in ast.parse(inspect.getsource(escapewheel_writer)).body
        if isinstance(node, ast.ImportFrom) and node.level == 1
        for alias in node.names
    }
    assert imported == _user()


def test_a_user_tier_name_comes_from_the_one_module_exporting_it():
    for name in sorted(_user()):
        assert len(_holders(name, getattr(escapewheel_writer, name))) == 1, name


def test_the_reference_documents_exactly_the_two_tiers():
    """A bare entry is a user-tier name and `adapter.name` an adapter-tier one the user tier lacks."""
    sections = _documented()
    entries = [entry for section, listed in sections.items() if section != MODULE_PAGES for entry in listed]
    assert len(entries) == len(set(entries))
    assert {entry for entry in entries if "." not in entry} == _user()
    assert {entry for entry in entries if "." in entry} == {
        f"{ADAPTER}.{name}" for name in set(adapter.__all__) - _user()
    }
    assert sections[MODULE_PAGES] == [ADAPTER]


def test_every_exception_class_is_in_the_user_tier():
    defined = {
        name
        for name, cls in inspect.getmembers(errors, inspect.isclass)
        if issubclass(cls, BaseException) and cls.__module__ == errors.__name__
    }
    assert defined <= _user()
    assert defined <= set(errors.__all__)


def test_a_module_or_a_test_imports_from_a_module_only_what_it_exports():
    """So a module's `__all__` is the whole of what moving it can break."""
    modules = _modules()
    files = [(Path(module.__file__), (name, hasattr(module, "__path__"))) for name, module in modules.items()]
    files += [(Path(escapewheel_writer.__file__), ("", True))]
    files += [(path, None) for path in sorted((PROJECT / "tests").glob("*.py"))]
    for path, importer in files:
        for module, name in _imports(path, importer):
            if name.startswith("_") or f"{module}.{name}".lstrip(".") in modules:
                continue
            exported = modules[module].__all__ if module else escapewheel_writer.__all__
            assert name in exported, f"{path.name} imports {module or PACKAGE}.{name}"


def test_a_test_imports_an_underscore_name_only_from_the_module_it_is_named_for():
    for path in sorted((PROJECT / "tests").glob("*.py")):
        for module, name in _imports(path):
            if name.startswith("_") and not name.startswith("__"):
                assert path.name == f"test_{module.rpartition('.')[2]}.py", f"{path.name} imports {module}.{name}"


def test_a_test_imports_no_underscore_name_from_a_test_or_helper_module():
    """A helper two test modules share has a public name, in a helper module or in `conftest.py`."""
    for path in sorted((PROJECT / "tests").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and (node.level or (node.module or "").split(".")[0] != PACKAGE):
                private = [alias.name for alias in node.names if alias.name.startswith("_")]
                assert not private, f"{path.name} imports {private} from {'.' * node.level}{node.module or ''}"
