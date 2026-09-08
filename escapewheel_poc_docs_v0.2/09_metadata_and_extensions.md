# Part 09 — Metadata Minimalism and Extensions

Normative.

## 1. Scope

This part defines how much metadata core requires, where richer metadata belongs, and how an extension declares it.

## 2. Tiers

| tier | contents | location |
|---|---|---|
| 1 | packet-level facts | the catalog |
| 2 | facts needed to interpret, validate, join, or reproduce | core tables |
| 3 | domain-rich, lab-specific facts | an extension's tables |
| 4 | human-readable context | `docs/` sidecars |
| 3-4 | such facts stated about one row, in the source's own vocabulary | that table's `metadata` column (R97 §3.4) |

## 3. Core inclusion rule

A field belongs in core only if common interpretation, validation, joining, or analysis would break without it.

A field SHOULD be in core when it is needed to interpret units, clocks, channels, arrays, or spike times; to validate a required relationship; to join tables; to filter or group a common analysis; to reproduce processing or curation; or to trace provenance.

A field SHOULD be in an extension or a sidecar when it is institutional, administrative, lab-specific, rarely queried, free-form, procedural but not required for analysis, or biologically rich but not required to interpret the recording.

## 4. Required minimum

A conforming packet requires only what is needed to identify, interpret, validate, query, and reproduce. The registry states the minimum per resource; this part does not restate it.

An import MUST NOT fail because optional extension metadata is absent.

## 5. Extensions

### 5.1 What an extension is

An extension is a registry document in the format of Part 02, in its own namespace (R17 §2). It declares tables, columns, references, and rules on exactly the same terms as core.

An extension needs no code. A registry document names its tables, Parquet files hold their rows, and neither imports anything of the reference implementation.

### 5.2 Namespacing

An extension's resource identifiers MUST be prefixed with its namespace: `dynamic_foraging.trials`, not `trials`. A namespace MUST NOT be `core`, `analysis`, or `nwb`.

### 5.3 Registration

A packet carrying extension resources MUST declare each namespace in the catalog with its version and the path to its registry document (04 §8).

A validator MUST check that a declared registry exists. It MUST NOT require an extension's schema in order to validate core.

### 5.4 Separate verdicts

An extension is validated on core's terms and its verdict is reported separately (R17 §4). A core failure MUST NOT be attributed to an extension, and an extension's failure MUST NOT invalidate core.

### 5.5 Independent versioning

An extension carries its own version, independent of `registry_version` (R17 §5).

## 6. Direction of reference

### 6.1 Core does not reference an extension

A core table MUST NOT declare a foreign key into an extension's table.

The reasons are separable verdicts (§5.4) and independent versioning (§5.5). "Interpretable when no extension is present" is *not* among them: a packet embeds its extension registries, so they are present whenever the resources are (R55 §5).

### 6.2 Core may name an extension

A core table MAY name an extension's resource through a `discriminator` column (Part 02 §8.3). `core.intervals.interval_kind` holds `dynamic_foraging.trials`, and a consumer resolves it by reading the kind, taking that resource's primary key from the registry, and joining.

**A discriminator names without depending.** It creates neither a shared verdict nor a version coupling, which is why it is the one mechanism core is allowed.

## 7. Promotion

A field moves from an extension into core through a revision of this specification, not by a writer deciding to emit it. Promotion is justified by §3's rule and by evidence that more than one producer needs it.

## 8. Anti-patterns

An implementation MUST NOT:

- make an extension's schema required in order to open core tables or arrays;
- hide analysis-critical metadata inside free-form JSON;
- use an object path as the only way to identify a resource;
- block an import because optional institutional metadata is incomplete;
- treat the catalog as a store for all metadata.

### 8.1 Untyped accretion

A table whose purpose is to hold arbitrary name-value pairs MUST NOT be added to core.

Nothing constrains the name, type, or meaning of what accretes in such a table, so two packets cannot be compared and neither can be checked. `core.trial_tags` was the one place this format permitted it and is withdrawn (R54 §2.3).

An extension needing a multi-valued attribute declares its own typed child table, as Part 02 §5.2 requires of everything else.
