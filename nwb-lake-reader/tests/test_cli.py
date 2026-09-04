import pytest

from nwb_lake_reader.scripts.cli import main


def test_ls_lists_resources(packet_root, capsys):
    assert main(["ls", str(packet_root)]) == 0
    out = capsys.readouterr().out
    assert "core.intervals" in out and "core.sessions" in out
    assert "sessions: s001" in out


def test_ls_marks_missing_resources(packet_root, capsys):
    (packet_root / "tables" / "core" / "intervals.parquet").unlink()
    assert main(["ls", str(packet_root)]) == 0
    assert "missing" in capsys.readouterr().out


def test_sql_runs_a_query(packet_root, capsys):
    assert main(["sql", str(packet_root), "SELECT COUNT(*) AS n FROM core_intervals"]) == 0
    assert "2" in capsys.readouterr().out


def test_packet_errors_exit_nonzero(tmp_path, capsys):
    assert main(["ls", str(tmp_path)]) == 1
    assert "error:" in capsys.readouterr().err


def test_missing_subcommand_is_a_usage_error(capsys):
    with pytest.raises(SystemExit):
        main([])


def test_absent_subcommand_names_its_package(packet_root, capsys):
    """`nwb-lake validate` without the validator installed says what to install."""
    assert main(["validate", str(packet_root)]) == 2
    assert "nwb-lake-validator" in capsys.readouterr().err


def test_installed_packages_extend_the_command(monkeypatch, capsys):
    """A package registering under `nwb_lake.commands` gains a real subcommand."""

    def register(subcommands):
        parser = subcommands.add_parser("validate", help="validate a packet")
        parser.add_argument("packet")
        parser.set_defaults(func=lambda args: print("validated") or 0)

    entry = type("Entry", (), {"name": "validate", "load": lambda self: register})()
    monkeypatch.setattr("nwb_lake_reader.scripts.cli.entry_points", lambda group: [entry])

    assert main(["validate", "somewhere"]) == 0
    assert "validated" in capsys.readouterr().out
