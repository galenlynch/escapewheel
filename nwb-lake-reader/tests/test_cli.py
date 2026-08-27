import pytest

from nwb_lake_reader.scripts.cli import main


def test_ls_lists_resources(packet_root, capsys):
    assert main(["ls", str(packet_root)]) == 0
    out = capsys.readouterr().out
    assert "core.trials" in out and "core.sessions" in out
    assert "sessions: s001" in out


def test_ls_marks_missing_resources(packet_root, capsys):
    (packet_root / "tables" / "core" / "trials.parquet").unlink()
    assert main(["ls", str(packet_root)]) == 0
    assert "missing" in capsys.readouterr().out


def test_sql_runs_a_query(packet_root, capsys):
    assert main(["sql", str(packet_root), "SELECT COUNT(*) AS n FROM core_trials"]) == 0
    assert "2" in capsys.readouterr().out


def test_packet_errors_exit_nonzero(tmp_path, capsys):
    assert main(["ls", str(tmp_path)]) == 1
    assert "error:" in capsys.readouterr().err


def test_missing_subcommand_is_a_usage_error(capsys):
    with pytest.raises(SystemExit):
        main([])
