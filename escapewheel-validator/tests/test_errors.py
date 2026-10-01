"""The package's exceptions are one taxonomy, defined in one module."""

import importlib
import inspect
import pkgutil

from escapewheel_reader import EscapewheelError

import escapewheel_validator
from escapewheel_validator import errors

from .copies import COPIED_MODULES

#: Modules copied from the specification's tree, whose exception classes are defined at that source.
COPIED = set(COPIED_MODULES)


def _defined():
    """Every exception class a module of the package defines, outside the copied modules."""
    for info in pkgutil.walk_packages(escapewheel_validator.__path__, "escapewheel_validator."):
        if info.name in COPIED:
            continue
        module = importlib.import_module(info.name)
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, BaseException) and cls.__module__ == module.__name__:
                yield cls


def test_the_modules_outside_the_taxonomy_are_the_tree_s_checkers():
    """The copy map says which modules are exempt, and exempts only a checker of the tree."""
    assert COPIED
    assert all(source.startswith("tools/checkers/") for source in COPIED_MODULES.values())


def test_every_exception_is_defined_in_the_error_module_under_the_package_base():
    """A caller catching `ValidatorError` catches every deliberate refusal, wherever it is raised."""
    classes = list(_defined())
    assert errors.ValidatorError in classes
    for cls in classes:
        assert cls.__module__ == errors.__name__, cls
        assert issubclass(cls, errors.ValidatorError), cls
    assert issubclass(errors.ValidatorError, EscapewheelError)


def test_an_error_a_caller_catches_as_a_built_in_stays_one():
    """Each replaced a built-in that a caller of the function raising it may catch."""
    assert issubclass(errors.UnknownAlgorithm, ValueError)
    assert issubclass(errors.ReplacedPacketUnreadable, FileNotFoundError)


def test_every_exception_is_documented_in_the_module_docstring():
    """The module docstring is the taxonomy a reader of the page sees."""
    for name, cls in inspect.getmembers(errors, inspect.isclass):
        if issubclass(cls, BaseException) and cls.__module__ == errors.__name__:
            assert f":class:`{name}`" in errors.__doc__, name
