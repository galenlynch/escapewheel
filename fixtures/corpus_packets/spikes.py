"""Packets that carry materialized spikes."""

from pathlib import Path

from .record import Build, Expected, Packet
from .session import content
from .writing import edit_manifest, write_packet


def materialize(c, clock):
    c["analysis.spike_events"] = [
        {
            "session_id": s["session_id"],
            "unit_id": s["unit_id"],
            "t_tick": s["t_tick"],
            "clock_id": clock,
            "time_bucket_tick": s["t_tick"] // SPIKE_BUCKET_TICKS * SPIKE_BUCKET_TICKS,
        }
        for s in c["core.spike_events"]
    ]


def ap_clock_only(c):
    # The AP clock alone, so the units keep theirs and only the missing reference is wrong.
    c["core.clocks"] = [clock for clock in c["core.clocks"] if clock["clock_id"] == "imec_ap_s001"]
    c["core.clock_observation_intervals"] = [
        r for r in c["core.clock_observation_intervals"] if r["clock_id"] == "imec_ap_s001"
    ]
    c.pop("core.clock_anchors", None)
    for rows in c.values():
        for row in rows:
            if row.get("clock_id") == "behavior_s001":
                row["clock_id"] = "imec_ap_s001"
    c["core.sessions"][0]["reference_clock_id"] = None


def derive_spikes(manifest: dict) -> None:
    for entry in manifest["resources"]:
        if entry["resource_id"] == "analysis.spike_events":
            entry["derived_from"] = ["core.spike_events"]


#: The width of a materialized spike's time bucket, in ticks of its clock.
SPIKE_BUCKET_TICKS = 100_000


def materialized(clock: str, mutate=None) -> Build:
    """A build of the valid session with its spikes materialized on `clock`, once `mutate` has edited its rows."""

    def build(out: Path) -> None:
        c = content()
        if mutate is not None:
            mutate(c)
        materialize(c, clock)
        write_packet(out, c)
        edit_manifest(out, derive_spikes)

    return build


#: Part 06 §4's materialized spikes: on the reference clock, off it, and in a session naming none.
SPIKE_PACKETS = (
    Packet("spikes_on_reference_clock", materialized("imec_ap_s001")),
    Packet(
        "spikes_off_reference_clock",
        materialized("behavior_s001"),
        Expected("error", "analysis.spike_events.on_reference_clock"),
    ),
    Packet(
        "spikes_without_reference_clock",
        materialized("imec_ap_s001", ap_clock_only),
        Expected("error", "analysis.spike_events.on_reference_clock"),
    ),
)
