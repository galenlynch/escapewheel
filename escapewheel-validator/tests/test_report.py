"""A report's evaluations and the verdicts they decide."""

from escapewheel_validator import EvaluationStatus, Report, check_table
from escapewheel_validator.report import ROW_CAP


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
