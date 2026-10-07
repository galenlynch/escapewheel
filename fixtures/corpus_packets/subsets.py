"""Packets that carry some of the valid session's tables."""

from .record import Expected, Packet
from .registry import EXTENSION
from .session import EXTRACELLULAR, variant


def without_extracellular(c):
    for resource in EXTRACELLULAR:
        del c[resource]


def behavior_clock_only(c):
    without_extracellular(c)
    c["core.clocks"] = [clock for clock in c["core.clocks"] if clock["clock_id"] == "behavior_s001"]
    for field in ("parent_clock_id", "transform_slope", "transform_offset"):
        c["core.clocks"][0][field] = None
    c["core.clock_observation_intervals"] = [
        r for r in c["core.clock_observation_intervals"] if r["clock_id"] == "behavior_s001"
    ]
    c["core.sessions"][0]["reference_clock_id"] = None


def sessions_and_subjects_only(c):
    for resource in [resource for resource in c if resource not in ("core.sessions", "core.subjects")]:
        del c[resource]
    for session in c["core.sessions"]:
        session["reference_clock_id"] = None  # a named clock would bring core.clocks


#: The valid session with tables removed.
SUBSET_PACKETS = (
    # Part 00 §1: the packet mechanism confines no packet to extracellular data, so this and
    # `sessions_only` conform.
    Packet("no_extracellular", variant(without_extracellular)),
    # Part 01 §3.3: a session declaring one clock needs no reference to name it.
    Packet("one_clock", variant(behavior_clock_only)),
    Packet("sessions_only", variant(sessions_and_subjects_only)),
    # Part 04 §8: an extension declaring none of the packet's resources is bound, which a validator
    # warns of and which leaves the packet conforming.
    Packet(
        "unused_extension",
        variant(sessions_and_subjects_only, unused=(EXTENSION,)),
        Expected("warning", "packet.registry.unused", count=1, conforming=True),
    ),
)
