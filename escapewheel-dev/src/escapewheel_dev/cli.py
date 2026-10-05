"""The ``escapewheel-dev`` command: the library's queries as subcommands, printing text or JSON.

Text output is one record per line, tab-separated, under a ``# Record: field ...`` header naming
the record type and the fields shown, so ``grep -v '^#'`` leaves only rows. ``--json`` prints
every field of each record, including those the text omits.
"""

import dataclasses
import inspect
import json
import os
import re
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Union

import tyro
from escapewheel_reader import open_packet
from escapewheel_validator import validate
from escapewheel_validator.generate import Check
from escapewheel_validator.report import Finding
from escapewheel_validator.rule_language import CheckedRule
from sqlglot import exp
from tyro.conf import Positional

from ._record import field_names
from ._root import ROOT
from .packets import corpus_packets, stored_columns, undeclared_columns
from .registry import (
    Column,
    Reference,
    Registry,
    Rule,
    Table,
    add_extensions,
    columns,
    references_to,
    registries,
    rule,
    rules,
    table,
    tables,
)
from .schemas import schema, schema_errors, schemas
from .spec import Citation, Requirement, Section, cited_by, requirements, section, section_by_anchor, sections
from .sql import checked, checks, node_counts, rules_reading

Json = Annotated[bool, tyro.conf.arg(name="json", help="Print JSON holding every field of each record.")]


def _named(metavar: str) -> Any:
    """Name a positional argument in usage lines, which otherwise show only its type."""
    return tyro.conf.arg(metavar=metavar)


#: Every record type a query returns, for `fields`.
RECORDS: Mapping[str, type] = {
    record.__name__: record
    for record in (
        Registry,
        Table,
        Column,
        Reference,
        Rule,
        CheckedRule,
        Check,
        Section,
        Citation,
        Requirement,
        Finding,
    )
}

COLUMN = ("registry", "table", "name", "type", "presence", "role", "identity", "unit", "description")
REFERENCE = ("registry", "table", "columns", "resource", "resource_columns")
RULE = ("registry", "table", "id", "level", "advisory", "message")
SECTION = ("part", "number", "title", "line", "anchor")


def _plain(value: Any) -> Any:
    """Convert a record, and what it holds, to JSON values; fields declared ``repr=False`` are left out."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        hidden = {field.name for field in dataclasses.fields(value) if not field.repr}
        return {name: _plain(getattr(value, name)) for name in field_names(type(value)) if name not in hidden}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value.relative_to(ROOT)) if value.is_relative_to(ROOT) else str(value)
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted(_plain(item) for item in value)
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _cell(value: Any) -> str:
    """Render one value on one line: missing as ``-``, a sequence comma-separated, a record's values colon-separated."""
    value = _plain(value)
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ",".join(_cell(item) for item in value)
    if isinstance(value, dict):
        return ":".join(_cell(item) for item in value.values())
    return " ".join(str(value).split())


def _get(record: Any, path: str) -> Any:
    for name in path.split("."):
        record = getattr(record, name)
    return record


def _print_json(value: Any) -> None:
    print(json.dumps(_plain(value), default=str, ensure_ascii=False))


def _emit(kind: str, records: Iterable[Any], shown: Sequence[str], as_json: bool) -> None:
    """Print records as JSON, or one tab-separated line each under a header naming `kind` and `shown`."""
    if as_json:
        _print_json(list(records))
        return
    print(f"# {kind}: " + "\t".join(shown))
    for record in records:
        print("\t".join(_cell(_get(record, path)) for path in shown))


def _block(record: Any, shown: Sequence[str]) -> None:
    """Print one record as ``field<TAB>value`` lines."""
    for name in shown:
        print(f"{name}\t{_cell(getattr(record, name))}")


# Registries ----------------------------------------------------------------------------------------


def _registries(as_json: Json = False) -> None:
    """List core and every extension registry in the working tree.

    Prints one Registry per line: registry_id, version, is_extension, path.
    """
    _emit("Registry", registries().values(), ("registry_id", "version", "is_extension", "path"), as_json)


def _tables(
    registry_id: Annotated[str | None, Positional, _named("[REGISTRY_ID]")] = None, as_json: Json = False
) -> None:
    """List declared tables.

    Prints one Table per line: registry, resource_id, content_class, primary_key. `--json` adds
    each table's columns, references and rules.

    Parameters
    ----------
    registry_id
        Only this registry's tables, such as `core`.
    """
    _emit("Table", tables(registry_id), ("registry", "resource_id", "content_class", "primary_key"), as_json)


def _table(resource_id: Annotated[str, Positional, _named("RESOURCE_ID")], as_json: Json = False) -> None:
    """Show one table's declaration: its fields, then its columns, references and rules.

    Prints `field<TAB>value` lines for resource_id, registry, content_class, primary_key, then the
    table's Column, Reference and Rule lines, each under its own header.

    Parameters
    ----------
    resource_id
        A table resource ID such as `core.units`, in whichever registry declares it.
    """
    declared = table(resource_id)
    if as_json:
        _print_json(declared)
        return
    _block(declared, ("resource_id", "registry", "content_class", "primary_key"))
    _emit("Column", declared.columns, COLUMN[2:], as_json)
    _emit("Reference", declared.references, REFERENCE[2:], as_json)
    _emit("Rule", declared.rules, RULE[2:], as_json)


def _columns(
    registry_id: Annotated[str | None, Positional, _named("[REGISTRY_ID]")] = None,
    presence: Annotated[str | None, _named("PRESENCE")] = None,
    role: Annotated[tuple[str, ...], _named("ROLE")] = (),
    as_json: Json = False,
) -> None:
    """List declared columns, filtered by registry, presence and role.

    Prints one Column per line: registry, table, name, type, presence, role, identity, unit,
    description.

    Parameters
    ----------
    registry_id
        Only this registry's columns.
    presence
        Only columns of this presence: required, nullable or optional.
    role
        Only columns with one of these roles, such as identifier or discriminator.
    """
    found = columns(registry_id, presence=presence, roles=role or None)
    _emit("Column", found, COLUMN, as_json)


def _references(resource_id: Annotated[str, Positional, _named("RESOURCE_ID")], as_json: Json = False) -> None:
    """List the foreign keys, in every registry, that resolve into one table.

    Prints one Reference per line: registry, table, columns, resource, resource_columns. The
    referencing side is `table.columns`.

    Parameters
    ----------
    resource_id
        The referenced table, such as `core.sessions`.
    """
    _emit("Reference", references_to(resource_id), REFERENCE, as_json)


# Rules and checks ----------------------------------------------------------------------------------


def _rules(
    registry_id: Annotated[str | None, Positional, _named("[REGISTRY_ID]")] = None, as_json: Json = False
) -> None:
    """List shipped Tier 2 rules.

    Prints one Rule per line: registry, table, id, level, advisory, message. `--json` adds sql;
    `rule ID` shows one rule's query and what it reads.

    Parameters
    ----------
    registry_id
        Only this registry's rules.
    """
    _emit("Rule", rules(registry_id), RULE, as_json)


def _rule(rule_id: Annotated[str, Positional, _named("RULE_ID")], as_json: Json = False) -> None:
    """Show one shipped rule, the columns its query reads by the validator's static check, and its SQL.

    Prints `field<TAB>value` lines for registry, table, id, level, advisory, message and reads (the
    `resource.column` pairs read), then a blank line and the SQL. `--json` prints the Rule's fields
    and `checked`, the validator's CheckedRule.

    Parameters
    ----------
    rule_id
        The rule's ID, such as one `rules` lists.
    """
    found = rule(rule_id)
    reads = checked(found)
    if as_json:
        _print_json({**_plain(found), "checked": _plain(reads)})
        return
    _block(found, RULE)
    print("reads\t" + ",".join(sorted(f"{resource}.{column}" for resource, column in reads.inputs)))
    print(f"\n{found.sql}")


def _rules_reading(
    resource_id: Annotated[str, Positional, _named("RESOURCE_ID")],
    column: Annotated[str, Positional, _named("COLUMN")],
    registry_id: Annotated[str | None, _named("REGISTRY_ID")] = None,
    as_json: Json = False,
) -> None:
    """List the shipped rules whose query reads one column, by the validator's static check.

    Prints one Rule per line: registry, table, id, level, advisory, message.

    Parameters
    ----------
    resource_id
        The table read, such as `core.units`.
    column
        The column of that table read.
    registry_id
        Only this registry's rules.
    """
    _emit("Rule", rules_reading(resource_id, column, rules(registry_id)), RULE, as_json)


def _node_counts(
    nodes: Annotated[tuple[str, ...], Positional, _named("NODES")],
    registry_id: Annotated[str | None, _named("REGISTRY_ID")] = None,
    as_json: Json = False,
) -> None:
    """Count sqlglot node types across shipped rules' parsed queries.

    Prints one `node<TAB>count` line per node type; `--json` prints an object of counts.

    Parameters
    ----------
    nodes
        sqlglot expression class names, such as Between, In or Window.
    registry_id
        Only this registry's rules.
    """
    types = []
    for name in nodes:
        node = getattr(exp, name, None)
        if not (isinstance(node, type) and issubclass(node, exp.Expr)):
            raise KeyError(f"sqlglot has no expression {name!r}")
        types.append(node)
    counts = node_counts(rules(registry_id), *types)
    if as_json:
        _print_json({node.__name__: counts[node] for node in types})
        return
    print("# node\tcount")
    for node in types:
        print(f"{node.__name__}\t{counts[node]}")


def _checks(
    registry_id: Annotated[str, Positional, _named("[REGISTRY_ID]")] = "core",
    advisory: bool = False,
    as_json: Json = False,
) -> None:
    """List the checks the validator generates from one registry: Tier 1 derived, Tier 2 shipped.

    Prints one Check per line: id, tier, level, resource, column, incomplete, message. `--json`
    adds sql, dependencies and optional_columns.

    Parameters
    ----------
    registry_id
        `core`, or an extension, whose checks are generated against core.
    advisory
        Include advisory rules.
    """
    shown = ("id", "tier", "level", "resource", "column", "incomplete", "message")
    _emit("Check", checks(registry_id, advisory=advisory), shown, as_json)


# Specification --------------------------------------------------------------------------------------


def _sections(part: Annotated[str | None, Positional, _named("[PART]")] = None, as_json: Json = False) -> None:
    """List numbered sections of the specification's parts, in document order.

    Prints one Section per line: part, number, title, line, anchor. `line` is a position, the
    first line of the part's file being 1. `section` shows one section's text.

    Parameters
    ----------
    part
        Only this part, as `02` or `2`.
    """
    key = None if part is None else f"{int(part):02d}"
    _emit("Section", [found for found in sections() if key in (None, found.part)], SECTION, as_json)


def _show_section(found: Section, as_json: bool) -> None:
    if as_json:
        _print_json({**_plain(found), "text": found.text})
        return
    _block(found, (*SECTION, "aliases", "citations"))
    print(f"\n{found.text}")


def _section(
    part: Annotated[str, Positional, _named("PART")],
    number: Annotated[str, Positional, _named("NUMBER")],
    as_json: Json = False,
) -> None:
    """Show one section: its fields, the sections it cites, then its text.

    Prints `field<TAB>value` lines for part, number, title, line, anchor, aliases and citations
    (`part:number` each), then a blank line and the text. `--json` adds text to the Section's fields.

    Parameters
    ----------
    part
        The part, as `02` or `2`.
    number
        The section number without the section sign, such as `6` or `10.1`.
    """
    _show_section(section(part, number), as_json)


def _anchor(anchor: Annotated[str, Positional, _named("ANCHOR")], as_json: Json = False) -> None:
    """Show the section a canonical or alias anchor names, as `section` does.

    Parameters
    ----------
    anchor
        The anchor without its `#`.
    """
    _show_section(section_by_anchor(anchor), as_json)


def _requirements(
    part: Annotated[str | None, Positional, _named("[PART]")] = None,
    keyword: Annotated[str | None, _named("KEYWORD")] = None,
    as_json: Json = False,
) -> None:
    """List BCP 14 sentences outside code blocks.

    Prints one Requirement per line: section.part, section.number, keywords, sentence. The split
    into sentences is approximate: a full stop before a capital ends one.

    Parameters
    ----------
    part
        Only this part, as `02` or `2`.
    keyword
        Only sentences carrying this keyword. `MUST NOT` is one keyword, distinct from `MUST`.
    """
    found = requirements(part, keyword=keyword)
    _emit("Requirement", found, ("section.part", "section.number", "keywords", "sentence"), as_json)


def _cited_by(
    part: Annotated[str, Positional, _named("PART")],
    number: Annotated[str, Positional, _named("NUMBER")],
    as_json: Json = False,
) -> None:
    """List the sections, in any part, citing exactly one section.

    Prints one Section per line: part, number, title, line, anchor.

    Parameters
    ----------
    part
        The cited part, as `02` or `2`.
    number
        The cited section number. A citation of a subsection does not count as one of its parent.
    """
    _emit("Section", cited_by(part, number), SECTION, as_json)


# Document schemas -----------------------------------------------------------------------------------


def _schemas(as_json: Json = False) -> None:
    """List the document JSON Schemas under spec/artifacts/.

    Prints one line per schema: name, title, $id.
    """
    found = [
        {"name": name, "title": document.get("title"), "$id": document.get("$id")}
        for name, document in schemas().items()
    ]
    if as_json:
        _print_json(found)
        return
    print("# name\ttitle\t$id")
    for entry in found:
        print("\t".join(_cell(value) for value in entry.values()))


def _schema(name: Annotated[str, Positional, _named("NAME")]) -> None:
    """Print one document schema as JSON.

    Parameters
    ----------
    name
        The schema's name, as `schemas` lists it, such as `manifest`.
    """
    _print_json(schema(name))


def _schema_errors(
    name: Annotated[str, Positional, _named("NAME")],
    document: Annotated[Path, Positional, _named("DOCUMENT")],
    as_json: Json = False,
) -> int:
    """Check a JSON document against one schema, formats included; exits 1 where it fails.

    Prints one `/pointer: message` line per error, nothing where the document passes.

    Parameters
    ----------
    name
        The schema's name, such as `manifest`.
    document
        A JSON file.
    """
    errors = schema_errors(name, json.loads(document.read_text()))
    if as_json:
        _print_json(errors)
    else:
        for error in errors:
            print(error)
    return 1 if errors else 0


# Packets ---------------------------------------------------------------------------------------------


def _corpus(as_json: Json = False) -> None:
    """List the conformance corpus's built packets; none until `fixtures/build.py` has run.

    Prints one line per packet: name, path.
    """
    found = [{"name": name, "path": path} for name, path in corpus_packets().items()]
    if as_json:
        _print_json(found)
        return
    print("# name\tpath")
    for entry in found:
        print(f"{entry['name']}\t{_cell(entry['path'])}")


def _validate(
    packet: Annotated[Path, Positional, _named("PACKET")], advisory: bool = False, as_json: Json = False
) -> int:
    """Validate a packet with the validator; exits 0 on a passing verdict and 1 otherwise.

    Prints one Finding per line: level, registry, check, resource, column, message, then a
    `# verdict` line. `--json` prints the validator's Part 05 report.

    Parameters
    ----------
    packet
        The packet's root directory.
    advisory
        Also run advisory rules, which never change the verdict.
    """
    opened = open_packet(packet)
    report = validate(opened, advisory=advisory)
    if as_json:
        _print_json(report.to_dict(opened.manifest.packet_id))
    else:
        _emit("Finding", report.findings, ("level", "registry", "check", "resource", "column", "message"), as_json)
        print(f"# verdict: {_cell(report.verdict())}, {report.errors} error(s), {report.warnings} warning(s)")
    return 0 if report.passed else 1


def _undeclared_columns(packet: Annotated[Path, Positional, _named("PACKET")], as_json: Json = False) -> None:
    """List, per table resource, the stored columns its bound declaration does not name.

    Prints one `resource_id<TAB>columns` line per table holding any; `--json` prints an object.

    Parameters
    ----------
    packet
        The packet's root directory.
    """
    found = undeclared_columns(open_packet(packet))
    if as_json:
        _print_json(found)
        return
    print("# resource_id\tcolumns")
    for resource_id, names in found.items():
        print(f"{resource_id}\t{_cell(names)}")


def _stored_columns(
    packet: Annotated[Path, Positional, _named("PACKET")],
    resource_id: Annotated[str, Positional, _named("RESOURCE_ID")],
    as_json: Json = False,
) -> None:
    """List the column names one table resource stores, read from its schema without reading rows.

    Prints one name per line.

    Parameters
    ----------
    packet
        The packet's root directory.
    resource_id
        A table resource the packet holds, such as `core.units`.
    """
    found = stored_columns(open_packet(packet), resource_id)
    if as_json:
        _print_json(found)
    else:
        print("\n".join(found))


def _sql(
    packet: Annotated[Path, Positional, _named("PACKET")],
    query: Annotated[str, Positional, _named("QUERY")],
    as_json: Json = False,
) -> None:
    """Run a DuckDB query over a packet's tables with the reader's `Packet.sql`.

    A table is named by its flattened resource ID: `core_units` for `core.units`. Prints a
    `# column ...` header and one row per line; `--json` prints an array of row objects.

    Parameters
    ----------
    packet
        The packet's root directory.
    query
        The query.
    """
    result = open_packet(packet).sql(query)
    if as_json:
        _print_json(result.to_pylist())
        return
    print("# " + "\t".join(result.column_names))
    for row in result.to_pylist():
        print("\t".join(_cell(value) for value in row.values()))


# Records --------------------------------------------------------------------------------------------


def _annotation(record: type, name: str) -> str:
    member = inspect.getattr_static(record, name, None)
    if isinstance(member, property) and member.fget is not None:
        annotation = inspect.signature(member.fget).return_annotation
    else:
        annotation = {field.name: field.type for field in dataclasses.fields(record)}[name]
    text = annotation if isinstance(annotation, str) else inspect.formatannotation(annotation)
    return re.sub(r"\b(?:\w+\.)+(\w+)", r"\1", text)


def _fields(record: Annotated[str | None, Positional, _named("[RECORD]")] = None) -> None:
    """List the fields of the records queries return, so an attribute need not be guessed.

    Prints one `record<TAB>field<TAB>type` line per field or property, in declaration order.

    Parameters
    ----------
    record
        Only this record type, such as `Requirement`.
    """
    chosen = RECORDS if record is None else {record: RECORDS[record]} if record in RECORDS else None
    if chosen is None:
        raise KeyError(f"no record {record!r}; records are {', '.join(RECORDS)}")
    print("# record\tfield\ttype")
    for name, kind in chosen.items():
        for field in field_names(kind):
            print(f"{name}\t{field}\t{_annotation(kind, field)}")


COMMANDS: Mapping[str, Callable[..., int | None]] = {
    "registries": _registries,
    "tables": _tables,
    "table": _table,
    "columns": _columns,
    "references": _references,
    "rules": _rules,
    "rule": _rule,
    "rules-reading": _rules_reading,
    "node-counts": _node_counts,
    "checks": _checks,
    "sections": _sections,
    "section": _section,
    "anchor": _anchor,
    "requirements": _requirements,
    "cited-by": _cited_by,
    "schemas": _schemas,
    "schema": _schema,
    "schema-errors": _schema_errors,
    "corpus": _corpus,
    "validate": _validate,
    "undeclared-columns": _undeclared_columns,
    "stored-columns": _stored_columns,
    "sql": _sql,
    "fields": _fields,
}

DESCRIPTION = (
    "Read-only queries over this repository's current registries, specification parts, document "
    "schemas and packets. Text output is tab-separated under a '# Record: field ...' header; --json "
    "prints every field. 'fields' lists each record's fields. '--extension PATH' before the "
    "subcommand, repeatable, also reads an extension document or a directory of them from outside "
    "this checkout, as ESCAPEWHEEL_DEV_EXTENSIONS does."
)

#: The option naming an extension outside the checkout, given before the subcommand.
EXTENSION_OPTION = "--extension"


def _extensions(given: list[str]) -> tuple[list[str], list[str]]:
    """Split the leading `--extension PATH` options from the subcommand and its arguments.

    Parsed here rather than by tyro, which offers no option shared by every subcommand of a union.
    """
    named = []
    while given and given[0].split("=", 1)[0] == EXTENSION_OPTION:
        option, *value = given.pop(0).split("=", 1)
        if not value:
            if not given:
                raise KeyError(f"{option} needs a path")
            value = [given.pop(0)]
        named.append(value[0])
    return named, given


def main(args: Sequence[str] | None = None) -> int:
    """Run one subcommand and return the exit status: 2 where a name it was given does not exist.

    Parameters
    ----------
    args
        The arguments after the program name, or None to read ``sys.argv``.
    """
    # tyro gives a subcommand one description for both the list and its own help. The list shows each
    # docstring's first line; the chosen subcommand keeps its whole docstring, so its help says what it prints.
    try:
        named, given = _extensions(list(sys.argv[1:] if args is None else args))
        add_extensions(*named)
    except (KeyError, FileNotFoundError) as error:
        print(f"error: {error.args[0] if error.args else error}", file=sys.stderr)
        return 2
    chosen = given[0] if given else None
    choices: Any = Union[  # noqa: UP007  # a union built from a runtime tuple
        tuple(
            Annotated[
                Any,
                tyro.conf.subcommand(
                    name,
                    constructor=command,
                    description=None if name == chosen else (command.__doc__ or "").split("\n")[0],
                ),
            ]
            for name, command in COMMANDS.items()
        )
    ]
    try:
        status = tyro.cli(
            choices,
            prog="escapewheel-dev",
            description=DESCRIPTION,
            args=given,
            config=(tyro.conf.FlagCreatePairsOff,),
        )
    except KeyError as error:
        print(f"error: {error.args[0] if error.args else error}", file=sys.stderr)
        return 2
    return int(status or 0)


def run() -> None:
    """Entry point of the ``escapewheel-dev`` script."""
    try:
        status = main()
        sys.stdout.flush()
    except BrokenPipeError:
        # A reader such as `head` closed the pipe; stop quietly rather than report it at exit.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        status = 0
    sys.exit(status)
