"""The generated check that two rows of one table carry one owned identifier's name (Part 02 §10.1)."""

import json
import unicodedata

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from escapewheel_reader import open_packet
from packet_fixture import install_registry, read_registry

from escapewheel_validator import validate
from escapewheel_validator.check_table import TABLE

from .builders import add_extension, owned_digest, read_table, rewrite_table, verdicts_of, with_column


def _with_interval_names(packet_root, names):
    intervals = read_table(packet_root, "intervals")
    rewrite_table(packet_root, "intervals", with_column(intervals, "interval_name", pa.array(names)))
    return validate(open_packet(packet_root))


def test_the_check_is_a_named_family_at_error():
    entry = next(e for e in TABLE if e.id == "<declaration_id>.<column>.unique")
    assert entry.named and entry.level == "error"


def test_two_rows_sharing_a_name_under_different_keys_draw_the_check_and_no_key_check(packet_root):
    report = _with_interval_names(packet_root, ["trial", "trial"])
    checks = {f.check for f in report.findings}
    assert "core.intervals.interval_name.unique" in checks
    assert "core.intervals.primary_key_unique" not in checks
    finding = next(f for f in report.findings if f.check == "core.intervals.interval_name.unique")
    assert finding.level == "error" and finding.registry == "core"
    assert len(finding.rows) == 2
    assert not report.passed


@pytest.mark.parametrize(
    "names",
    [
        ["Trial", "trial"],
        [unicodedata.normalize("NFC", "café"), unicodedata.normalize("NFD", "café")],
    ],
    ids=["case", "normalization"],
)
def test_names_differing_only_in_case_or_normalization_are_distinct(packet_root, names):
    """Part 02 §10.1 compares Unicode scalar sequences, as Part 11 §5 does, with no folding."""
    report = _with_interval_names(packet_root, names)
    assert not any(f.check.endswith(".unique") for f in report.findings)


def test_a_null_name_draws_the_non_null_check_and_not_the_name_check(packet_root):
    units = read_table(packet_root, "units")
    rewrite_table(packet_root, "units", with_column(units, "unit_name", pa.array([None, None], type=pa.string())))
    checks = {f.check for f in validate(open_packet(packet_root)).findings}
    assert "core.units.unit_name.not_null" in checks
    assert "core.units.unit_name.unique" not in checks


def _blocks(root, *, presence="required", names=("block_01", "block_02"), sessions=None):
    """Give the packet an extension table owning `block_id` under a key led by its session."""
    root = add_extension(root)
    document = read_registry(root, "task")
    columns = [
        {
            "name": "session_id",
            "type": "int32",
            "presence": "required",
            "role": "identifier",
            "identity": "assigned",
            "description": "Session identity.",
        },
        {
            "name": "block_id",
            "type": "int32",
            "presence": "required",
            "role": "identifier",
            "identity": "assigned",
            "description": "Block identity.",
        },
        {
            "name": "block_name",
            "type": "string",
            "presence": presence,
            "role": "data",
            "vocabulary": "free",
            "description": "What `block_id` stands for.",
        },
        {
            "name": "metadata",
            "type": "json_string",
            "presence": "optional",
            "role": "data",
            "description": (
                "What the source stated about this row that the standard does not model, "
                "carried in the source's own vocabulary and read by no rule."
            ),
        },
    ]
    document["resources"]["task.blocks"] = {
        "content_class": "extension",
        "kind": "table",
        "instances": {"mode": "singleton", "presence": "optional"},
        "requires": [],
        "lineage": "optional",
        "table": {
            "columns": columns,
            "primary_key": ["session_id", "block_id"],
            "amendment_groups": [["session_id", "block_id"]],
            "references": [
                {"columns": ["session_id"], "resource": "core.sessions", "resource_columns": ["session_id"]}
            ],
            "rules": [],
        },
    }
    install_registry(root, document)
    session = read_table(root, "sessions")["session_id"][0].as_py()
    rows = {
        "session_id": pa.array(sessions or [session, session], type=pa.int32()),
        "block_id": pa.array([0, 1], type=pa.int32()),
    }
    if names is not None:
        rows["block_name"] = pa.array(list(names))
    pq.write_table(pa.table(rows), root / "tables" / "task" / "blocks.parquet")
    manifest = json.loads((root / "packet.json").read_text())
    manifest["resources"].append(
        {
            "resource_id": "task.blocks",
            "declaration_id": "task.blocks",
            "uri": "tables/task/blocks.parquet",
            "digest": owned_digest(root, "tables/task/blocks.parquet"),
            "validation_state": "passed",
        }
    )
    (root / "packet.json").write_text(json.dumps(manifest))
    return root


def test_an_extension_name_shared_under_its_own_key_is_the_extensions_finding(packet_root):
    """The check groups on the name alone (Part 02 §10.1); Part 05 §5.4 files it under the extension."""
    report = validate(open_packet(_blocks(packet_root, names=("block_01", "block_01"))))
    finding = next(f for f in report.findings if f.check == "task.blocks.block_name.unique")
    assert finding.registry == "task" and finding.level == "error"
    assert verdicts_of(report, "core", "task") == ("failed", "passed", "failed")


def test_a_name_shared_by_rows_of_two_sessions_is_reported(packet_root):
    """A name identifies its row within the packet, so the session in the key does not separate two."""
    sessions = read_table(packet_root, "sessions")
    second = sessions.slice(0, 1)
    second = with_column(second, "session_id", pa.array([second["session_id"][0].as_py() + 1], type=pa.int32()))
    second = with_column(second, "session_name", pa.array(["second-session"]))
    rewrite_table(packet_root, "sessions", pa.concat_tables([sessions, second]))
    first = sessions["session_id"][0].as_py()
    report = validate(open_packet(_blocks(packet_root, names=("block_01", "block_01"), sessions=[first, first + 1])))
    finding = next(f for f in report.findings if f.check == "task.blocks.block_name.unique")
    assert finding.registry == "task" and len(finding.rows) == 2
