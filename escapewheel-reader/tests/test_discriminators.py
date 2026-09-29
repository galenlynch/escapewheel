"""Resolving a discriminator, which Part 05 §13.4 asks a reader to offer."""

from __future__ import annotations

import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from escapewheel_reader import declared, kinds, open_packet, resolved, specialised, unresolved

from .conftest import install_registry, read_registry


def _with_detail(packet_root, *, kind="task.trials"):
    """Add the detail table `core.intervals` already names, as a shared-key resource.

    The fixture's rows name `task.trials` and nothing holds it, which is how the packet arrives:
    a kind that resolves to nothing. Giving it the table is what makes the join testable.
    """
    manifest = packet_root / "packet.json"
    entry = json.loads(manifest.read_text())
    rows = read_registry(packet_root)
    intervals = pq.read_table(packet_root / "tables" / "core" / "intervals.parquet")

    detail = pa.table(
        {
            "session_id": intervals.column("session_id"),
            "trial_id": intervals.column("interval_id"),
            "outcome": pa.array(["hit", "miss"]),
        }
    )
    path = packet_root / "tables" / "task"
    path.mkdir(parents=True, exist_ok=True)
    pq.write_table(detail, path / "trials.parquet")

    entry["resources"].append(
        {
            "resource_id": kind,
            "declaration_id": kind,
            "uri": "tables/task/trials.parquet",
        }
    )
    manifest.write_text(json.dumps(entry))

    rows["resources"][kind] = {
        "content_class": "extension",
        "kind": "table",
        "instances": {"mode": "singleton", "presence": "optional"},
        "requires": [],
        "lineage": "optional",
        "table": {
            "columns": [
                {"name": "session_id", "type": "int32", "presence": "required", "role": "identifier"},
                {"name": "trial_id", "type": "int32", "presence": "required", "role": "identifier"},
                {"name": "outcome", "type": "string", "presence": "optional", "role": "data"},
            ],
            "primary_key": ["trial_id"],
            "references": [
                {"columns": ["session_id"], "resource": "core.sessions", "resource_columns": ["session_id"]},
                {"columns": ["trial_id"], "resource": "core.intervals", "resource_columns": ["interval_id"]},
            ],
            "rules": [],
        },
    }
    install_registry(packet_root, rows)
    return open_packet(packet_root)


def test_a_discriminator_is_found_with_its_shape(packet_root):
    found = {d.column: d for d in declared(open_packet(packet_root))}
    assert found["interval_kind"].shape == "shared key"
    assert found["interval_kind"].resolves == "required"
    assert found["interval_kind"].specialised == "core.intervals"


def test_kinds_counts_what_the_rows_name(packet_root):
    assert kinds(open_packet(packet_root), "core.intervals") == {"task.trials": 2}


def test_a_kind_the_packet_does_not_hold_is_a_defect_where_it_must_resolve(packet_root):
    """Part 02 §8.3: `required` makes an unresolvable value a defect, `optional` a fact."""
    reported = {u.kind: u for u in unresolved(open_packet(packet_root))}
    assert reported["task.trials"].level == "defect"
    assert "does not hold" in str(reported["task.trials"])


def test_the_join_crosses_into_the_named_resource(packet_root):
    """The shared-key shape: join on the discriminated table's whole key (Part 02 §8.3)."""
    table = resolved(_with_detail(packet_root), "core.intervals", "task.trials")
    assert table.num_rows == 2
    assert set(table.column("outcome").to_pylist()) == {"hit", "miss"}
    assert "start_tick" in table.column_names  # the discriminated row's own columns survive
    assert table.column_names.count("session_id") == 1  # a column both tables carry is kept once


def test_a_key_without_the_kind_resolves_only_rows_of_that_kind(packet_root):
    """`core.intervals` keys on `interval_id` alone, so the kind filters the rows before the join."""
    _with_detail(packet_root)
    intervals = pq.read_table(packet_root / "tables" / "core" / "intervals.parquet")
    kinds_column = intervals.schema.get_field_index("interval_kind")
    relabelled = intervals.set_column(kinds_column, "interval_kind", pa.array(["task.trials", "task.pulses"]))
    pq.write_table(relabelled, packet_root / "tables" / "core" / "intervals.parquet")
    table = resolved(open_packet(packet_root), "core.intervals", "task.trials")
    assert table.column("interval_id").to_pylist() == [0]


def test_resolution_is_keyed_by_kind_because_two_kinds_do_not_concatenate(packet_root):
    holding = _with_detail(packet_root)
    assert {k: t.num_rows for k, t in specialised(holding, "core.intervals").items()} == {"task.trials": 2}


def test_a_kind_that_resolves_is_not_reported_unresolved(packet_root):
    reported = unresolved(_with_detail(packet_root))
    assert "task.trials" not in {u.kind for u in reported}
    # A row declaring no kind is undeterminable whatever the packet holds, and stays reported.
    assert all(u.kind is None and u.level == "undeterminable" for u in reported)


def test_naming_a_kind_the_packet_lacks_says_so(packet_root):
    with pytest.raises(LookupError, match="does not hold"):
        resolved(open_packet(packet_root), "core.intervals", "task.trials")


def test_a_table_with_no_discriminator_says_so(packet_root):
    with pytest.raises(LookupError, match="declares no discriminator"):
        kinds(open_packet(packet_root), "core.units")


def _demo_table(columns, key, references=()):
    return {
        "content_class": "extension",
        "kind": "table",
        "instances": {"mode": "singleton", "presence": "optional"},
        "requires": [],
        "lineage": "optional",
        "table": {"columns": columns, "primary_key": key, "references": list(references), "rules": []},
    }


def _add_tables(packet_root, declarations, tables):
    """Declare and write demo tables, returning the reopened packet."""
    entry = json.loads((packet_root / "packet.json").read_text())
    rows = read_registry(packet_root)
    (packet_root / "tables" / "demo").mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        uri = f"tables/demo/{name.split('.')[1]}.parquet"
        pq.write_table(table, packet_root / uri)
        entry["resources"].append({"resource_id": name, "declaration_id": name, "uri": uri})
        rows["resources"][name] = declarations[name]
    (packet_root / "packet.json").write_text(json.dumps(entry))
    install_registry(packet_root, rows)
    return open_packet(packet_root)


def _identifier(name, presence="required", identity="assigned"):
    return {"name": name, "type": "int32", "presence": presence, "role": "identifier", "identity": identity}


def _labelled(packet_root):
    """Two axes: one labelled by units, one by sessions, with each position's row in `demo.labels`.

    Label 1 names a unit on the first axis and nothing on the second, where the only session is
    another number: a value resolves in its own row's kind.
    """
    session = open_packet(packet_root).table("core.sessions").column("session_id")[0].as_py()
    unit = open_packet(packet_root).table("core.units").column("unit_id")[0].as_py()
    axes = _demo_table(
        [
            _identifier("axis_id", identity="carried"),
            {
                "name": "names",
                "type": "string",
                "presence": "nullable",
                "role": "discriminator",
                "resolves": "required",
                "discriminates_via": "demo.labels.axis_id",
                "discriminates": "label_id",
            },
        ],
        ["axis_id"],
    )
    labels = _demo_table(
        [
            _identifier("axis_id", identity="carried"),
            {"name": "position_index", "type": "int64", "presence": "required", "role": "structural_index"},
            _identifier("label_id", presence="nullable"),
        ],
        ["axis_id", "position_index"],
        [{"columns": ["axis_id"], "resource": "demo.axes", "resource_columns": ["axis_id"]}],
    )
    return _add_tables(
        packet_root,
        {"demo.axes": axes, "demo.labels": labels},
        {
            "demo.axes": pa.table(
                {"axis_id": pa.array([1, 2], type=pa.int32()), "names": pa.array(["core.units", "core.sessions"])}
            ),
            "demo.labels": pa.table(
                {
                    "axis_id": pa.array([1, 1, 2, 2], type=pa.int32()),
                    "position_index": pa.array([0, 1, 0, 1], type=pa.int64()),
                    "label_id": pa.array([unit, None, session, unit], type=pa.int32()),
                }
            ),
        },
    )


def test_an_identifier_paired_value_resolves_through_the_specialised_table(packet_root):
    """Part 02 §8.3: the value sits on the table `discriminates_via` names and holds the key itself."""
    packet = _labelled(packet_root)
    units = resolved(packet, "demo.axes", "core.units")
    assert units.column("position_index").to_pylist() == [0], "a null value names no row"
    assert "quality_label" in units.column_names
    sessions = resolved(packet, "demo.axes", "core.sessions")
    assert sessions.column("position_index").to_pylist() == [0], "a unit's number is not a session's"


def test_a_string_paired_value_joins_an_assigned_keys_name(packet_root):
    """On its own table, a string value names an assigned key's row by its `*_name` (Part 02 §8.3)."""
    name = open_packet(packet_root).table("core.sessions").column("session_name")[0].as_py()
    runs = _demo_table(
        [
            _identifier("run_id", identity="carried"),
            {
                "name": "scope_kind",
                "type": "string",
                "presence": "required",
                "role": "discriminator",
                "resolves": "optional",
                "discriminates": "scope",
            },
            {"name": "scope", "type": "string", "presence": "required", "role": "data"},
        ],
        ["run_id"],
    )
    packet = _add_tables(
        packet_root,
        {"demo.runs": runs},
        {
            "demo.runs": pa.table(
                {
                    "run_id": pa.array([1, 2], type=pa.int32()),
                    "scope_kind": pa.array(["core.sessions", "demo.rigs"]),
                    "scope": pa.array([name, name]),
                }
            )
        },
    )
    joined = resolved(packet, "demo.runs", "core.sessions")
    assert joined.column("run_id").to_pylist() == [1]
    assert "session_start_time" in joined.column_names
