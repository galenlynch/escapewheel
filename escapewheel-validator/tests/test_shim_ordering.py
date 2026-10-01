"""The ordering scan over one table, and the same comparison made over batches on the way in."""

from types import SimpleNamespace

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from escapewheel_reader import open_packet

from escapewheel_validator import OrderFault, OrderViolation, Report, validate
from escapewheel_validator.shim.ordering import _scan_one_ordering, verify_order

from .builders import rewrite_table


def _batch(first_tick, n=5, unit="u1"):
    return pa.record_batch(
        {
            "unit_id": pa.array([unit] * n),
            "t_tick": pa.array(range(first_tick, first_tick + n), type=pa.int64()),
        }
    )


KEYS = ["unit_id", "t_tick"]


def test_ordered_batches_pass_through_unchanged():
    batches = [_batch(0), _batch(5), _batch(10)]
    assert [b.num_rows for b in verify_order(iter(batches), KEYS)] == [5, 5, 5]


def test_a_descent_inside_a_batch_is_caught():
    bad = pa.record_batch({"unit_id": pa.array(["u1"] * 3), "t_tick": pa.array([0, 5, 2], type=pa.int64())})
    with pytest.raises(OrderViolation) as refused:
        list(verify_order(iter([bad]), KEYS))
    assert (refused.value.kind, refused.value.row, refused.value.resource_id) == (OrderFault.DESCENT, 2, None)


def test_a_descent_on_a_batch_seam_is_caught():
    """The case a per-batch check misses: each batch is ordered, the pair is not."""
    with pytest.raises(OrderViolation) as refused:
        list(verify_order(iter([_batch(10), _batch(0)]), KEYS))
    assert (refused.value.kind, refused.value.row) == (OrderFault.DESCENT, 5)


def test_a_duplicate_on_a_batch_seam_is_caught():
    tail = pa.record_batch({"unit_id": pa.array(["u1"]), "t_tick": pa.array([4], type=pa.int64())})
    with pytest.raises(OrderViolation) as refused:
        list(verify_order(iter([_batch(0), tail]), KEYS, unique=KEYS))
    assert (refused.value.kind, refused.value.row) == (OrderFault.REPEAT, 5)


def test_a_violation_is_worded_by_position_and_names_its_table_once_known():
    """The stored row is an index, so the sixth row is stored as 5 and reads as row 6."""
    with pytest.raises(OrderViolation) as refused:
        list(verify_order(iter([_batch(10), _batch(0)]), KEYS))
    assert str(refused.value).startswith("row 6 sorts before the row above it")
    refused.value.resource_id = "core.spike_events"
    assert str(refused.value).startswith("core.spike_events: row 6 sorts before")


def test_an_empty_batch_does_not_break_the_seam():
    empty = _batch(0, n=0)
    assert [b.num_rows for b in verify_order(iter([_batch(0), empty, _batch(5)]), KEYS)] == [5, 0, 5]


def test_a_row_breaking_a_determined_by_declaration_is_named_by_position(tmp_path):
    """Part 03 §5.3: the third row shares the second's key and differs in both columns the key determines."""
    path = tmp_path / "spike_events.parquet"
    pq.write_table(
        pa.table(
            {
                "session_id": pa.array([1, 1, 1, 1], type=pa.int32()),
                "clock_id": pa.array([1, 1, 2, 2], type=pa.int32()),
                "time_bucket_tick": pa.array([0, 0, 1, 1], type=pa.int64()),
                "unit_id": pa.array([1, 1, 1, 2], type=pa.int32()),
                "t_tick": pa.array([5, 6, 6, 9], type=pa.int64()),
            }
        ),
        path,
    )
    spec = {
        "columns": [
            {"name": "session_id"},
            {"name": "unit_id"},
            {"name": "t_tick"},
            {"name": "clock_id", "determined_by": ["session_id"]},
            {"name": "time_bucket_tick", "determined_by": ["t_tick"]},
        ],
        "primary_key": ["session_id", "unit_id", "t_tick"],
    }
    report = Report()
    handle = SimpleNamespace(path=path, schema=lambda: pq.read_schema(path))
    _scan_one_ordering("analysis.spike_events", handle, spec, report)
    assert [(f.check, f.rows) for f in report.findings] == [
        (
            "analysis.spike_events.determined_by",
            (("row 3", "clock_id", "1 != 2"), ("row 3", "time_bucket_tick", "0 != 1")),
        ),
        ("analysis.spike_events.primary_key_unique", (("row 3", "(1, 6)"),)),
    ]


def test_a_bound_registry_lacking_an_overrides_column_departs_from_its_order():
    """Part 03 §5.4: without `time_bucket_tick` the table cannot take the descriptor's order."""
    report = Report()
    spec = {
        "columns": [
            {"name": "session_id"},
            {"name": "unit_id"},
            {"name": "t_tick"},
            {"name": "clock_id", "determined_by": ["session_id"]},
        ],
        "primary_key": ["session_id", "unit_id", "t_tick"],
    }
    _scan_one_ordering("analysis.spike_events", None, spec, report)
    (finding,) = report.findings
    assert (finding.check, finding.level) == ("analysis.spike_events.physical_order", "error")
    assert "declares no time_bucket_tick" in finding.message


#: `analysis.spike_events` as a registry declares it: two sort columns ahead of the key, each
#: declared a function of it.
_SPIKE_EVENTS = {
    "columns": [
        {"name": "session_id"},
        {"name": "unit_id"},
        {"name": "t_tick"},
        {"name": "clock_id", "determined_by": ["session_id"]},
        {"name": "time_bucket_tick", "determined_by": ["t_tick"]},
    ],
    "primary_key": ["session_id", "unit_id", "t_tick"],
}


def _scanned_spike_events(tmp_path, *, clock_id, unit_id=(1, 1, 2), t_tick=(5, 5, 9)):
    """The ordering scan's findings over one session's spikes, as (check, rows) pairs."""
    path = tmp_path / "spike_events.parquet"
    rows = len(clock_id)
    pq.write_table(
        pa.table(
            {
                "session_id": pa.array([1] * rows, type=pa.int32()),
                "clock_id": pa.array(clock_id, type=pa.int32()),
                "time_bucket_tick": pa.array([0] * rows, type=pa.int64()),
                "unit_id": pa.array(unit_id, type=pa.int32()),
                "t_tick": pa.array(t_tick, type=pa.int64()),
            }
        ),
        path,
    )
    report = Report()
    handle = SimpleNamespace(path=path, schema=lambda: pq.read_schema(path))
    _scan_one_ordering("analysis.spike_events", handle, _SPIKE_EVENTS, report)
    return [(f.check, f.rows) for f in report.findings]


def test_a_repeated_key_under_a_constant_determined_column_is_only_a_duplicate(tmp_path):
    """Part 03 §5.3: a column the file holds as one value agrees with itself at every repeated key."""
    assert _scanned_spike_events(tmp_path, clock_id=[1, 1, 1]) == [
        ("analysis.spike_events.primary_key_unique", (("row 2", "(1, 5)"),)),
    ]


def test_a_repeated_key_under_a_varying_determined_column_is_also_a_false_declaration(tmp_path):
    assert _scanned_spike_events(tmp_path, clock_id=[1, 2, 2]) == [
        ("analysis.spike_events.determined_by", (("row 2", "clock_id", "1 != 2"),)),
        ("analysis.spike_events.primary_key_unique", (("row 2", "(1, 5)"),)),
    ]


def test_a_table_of_one_repeated_row_keeps_every_key_and_reports_the_duplicate(tmp_path):
    """Every key is constant, so the scan drops none of them and reads the determined columns."""
    assert _scanned_spike_events(tmp_path, clock_id=[1, 1], unit_id=[1, 1], t_tick=[5, 5]) == [
        ("analysis.spike_events.primary_key_unique", (("row 2", "(1, 1, 5)"),)),
    ]


def test_physical_order_is_an_error(packet_root):
    """Part 03 §5.3. A waiver may not rest on a property nothing requires.

    Part 02 §10.1 skips the uniqueness query for a table whose order settles its key, so the order
    is what a correctness check is discharged by and a departure fails the packet.
    """
    events = pq.read_table(packet_root / "tables" / "core" / "events.parquet")
    rewrite_table(packet_root, "events", events.take([2, 0, 1]))
    report = validate(open_packet(packet_root))
    assert not report.passed
    (finding,) = [f for f in report.findings if f.check == "core.events.physical_order"]
    assert finding.level == "error"
    # The second row sorts before the first: a finding names a row by its position.
    assert [row[0] for row in finding.rows] == ["row 2"]


def test_a_duplicate_beside_its_twin_is_caught_by_the_scan(packet_root):
    """core.intervals is sorted by its key, so duplicates are neighbours and no GROUP BY runs."""
    intervals = pq.read_table(packet_root / "tables" / "core" / "intervals.parquet")
    rewrite_table(packet_root, "intervals", intervals.take([0, 0, 1]))
    report = validate(open_packet(packet_root))
    assert not report.passed
    (finding,) = [f for f in report.findings if f.check == "core.intervals.primary_key_unique"]
    assert [row[0] for row in finding.rows] == ["row 2"]  # the second row repeats the first


def test_a_duplicate_out_of_order_still_fails(packet_root):
    """Adjacency is unsound on an unordered file, so uniqueness falls back to the aggregate.

    Ordering stays a warning -- a packet in the wrong order still conforms -- so the fallback
    is what keeps the check from passing by omission.
    """
    intervals = pq.read_table(packet_root / "tables" / "core" / "intervals.parquet")
    rewrite_table(packet_root, "intervals", intervals.take([1, 0, 0]))
    report = validate(open_packet(packet_root))
    assert not report.passed
    assert any(f.check == "core.intervals.primary_key_unique" for f in report.findings)


def test_scanning_nothing_leaves_the_ordering_unchecked(packet_root):
    """What `commit` relies on: a caller that established the order elsewhere skips the read."""
    intervals = pq.read_table(packet_root / "tables" / "core" / "intervals.parquet")
    rewrite_table(packet_root, "intervals", intervals.sort_by([("interval_id", "descending")]))
    assert any(f.check == "core.intervals.physical_order" for f in validate(open_packet(packet_root)).findings)
    assert not any(
        f.check == "core.intervals.physical_order" for f in validate(open_packet(packet_root), scan=set()).findings
    )
