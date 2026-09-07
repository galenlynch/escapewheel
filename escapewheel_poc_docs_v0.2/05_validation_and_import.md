# Part 05 — Validation and Import

Normative.

## 1. Core principle

**Validation is importation.** Copying bytes into a packet directory is staging, not import.

A resource is imported when it has been discovered, extracted to staging, normalized to the logical schemas, validated, committed, and recorded in the catalog with its provenance.

A staged resource MUST NOT appear in the catalog as a committed canonical resource. Nothing becomes core data before it has passed the validators that apply to it.

## 2. Pipeline

| stage | action |
|---|---|
| 1 | discover what each source offers |
| 2 | extract candidate resources to staging |
| 3 | normalize to the logical schemas |
| 4 | validate the staged resources |
| 5 | commit |
| 6 | record provenance |
| 7 | materialize analysis resources |

An importer MUST NOT combine parsing, normalization, validation, and writing into one opaque step. A source adapter returns records; it MUST NOT write files.

## 3. The session recipe

### 3.1 Purpose

One source is rarely sufficient: integer sample indices come from a sorter, task structure and registration from an exported file, and session identity from acquisition metadata. The unit of work is therefore a **recipe** naming several sources, not a single input file.

A recipe declares, for one packet:

- each source: its kind, its root, and its options;
- which resources each source supplies;
- the clocks the packet declares, and their parents;
- what to materialize;
- session facts no source carries.

A recipe MAY declare a fact a source it reads also states; §3.6 says which of the two the packet gets. `core.subjects` is not a resource the recipe supplies unconditionally: a source that states a subject MAY own it, arbitrated as any other resource two sources can produce, and the recipe's `[subject]` block supplies the table only where no source owns it (R87 §2.8).

### 3.2 The recipe is the provenance record

A recipe MUST be recorded in the import run's parameters, and its digest MUST be recorded as the run's `code_uri`. A committed packet therefore states what produced it.

### 3.3 Ownership

Each source declares its resources as `owns` or `contributes`.

| declaration | meaning |
|---|---|
| `owns` | this source is solely responsible; records another source emits for the resource are discarded |
| `contributes` | this source adds rows alongside others |

`contributes` exists because some resources genuinely have several suppliers. Without the distinction, the last adapter to run wins silently.

### 3.4 What a source can produce

Every source adapter MUST declare `PRODUCES`, the set of resource identifiers it can supply (R63 §2.1). It is static: a property of the adapter, readable with nothing open, and distinct from what a particular source root happens to hold.

A source entry that declares no `owns` MUST be read as owning every resource in its adapter's `PRODUCES` that no other source owns (R63 §2.2). **A recipe states what it narrows; silence means the whole.**

Where two sources default to the same resource and no preference is declared, the recipe MUST be refused naming both.

A build MUST also be able to determine, for each source a recipe names and without opening it, which recipe fields that source can **state**, and MUST refuse a recipe naming a source it cannot determine that for (R87 §2.2). What that declaration is called and where it lives is Part 07 §4's.

### 3.5 Checking a recipe

A recipe MUST be checked against the registry before any source is opened. The check MUST refuse:

- a resource owned by more than one source;
- an owned resource the registry does not define;
- an owned table whose **required** foreign key targets a table nothing supplies;
- a clock declared twice, referenced but absent, or parented to nothing;
- a required source option that is not set.

The check MUST report as a **warning**:

- an owned table whose **nullable** foreign key targets a table nothing supplies;
- a resource some listed source declares in `PRODUCES` that no source claims (R63 §2.3);
- a field the recipe declares that some listed source states and no override covers (R87 §2.3).

A warning is not an error because narrowing is legitimate, and only the recipe's author knows whether this one was meant.

### 3.6 Authority for a declared fact

Where a recipe declares a fact and a source the same recipe reads states that fact, a build MUST report a difference between the two, naming the field, the declared value, the source's value and the file it came from (R87 §2.1). A build MUST refuse only where the fact identifies something a reader resolves across packets; otherwise it proceeds, and `--strict` refuses. `[subject].subject_id` is that case and the only one: a subject is not scoped to a session, so a wrong one agrees with another packet's animal instead of colliding with the true value.

Two values are compared at the type the packet will store, both normalized to it first. A source stating no value for a declared fact is not a disagreement: the declaration stands, a writer MUST NOT report it as a mismatch, and SHOULD note that it went unchecked (R87 §2.4).

A recipe MAY declare that its own value supersedes the source's, by naming the field in a top-level `[overrides]` table keyed `block.field`. The value MUST be a non-empty reason. Declaring an override is never required: it records a decision and silences the report, and a recipe declaring none is conforming. A build MUST report an override for a field the source agrees with, or that no source states, and MUST NOT refuse on either (R87 §2.5).

The comparison needs the source read, so it happens as each source is built and MUST refuse before any resource is staged (R87 §2.6). A source's statement of a fact is whatever its adapter exposes for that fact; which of several values inside a file it stands behind is the adapter's judgement and not the recipe's.

A fact the source **derives** is the source's. `core.sessions.session_start_time` and `session_end_time` come from the session source's declared stream windows, and a writer MUST use the source's value where a session source is present and MUST report a declaration it did not use rather than discarding it silently (R87 §2.7).

## 4. Stages 1 to 3

### 4.1 Discover

For each source, report what it offers per resource, and how many rows. Discovery MUST NOT write to the packet.

### 4.2 Extract

Copy or stream candidate resources into a staging area under the packet root. A table whose row count is large MUST be streamed rather than materialized as host objects.

### 4.3 Normalize

Map source objects onto the logical schemas: assign identifiers packet-wide before any table is written (R53 §2.5), apply the declared sort, and coerce types to the registry's.

Normalization MUST be deterministic in the recipe. Two runs of the same recipe over the same sources produce the same packet.

An interval is closed (01 §2.3). A source whose intervals are half-open — `[start, stop)` — MUST be converted, which is a subtraction on the stop bound. A writer MUST NOT carry a half-open bound through unchanged.

An adapter compensating for a known defect in its source MUST declare the compensation, and every compensation applied MUST be recorded in the import run's parameters. Choosing not to correct a known defect is equally a compensation and is declared as a pass-through.

## 5. Stage 4: Validate

### 5.1 Tier 1

Generated from structure (Part 02 §10.1): required-column non-null, primary-key uniqueness, foreign-key anti-joins, closed-vocabulary membership.

### 5.2 Tier 2

Declared per table as SQL returning offending rows, or as an expanded template (Part 02 §10.2).

### 5.3 The shim

Physical order, file presence, Parquet types, Zarr rank and codecs, and checksums MUST be checked outside SQL (R12 §4). A query cannot observe them, so such a check written as SQL fails silently rather than loudly.

A claim that crosses from the manifest to a table belongs here for the same reason. A resource's `processing_run_id` lives in the manifest, which no query sees, so the check that it names a run present in `core.processing_runs` is the shim's and not a foreign key (R31 §5).

### 5.4 Extensions

Each extension registry present is validated on the same terms as core, and its verdict is reported separately (R17 §4). A core failure MUST NOT be attributed to an extension, and an extension failure MUST NOT invalidate core.

## 6. Stage 5: Commit

Commit MUST be atomic with respect to a concurrent reader:

1. write the staged resources;
2. validate them;
3. move resources into their final paths;
4. **publish** the packet catalog at `packet.json`, last and atomically.

A reader MUST observe either the previously committed catalog or the newly published one, and MUST
NOT observe a catalog naming a resource that is not yet in place (R74 §2.1). Every packet-owned
resource the catalog names MUST already be at its final location and MUST have passed validation
before it is published.

The publication mechanism is the profile's. A filesystem profile MAY publish by atomic rename
within one directory; an object-store profile MAY publish by a single-object write. A writer MUST
NOT be required to perform an atomic **directory** rename (R74 §2.2), which no object store
offers and which the packet layout does not need — the catalog is one object.

Where the store offers a conditional write, a writer publishing a new version SHOULD use it, so
two writers cannot silently overwrite one another's head. Where it offers none, a writer MUST NOT
claim it detected a conflict it could not detect (R74 §2.3).

A commit that finds an error MUST NOT write a manifest at the packet root, and SHOULD leave staging in place for inspection.

## 7. Stage 6: Provenance

Record `core.source_files` for the inputs, one `core.processing_runs` row for the import, and `core.processing_run_inputs` linking them. The run declares its `scope` and `scope_kind` (R44 §2, R49 §2).

## 8. Stage 7: Materialize

Materialization runs inside the import: core is staged, the staged packet is opened, derived resources are computed from it, and everything is validated together before anything is promoted.

Deriving into an already-committed packet is an amendment (03 §9.1), not part of an import.

## 9. Reporting

### 9.1 Findings

A finding declares a level, the check that produced it, and a message. Where a check is a query, the offending rows are the finding.

| level | meaning |
|---|---|
| `error` | the packet does not conform |
| `warning` | conformant, but likely not intended |
| `info` | recorded, not judged |

### 9.2 Error policy

An import MUST refuse to commit on any error.

A validator MUST NOT downgrade an error to make a packet pass. An advisory rule MUST NOT be an error (Part 02 §10.2), so enabling advisory checks cannot change whether a packet previously passed.

### 9.3 Comparison against a prior packet

Where an import replaces an existing packet, it SHOULD report every resource the prior catalog declared that the new one does not. This is a warning: narrowing is legitimate, and no other check sees a resource that is simply absent.

## 10. Two conformance classes

A report says which of two claims it is making (R79 §2.1).

**Packet conformance** is a property of the bytes. It is evaluated on a packet regardless of how the packet was produced, and it is what `validate` reports. Provenance is SHOULD within it: a packet carrying none is conforming (R9 §5).

**Importer conformance** is a property of a process. An importer conforms when it satisfies this part, which includes recording provenance for the import activity and the inputs it read. A packet is not judged by it.

A validator MUST report packet conformance, and MUST NOT report a packet as non-conforming for an obligation that binds only an importer. Where it also checks importer obligations — a build-time run inside `import`, which has the process in hand — it MUST report the two separately (R79 §2.2), as it already does for core and extension verdicts.

An analysis resource is where the two meet: `processing_run_id` is MUST for one (R31 §3), and that is a packet obligation rather than an importer's, because a derived resource naming no run is unreproducible whoever built it (R79 §2.3).

## 11. Minimum acceptance criteria

An importer conforms when it:

1. refuses a recipe that cannot produce a valid packet, before opening any source;
2. produces a packet that passes Tier 1, Tier 2, and the shim;
3. records provenance for what it read and what it ran;
4. leaves no manifest at the packet root when it refuses;
5. is **logically deterministic**: for the same recipe, the same source bytes and the same
   declared normalization, it produces the same canonical rows, the same values, the same assigned
   identifiers, the same resource identities and the same declared physical ordering (R75 §2.1).
   Identifier assignment MUST be a function of the recipe and the sources, never of wall-clock
   time, iteration order over an unordered collection, or the order a filesystem listed a
   directory.

Byte-identical output is **not** required and cannot be: a manifest carries `created_at` and
`validated_at`, and encoders may encode identical logical content differently between library
versions. An implementation MAY offer a deterministic-build mode that pins those, and a packet
MUST NOT be judged non-conforming for lacking one (R75 §2.2).

A recorded `sha256` therefore says what a packet's bytes **are**, not what a second build would
produce. Two conforming builds of one dataset may record different digests for the same rows
(R75 §2.3).

## 11. Alternatives are resolved before a commit

Where two or more `core.processing_runs` rows share `(session_id, activity_type, scope_kind, scope)`, the packet **MUST** carry a `core.preferred_runs` row naming one of them, and a writer **MUST** refuse to commit one that does not (R82 §2.1). Where an activity has more than one run in a session, every one of those runs **MUST** declare `scope` and `scope_kind` (R82 §2.2) — without a scope the runs cannot be grouped, so an ambiguity cannot be found rather than not existing.

Both are checked at `error` level. R41 §2.4's rule that a consumer MUST NOT silently choose stands and becomes unreachable on a conforming packet: a consumer that meets an unresolved alternative is holding a packet that failed validation and reports that (R82 §2.3). Nothing here forbids a packet holding two sortings of one probe or two curations of one sorting (R82 §2.4); what it requires is that the packet says which is current.
