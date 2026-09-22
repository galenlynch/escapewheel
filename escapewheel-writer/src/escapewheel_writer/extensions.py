"""Find the extension registries a recipe names.

Part 09 §2 makes an extension a registry document, and Part 09 §6 has the packet carry it. Between the
two sits a mechanical question this module answers: **where does a build get the document from?**

Two answers, because there are two situations. A document being drafted is a file beside the
recipe, named by its path. A document someone else maintains arrives in an installed
distribution, which has no path a recipe could name -- so it registers under an entry-point
group, the same way Part 07's single CLI is assembled from three packages and a source adapter is
found (`escapewheel_writer.sources.SOURCE_GROUP`).

Note what a distribution is **for**. It carries the registry document and, where the raw source
needs parsing, a source adapter -- both of which matter only while a packet is being *built*.
Once built, the packet embeds the document, and reading it needs nothing installed. That is the
whole difference from an `ndx-` extension, which must be installed to read a file at all.
"""

from __future__ import annotations

import json
import warnings
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any

from escapewheel_validator import CheckedRegistryContext, check_registry_context, check_registry_context_bytes

#: Entry-point group a distribution registers an extension registry under. The value loads to the
#: parsed document, or to a path to it -- whichever is natural for how the package ships it.
EXTENSION_GROUP = "escapewheel.extensions"


class ExtensionNotFound(Exception):
    """A recipe names an extension that is neither a file nor an installed distribution."""


def _document(loaded: Any, source: str) -> dict[str, Any]:
    """Coerce whatever an entry point loaded into a registry document."""
    if callable(loaded) and not isinstance(loaded, type):
        loaded = loaded()
    if isinstance(loaded, dict):
        return loaded
    if isinstance(loaded, (str, Path)):
        return dict(json.loads(Path(loaded).read_text()))
    raise ExtensionNotFound(f"{source} loaded {type(loaded).__name__}, not a document or a path to one")


def installed() -> dict[str, dict[str, Any]]:
    """Extension registries registered by installed distributions, by the name they claim.

    One that fails to load is skipped with its reason rather than raised: a broken third-party
    package must not make every other extension unavailable, which is the failure mode that makes
    a plugin system worse than no plugin system.
    """
    found: dict[str, dict[str, Any]] = {}
    for entry in entry_points(group=EXTENSION_GROUP):
        try:
            found[entry.name] = _document(entry.load(), f"extension {entry.name!r}")
        except Exception as exc:  # noqa: BLE001 - one broken package is one extension, not all
            warnings.warn(f"extension {entry.name!r} could not be loaded: {exc}", stacklevel=2)
    return found


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
        f"{named!r} is neither a file nor an installed extension; registered under {EXTENSION_GROUP}: {known}"
    )


def load_checked(named: str, core: CheckedRegistryContext, *, base: Path | None = None) -> CheckedRegistryContext:
    """Load and check one extension, preserving exact bytes whenever this process owns them."""
    candidates = [Path(named)] + ([base / named] if base is not None else [])
    for candidate in candidates:
        if candidate.is_file():
            return check_registry_context_bytes(candidate.read_bytes(), core=core)
    available = installed()
    if named in available:
        return check_registry_context(available[named], core=core)
    known = ", ".join(sorted(available)) or "none installed"
    raise ExtensionNotFound(
        f"{named!r} is neither a file nor an installed extension; registered under {EXTENSION_GROUP}: {known}"
    )


__all__ = ["EXTENSION_GROUP", "ExtensionNotFound", "installed", "load", "load_checked"]
