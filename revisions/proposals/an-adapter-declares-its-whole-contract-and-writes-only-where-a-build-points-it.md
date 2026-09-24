# An adapter declares its whole contract and writes only where a build points it

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-24 |
| **Based on** | `63aa520d947c1278d4731c4a567ff4b883cf10c4` |
| **Decision domain** | specification |
| **Affects** | Part 03 §§11 and 11.5; Part 04 §5.5; Part 05 §§2 and 3.5; Part 07 §4; `registry/adapter.schema.json`; `registry/sources.schema.json`; the reference writer's declaration checks, `escapewheel declare`, `session.build`, and array delivery; the reference reader's source resolution |

## 1. Problem

A build reads what an adapter declares before it opens any source.
[Part 03 §11.5](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-adapter-declaration-document)
names the eight members of the declaration document, and
[Part 05 §3.5](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-recipe-check) lists
what a build refuses a declaration for. Three gaps separate that contract from what a build can
rely on.

The document's schema is published but not incorporated, and it requires four of the eight
members. A document omitting `states`, `accepts`, `consumes`, or `contributes` is valid; the writer
reads three of those omissions as empty lists by convention and refuses the fourth.

A build checks a declaration only on one route. The reference writer applies the schema and the
refusals to a declaration document that a recipe's `[source.delivery]` block names. It applies
neither to an importable class, whether built in or registered by an installed package, although
Part 03 §11.5 makes a class and a document one declaration. `escapewheel declare` writes a document
it never validates, and `session.build` builds from a recipe it never checks. The source
resolution document that a reader follows has the same gap: its schema is published, not
incorporated, and the reader never applies it.

Part 05 §2 still says a source adapter returns records and writes no files. Part 03 §11.3 has an
adapter write a packet-owned array into a location the build supplies, and the protocols of Part 03
§11.2 have it write a delivery directory and a report. Neither part says who owns those locations, so
an adapter author cannot tell which writes are permitted.

## 2. Evidence

All observations were reproduced at the recorded baseline. Probes ran in the writer's environment
against `registry/logical_schemas.json`, using throwaway recipes, adapter classes, and documents
under a scratch directory.

### 2.1 The declaration schema admits an incomplete document

`registry/adapter.schema.json` requires `kind`, `protocol`, `produces`, and `needs`, and closes the
object. A document carrying only those four validates with no error. Part 03 §11.5 says only that
the document's shape "is published as" the schema; under
[Part 00 §2.2](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-authority-by-concern), an
artifact acquires authority only where a numbered part expressly incorporates it.

The prose already makes two omissions meaningful. An absent `accepts` means the adapter accepts no
option beyond what it needs (Part 03 §11.5), and an absent `contributes` means it supplies no
resource only in part. An absent `states` has no stated meaning, yet
[Part 05 §3.4](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-source-declarations)
requires a build to refuse a source whose stated fields it cannot determine, so the writer
refuses a document without `states` that the schema admits. An absent `consumes` becomes an empty
list in the writer's `declared()`.

`registry/adapter.example.json` carries all eight members. No other declaration document is
tracked in the repository.

### 2.2 A class declaration escapes the refusals

A class registered as kind `bogus` with `PRODUCES = {"core.tirals"}` and `ACCEPTS = ("root",)`
was checked by `Recipe.check`. Its errors named the undeclared resource through the ownership check
and nothing about `accepts`. The same facts rendered by `declaration.of` and passed to
`declaration.refusals` produced two refusals: `produces core.tirals, which no loaded registry
declares` and `accepts root, which is a term a build fills rather than an option a recipe sets`.
`Recipe._declaration_problems` skips every source without a `[source.delivery]` block, which is
every built-in adapter and every adapter registered through the `escapewheel.sources` entry-point
group.

`sources.discovered()` loads each registered class and checks nothing about its declarations.
`escapewheel declare` renders a class with `declaration.of` and writes the result without
validating it; only the AIND package's tests check its generated documents against the schema.

### 2.3 A build runs from an unchecked recipe

`session.build`'s docstring says the recipe is "assumed already checked; `Recipe.check` is the
caller's job", and its body does not call it. The command line calls `Recipe.check` before
`session.build`, so the gap is open to a caller of the Python function, which is the route an
orchestrator takes.

### 2.4 The reader never applies the resolution schema

[Part 04 §5.5](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#55-source-resolution) says the
source resolution document's shape "is published as" `https://escapewheel.org/schemas/sources/0.1.0`.
The reader vendors `sources.schema.json` and exports `sources_schema()`, and `read_sources` checks
only `sources_standard_version`. A document whose entry carries `url` instead of `uri` and an
extra top-level member raises `KeyError: 'uri'` from `read_sources`. The schema reports all three
defects. The writer writes `sources.json` at commit without validating it either.

### 2.5 Part 05 §2 contradicts the delivery routes

Part 05 §2 closes on the rule that a source adapter returns records and writes no files. It
predates R115 and R117, which introduced the delivery routes; neither lists Part 05 §2 among the
sections it amends. The routes an adapter writes through are:

| location | supplied as | written by |
|---|---|---|
| a packet-owned array | `array_location` (Part 03 §11.2) | the adapter, as Zarr v3 (Part 03 §11.3) |
| a `files-v0.1` delivery | `delivery_root` | the adapter, as Parquet |
| a report | `report_path` | the adapter, under `files-v0.1` and `stream-v0.1` |
| a `flight-v0.1` socket | `socket` | the adapter binds it |

[Part 03 §11](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#11-reaching-a-source)
repeats that an adapter "reads one source and returns records", and
[Part 07 §4](../../escapewheel_poc_docs_v0.2/07_reference_implementation.md#ew-reference-object-model)
says an adapter's return type is records, not a path, before describing an adapter that writes
an array. The writer's `sources/__init__.py` docstring says an adapter never writes.

The writer creates each location under its own workspace and removes the workspace when a build
ends, so cleanup already belongs to the build; no part says so.

One write takes no supplied location. An adapter reading a remote store keeps fetched objects in a
cache, found from `ESCAPEWHEEL_SOURCE_CACHE` or else under `TMPDIR`, because an environment
variable reaches a delivering command where a value set in the build's process does not. The
cache holds source bytes and nothing a build reads as a delivery.

### 2.6 The writer's array delivery drifts from Part 03 §11.3

Part 03 §11.3 has an adapter name each packet-owned array's directory by its catalog row's
`resource_id` and a build bind bytes to rows one-to-one. The writer names the directory by
`array_asset_id` and writes a `_resources.json` beside the arrays, which no part mentions and no
schema checks; the build reads the binding from that file.

### 2.7 Test baseline

The writer's suite has 592 tests and the AIND package's 67, all passing at the baseline, and the
full repository verifier passes its 35 stages.

## 3. Desired outcome and constraints

- A declaration document states every member, so an omission is a defect a schema reports rather
  than a meaning a reader infers.
- The declaration schema and the source resolution schema carry authority for their shape, as the
  manifest and delivery schemas do, and the prose keeps what each member means.
- A build applies one set of checks to a declaration, whichever form it arrives in and whichever
  public route reaches the build.
- The pipeline rule says what an adapter may write: only into a location a build supplied for it,
  which the build creates and removes.
- The change keeps an adapter's source-format knowledge in the adapter and the packet contract in
  the registries and profiles, and it changes no packet bytes.

## 4. Options and tradeoffs

### 4.1 Declaration completeness

**Require every member, allowing empty lists** (preferred). The schema lists all eight members
under `required`, and Part 03 §11.5 states that a document names each. An omission then has no
meaning to settle. Every document written before the change becomes invalid until regenerated;
the only tracked one already complies, and a generated document complies by construction.

**Keep the current four and define each omission.** The prose already does this for `accepts` and
`contributes`, so adding `states` and `consumes` would be consistent. It leaves a schema that
cannot tell a deliberate empty list from a forgotten key, which is the defect the review raised.

**Require only `states`, `accepts`, and `consumes`.** This matches the direction agreed before
`contributes` existed. `contributes` was added as optional so that documents without it kept
their meaning; requiring it now costs nothing further, since the same regeneration covers it.

### 4.2 Incorporation

**Incorporate both schemas** (preferred): the declaration schema from Part 03 §11.5, and the
source resolution schema from Part 04 §5.5, each stating the extent the schema owns, as Part 04's
opening does for the manifest schema. The writer validates the resolution document it writes. A
reader need not validate one, as a reader need not validate a registry for ordinary access
([Part 02 §2.7](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-resource-provenance-policy)), and
may validate one to report a malformed document clearly. The reference reader validates a
caller-supplied document, so a malformed one is refused with the place it fails rather than a
`KeyError`, and keeps its advisory reading of the packet root's `sources.json`.

**Leave both published and unincorporated.** A build would keep checking a shape that governs
nothing, and a disagreement between prose and schema would not be an inconsistency the candidate
can detect.

### 4.3 Checks at every public boundary

**Apply the schema and refusals to every declaration a recipe names** (preferred). A build
renders a class declaration into the document form, checks its shape, and applies Part 03 §11.5's
and Part 05 §3.5's refusals, so a class and a document are refused alike. `escapewheel declare`
validates what it writes. `session.build` runs the recipe check itself and refuses on an error, so
no public route builds from an unchecked recipe; the command line's earlier check then costs one
repeated pass over the recipe.

**Check at discovery.** Validating a registered class when its entry point loads would refuse a
package before any recipe names it, and a broken package would stop a build that never uses it.
Discovery skips a class that fails to import today for the same reason.

### 4.4 What an adapter writes

**An adapter writes only into the locations a build supplies** (preferred). Part 05 §2 would say
that an adapter delivers records, arrays, and reports only through `array_location`,
`delivery_root`, `report_path`, or the protocol's socket, and that the build creates those
locations under its staging area and removes them. Part 03 §11 and Part 07 §4 would stop
describing an adapter as returning only records.

**Delete the sentence.** The contradiction goes, and nothing then says where an adapter may write,
which the review asked to state.

**Keep the sentence and treat arrays as the exception.** It would leave the files protocol and the
report unaccounted for.

A source cache is outside the delivery. Any of the options above can leave it ungoverned, so long
as the rule is about what a build reads and stages rather than about every byte an adapter
process writes.

### 4.5 Array delivery binding

The writer's directory naming and its `_resources.json` depart from Part 03 §11.3 without a
decision behind them. Bringing the writer to the current rule, directories named by `resource_id`
and binding by catalog row, needs no specification change and belongs with this implementation.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged; no scientific meaning changes. |
| logical prose and registry | Unchanged; neither declares an adapter or a resolution document. |
| physical profiles | Part 03 §11 stops describing an adapter as returning only records; §11.5 incorporates the declaration schema and requires every member. |
| packet manifest and JSON Schemas | `adapter.schema.json` requires all eight members; Part 04 §5.5 incorporates `sources.schema.json`. The manifest and delivery schemas are unchanged. Schema `$id` versions stay until release identifiers are assigned. |
| validation and import | Part 05 §2 states which writes an adapter makes and that the build owns their locations; §3.5 applies its declaration refusals to every declaration a recipe names. |
| extensions | Registry content unchanged. The AIND package's generated documents gain any missing members when regenerated. |
| reader, writer, validator, adapters | The reference reader validates a caller-supplied resolution document; the specification permits but does not require it. The writer checks class declarations, validates `escapewheel declare`'s output and the `sources.json` it writes, runs the recipe check inside `session.build`, and names array directories by `resource_id`, binding by catalog row. The validator is unchanged. |
| existing packets | Unchanged; no packet byte moves. A packet's `sources.json` that fails the schema is nonconforming, and a reader may still ignore it as it does now. |
| conformance fixtures and tests | Writer tests for a class declaration refused as its document would be, an incomplete document refused, `session.build` refusing an unchecked recipe, and array directories named by `resource_id`; reader tests for a caller-supplied resolution document failing its schema. |
| revision-process tooling | Ordinary ledger and evidence records. Part 04 §5.5 and Part 05 §2 have no canonical anchors, so a structural draft needs an anchor bootstrap first. |
| documentation | The writer and reader READMEs, `registry/README.md`'s incorporation column, and the writer's `sources/__init__.py` docstring. |

## 6. Open questions

1. Does `contributes` join the required members? Recommendation: yes, so that every member is
   stated and one regeneration covers all of them.
2. Resolved: a reader need not validate a resolution document and may. Whether to validate is an
   implementation's choice about how clearly it reports a malformed document, as with a registry,
   so the specification requires neither refusing nor skipping one.
3. Is the source cache governed? Recommendation: no. The write rule covers what a build reads and
   stages, and the cache is neither.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [ ] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.
