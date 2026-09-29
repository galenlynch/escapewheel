"""Writer, reader, and validator against the current registries, one cell per resource kind.

Each test commits with the writer, reads only through the reader's public API, and judges with
the validator, so a disagreement between any two of them fails here rather than in the field.
"""

import copy
import json
import re

import jsonschema
import numpy as np
import pytest
from escapewheel_reader import NumericAxis, Scaling, describe, open_packet
from escapewheel_validator import RegistryRejected, validate
from escapewheel_writer import CommitRefused

import example

MANIFEST_SCHEMA = json.loads((example.ROOT / "registry" / "manifest.schema.json").read_text())


def _entry(root, resource_id):
    (entry,) = [
        e for e in json.loads((root / "packet.json").read_text())["resources"] if e["resource_id"] == resource_id
    ]
    return entry


def _errors(caught):
    return {(f.check, f.registry) for f in caught.value.report.findings if f.level == "error"}


# -- core ----------------------------------------------------------------------------------


def test_the_example_validates_clean_with_every_registry_bound(packet_root):
    report = validate(open_packet(packet_root))
    assert report.passed and report.errors == 0
    assert set(report.bound) == {"core", *example.EXTENSIONS}


def test_every_table_reads_back_with_the_rows_written(packet_root):
    packet = open_packet(packet_root)
    written = {rid: len(rows) for rid, rows in example.tables().items()}
    # The materializer adds its own run, and maps every spike, since each is on the reference clock.
    written["core.processing_runs"] += 1
    written["analysis.spike_events"] = written["core.spike_events"]
    read = {r.resource_id: packet.table(r.resource_id).num_rows for r in packet.resources(kind="table")}
    assert read == written


def test_the_manifest_meets_the_published_schema_with_its_formats_asserted(packet_root):
    """Part 04 §10: `date-time` is asserted, not annotated, which needs a checker that knows it."""
    checker = jsonschema.Draft202012Validator.FORMAT_CHECKER
    assert "date-time" in checker.checkers, "install rfc3339-validator, or date-time passes anything"
    schema = jsonschema.Draft202012Validator(MANIFEST_SCHEMA, format_checker=checker)
    manifest = json.loads((packet_root / "packet.json").read_text())
    assert list(schema.iter_errors(manifest)) == []
    malformed = dict(manifest, created_at="26 September 2026")
    assert [error.validator for error in schema.iter_errors(malformed)] == ["format"]


# -- extensions ----------------------------------------------------------------------------


@pytest.mark.parametrize("resource_id", ["dynamic_foraging.trials", "aind_unit_qc.metrics"])
def test_a_shipped_extension_table_is_declared_read_and_validated(packet_root, resource_id):
    extension_id = resource_id.split(".", 1)[0]
    packet = open_packet(packet_root)
    assert _entry(packet_root, resource_id)["declaration_id"] == resource_id
    assert packet.table(resource_id).num_rows == len(example.tables()[resource_id])
    validated = [
        f for f in validate(packet).findings if f.check == "extension.validated" and f.registry == extension_id
    ]
    assert len(validated) == 1


def test_an_extension_row_breaking_its_rule_refuses_the_commit(tmp_path):
    rows = example.tables()
    rows["aind_unit_qc.metrics"][0]["presence_ratio"] = 1.5
    root = tmp_path / example.SESSION
    with pytest.raises(CommitRefused) as caught:
        example.build(root, rows=rows)
    assert _errors(caught) == {("aind_unit_qc.metrics.presence_ratio_is_bounded", "aind_unit_qc")}
    assert not (root / "packet.json").exists()


def test_an_extension_the_contract_rejects_is_refused_before_anything_is_written():
    extensions = copy.deepcopy(example.EXTENSIONS)
    column = extensions["aind_unit_qc"]["resources"]["aind_unit_qc.metrics"]["table"]["columns"][2]
    column["type"] = "decimal"
    with pytest.raises(RegistryRejected) as caught:
        example.writer(extensions=extensions)
    assert "aind_unit_qc" in str(caught.value)


# -- arrays --------------------------------------------------------------------------------


def test_a_packet_owned_array_reads_back(packet_root):
    values = np.asarray(open_packet(packet_root).array(example.OWNED)[:])
    assert np.array_equal(values, np.arange(60, dtype="int16").reshape(2, 3, 10))


def test_a_derived_array_carries_its_lineage_and_reads_back(packet_root):
    entry = _entry(packet_root, example.DERIVED)
    assert entry["declaration_id"] == "analysis.array_asset_instances"
    assert entry["derived_from"] == example.LINEAGE
    assert np.all(np.asarray(open_packet(packet_root).array(example.DERIVED)[:]) == 3.0)


def test_a_derived_array_without_lineage_is_refused(tmp_path):
    """Its declaration requires lineage, so the validator refuses the commit without it."""
    with pytest.raises(CommitRefused) as caught:
        example.build(tmp_path / example.SESSION, lineage=False)
    assert ("packet.resource.derived_from_required", "core") in _errors(caught)


def test_an_external_array_is_recorded_and_not_copied(packet_root):
    entry = _entry(packet_root, example.EXTERNAL)
    assert entry["external"] is True and entry["uri"].startswith("s3://")
    assert "digest" not in entry
    assert not (packet_root / "arrays" / "core" / "probe0_lfp.zarr").exists()
    unassessed = [f for f in validate(open_packet(packet_root)).findings if f.check == "external.physical_unassessed"]
    assert [row[0] for f in unassessed for row in f.rows] == [example.EXTERNAL]


def test_an_owned_array_names_each_units_own_contacts(packet_root):
    """The writer's labels, read under the shipped registry: the second unit's last channel is padding."""
    unit, channel, sample = (axis.coordinates for axis in describe(open_packet(packet_root), example.OWNED).axes)
    assert unit.rows["local_unit_label"].to_pylist() == ["17", "42"]
    assert channel.depends_on == 0
    names = channel.rows["electrode_name"].to_pylist()
    assert names == ["elec_000", "elec_001", "elec_003", "elec_001", "elec_003", None]
    assert channel.labels().mask.tolist() == [[False, False, False], [False, False, True]]
    assert sample == NumericAxis(-3.0, 1.0, "{sample}")


def test_a_derived_array_reads_its_labels_from_the_analysis_table(packet_root):
    """Its unit axis is labelled through `analysis.array_labels`, and its rates keep their unit."""
    described = describe(open_packet(packet_root), example.DERIVED)
    unit, time_bin = (axis.coordinates for axis in described.axes)
    assert unit.rows["local_unit_label"].to_pylist() == ["17", "42"]
    assert time_bin == NumericAxis(0.0, 1.0, "1")
    assert described.scaling == Scaling("Hz", 1.0, 0.0)


# -- Part 08 -------------------------------------------------------------------------------


def test_part_08_shows_this_packet(packet_root):
    manifest = json.loads((packet_root / "packet.json").read_text())
    assert example.render(manifest) == example.PART.read_text(), "run integration/example.py"


def _queries():
    section = example.PART.read_text().split('<a id="ew-example-queries"', 1)[1]
    return re.findall(r"```sql\n(.*?)```", section, flags=re.DOTALL)


def test_part_08_joins_core_and_an_extension_on_the_unit(packet_root):
    quality, _ = _queries()
    rows = open_packet(packet_root).sql(quality.rstrip().rstrip(";")).to_pylist()
    # One unit per label ties on the query's ordering, so the rows are compared as a set.
    assert {tuple(row.values()) for row in rows} == {("sua", 1, 0.4), ("mua", 1, 2.7)}


def test_part_08_windows_the_derived_spikes(packet_root):
    _, window = _queries()
    packet = open_packet(packet_root)
    connection = packet.duckdb(for_query=window)
    (count,) = connection.execute(window.rstrip().rstrip(";"), [0, 2**62]).fetchone()
    assert count == packet.table("core.spike_events").num_rows
