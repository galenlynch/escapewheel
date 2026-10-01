"""The vocabularies a report is written in are string enumerations, declared once."""

import ast
import json
from importlib import resources
from pathlib import Path

from escapewheel_reader import open_packet

import escapewheel_validator
from escapewheel_validator import EvaluationStatus, Level, RegistryState, Report, Verdict, validate
from escapewheel_validator.report import VERDICTS

from .copies import COPIED_FILES

SRC = Path(escapewheel_validator.__file__).resolve().parent
#: A phase of a registry result is `passed`, which is a state of the copied checker and no verdict.
PHASE_STATES = {("manifest.py", "passed")}


def test_a_member_is_the_string_a_report_carries():
    assert [*Level] == ["error", "warning", "info"]
    assert [*EvaluationStatus] == ["complete", "incomplete", "invalid", "unsupported"]
    assert json.dumps([Level.ERROR, Verdict.PASSED, EvaluationStatus.COMPLETE, RegistryState.VALID]) == (
        '["error", "passed", "complete", "valid"]'
    )
    assert f"{Level.WARNING:8s}|" == "warning |"


def test_verdicts_are_declared_from_least_to_most_severe():
    """Part 05 §9.5: the packet verdict is the worst in the order `failed`, `incomplete`, `passed`."""
    assert VERDICTS == (Verdict.PASSED, Verdict.INCOMPLETE, Verdict.FAILED) == ("passed", "incomplete", "failed")


def test_registry_states_are_the_ones_the_result_schema_admits():
    schema = json.loads(
        resources.files("escapewheel_validator").joinpath("schemas/registry_result.schema.json").read_text()
    )
    assert set(RegistryState) == set(schema["properties"]["state"]["enum"])


def test_a_report_holds_members_and_renders_strings(packet_root):
    report = validate(open_packet(packet_root))
    assert report.findings and all(type(finding.level) is Level for finding in report.findings)
    assert report.evaluations and all(type(e.status) is EvaluationStatus for e in report.evaluations)
    assert type(report.verdict()) is Verdict and type(report.verdict("core")) is Verdict
    rendered = json.loads(json.dumps(report.to_dict("p")))
    assert rendered["status"] == "passed" and rendered["verdicts"] == {"core": "passed"}
    assert {finding["level"] for finding in rendered["findings"]} <= {"error", "warning", "info"}
    assert {evaluation["status"] for evaluation in rendered["evaluations"]} == {"complete"}


def test_a_status_given_as_its_string_is_stored_as_the_member():
    report = Report()
    report.record_evaluation("core", "complete")
    assert report.evaluations[0].status is EvaluationStatus.COMPLETE


def test_no_module_writes_a_vocabulary_string():
    """A level, verdict, status or state is written as its member outside the module declaring it."""
    words = {str(member) for vocabulary in (Level, Verdict, EvaluationStatus, RegistryState) for member in vocabulary}
    found = set()
    for path in sorted(SRC.rglob("*.py")):
        if path in COPIED_FILES or path.name == "vocabulary.py":
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in words:
                found.add((path.name, node.value))
    assert found == PHASE_STATES
