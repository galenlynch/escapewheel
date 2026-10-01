"""The subcommand this package contributes to `escapewheel`.

These go through `escapewheel_reader`'s `main`, so a pass proves the entry-point wiring, not
just the handler.
"""

import json

import pyarrow as pa
import pyarrow.parquet as pq
from escapewheel_reader.scripts.cli import main

from escapewheel_validator import Report
from escapewheel_validator.errors import StoreUnreachable
from escapewheel_validator.scripts import cli

from .test_replaces import _item, _replacing
from .test_validation import _extension


def test_validate_reports_a_conforming_packet(packet_root, capsys):
    assert main(["validate", str(packet_root)]) == 0
    assert "passed" in capsys.readouterr().out


def test_validate_exits_nonzero_on_a_finding(packet_root, capsys):
    intervals = pq.read_table(packet_root / "tables" / "core" / "intervals.parquet")
    pq.write_table(
        pa.concat_tables([intervals, intervals.slice(0, 1)]),
        packet_root / "tables" / "core" / "intervals.parquet",
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


def test_a_checksum_flag_asks_for_the_external_level_under_it(packet_root, monkeypatch, capsys):
    asked = []
    monkeypatch.setattr(cli, "validate", lambda packet, **options: asked.append(options["verification"]) or Report())
    for flags in ([], ["--checksums"], ["--store-digests"], ["--external"], ["--checksums", "--no-store-checksums"]):
        main(["validate", str(packet_root), *flags])
    assert [modes.resolves_external for modes in asked] == [False, True, True, True, True]
    assert [modes.checksums for modes in asked] == [False, True, False, False, True]
    assert [modes.store_checksums for modes in asked] == [True, True, True, True, False]


def test_validate_prints_a_refusal_in_place_of_a_traceback(packet_root, monkeypatch, capsys):
    def refuse(*args, **kwargs):
        raise StoreUnreachable("s3://bucket/arr: no credentials", uri="s3://bucket/arr")

    monkeypatch.setattr(cli, "validate", refuse)
    assert main(["validate", str(packet_root)]) == 1
    assert capsys.readouterr().err == "error: s3://bucket/arr: no credentials\n"


def test_validate_treats_an_unreadable_replaced_manifest_as_a_bad_argument(packet_root, tmp_path, capsys):
    """An absent path and an unparsable manifest are one refusal, so they exit alike."""
    _replacing(packet_root, "1.0.0", _item())
    unparsable = tmp_path / "unparsable"
    unparsable.mkdir()
    (unparsable / "packet.json").write_text("not json")
    for supplied in (tmp_path / "absent", unparsable):
        assert main(["validate", str(packet_root), "--replaced", str(supplied)]) == 2
        streams = capsys.readouterr()
        assert "no published manifest" in streams.out + streams.err
