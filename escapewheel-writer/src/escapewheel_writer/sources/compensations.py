"""Declare what an adapter does about a known fault in its source, so the packet records it.

- :class:`Compensation` -- one fault, what an adapter does about it, and where it is measured.
- :class:`Compensates` -- the mixin through which an adapter declares a compensation it applied.
- :func:`registered` -- every compensation an adapter may declare, built in or registered by a
  distribution.
- :func:`describe` -- applied compensations rendered for `core.processing_runs.parameters`.
- :data:`COMPENSATIONS` -- the compensations this package declares.
- :data:`COMPENSATION_GROUP` -- the entry-point group under which a distribution registers its
  own compensations.

A packet shows no trace of a correction, so one still applied after its fault is fixed upstream
goes wrong unseen. Passing a fault through on purpose is an assumption too, and is registered the
same way.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import Any

from ..errors import CompensationsInvalid, UnknownCompensation

#: Entry-point group a distribution registers its own compensations under. The value loads to a
#: mapping of identifier to :class:`Compensation`, or to a callable returning one.
#:
#: An adapter shipped elsewhere works around its own source's faults, and the record of what it
#: assumed has to reach the packet the same way a built-in adapter's does -- so the registry is
#: open for the same reason `escapewheel.extensions` and `escapewheel.sources` are. What stays
#: closed is this module's own dict: the writer declares the faults of the sources it reads, and
#: nothing else.
COMPENSATION_GROUP = "escapewheel.compensations"


@dataclass(frozen=True)
class Compensation:
    """One thing an adapter does about a known upstream fault.

    Attributes
    ----------
    defect : str
        What is wrong at the source.
    action : str
        What this importer does about it, including doing nothing on purpose.
    evidence : str
        Where the fault is measured.
    """

    defect: str
    action: str
    evidence: str


#: Every compensation an adapter may declare. A new one goes here with its evidence, so the
#: list stays a record of measured faults rather than a place to park a guess.
COMPENSATIONS: dict[str, Compensation] = {
    "nwb.signal_device_declared": Compensation(
        defect="an instrument acquired by a separate workflow contributes its data and none of "
        "its metadata: the stream lands in the packet while no metadata document mentions it at "
        "all -- measured on ecephys_786867, zero occurrences across rig.json, metadata.nd.json, "
        "processing.json, quality_control.json and the behaviour JSON. The one statement that "
        "reaches the importer is the signal's own description, 'imported from HARP "
        "SniffDetector__32.bin', which is prose no join can reach",
        action="the instrument named in that description is used as the array's device link. The "
        "device row itself is read from the instrument's own schema where the recipe names that "
        "source, so nothing is invented here; without it the link dangles and the validator says "
        "so, which is the honest outcome for a packet missing a source",
        evidence="inventory/upstream-defects.md §signal-device-in-a-description",
    ),
    "nwb.stored_offset_kept": Compensation(
        defect="the NWB stamps -07:53 on a date of birth, the Local Mean Time of the Pacific "
        "coast and the signature of localising a date without a database",
        action="the stored value is kept and reported; overriding it would be a second guess on top of the first",
        evidence="inventory/nwb-zarr-776259-2025-04-09.md §3.2",
    ),
    "lfp.timestamps_distrusted": Compensation(
        defect="LFP timestamps carry a negated t0 and a regenerated nominal grid, putting LFP "
        "268 days from the spikes and drifting up to 70 ms per probe over a session",
        action="the stored timestamps are not read; the axis is derived from the probe's own "
        "clock, which the data shows LFP sample 0 begins on",
        evidence="inventory/upstream-defects.md §6, nwb-zarr-776259-2025-04-09.md §3.4-3.5",
    ),
}


def _mapping(loaded: Any, source: str) -> dict[str, Compensation]:
    """Coerce whatever an entry point loaded into a mapping of identifier to compensation."""
    if callable(loaded) and not isinstance(loaded, type):
        loaded = loaded()
    if not isinstance(loaded, dict):
        raise CompensationsInvalid(f"{source} loaded {type(loaded).__name__}, not a mapping of compensations")
    for identifier, entry in loaded.items():
        if not isinstance(entry, Compensation):
            raise CompensationsInvalid(
                f"{source} registered {identifier!r} as {type(entry).__name__}, not a Compensation"
            )
        if not (entry.defect and entry.action and entry.evidence):
            raise CompensationsInvalid(
                f"{source} registered {identifier!r} with no {'defect' if not entry.defect else ''}"
                f"{'action' if not entry.action else ''}{'evidence' if not entry.evidence else ''}"
            )
    return dict(loaded)


def registered() -> dict[str, Compensation]:
    """Every compensation an adapter may declare: this package's, plus what distributions register.

    A distribution that fails to load is skipped with its reason rather than raised, as an
    extension is: one broken package must not make every other compensation unregistered, which
    would turn a bad install into a build that refuses every adapter's `compensate`.

    A registered identifier never replaces a built-in one. The dict here is what this package
    measured and stands behind, and a third party silently redefining `lfp.timestamps_distrusted`
    would put its account of the defect into packets this writer built.
    """
    found = dict(COMPENSATIONS)
    for entry in entry_points(group=COMPENSATION_GROUP):
        try:
            loaded = _mapping(entry.load(), f"compensations {entry.name!r}")
        except Exception as exc:  # noqa: BLE001 - one broken package is one distribution, not all
            warnings.warn(f"compensations {entry.name!r} could not be loaded: {exc}", stacklevel=2)
            continue
        for identifier, compensation in loaded.items():
            if identifier in found:
                warnings.warn(
                    f"compensations {entry.name!r} redefines {identifier!r}, which is kept as declared here",
                    stacklevel=2,
                )
                continue
            found[identifier] = compensation
    return found


class Compensates:
    """Mixin giving an adapter somewhere to declare what it worked around.

    Parallel to `notes`, and separate on purpose: a note says what this run of this adapter
    found, while a compensation says what the importer assumes about the source in general.
    """

    def __init__(self) -> None:
        self.compensations: list[str] = []

    def compensate(self, identifier: str) -> None:
        """Declare that a registered compensation was applied."""
        if identifier not in registered():
            raise UnknownCompensation(
                f"{identifier!r} is not a registered compensation; add it with its evidence", identifier=identifier
            )
        if identifier not in self.compensations:
            self.compensations.append(identifier)


def describe(applied: list[str]) -> list[dict[str, str]]:
    """Render applied compensations for `core.processing_runs.parameters`."""
    known = registered()
    return [
        {"id": identifier, "defect": c.defect, "action": c.action, "evidence": c.evidence}
        for identifier in sorted(set(applied))
        if (c := known.get(identifier)) is not None
    ]


__all__ = ["COMPENSATIONS", "COMPENSATION_GROUP", "Compensates", "Compensation", "describe", "registered"]
