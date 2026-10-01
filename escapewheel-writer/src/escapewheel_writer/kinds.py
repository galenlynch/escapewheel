"""What the adapter of a source kind declares, read from its class (Part 05 §3.4).

- :func:`adapter_for` -- the class a kind names.
- :func:`produces`, :func:`contributes`, :func:`consumes` -- the resources it can supply, those
  it supplies only part of, and the kinds whose output it reads.
- :func:`needs`, :func:`accepts` -- the names a build must supply it, and the options it can run
  without.
- :func:`states`, :func:`declares_states`, :func:`state_accessors` -- the recipe fields it can
  state, whether it declares any, and the declared fields whose attribute the class lacks.
- :func:`protocols` -- the protocols it declares.
- :func:`builtin`, :func:`importable` -- whether this build ships the adapter, and whether it can
  import it.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def adapter_for(kind: str) -> Any:
    """Return the class this kind names, built-in or registered by another distribution.

    Imported here rather than at module load: `Recipe` is meant to be parseable without the
    adapters, and this is the one thing it needs from them. The adapters cost 0.16 s to import and
    open nothing, so a check that consults them still reports before any I/O. A registered kind is
    consulted too, because a build that read less of one than of a built-in would give an adapter
    from another distribution the worse deal (Part 05 §3.4).
    """
    from . import sources

    return sources.ADAPTERS.get(kind) or sources.discovered().get(kind)


def states(kind: str) -> Mapping[str, str]:
    """Return the recipe fields an adapter of this kind can state, to the attribute holding each.

    Part 05 §3.4 puts the obligation on the build rather than on the adapter, so a kind whose adapter
    declares nothing is reported by `check` rather than silently treated as stating nothing --
    which is the failure `produces` has, and which R63 §4 left open.
    """
    adapter = adapter_for(kind)
    stated = getattr(adapter, "STATES", None) if adapter is not None else None
    return dict(stated) if stated is not None else {}


def declares_states(kind: str) -> bool:
    """Whether this kind's adapter declares `STATES` at all, empty or not (Part 05 §3.4)."""
    adapter = adapter_for(kind)
    return adapter is not None and getattr(adapter, "STATES", None) is not None


def state_accessors(kind: str) -> Mapping[str, str]:
    """`STATES` entries whose named attribute the adapter class does not expose (Part 05 §3.4)."""
    adapter = adapter_for(kind)
    return {f: a for f, a in states(kind).items() if adapter is not None and not hasattr(adapter, a)}


def needs(kind: str) -> tuple[str, ...]:
    """Return the names a build must supply an adapter of this kind (Part 05 §3.4).

    Each resolves against Part 12 §4's terms first and the recipe's options second, so what a
    recipe has to carry is whatever is left: the declaration is where the options a source cannot
    be constructed without are recorded, rather than a table here keyed by kind.
    """
    # The floor is what every adapter needs and no declaration can omit: a root to open and the
    # session it is built for (Part 12 §4).
    adapter = adapter_for(kind)
    return tuple(getattr(adapter, "NEEDS", ("root", "session_id")) if adapter is not None else ())


def accepts(kind: str) -> tuple[str, ...]:
    """Return the options an adapter of this kind reads and can run without (Part 05 §3.4).

    Separate from `needs` because the two differ in what a recipe owes: a declared need a recipe
    does not set is refused, so an option holding a default is declarable only here (R119 §2.1).
    """
    adapter = adapter_for(kind)
    return tuple(getattr(adapter, "ACCEPTS", ()) if adapter is not None else ())


def consumes(kind: str) -> tuple[str, ...]:
    """Return the kinds whose output an adapter of this kind reads (Part 05 §3.4)."""
    adapter = adapter_for(kind)
    return tuple(getattr(adapter, "CONSUMES", ()) if adapter is not None else ())


def contributes(kind: str) -> frozenset[str]:
    """Return the resources an adapter of this kind supplies only part of (Part 05 §3.4).

    A source entry without `owns` contributes these rather than owning them, because every such
    adapter supplies its own streams' clocks or its own arrays and devices, and another source
    supplies the rest.
    """
    adapter = adapter_for(kind)
    return frozenset(getattr(adapter, "CONTRIBUTES", ()) if adapter is not None else ())


def protocols(kind: str) -> tuple[str, ...]:
    """Return the protocols an adapter of this kind declares, empty for one this build ships."""
    adapter = adapter_for(kind)
    return tuple(getattr(adapter, "PROTOCOLS", ()) if adapter is not None else ())


def produces(kind: str) -> frozenset[str]:
    """Return what an adapter of this kind can supply (Part 05 §3.4).

    Empty where no adapter of this kind can be imported, which `check` reports through the
    declaration a recipe must then name (Part 12 §7) rather than treating as a source that
    produces nothing.
    """
    adapter = adapter_for(kind)
    return frozenset(getattr(adapter, "PRODUCES", ()) if adapter is not None else ())


def builtin(kind: str) -> bool:
    """Whether this build ships the adapter for a kind, which is what makes in process its route."""
    from . import sources

    return kind in sources.ADAPTERS


def importable(kind: str) -> bool:
    """Whether this build can read a kind's declarations by importing its adapter."""
    return adapter_for(kind) is not None


__all__ = [
    "accepts",
    "adapter_for",
    "builtin",
    "consumes",
    "contributes",
    "declares_states",
    "importable",
    "needs",
    "produces",
    "protocols",
    "state_accessors",
    "states",
]
