"""Find the extension registries a recipe names.

- :func:`load` -- the registry an entry names, by a path beside the recipe or an installed id.
- :func:`load_checked` -- the same registry checked against core, from a file's exact bytes.
- :func:`installed` -- the registries that installed distributions register, keyed by the name each
  claims.
- :data:`EXTENSION_GROUP` -- the entry-point group a distribution registers a registry under.

A distribution is needed only while a packet is built: the packet embeds the registry document
(Part 09 §5.3), so reading the packet needs nothing installed.
"""

from __future__ import annotations

import json
import warnings
from collections.abc import Callable
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any

from escapewheel_validator import CheckedRegistryContext, check_registry_context, check_registry_context_bytes

from .errors import ExtensionNotFound

#: Entry-point group a distribution registers an extension registry under. The value loads to the
#: parsed document, or to a path to it -- whichever is natural for how the package ships it.
EXTENSION_GROUP = "escapewheel.extensions"


def _registered(loaded: Any, source: str) -> dict[str, Any] | bytes:
    """Coerce whatever an entry point loaded into a registry document, or the exact bytes of the file it names."""
    if callable(loaded) and not isinstance(loaded, type):
        loaded = loaded()
    if isinstance(loaded, dict):
        return loaded
    if isinstance(loaded, (str, Path)):
        return Path(loaded).read_bytes()
    raise ExtensionNotFound(f"{source} loaded {type(loaded).__name__}, not a document or a path to one", named=source)


def _document(loaded: Any, source: str) -> dict[str, Any]:
    """Coerce whatever an entry point loaded into a registry document."""
    registered = _registered(loaded, source)
    return dict(json.loads(registered)) if isinstance(registered, bytes) else registered


def _installed[T](coerce: Callable[[Any, str], T]) -> dict[str, T]:
    """Return what each installed distribution registers, as `coerce` reads it, by the name it claims."""
    found: dict[str, T] = {}
    for entry in entry_points(group=EXTENSION_GROUP):
        try:
            found[entry.name] = coerce(entry.load(), f"extension {entry.name!r}")
        except Exception as exc:  # noqa: BLE001 - one broken package is one extension, not all
            warnings.warn(f"extension {entry.name!r} could not be loaded: {exc}", stacklevel=3)
    return found


def installed() -> dict[str, dict[str, Any]]:
    """Extension registries registered by installed distributions, by the name they claim.

    One that fails to load is skipped with its reason rather than raised: a broken third-party
    package must not make every other extension unavailable, which is the failure mode that makes
    a plugin system worse than no plugin system.
    """
    return _installed(_document)


def load(named: str, *, base: Path | None = None) -> dict[str, Any]:
    """Return the registry a recipe entry names, whether a path or an installed extension id.

    A path is tried first and only where it exists, so an id can never be shadowed by a file that
    happens to share its name, and a typo in a path reports as a missing extension listing what is
    installed rather than as a file-not-found with no next step.
    """
    candidates = [Path(named)] + ([base / named] if base is not None else [])
    for candidate in candidates:
        if candidate.is_file():
            return dict(json.loads(candidate.read_text()))
    available = installed()
    if named in available:
        return available[named]
    known = ", ".join(sorted(available)) or "none installed"
    raise ExtensionNotFound(
        f"{named!r} is neither a file nor an installed extension; registered under {EXTENSION_GROUP}: {known}",
        named=named,
        known=sorted(available),
    )


def load_checked(named: str, core: CheckedRegistryContext, *, base: Path | None = None) -> CheckedRegistryContext:
    """Load and check one extension, preserving exact bytes whenever this process owns them.

    A file, whether the entry names it or an installed distribution registers its path, is checked
    through the byte entry point, and a document a distribution registers through the mapping one
    (Part 05 §14.2).
    """
    candidates = [Path(named)] + ([base / named] if base is not None else [])
    for candidate in candidates:
        if candidate.is_file():
            return check_registry_context_bytes(candidate.read_bytes(), core=core)
    available = _installed(_registered)
    if named in available:
        registered = available[named]
        if isinstance(registered, bytes):
            return check_registry_context_bytes(registered, core=core)
        return check_registry_context(registered, core=core)
    known = ", ".join(sorted(available)) or "none installed"
    raise ExtensionNotFound(
        f"{named!r} is neither a file nor an installed extension; registered under {EXTENSION_GROUP}: {known}",
        named=named,
        known=sorted(available),
    )


__all__ = ["EXTENSION_GROUP", "installed", "load", "load_checked"]
