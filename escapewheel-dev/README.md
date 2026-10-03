# escapewheel-dev

Read-only, typed queries over this repository's current registries, specification parts, document
schemas and packets, as a library and the `escapewheel-dev` command; its queries cover what most
throwaway scripts here asked. It reads the working tree it was installed from, writes nothing, and
is never released. History, revision documents and the ledger are out of scope.

```bash
cd escapewheel-dev && uv sync
uv run escapewheel-dev --help            # one line per subcommand; `<subcommand> --help` says what it prints
uv run escapewheel-dev columns core --presence nullable --role identifier discriminator
uv run escapewheel-dev requirements 2 --keyword MUST
uv run escapewheel-dev rules-reading core.units unit_id
uv run escapewheel-dev section 2 6 --json
uv run escapewheel-dev fields Requirement   # a record's fields, rather than guessing one
```

Text output is one record per line, tab-separated, under a `# Record: field ...` header; `--json`
prints every field. A name that does not exist exits 2. Tests: `uv run pytest` from a monorepo checkout.

## Python API

Everything is exported from `escapewheel_dev`. A record's missing attribute raises an error listing
the ones it has.

| Function | Returns, with its fields |
|---|---|
| `registries()`, `registry(id)` | `Registry`: registry_id, version, path, document, tables, is_extension |
| `tables(id)`, `table(resource_id)` | `Table`: registry, resource_id, content_class, columns, primary_key, references, rules, raw; `.column(name)` |
| `columns(id, presence=, roles=)` | `Column`: registry, table, name, type, presence, role, identity, unit, description, raw |
| `references_to(resource_id)` | `Reference`: registry, table, columns, resource, resource_columns |
| `rules(id)`, `rule(rule_id)`, `rules_reading(resource_id, column, rules)` | `Rule`: registry, table, id, level, message, sql, advisory |
| `checked(rule)` | the validator's `CheckedRule`: sql, resources, inputs, result_names |
| `parse(rule)`, `node_counts(rules, *node_types)` | a sqlglot tree; a `Counter` by node type |
| `checks(id, advisory=)` | the validator's `Check`: id, level, tier, resource, column, message, sql, dependencies, optional_columns, incomplete |
| `sections()`, `section(part, number)`, `section_by_anchor(anchor)`, `cited_by(part, number)` | `Section`: part, number, title, line, text, anchor, aliases, citations (`Citation`: part, section) |
| `requirements(part, keyword=)` | `Requirement`: section, keywords, sentence |
| `schemas()`, `schema(name)`, `schema_errors(name, document)` | schemas by name; `/pointer: message` strings |
| `open_packet`, `validate`, `corpus_packets()`, `undeclared_columns(packet)`, `stored_columns(packet, resource_id)` | the reader's `Packet`, the validator's `Report`; paths or column names |

Where answers come from:

- Rule inputs and checks are the validator's `check_rule` and `generate`, so they match validation.
  Section headings and anchors are `spec/tools/specdoc.py`'s and `headings.py`'s.
- A part is `"02"` or `2`; `Section.line` is a position, the first line being 1. A bare `§x` cites
  the same part; `R12 §4` and `RFC 3339 §5.6` cite no part.
- A requirement is a sentence outside code blocks holding a BCP 14 keyword; a full stop before a
  capital ends a sentence, so the split is approximate.
- `Packet.sql` names a table by its flattened resource ID, `core_units` for `core.units`.
- `validate` spills DuckDB to a temporary `.validate-*` directory beside the packet and removes it.
