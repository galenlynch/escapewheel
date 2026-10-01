"""The package's two tiers of public names, and whose names its modules and tests may use.

The user tier is `escapewheel_validator.__all__`. The support tier is every other name a module's
`__all__` holds, for another Escapewheel package to import from that module. `api.rst` documents
both and nothing else.
"""

import ast
import importlib
import inspect
import pkgutil
import tomllib
from pathlib import Path

import escapewheel_reader

import escapewheel_validator
from escapewheel_validator import errors

PROJECT = Path(__file__).resolve().parents[1]
API = PROJECT / "docs" / "source" / "api.rst"
PACKAGE = escapewheel_validator.__name__
READER = escapewheel_reader.__name__

#: The section of `api.rst` listing module pages rather than names.
MODULE_PAGES = "Modules"


def _copied():
    """Modules copied from the specification's tree, whose names this package does not choose."""
    copies = tomllib.loads((PROJECT / "pyproject.toml").read_text())["tool"]["escapewheel"]["copies"]
    return {
        Path(path).relative_to("src").with_suffix("").as_posix().replace("/", ".").removeprefix(f"{PACKAGE}.")
        for path in copies
        if path.endswith(".py")
    }


def _modules():
    """Every module of the package but its `__init__`, by dotted name relative to the package."""
    found = pkgutil.walk_packages(escapewheel_validator.__path__, f"{PACKAGE}.")
    return {info.name.removeprefix(f"{PACKAGE}."): importlib.import_module(info.name) for info in found}


def _own():
    """The modules whose `__all__` this package writes."""
    return {name: module for name, module in _modules().items() if name not in _copied()}


def _user():
    return set(escapewheel_validator.__all__) - {"__version__"}


def _support():
    """Each support-tier name of this package's own modules, as `module.name`."""
    user = _user()
    return {
        f"{module_name}.{name}" for module_name, module in _own().items() for name in module.__all__ if name not in user
    }


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
            names.update(target.id for target in targets if isinstance(target, ast.Name))
    return names


def _imports(source):
    """Each `from module import name` in a source text, at any depth, as (level, module, name)."""
    return [
        (node.level, node.module or "", alias.name)
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    ]


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
    for name, module in {"": escapewheel_validator, **_own()}.items():
        exported = getattr(module, "__all__", None)
        assert isinstance(exported, list), f"{name or PACKAGE} declares no __all__"
        assert len(exported) == len(set(exported)), name
        for member in exported:
            assert hasattr(module, member), f"{name}.{member}"


def test_a_module_exports_only_what_it_defines():
    """A name has one module, so no module passes on another's and no import path is an alias."""
    for name, module in _own().items():
        assert set(module.__all__) <= _defined(module), name


def test_the_package_imports_from_its_modules_exactly_the_user_tier():
    """A name `__init__` imported and did not export would be importable from the package by accident."""
    imported = {
        alias.asname or alias.name
        for node in ast.parse(inspect.getsource(escapewheel_validator)).body
        if isinstance(node, ast.ImportFrom) and node.level == 1
        for alias in node.names
    }
    assert imported == _user()


def test_a_user_tier_name_comes_from_the_one_module_exporting_it():
    """A module is its own name; a name of a copied module comes from the copy `__init__` names."""
    modules = _modules()
    from_copies = {
        name: modules[module]
        for level, module, name in _imports(inspect.getsource(escapewheel_validator))
        if level == 1 and module in _copied()
    }
    for name in sorted(_user()):
        if name in modules:
            assert getattr(escapewheel_validator, name) is modules[name], name
            continue
        holders = [module for module in _own().values() if name in module.__all__]
        holders = holders or [from_copies[name]]
        assert len(holders) == 1, name
        assert getattr(escapewheel_validator, name) is getattr(holders[0], name), name


def test_the_reference_documents_exactly_the_two_tiers():
    """A bare entry is a user-tier name, `module.name` a support-tier one, and a module all it exports.

    A copied module's names are documented by listing the module, and only what the reference
    lists of them is checked: which copies exist is the specification tree's choice.
    """
    sections = _documented()
    entries = [entry for section, listed in sections.items() if section != MODULE_PAGES for entry in listed]
    assert len(entries) == len(set(entries))
    modules, own, user = _modules(), _own(), _user()
    assert {entry for entry in entries if "." not in entry and (entry not in modules or entry in user)} == user
    support = {entry for entry in entries if "." in entry and entry not in modules}
    for whole in (entry for entry in entries if entry in own):
        support |= {f"{whole}.{name}" for name in own[whole].__all__ if name not in user}
    assert support == _support()


def test_the_reference_gives_a_page_to_each_module_holding_a_public_name():
    sections = _documented()
    whole = {entry for section, listed in sections.items() if section != MODULE_PAGES for entry in listed}
    paged = {name for name, module in _own().items() if module.__all__ and name not in whole}
    assert set(sections[MODULE_PAGES]) == paged


def test_every_exception_class_is_in_the_user_tier():
    defined = {
        name
        for name, cls in inspect.getmembers(errors, inspect.isclass)
        if issubclass(cls, BaseException) and cls.__module__ == errors.__name__ and not name.startswith("_")
    }
    assert defined <= _user()
    assert defined <= set(errors.__all__)


def test_the_package_imports_from_the_reader_only_its_public_names():
    """So the reader may change any name outside its two tiers without breaking this package."""
    for module_name, module in _own().items():
        for level, source, name in _imports(inspect.getsource(module)):
            if level or source.split(".")[0] != READER:
                continue
            assert name in importlib.import_module(source).__all__, f"{module_name}: {source}.{name}"


def test_a_module_uses_no_other_modules_underscore_name():
    """`_Unmappable` is the exception: an error class, so defined in `errors`, that never leaves the package."""
    shared = {("errors", "_Unmappable")}
    for module_name, module in _own().items():
        for level, source, name in _imports(inspect.getsource(module)):
            if name.startswith("_") and not name.startswith("__"):
                assert level and (source, name) in shared, f"{module_name}: {source}.{name}"


def _named_for(test, module):
    """Whether a test file is named for a module: `test_ordering` and `test_shim_ordering` are for `shim.ordering`."""
    parts = module.split(".")
    return test in {"test_" + "_".join(parts[start:]) for start in range(len(parts))}


def test_a_test_uses_the_underscore_names_of_its_own_module_only():
    """An underscore name is for its module, and for the test file named for that module."""
    for path in sorted(Path(__file__).parent.glob("*.py")):
        for level, source, name in _imports(path.read_text()):
            if not name.startswith("_") or name.startswith("__"):
                continue
            package, _, module = source.partition(".")
            assert level or package != READER, f"{path.name}: {source}.{name}"
            if not level and package == PACKAGE:
                assert _named_for(path.stem, module), f"{path.name}: {source}.{name}"
