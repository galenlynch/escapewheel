"""The package's two tiers of public names, and what `Packet` does not repeat.

The user tier is `escapewheel_reader.__all__`. The support tier is every other name a module's
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
from escapewheel_reader import Packet, errors
from escapewheel_reader.protocols import PacketLike

PROJECT = Path(__file__).resolve().parents[1]
API = PROJECT / "docs" / "source" / "api.rst"
PACKAGE = escapewheel_reader.__name__

#: The section of `api.rst` listing module pages rather than names.
MODULE_PAGES = "Modules"


def _copied():
    """Modules copied from the specification's tree, whose names this package does not choose."""
    copies = tomllib.loads((PROJECT / "pyproject.toml").read_text())["tool"]["escapewheel"]["copies"]
    return {
        Path(path).relative_to("src").with_suffix("").as_posix().replace("/", ".")
        for path in copies
        if path.endswith(".py")
    }


def _modules():
    """Every module of the package but its `__init__`, by dotted name relative to the package."""
    found = pkgutil.walk_packages(escapewheel_reader.__path__, f"{PACKAGE}.")
    return {info.name.removeprefix(f"{PACKAGE}."): importlib.import_module(info.name) for info in found}


def _own():
    """The modules whose `__all__` this package writes."""
    return {name: module for name, module in _modules().items() if f"{PACKAGE}.{name}" not in _copied()}


def _user():
    return set(escapewheel_reader.__all__) - {"__version__"}


def _support():
    """Each support-tier name, as `module.name`."""
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
    for name, module in {"": escapewheel_reader, **_modules()}.items():
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
        for node in ast.parse(inspect.getsource(escapewheel_reader)).body
        if isinstance(node, ast.ImportFrom) and node.level == 1
        for alias in node.names
    }
    assert imported == _user()


def test_a_user_tier_name_comes_from_the_one_module_exporting_it():
    for name in sorted(_user()):
        holders = [module for module in _own().values() if name in module.__all__]
        assert len(holders) == 1, name
        assert getattr(escapewheel_reader, name) is getattr(holders[0], name), name


def test_the_reference_documents_exactly_the_two_tiers():
    """A bare entry is a user-tier name, `module.name` a support-tier one, and a module all it exports."""
    sections = _documented()
    entries = [entry for section, listed in sections.items() if section != MODULE_PAGES for entry in listed]
    assert len(entries) == len(set(entries))
    own = _own()
    user = {entry for entry in entries if "." not in entry and entry not in own}
    support = {entry for entry in entries if "." in entry and entry not in own}
    for whole in (entry for entry in entries if entry in own):
        support |= {f"{whole}.{name}" for name in own[whole].__all__}
    assert user == _user()
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
        if issubclass(cls, BaseException) and cls.__module__ == errors.__name__
    }
    assert defined <= _user()
    assert defined <= set(errors.__all__)


def test_a_function_taking_a_packet_is_typed_against_the_protocol():
    """So each accepts whatever reads as a packet does, not only `Packet`; a transform also takes a packet set."""
    for module_name, module in _own().items():
        for name, function in inspect.getmembers(module, inspect.isfunction):
            if function.__module__ != module.__name__:
                continue
            parameter = inspect.signature(function).parameters.get("packet")
            if parameter is not None:
                assert parameter.annotation in (PacketLike.__name__, f"{PacketLike.__name__} | PacketSet"), (
                    f"{module_name}.{name}"
                )


def test_no_packet_method_mirrors_an_exported_function():
    """A read has one spelling: the free function taking the packet."""
    functions = {name for name in _user() if inspect.isfunction(getattr(escapewheel_reader, name))}
    members = {name for name in vars(Packet) if not name.startswith("_")}
    assert not functions & members


def test_a_test_imports_an_underscore_name_only_from_the_module_it_is_named_for():
    """So a helper two test files share has a public name, in `conftest.py` or the shared fixture."""
    for path in sorted(Path(__file__).parent.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.ImportFrom):
                continue
            for alias in node.names:
                if alias.name.startswith("_") and not alias.name.startswith("__"):
                    named_for = f"{PACKAGE}.{path.stem.removeprefix('test_')}"
                    assert not node.level and node.module == named_for, f"{path.name}: {node.module}.{alias.name}"
