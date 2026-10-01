"""Every check ID the package declares is in one table, and no other module writes one."""

import ast
import inspect
import re
from pathlib import Path

import pytest
from escapewheel_reader import open_packet

import escapewheel_validator
from escapewheel_validator import CheckEntry, Level, Report, Scope, check_table, validate
from escapewheel_validator.check_table import TABLE

SRC = Path(escapewheel_validator.__file__).resolve().parent
#: Copied from the specification's tree, and edited there.
COPIED = {"registry_document.py", "rule_language.py"}
FIXED = [entry for entry in TABLE if not entry.templated]
FAMILIES = [entry for entry in TABLE if entry.templated]
#: The constructors of an entry for an ID a registry or the registry contract declares.
DECLARED_ELSEWHERE = {"rule", "registry_outcome"}
PART = re.compile(r"<(\w+)>")
#: The numbered parts of the specification, which stand beside this package in the monorepo.
PARTS = Path(__file__).resolve().parents[2] / "spec" / "parts"


def _pattern(template: str) -> re.Pattern[str]:
    """Compile a family's template, each part standing for one or more ID characters."""
    return re.compile(r"[a-z0-9_.]+".join(re.escape(text) for text in PART.split(template)[::2]))


def _family_functions():
    return {
        name: getattr(check_table, name)
        for name in check_table.__all__
        if inspect.isfunction(getattr(check_table, name)) and name not in DECLARED_ELSEWHERE
    }


def test_no_two_entries_share_an_id():
    assert len({entry.id for entry in TABLE}) == len(TABLE)


def test_a_fixed_id_is_a_constant_named_after_it():
    for entry in FIXED:
        name = entry.id.upper().replace(".", "_")
        assert getattr(check_table, name) is entry, entry.id
        assert name in check_table.__all__
    constants = {name for name in check_table.__all__ if isinstance(getattr(check_table, name), CheckEntry)}
    assert len(constants) == len(FIXED)


def test_each_family_has_one_function_building_its_ids():
    """Given each part's own name, a family's function writes its template without the brackets."""
    built = {}
    for name, function in _family_functions().items():
        parameters = inspect.signature(function).parameters
        entry = function(*([part] if part == "columns" else part for part in parameters))
        built[entry.id] = (name, entry)
    assert len(built) == len(_family_functions()) == len(FAMILIES)
    for family in FAMILIES:
        name, entry = built[PART.sub(r"\1", family.id)]
        assert (entry.level, entry.scope, entry.named) == (family.level, family.scope, family.named), name


def test_a_family_function_writes_the_id_its_parts_give():
    assert check_table.not_null("core.intervals", "t_start_tick").id == "core.intervals.t_start_tick.not_null"
    assert check_table.primary_key_unique("core.intervals").id == "core.intervals.primary_key_unique"
    assert check_table.reference_resolves("core.intervals", ["session_id", "clock_id"]).id == (
        "core.intervals.session_id_clock_id_resolves"
    )
    assert check_table.names_a_row_of_its_kind("core.spike_units", ["session_id", "unit_id"]).id == (
        "core.spike_units.session_id_unit_id.names_a_row_of_its_kind"
    )
    assert check_table.is_specialised("core.units", "unit_kind", "ext.probe_units").id == (
        "core.units.unit_kind.ext_probe_units_is_specialised"
    )
    assert check_table.paired_value_resolves("core.intervals", "interval_kind", "core.units").id == (
        "core.intervals.interval_kind.core_units_resolves"
    )


def test_an_entry_is_built_at_another_level_without_changing_the_table():
    entry = check_table.PHYSICAL_OUTSIDE_READER_FLOOR
    raised = entry.at(Level.WARNING)
    assert (raised.id, raised.level, raised.scope, raised.named) == (entry.id, Level.WARNING, entry.scope, entry.named)
    assert entry.level is Level.INFO and entry in TABLE
    assert entry.at("warning") == raised


def test_an_id_declared_elsewhere_carries_no_named_flag():
    declared = check_table.rule("core.intervals.stop_after_start", "warning")
    assert (declared.id, declared.level, declared.named) == ("core.intervals.stop_after_start", Level.WARNING, None)
    outcome = check_table.registry_outcome("registry.json.invalid_syntax")
    assert (outcome.level, outcome.scope, outcome.named) == (Level.ERROR, Scope.REGISTRY, None)
    assert all(entry.named is not None for entry in TABLE)


def test_a_report_records_a_finding_under_an_entry():
    report = Report()
    report.add(check_table.OWNED_DIGEST, "a digest differs", [(1, "a")], registry="core")
    report.add(check_table.physical_order("core.intervals").at(Level.INFO), "out of order")
    first, second = report.findings
    assert (first.level, first.check, first.rows, first.registry) == (
        Level.ERROR,
        "owned.digest",
        (("1", "a"),),
        "core",
    )
    assert (second.level, second.check, second.registry) == (Level.INFO, "core.intervals.physical_order", None)
    assert type(first.check) is str


def test_every_finding_of_a_packet_is_under_an_id_the_table_admits(packet_root):
    report = validate(open_packet(packet_root))
    fixed = {entry.id for entry in FIXED}
    families = [_pattern(entry.id) for entry in FAMILIES]
    assert report.findings
    for finding in report.findings:
        assert finding.check in fixed or any(family.fullmatch(finding.check) for family in families), finding.check


def _literal(node: ast.expr) -> bool:
    return isinstance(node, ast.JoinedStr) or (isinstance(node, ast.Constant) and isinstance(node.value, str))


def test_no_module_writes_a_check_id():
    """Outside the table, no string is a fixed ID, ends a family's ID, or stands where an entry does."""
    fixed = {entry.id for entry in FIXED}
    endings = {PART.split(entry.id)[-1] for entry in FAMILIES}
    takes_an_entry = {"add", "Check", "Issue", "Finding"}
    found = set()
    for path in sorted(SRC.rglob("*.py")):
        if path.name in COPIED or path.name == "check_table.py":
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Constant) and node.value in fixed:
                found.add((path.name, node.value))
            if isinstance(node, ast.JoinedStr) and isinstance(last := node.values[-1], ast.Constant):
                found.update((path.name, last.value) for ending in endings if last.value == ending)
            if isinstance(node, ast.Call) and node.args and _literal(node.args[0]):
                called = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", None)
                if called in takes_an_entry:
                    found.add((path.name, ast.unparse(node.args[0])))
    assert not found


def _written(check_id: str) -> re.Pattern[str]:
    """Compile the text that names an ID in a part.

    The ID stands alone: no ID character or full stop joins it to a longer ID on either side, so
    `registry.determined_by.resolves` does not name `<resource_id>.determined_by`. A family is named
    by its template or by one of its IDs, so each part of the template stands for any run of ID
    characters, full stops and angle brackets, whatever the part calls it.
    """
    body = r"[\w<>.]+".join(re.escape(text) for text in PART.split(check_id)[::2])
    return re.compile(r"(?<![\w.<>])" + body + r"(?![\w<]|\.[\w<])")


@pytest.mark.skipif(not PARTS.is_dir(), reason="the specification's tree is not beside this package")
def test_an_entry_is_flagged_named_where_a_numbered_part_writes_its_id():
    parts = [path.read_text() for path in sorted(PARTS.glob("[0-9][0-9]_*.md"))]
    assert parts
    named = {entry.id for entry in TABLE if any(_written(entry.id).search(text) for text in parts)}
    assert {entry.id for entry in TABLE if entry.named} == named
