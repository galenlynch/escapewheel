"""The subcommand this package contributes to `escapewheel`.

These go through `escapewheel_reader`'s `main`, so a pass proves the entry-point wiring, not
just the handler.
"""

import json

import pyarrow as pa
import pyarrow.parquet as pq
from escapewheel_reader.scripts.cli import main

from .test_validation import _extension


def test_validate_reports_a_conforming_packet(packet_root, capsys):
    assert main(["validate", str(packet_root)]) == 0
    assert "passed" in capsys.readouterr().out


def test_validate_exits_nonzero_on_a_finding(packet_root, capsys):
    trials = pq.read_table(packet_root / "tables" / "core" / "trials.parquet")
    pq.write_table(
        pa.concat_tables([trials, trials.slice(0, 1)]),
        packet_root / "tables" / "core" / "trials.parquet",
        compression="zstd",
    )
    assert main(["validate", str(packet_root)]) == 1
    assert "primary_key_unique" in capsys.readouterr().out


def test_validate_writes_a_json_report(packet_root, tmp_path, capsys):
    report = tmp_path / "report.json"
    assert main(["validate", str(packet_root), "--report", str(report)]) == 0
    assert json.loads(report.read_text())["status"] == "passed"


def test_validate_reports_a_manifest_the_reader_refuses(packet_root, capsys):
    """Part 04 §10: a repeated resource ID stops a reader, and still gets its finding."""
    path = packet_root / "packet.json"
    manifest = json.loads(path.read_text())
    manifest["resources"].append(manifest["resources"][0])
    path.write_text(json.dumps(manifest))
    assert main(["validate", str(packet_root)]) == 1
    assert "packet.resource.id_unique" in capsys.readouterr().out


def test_validate_exits_on_the_packet_verdict(packet_root, capsys):
    """Part 05 §9.5: a failing extension fails the packet even where core passes."""
    root = _extension(packet_root, mutate=lambda rows: rows["choice"].__setitem__(0, "sideways"))
    assert main(["validate", str(root)]) == 1
    out = capsys.readouterr().out
    assert "[task] task.trials.choice.in_vocabulary" in out
    assert "core: passed" in out and "task: failed" in out
