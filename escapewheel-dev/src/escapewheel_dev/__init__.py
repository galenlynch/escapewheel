"""Read-only queries over this repository's current specification, registries, schemas and packets.

A development tool, never released: it reads the working tree it was installed from. Opening and
validating a packet are the reader's and the validator's own functions, re-exported here so one
import serves.
"""

from escapewheel_reader import Packet, open_packet
from escapewheel_validator import Report, validate
from escapewheel_validator.generate import Check

from ._root import ROOT
from .packets import corpus_packets, stored_columns, undeclared_columns
from .registry import (
    Column,
    Reference,
    Registry,
    Rule,
    Table,
    columns,
    references_to,
    registries,
    registry,
    rules,
    table,
    tables,
)
from .schemas import schema, schema_errors, schemas
from .spec import Citation, Requirement, Section, cited_by, requirements, section, section_by_anchor, sections
from .sql import checked, checks, node_counts, parse, rules_reading

__all__ = [
    "ROOT",
    "Check",
    "Citation",
    "Column",
    "Packet",
    "Reference",
    "Registry",
    "Report",
    "Requirement",
    "Rule",
    "Section",
    "Table",
    "checked",
    "checks",
    "cited_by",
    "columns",
    "corpus_packets",
    "node_counts",
    "open_packet",
    "parse",
    "references_to",
    "registries",
    "registry",
    "requirements",
    "rules",
    "rules_reading",
    "schema",
    "schema_errors",
    "schemas",
    "section",
    "section_by_anchor",
    "sections",
    "stored_columns",
    "table",
    "tables",
    "undeclared_columns",
    "validate",
]
