# R17 — Extension Registries

| | |
|---|---|
| **Status** | **Accepted** 2026-08-27 |
| **Amends** | `09_metadata_minimalism_and_extensions.md`, R2 |
| **Depends on** | R2 (registry format) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

`09` §5 requires an extension to declare its `extension_id`, version, namespace, **schema
locations**, resources provided, validation rules, and core mappings. `09` §6 registers it in
the packet catalog. Neither says what a schema location contains, and R2 defines the registry
format for core alone.

So the extension path is specified in outline and unusable in practice. Three decisions have
now deferred to it: R16 §5 sends continuous quality metrics there, R9 §2 sends richer
provenance there, and `09` §2.3 sends procedural and institutional metadata there. None can
proceed.

NWB solves the same problem with `DynamicTable`, which permits arbitrary runtime columns with
no schema. Measured on one AIND file that is not a marginal facility: `units` carries 55
columns where core NWB defines 12, and `electrodes` carries 19 where core NWB defines about
seven. **Most columns in that file conform to nothing.**

That mechanism has a virtue this specification lacks — scientific tables accrete columns
nobody enumerated in advance — and a cost: nothing constrains the name, type, or meaning of
what accretes, so two files cannot be compared and neither can be checked.

## 2. An extension is a registry

An extension provides a **registry document in R2's format**, differing only in namespace.

```json
{
  "registry_version": "0.2.1",
  "extension_id": "aind",
  "extends": "escapewheel-logical-v0.1",
  "tables": {
    "aind.unit_metrics": {
      "columns": [
        {"name": "session_id", "type": "string", "presence": "required"},
        {"name": "unit_id", "type": "string", "presence": "required"},
        {"name": "snr", "type": "float64", "presence": "nullable"},
        {"name": "presence_ratio", "type": "float64", "presence": "nullable"}
      ],
      "primary_key": ["session_id", "unit_id"],
      "references": [
        {"columns": ["session_id", "unit_id"], "resource": "core.units",
         "resource_columns": ["session_id", "unit_id"]}
      ],
      "sort": ["session_id", "unit_id"],
      "rules": []
    }
  }
}
```

Table names MUST be namespaced by `extension_id`. An extension MUST NOT define a table in the
`core` or `analysis` namespace, and MUST NOT redefine a core table.

An extension MAY reference core tables. Core MUST NOT reference an extension: core resources
must stay interpretable when no extension is present, which `09` §2.3 already requires.

## 3. Why the same format

Everything R2 built applies unchanged. The meta-schema validates an extension registry as
readily as the core one. Tier 1 checks generate from its structure — required columns, keys,
foreign keys, closed vocabularies — with no per-extension code. Its Tier 2 rules are SQL
under the same contract. A consumer holding the extension registry gets the validation core
gets.

That is the argument for this shape over `DynamicTable`: **the same extensibility, but typed
and checkable when the schema is present**. An accreted column stops being a string nobody
can validate and becomes a declared one a generator handles like any other.

## 4. Conformance is layered

`09` §6 already states the rule and this revision does not weaken it: a core validator MUST
verify that declared extension files exist and MUST NOT require their schemas. A packet
remains core-conformant carrying extension registries it cannot parse.

A validator given an extension registry SHOULD validate that extension's tables as it
validates core's, and MUST report the two separately. A finding against `aind.unit_metrics`
is not a finding against the packet's core conformance.

An extension table's resource entry declares `layer: "extension"` and carries the
`extension_id`, so a reader knows what it holds without parsing the registry.

## 5. Versioning

An extension registry carries its own `registry_version`, independent of core's, and
`extends` names the logical standard version it was written against. An extension MAY track a
core version it predates; nothing requires them to move together.

## 6. What this does not do

**No schema translation.** An extension declares its own columns; nothing maps them into core
automatically. `09` §7's mapping guidance stays a job for importers.

**No dependency resolution.** An extension referencing a core table a packet omits is simply
unvalidatable, and reported as such. Extensions declare no requirements on each other.

**No promotion path.** Moving an extension field into core remains `09` §8's process — a
revision, with evidence the field is broadly needed.
