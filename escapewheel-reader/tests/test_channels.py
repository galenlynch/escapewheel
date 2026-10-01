"""Resolving a channel index through the list its run kept (Part 02 §12.2)."""

import json
import shutil

import numpy as np
import pyarrow as pa
import pytest

from escapewheel_reader import open_packet
from escapewheel_reader.channels import (
    ChannelsUndeclared,
    electrode_at,
    kept_channels,
    runs_without_channels,
)
from escapewheel_reader.errors import PacketError, UnresolvableChannelIndex

from .conftest import SESSION, SORTING_RUN, _resource, _write

#: The probe's four contacts, and the three a run kept: contact 1 is dropped, so every index from
#: 1 on names a different electrode than the contact list would -- which is the whole hazard.
CONTACTS = (100, 101, 102, 103)
KEPT = (100, 102, 103)


def _with_channels(tmp_path, packet_root, name, *, runs, channels):
    """Copy the fixture packet, give it a run log, and declare channels for some of the runs.

    `runs` is a list of run ids; `channels` maps a run id to the electrodes it kept, in the run's
    own order. A run absent from `channels` declares none, which Part 02 §12.2 makes a state a
    conforming packet may be in.
    """
    root = tmp_path / name
    shutil.copytree(packet_root, root)
    manifest = json.loads((root / "packet.json").read_text())
    i32, i64 = pa.int32(), pa.int64()

    manifest["resources"].append(
        _resource(
            "core.sorting_runs",
            _write(
                root,
                "sorting_runs",
                pa.table(
                    {
                        "sorting_run_id": pa.array(runs, type=i32),
                        "session_id": pa.array([SESSION] * len(runs), type=i32),
                        "probe_id": pa.array([0] * len(runs), type=i32),
                    }
                ),
            ),
        )
    )
    if channels:
        rows = [(run, index, electrode) for run, kept in channels.items() for index, electrode in enumerate(kept)]
        manifest["resources"].append(
            _resource(
                "core.sorting_run_channels",
                _write(
                    root,
                    "sorting_run_channels",
                    pa.table(
                        {
                            "session_id": pa.array([SESSION] * len(rows), type=i32),
                            "sorting_run_id": pa.array([r[0] for r in rows], type=i32),
                            "channel_index": pa.array([r[1] for r in rows], type=i64),
                            "electrode_id": pa.array([r[2] for r in rows], type=i32),
                        }
                    ),
                ),
            )
        )
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))
    return open_packet(root)


@pytest.fixture
def declaring(tmp_path, packet_root):
    """One run that kept three of the probe's four contacts."""
    return _with_channels(tmp_path, packet_root, "declaring", runs=[SORTING_RUN], channels={SORTING_RUN: KEPT})


@pytest.fixture
def silent(tmp_path, packet_root):
    """One run, and no channel list for it."""
    return _with_channels(tmp_path, packet_root, "silent", runs=[SORTING_RUN], channels={})


def test_an_index_counts_the_channels_the_run_kept(declaring):
    """Index 1 is the second channel kept, not the probe's second contact (Part 02 §12.2)."""
    assert electrode_at(declaring, SORTING_RUN, 1) == KEPT[1]
    assert KEPT[1] != CONTACTS[1]


def test_many_indices_resolve_in_one_pass(declaring):
    """6,781 units' peak channels are the real call, and one lookup each is not it."""
    found = electrode_at(declaring, SORTING_RUN, [0, 2, 1])
    assert list(found) == [KEPT[0], KEPT[2], KEPT[1]]
    assert found.dtype == np.int32


def test_a_run_declaring_no_channels_is_reported_not_resolved(silent):
    """Part 02 §12.2: the gap is a fact about the packet, so the caller is told which run it is."""
    assert runs_without_channels(silent) == (ChannelsUndeclared(SORTING_RUN, SESSION),)
    with pytest.raises(UnresolvableChannelIndex) as raised:
        electrode_at(silent, SORTING_RUN, 0)
    # `None` is what separates it from an index outside a declared list, and the two want
    # different repairs: record the list, against correct the index.
    assert raised.value.channels_declared is None


def test_the_packet_is_not_failed_for_declaring_no_channels(silent):
    """A conforming packet may hold no list at all, so nothing else about reading it changes."""
    assert kept_channels(silent) == {}
    assert silent.table("core.sorting_runs").num_rows == 1


def test_an_index_past_the_kept_list_names_how_many_there_were(declaring):
    """The index and the packet disagree about one run, which is a different fact from a gap."""
    with pytest.raises(UnresolvableChannelIndex) as raised:
        electrode_at(declaring, SORTING_RUN, len(KEPT))
    assert raised.value.channels_declared == len(KEPT)
    assert str(len(KEPT)) in str(raised.value)


def test_a_declared_run_is_not_reported_as_a_gap(declaring):
    """Only the runs a caller cannot resolve an index for are worth reporting."""
    assert runs_without_channels(declaring) == ()
    assert kept_channels(declaring) == {SORTING_RUN: KEPT}


def test_one_run_declaring_leaves_the_other_reported(tmp_path, packet_root):
    """A packet may know one run's channels and not another's; the answer is per run."""
    packet = _with_channels(
        tmp_path,
        packet_root,
        "mixed",
        runs=[SORTING_RUN, SORTING_RUN + 1],
        channels={SORTING_RUN: KEPT},
    )
    assert runs_without_channels(packet) == (ChannelsUndeclared(SORTING_RUN + 1, SESSION),)
    assert electrode_at(packet, SORTING_RUN, 0) == KEPT[0]


def test_a_packet_predating_the_table_reports_every_run(tmp_path, packet_root):
    """A writer may emit no such table (Part 02 §12.2), and the packet then declares no channels anywhere."""
    packet = _with_channels(tmp_path, packet_root, "older", runs=[SORTING_RUN], channels={})
    assert [gap.sorting_run_id for gap in runs_without_channels(packet)] == [SORTING_RUN]


def test_no_run_log_reports_nothing(packet_root):
    """A packet with no sorting runs has no index to resolve and no gap to report."""
    packet = open_packet(packet_root)
    assert runs_without_channels(packet) == ()
    assert kept_channels(packet) == {}


def test_a_gap_in_the_indices_is_refused(tmp_path, packet_root):
    """A position that is not the index it was recorded under returns a wrong electrode silently.

    `index_contiguous` refuses this at error level, and this reader validates nothing, so the
    check is repeated here rather than assumed.
    """
    packet = _with_channels(tmp_path, packet_root, "gapped", runs=[SORTING_RUN], channels={SORTING_RUN: KEPT})
    root = packet.root
    manifest = json.loads((root / "packet.json").read_text())
    i32, i64 = pa.int32(), pa.int64()
    _write(
        root,
        "sorting_run_channels",
        pa.table(
            {
                "session_id": pa.array([SESSION] * 3, type=i32),
                "sorting_run_id": pa.array([SORTING_RUN] * 3, type=i32),
                "channel_index": pa.array([0, 1, 3], type=i64),
                "electrode_id": pa.array(list(KEPT), type=i32),
            }
        ),
    )
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))
    with pytest.raises(PacketError, match="index_contiguous"):
        kept_channels(open_packet(root))


def test_the_report_says_which_run_and_which_session(silent):
    """A caller reporting the gap onward prints this, so it names both halves of the key."""
    line = str(runs_without_channels(silent)[0])
    assert f"sorting run {SORTING_RUN}" in line
    assert f"session {SESSION}" in line


def test_asking_for_one_run_does_not_return_another(tmp_path, packet_root):
    """Two runs on one probe may keep different channels, so the narrowing has to hold."""
    other = SORTING_RUN + 1
    packet = _with_channels(
        tmp_path,
        packet_root,
        "two",
        runs=[SORTING_RUN, other],
        channels={SORTING_RUN: KEPT, other: CONTACTS},
    )
    assert kept_channels(packet, sorting_run_id=other) == {other: CONTACTS}
    assert electrode_at(packet, other, 1) == CONTACTS[1]
    assert electrode_at(packet, SORTING_RUN, 1) == KEPT[1]


def test_a_table_missing_a_required_column_is_refused(tmp_path, packet_root):
    """Reading it as a run that declared nothing is the silent wrong answer, so it raises."""
    packet = _with_channels(tmp_path, packet_root, "narrow", runs=[SORTING_RUN], channels={SORTING_RUN: KEPT})
    root = packet.root
    i32 = pa.int32()
    _write(
        root,
        "sorting_run_channels",
        pa.table(
            {
                "session_id": pa.array([SESSION] * 3, type=i32),
                "sorting_run_id": pa.array([SORTING_RUN] * 3, type=i32),
                "electrode_id": pa.array(list(KEPT), type=i32),
            }
        ),
    )
    with pytest.raises(PacketError, match="carries no channel_index"):
        kept_channels(open_packet(root))
