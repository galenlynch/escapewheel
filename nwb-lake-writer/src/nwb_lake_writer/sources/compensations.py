"""What this importer does about faults in its sources, recorded rather than assumed.

Every adapter here works around something known to be wrong upstream — `inventory/`
carries eight such defects, measured. A correction is silent by construction: a packet built
from a corrected source looks exactly like one built from a source that was never broken.

That is fine until the fault is fixed. An importer that keeps compensating for a defect its
source no longer has does not fail; it produces a packet that is wrong in the opposite
direction, and nothing in the packet says so. Negating an LFP `t0` that has already been
negated is the concrete case.

So a compensation is declared, and every one an import applied lands in
`core.processing_runs.parameters`. A packet then answers "what did the importer assume about
its sources?", and when a defect is fixed upstream you can find the packets that assumed
otherwise. This is deliberately *not* a source version: some of our sources declare none, and
what matters for the audit is what we did rather than what we read.

A knowing pass-through is registered too. Choosing not to correct is as much an assumption as
choosing to.
"""

from __future__ import annotations

from dataclasses import dataclass


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
    "aind.stored_offset_distrusted": Compensation(
        defect="aind-data-schema JSONs stamp an offset that disagrees with the reading, "
        "notably +00:00 on a Pacific wall clock -- a seven-hour error",
        action="the stored offset is dropped and the reading localised to the declared zone",
        evidence="inventory/upstream-defects.md, nwb-zarr-776259-2025-04-09.md §3.1",
    ),
    "aind.tick_zero_from_stream_start": Compensation(
        defect="a HARP clock free-runs from device power-on, so tick 0 is a power-on instant "
        "no file records; the NWB's timestamps_reference_time claims to locate it and is wrong "
        "by 134 days",
        action="tick 0 is placed by pairing the ephys stream's declared start with the first "
        "spike observed on the clock, which is accurate to about a second -- the stream's "
        "whole-second stamp plus the sub-second wait for the first of thousands of units",
        evidence="inventory/nwb-zarr-776259-2025-04-09.md §3.1, §3.3",
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


class Compensates:
    """Mixin giving an adapter somewhere to declare what it worked around.

    Parallel to `notes`, and separate on purpose: a note says what this run of this adapter
    found, while a compensation says what the importer assumes about the source in general.
    """

    def __init__(self) -> None:
        self.compensations: list[str] = []

    def compensate(self, identifier: str) -> None:
        """Declare that a registered compensation was applied."""
        if identifier not in COMPENSATIONS:
            raise KeyError(f"{identifier!r} is not a registered compensation; add it with its evidence")
        if identifier not in self.compensations:
            self.compensations.append(identifier)


def describe(applied: list[str]) -> list[dict[str, str]]:
    """Render applied compensations for `core.processing_runs.parameters`."""
    return [
        {"id": identifier, "defect": c.defect, "action": c.action, "evidence": c.evidence}
        for identifier in sorted(set(applied))
        if (c := COMPENSATIONS.get(identifier)) is not None
    ]


__all__ = ["COMPENSATIONS", "Compensates", "Compensation", "describe"]
