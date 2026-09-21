"""Choosing between coexisting runs (R41, R44)."""

import json
import shutil

import pyarrow as pa
import pytest

from escapewheel_reader import open_packet
from escapewheel_reader.errors import AmbiguousRun
from escapewheel_reader.runs import ambiguities, check, preferences, preferred_run

from .conftest import SESSION, UNITS, _resource, _write


def _with_runs(tmp_path, packet_root, name, runs, prefs=None):
    """Copy the fixture packet and give it a run log, optionally with preferences.

    `runs` is a list of ``(run_id, activity_type, scope)``; a scope of None is a run whose
    subject the packet does not record, which is the state R44 §2.1 exists to remove. The kind
    (R49 §2.1) is derived from the activity, since every scope in these fixtures is a probe or a
    sorting run.
    """
    kind_of = {
        "spike_sorting": "core.probes",
        "curation": "core.sorting_runs",
        "pose_estimation": "core.devices",
        "import": "core.sessions",
    }
    root = tmp_path / name
    shutil.copytree(packet_root, root)
    manifest = json.loads((root / "packet.json").read_text())

    table = pa.table(
        {
            "processing_run_id": pa.array([r[0] for r in runs]),
            "session_id": pa.array([SESSION] * len(runs)),
            "activity_type": pa.array([r[1] for r in runs]),
            "scope_kind": pa.array([kind_of.get(r[1]) if r[2] else None for r in runs], type=pa.string()),
            "scope": pa.array([r[2] for r in runs], type=pa.string()),
            "status": pa.array(["succeeded"] * len(runs)),
        }
    )
    manifest["resources"].append(_resource("core.processing_runs", _write(root, "processing_runs", table)))

    if prefs:
        chosen = pa.table(
            {
                "session_id": pa.array([SESSION] * len(prefs)),
                "activity_type": pa.array([p[0] for p in prefs]),
                "scope_kind": pa.array([kind_of[p[0]] for p in prefs]),
                "scope": pa.array([p[1] for p in prefs]),
                "processing_run_id": pa.array([p[2] for p in prefs]),
            }
        )
        manifest["resources"].append(_resource("core.preferred_runs", _write(root, "preferred_runs", chosen)))

    (root / "packet.json").write_text(json.dumps(manifest, indent=2))
    return open_packet(root)


def test_no_run_log_is_clean(packet_root):
    """A packet recording no provenance has nothing to disambiguate (Part 01 §2.4)."""
    assert ambiguities(open_packet(packet_root)) == ()
    assert check(open_packet(packet_root)) is None


def test_one_run_per_scope_is_unambiguous(tmp_path, packet_root):
    """Twelve probes sorted once each are complementary, not alternatives (R44 §1).

    Grouping by activity alone would call this ambiguous, which is the mistake R44 exists to
    stop; the scope is what separates the two cases.
    """
    runs = [(i, "spike_sorting", f"probe_{i}") for i in range(12)]
    packet = _with_runs(tmp_path, packet_root, "per_probe", runs)
    assert ambiguities(packet) == ()
    assert check(packet) is None


def test_two_runs_one_scope_is_ambiguous(tmp_path, packet_root):
    """One probe sorted twice, with nothing saying which to read (Part 01 §2.4)."""
    runs = [(1, "spike_sorting", "probe_1"), (2, "spike_sorting", "probe_1")]
    packet = _with_runs(tmp_path, packet_root, "resorted", runs)

    (found,) = ambiguities(packet)
    assert found.activity_type == "spike_sorting"
    assert found.scope == "probe_1"
    assert set(found.run_ids) == {1, 2}
    assert found.determinable

    with pytest.raises(AmbiguousRun, match="does not say which run to read"):
        check(packet)


def test_a_preference_resolves_it(tmp_path, packet_root):
    """A declared preference settles the choice and removes the finding (Part 01 §2.4)."""
    runs = [(1, "spike_sorting", "probe_1"), (2, "spike_sorting", "probe_1")]
    packet = _with_runs(tmp_path, packet_root, "chosen", runs, prefs=[("spike_sorting", "probe_1", 2)])

    assert ambiguities(packet) == ()
    assert check(packet) is None
    assert preferred_run(packet, "spike_sorting", "core.probes", "probe_1") == 2
    assert preferences(packet) == {(SESSION, "spike_sorting", "core.probes", "probe_1"): 2}


def test_a_preference_does_not_leak_across_scopes(tmp_path, packet_root):
    """Choosing for one probe says nothing about another."""
    runs = [
        (1, "spike_sorting", "probe_1"),
        (2, "spike_sorting", "probe_1"),
        (3, "spike_sorting", "probe_2"),
        (4, "spike_sorting", "probe_2"),
    ]
    packet = _with_runs(tmp_path, packet_root, "half_chosen", runs, prefs=[("spike_sorting", "probe_1", 1)])

    (found,) = ambiguities(packet)
    assert found.scope == "probe_2"


def test_unrecorded_scope_warns_rather_than_refusing(tmp_path, packet_root):
    """Without scopes the packet cannot be judged either way (Part 01 §2.4).

    Reported rather than refused, because the fix is to record the scopes and not to choose
    between the runs.
    """
    runs = [(1, "spike_sorting", None), (2, "spike_sorting", None)]
    packet = _with_runs(tmp_path, packet_root, "unscoped", runs)

    (found,) = ambiguities(packet)
    assert not found.determinable
    assert found.scope is None

    with pytest.warns(UserWarning, match="alternatives or complementary"):
        check(packet)


def test_one_unscoped_run_is_not_a_finding(tmp_path, packet_root):
    """A single run needs no scope: it is the preference by construction (Part 01 §2.4)."""
    runs = [(1, "import", None), (2, "spike_sorting", "probe_1")]
    packet = _with_runs(tmp_path, packet_root, "one_each", runs)
    assert ambiguities(packet) == ()


def test_preferred_run_falls_back_to_the_only_run(tmp_path, packet_root):
    """Exactly one run needs no declaration to be the answer."""
    runs = [(1, "spike_sorting", "probe_1")]
    packet = _with_runs(tmp_path, packet_root, "single", runs)
    assert preferred_run(packet, "spike_sorting", "core.probes", "probe_1") == 1


def test_preferred_run_refuses_to_guess(tmp_path, packet_root):
    """Two runs and no preference is an error, not a choice (Part 01 §2.4)."""
    runs = [(1, "spike_sorting", "probe_1"), (2, "spike_sorting", "probe_1")]
    packet = _with_runs(tmp_path, packet_root, "guess", runs)
    with pytest.raises(AmbiguousRun, match="none is preferred"):
        preferred_run(packet, "spike_sorting", "core.probes", "probe_1")


def test_preferred_run_rejects_an_unknown_purpose(tmp_path, packet_root):
    """Asking about a purpose the packet has no run for is a lookup failure, not ambiguity."""
    runs = [(1, "spike_sorting", "probe_1")]
    packet = _with_runs(tmp_path, packet_root, "unknown", runs)
    with pytest.raises(KeyError, match="no 'spike_sorting' run for scope 'probe_9'"):
        preferred_run(packet, "spike_sorting", "core.probes", "probe_9")


def test_units_refuses_an_unresolved_sorting(tmp_path, packet_root):
    """The accessor promising "the units" must not hand back two sortings of them."""
    runs = [(1, "spike_sorting", "probe_1"), (2, "spike_sorting", "probe_1")]
    packet = _with_runs(tmp_path, packet_root, "units_refuse", runs)
    with pytest.raises(AmbiguousRun):
        packet.units()


def test_exact_spike_selection_bypasses_an_unresolved_sorting(tmp_path, packet_root):
    """A packet-unique unit ID selects rows; it does not ask which result is current."""
    runs = [(1, "curation", "sort_1"), (2, "curation", "sort_1")]
    packet = _with_runs(tmp_path, packet_root, "spikes_refuse", runs)
    assert packet.spike_times(UNITS[0]).num_rows == 3
    explicit = packet.table("core.units", unit_id=UNITS[0])
    assert packet.spike_times(units=explicit).num_rows == 3


def test_the_raw_table_read_is_the_escape_hatch(tmp_path, packet_root):
    """`table` promises rows, not units, so it returns them and stays unguarded."""
    runs = [(1, "spike_sorting", "probe_1"), (2, "spike_sorting", "probe_1")]
    packet = _with_runs(tmp_path, packet_root, "escape", runs)
    assert packet.table("core.units").num_rows == 2


def test_an_unrelated_activity_does_not_block_units(tmp_path, packet_root):
    """Two pose-estimation runs say nothing about which sorting to read."""
    runs = [
        (1, "spike_sorting", "probe_1"),
        (2, "pose_estimation", "camera_1"),
        (3, "pose_estimation", "camera_1"),
    ]
    packet = _with_runs(tmp_path, packet_root, "unrelated", runs)
    assert packet.units().num_rows == 2
    with pytest.raises(AmbiguousRun, match="pose_estimation"):
        check(packet)
