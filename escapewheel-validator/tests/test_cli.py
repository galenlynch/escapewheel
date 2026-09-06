"""The subcommand this package contributes to `escapewheel`.

These go through `escapewheel_reader`'s `main`, so a pass proves the entry-point wiring, not
just the handler.
"""

import json

import pyarrow as pa
import pyarrow.parquet as pq
from escapewheel_reader.scripts.cli import main


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
