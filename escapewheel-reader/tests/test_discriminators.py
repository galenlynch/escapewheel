"""Resolving a discriminator, which Part 02 §8.3 asks a reader to offer."""

from __future__ import annotations

import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from escapewheel_reader import declared, kinds, open_packet, resolved, specialised, unresolved


def _with_detail(packet_root, *, kind="task.trials"):
    """Add the detail table `core.intervals` already names, as a shared-key resource.

    The fixture's rows name `task.trials` and nothing holds it, which is how the packet arrives:
    a kind that resolves to nothing. Giving it the table is what makes the join testable.
    """
    manifest = packet_root / "packet.json"
    entry = json.loads(manifest.read_text())
    rows = json.loads((packet_root / "schemas" / "logical_schemas.json").read_text())
    intervals = pq.read_table(packet_root / "tables" / "core" / "intervals.parquet")

    detail = pa.table({
        "session_id": intervals.column("session_id"),
        "interval_kind": intervals.column("interval_kind"),
        "trial_id": intervals.column("interval_id"),
        "outcome": pa.array(["hit", "miss"]),
    })
    path = packet_root / "tables" / "task"
    path.mkdir(parents=True, exist_ok=True)
    pq.write_table(detail, path / "trials.parquet")

    entry["resources"].append({
        "resource_id": kind,
        "layer": "core",
        "kind": "table",
        "uri": "tables/task/trials.parquet",
    })
    manifest.write_text(json.dumps(entry))

    rows["tables"][kind] = {
        "columns": [
            {"name": "session_id", "type": "int32", "presence": "required", "role": "identifier"},
            {"name": "interval_kind", "type": "string", "presence": "required", "role": "data"},
            {"name": "trial_id", "type": "int32", "presence": "required", "role": "identifier"},
            {"name": "outcome", "type": "string", "presence": "optional", "role": "data"},
        ],
        "primary_key": ["session_id", "trial_id"],
        "references": [{
            "columns": ["session_id", "interval_kind", "trial_id"],
            "resource": "core.intervals",
            "resource_columns": ["session_id", "interval_kind", "interval_id"],
        }],
        "rules": [],
    }
    (packet_root / "schemas" / "logical_schemas.json").write_text(json.dumps(rows))
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
