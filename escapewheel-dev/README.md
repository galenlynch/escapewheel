# escapewheel-dev

Read-only, typed queries over this repository's current state: the specification's parts, the
core and extension registries, the document JSON Schemas, and packets. One import answers a
question that would otherwise be a throwaway script.

It is a development tool for this repository and is never released. It reads the working tree it
was installed from, depends on the sibling packages by path, and writes nothing into the tree.

```bash
cd escapewheel-dev && uv sync
uv run python -c 'import escapewheel_dev as ew; print(len(ew.rules()))'
```

## What it answers

```python
import escapewheel_dev as ew
from sqlglot import exp

# Nullable identifier and discriminator columns in core.
ew.columns("core", presence="nullable", roles=("identifier", "discriminator"))

# Shipped rules, and how often their SQL uses BETWEEN and IN.
ew.node_counts(ew.rules(), exp.Between, exp.In)

# Which rules read core.units.unit_id, by the validator's own static check.
ew.rules_reading("core.units", "unit_id", ew.rules())

# A section, its MUST sentences, and who cites it.
ew.section(2, "6").title
ew.requirements(2, keyword="MUST")
ew.cited_by(2, "6")

# A stored column a packet's declarations do not name.
packet = ew.open_packet("fixtures/packets/valid")
ew.undeclared_columns(packet)
packet.sql("SELECT count(*) FROM core_units")
ew.validate(packet).passed
```

## API

Everything is exported from `escapewheel_dev`.

| Subject | Names |
|---|---|
| Registries | `registries()`, `registry(id)`, `tables(id)`, `table(resource_id)`, `columns(id, presence=, roles=)`, `references_to(resource_id)`, `rules(id)`; records `Registry`, `Table`, `Column`, `Reference`, `Rule`, each keeping its raw JSON |
| Rule SQL and checks | `parse(rule)`, `node_counts(rules, *node_types)`, `checked(rule)`, `rules_reading(resource_id, column, rules)`, `checks(id, advisory=)`, `Check` |
| Specification parts | `sections()`, `section(part, number)`, `section_by_anchor(anchor)`, `requirements(part, keyword=)`, `cited_by(part, number)`; records `Section` (with `.citations`), `Citation`, `Requirement` |
| Document schemas | `schemas()`, `schema(name)`, `schema_errors(name, document)` |
| Packets | `open_packet`, `Packet`, `validate`, `Report` (the reader's and validator's own), `undeclared_columns(packet)`, `stored_columns(packet, resource_id)`, `corpus_packets()` |

Where it reuses rather than restates:

- Rule parsing and inputs come from the validator's `rule_language.check_rule`, and checks from
  its `generate.generate`, so an answer matches what validation does.
- Section headings and anchors come from `spec/tools/specdoc.py` and `headings.py`.
- A part is given as `"02"` or `2`. A `Section.line` is a position, the first line being 1.
- A bare `§x` in a section is read as a citation of the same part. `R12 §4` and `RFC 3339 §5.6`
  are not citations of a part.
- Requirements are sentences outside code blocks holding a BCP 14 keyword. The sentence split is
  approximate: a full stop before a capital ends one.
- `Packet.sql` names a table by its flattened resource ID, `core_units` for `core.units`.
- `validate` spills DuckDB to a temporary `.validate-*` directory beside the packet and removes it
  afterwards. It changes nothing in the packet.

Out of scope: the registry at another commit, history, revision documents, the ledger, and the
workflow commands. It is a reader, not a tool for changing the tree.

## Why these queries

Before the API was chosen, the ad hoc scripts written while working on this repository were
surveyed. There were 1,474, and each was classified by keyword, so the counts are approximate and
a script can count in several rows.

| What the script asked | Scripts |
|---|---|
| Packets: opened with the reader | 293 |
| Packets: validated | 235 |
| Registries: references between tables | 220 |
| Specification: section text and anchors | 176 |
| Registries: columns by presence or role | 147 |
| Registries: core or an extension document loaded | 140 |
| Specification: MUST and SHOULD clauses | 131 |
| JSON Schemas of the documents | 96 |
| Packets: Parquet tables read directly | 93 |
| Rules: shipped rules and their SQL | 92 |
| Packets: `packet.json` manifest | 80 |
| Packets: DuckDB queries | 66 |
| Packets: the fixture corpus | 25 |
| Rules: SQL parsed with sqlglot | 16 |

Another 273 scripts asked about revision documents or the ledger, and 20 about history through
the version log. Those are out of scope: the current documents are what this library reads.

## Tests

```bash
cd escapewheel-dev && uv run pytest
```

The suite reads the repository and builds the conformance corpus's valid packet in a temporary
directory, so it runs from a checkout of the monorepo and not from the package alone.
