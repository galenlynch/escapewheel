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

An extension's resource identifier MUST begin with its namespace: `dynamic_foraging.trials`, not `trials`. A namespace MUST NOT be `core`, `analysis`, or `nwb`.

### 5.3 Registration

A packet carrying extension resources MUST declare each namespace in the catalog with its version and the path to its registry document (04 §8).

A validator MUST check that a declared registry exists. It MUST NOT require an extension's schema in order to validate core.

### 5.4 Separate verdicts

An extension is validated on core's terms and its verdict is reported separately (R17 §4). A validator MUST NOT attribute a core failure to an extension, and MUST NOT let an extension's failure invalidate core.

### 5.5 Independent versioning

An extension carries its own version, independent of `registry_version` (R17 §5).

### 5.6 A writer requires no code of an extension

A writer MUST be able to build a packet carrying an extension's tables given only the extension's registry document and its rows as files. A writer MUST NOT require an extension to be installed, importable, or resolvable in the writer's own environment (R109 §3.1).

A writer MAY accept an extension that ships code — an adapter registered under an entry-point group, or a registry document loaded from an installed distribution — and MUST NOT treat either as the ordinary case. That is what turns §5.1's "needs no code" from a possibility into a promise.

### 5.7 How an extension's document and rows reach a build

An extension delivers a registry document in the format of Part 02 and, per table it declares, rows as Parquet. Where a raw source needs converting first, a recipe names a command: an argument list run in the source's own root, not a shell line, so an extension isolates its dependencies however it likes and a build states no opinion about how (R109 §3.2).

Rows arrive carrying identifiers as the names their source used, and a writer numbers them (R53 §2.5), so an extension neither knows nor needs the packet's numbering.

How the registry document is produced is the extension's business, but an extension MUST NOT derive it from the rows it delivers for the packet being built. A declaration derived from one packet's data cannot disagree with that data, so it declares nothing, and two packets whose extensions each derived one no longer share a schema. Part 02 §5's three presence states are what carry the difference between a column this run did not compute and one the extension does not have.

An extension's command MUST produce the same rows from the same inputs, and MUST NOT let wall-clock time, an unfixed random seed, or iteration over an unordered collection reach a value it writes (R109 §3.7). Which program the command resolves to is the recipe author's, and R75 §2.2 places it: pinning library versions so two runs agree byte for byte is a build property, and a validator MUST NOT judge a packet non-conforming for lacking one. An extension that cannot be a function of its inputs delivers a file produced beforehand rather than a command the build runs.

### 5.8 What an extension may state about its own run

An extension MAY validate its own tables before returning them, against its own registry document and on the same terms a validator applies to core (R17 §4). A build MUST NOT rely on its having done so; its own validation runs over every staged resource whatever produced it (R109 §3.5).

An extension MAY write a report of its run at a path the recipe names, and a build MUST report what one contains where it is present. A build MUST NOT require one, and MUST NOT fail on a report's contents alone (R109 §3.6).

A report carries what a build cannot derive, and a build SHOULD ignore what it can: rows per table, which tables exist, and whether their schemas conform are each established without asking. What no artifact holds is what the command read, what it skipped and why, and whether a table that is short is legitimately short.

A report is JSON. An optional `problems` array carries an entry per finding, each with a `level` of `error`, `warning` or `info` (R2 §7.3), a `message`, and optionally the `resource` the finding concerns; an optional `read` array names what the command consumed. A build MUST report every problem it is given and MUST NOT refuse a report for carrying keys it does not recognise.

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

A reader MUST NOT make an extension's schema required in order to open core tables or arrays.

A writer MUST NOT:

- hide analysis-critical metadata inside free-form JSON;
- use an object path as the only way to identify a resource;
- treat the catalog as a store for all metadata.

A build MUST NOT block an import because optional institutional metadata is incomplete.

### 8.1 Untyped accretion

Core MUST NOT contain a table whose purpose is to hold arbitrary name-value pairs.

Nothing constrains the name, type, or meaning of what accretes in such a table, so two packets cannot be compared and neither can be checked. `core.trial_tags` was the one place this format permitted it and is withdrawn (R54 §2.3).

An extension needing a multi-valued attribute declares its own typed child table, as Part 02 §5.2 requires of everything else.
