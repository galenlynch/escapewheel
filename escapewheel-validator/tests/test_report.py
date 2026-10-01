"""A report's findings, its evaluations and the verdicts they decide, and the JSON it renders."""

import json

from escapewheel_reader import open_packet

from escapewheel_validator import EvaluationStatus, Report, check_table, validate
from escapewheel_validator.report import ROW_CAP

from .builders import add_extension


def test_completing_an_evaluation_records_it_complete():
    """Part 05 §9.5: a registry passes only once its evaluation is recorded complete."""
    report = Report(bound=("core",))
    assert report.verdict("core") == "incomplete"
    report.complete("core")
    assert [(e.registry, e.status) for e in report.evaluations] == [("core", "complete")]


def test_completing_leaves_an_evaluation_that_ended_otherwise():
    report = Report(bound=("core", "task"))
    report.record_evaluation("core", EvaluationStatus.INCOMPLETE, rule="core.rule", detail="unreadable")
    report.complete("core")
    report.complete("task")
    assert [(e.registry, e.status) for e in report.evaluations] == [("core", "incomplete"), ("task", "complete")]


def test_a_finding_keeps_the_first_rows_of_any_iterable():
    report = Report()
    report.add(check_table.EXTERNAL_MEMBERS, "members differ", ((key,) for key in range(ROW_CAP + 3)))
    assert report.findings[0].rows == tuple((str(key),) for key in range(ROW_CAP))


def test_a_finding_names_its_resource_column_and_counts():
    report = Report()
    report.add(
        check_table.outside_reserved_set("core.units", "unit_kind"),
        "2 value(s) outside the reserved set",
        registry="core",
        resource="core.units",
        column="unit_kind",
        counts={"values": 2},
    )
    report.add(check_table.PACKET_RESOURCE_LINEAGE_CYCLE, "lineage cycle reaches a")
    named, bare = report.findings
    assert (named.resource, named.column, named.counts) == ("core.units", "unit_kind", {"values": 2})
    assert (bare.resource, bare.column, bare.counts) == (None, None, {})
    assert len({named, bare}) == 2


def test_a_finding_about_a_resource_belongs_to_the_registry_declaring_it():
    report = Report(bound=("core", "task"))
    report.declared_by = {"task.trials": "task"}
    report.declarations = {"task.trials": "task.trials", "raw_ap": "core.raw_recording"}
    report.add_about("task.trials", check_table.RESOURCE_MISSING, "task.trials: no file", column="outcome")
    report.add_about("raw_ap", check_table.RESOURCE_MISSING, "raw_ap: no file")
    first, second = report.findings
    assert (first.registry, first.resource, first.column) == ("task", "task.trials", "outcome")
    assert (second.registry, second.resource) == (None, "raw_ap")


def test_a_rendered_finding_gains_members_and_keeps_the_others():
    report = Report()
    report.add_about("core.units", check_table.OWNED_DIGEST, "a digest differs", [(1,)], counts={"checked": 1})
    (rendered,) = report.to_dict("p")["findings"]
    assert rendered == {
        "level": "error",
        "check": "owned.digest",
        "message": "a digest differs",
        "rows": [["1"]],
        "registry": None,
        "resource": "core.units",
        "column": None,
        "counts": {"checked": 1},
    }


def test_report_renders_as_json(packet_root):
    report = validate(open_packet(packet_root))
    rendered = report.to_dict("session_001")
    assert rendered["status"] == "passed"
    assert rendered["summary"] == {"errors": 0, "warnings": 0}
    assert rendered["registries"][0]["subject"] == "core"
    assert rendered["registries"][0]["result"]["state"] == "valid"


def test_report_records_whether_advisories_ran(packet_root):
    """An empty advisory result is ambiguous unless the report says (R26 §5)."""
    assert validate(open_packet(packet_root)).to_dict("p")["advisory"] is False
    assert validate(open_packet(packet_root), advisory=True).to_dict("p")["advisory"] is True


def test_the_json_report_states_every_verdict_and_subject(packet_root):
    """Part 05 §9.5: a report states the packet's verdict, each registry's, and each finding's subject."""
    root = add_extension(packet_root, mutate=lambda r: r["choice"].__setitem__(0, "sideways"))
    document = validate(open_packet(root)).to_dict("p")
    assert document["status"] == "failed"
    assert document["verdicts"] == {"core": "passed", "task": "failed"}
    errors = [f for f in document["findings"] if f["level"] == "error"]
    assert [(f["check"], f["registry"]) for f in errors] == [("task.trials.choice.in_vocabulary", "task")]
    assert json.loads(json.dumps(document)) == document
