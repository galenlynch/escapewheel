"""Packets about how units are numbered."""

from datetime import timedelta

from .record import Expected, Packet
from .session import variant


def labelled(first, second):
    def mutate(c):
        c["core.units"][0]["local_unit_label"] = first
        c["core.units"][1]["local_unit_label"] = second

    return mutate


def later_run(c):
    # A second run of the same probe, whose one curation holds the second unit.
    run, curation = c["core.sorting_runs"][0], c["core.curation_versions"][0]
    c["core.sorting_runs"].append(
        run
        | {
            "sorting_run_id": "sort_ks4_002",
            "started_at": run["ended_at"],
            "ended_at": run["ended_at"] + timedelta(hours=1),
        }
    )
    c["core.sorting_run_channels"] += [r | {"sorting_run_id": "sort_ks4_002"} for r in c["core.sorting_run_channels"]]
    c["core.curation_versions"].append(
        curation
        | {
            "curation_id": "curation_002",
            "sorting_run_id": "sort_ks4_002",
            "created_at": curation["created_at"] + timedelta(hours=2),
        }
    )
    c["core.units"][1] |= {"sorting_run_id": "sort_ks4_002", "curation_id": "curation_002"}


#: Part 02 §12.1's numbering: packets numbering units in each admitted order, and one per defect.
#: The two units are named "1" and "2" and numbered in that order unless a variant says otherwise.
UNIT_PACKETS = (
    Packet(
        "units_numbered_by_scalar",
        variant(labelled("10", "2")),
        Expected("error", "core.units.numbered_in_order"),
    ),
    Packet(
        "units_numbered_from_one",
        variant(numbers={"unit_id": {"1": 1, "2": 2}}),
        Expected("error", "core.units.numbered_in_order"),
    ),
    Packet("unit_labels_by_length", variant(labelled("7", "007"))),
    Packet("null_unit_labels", variant(labelled(None, None))),
    Packet("null_unit_labels_swapped", variant(labelled(None, None), numbers={"unit_id": {"2": 0, "1": 1}})),
    Packet("later_run_numbered_first", variant(later_run, numbers={"unit_id": {"2": 0, "1": 1}})),
)
