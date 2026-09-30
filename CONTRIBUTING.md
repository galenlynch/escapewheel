# Contributing

How the registry, its schemas, the rules and the validators fit together, and what to run when
you change one.

The repository-wide [authority model](README.md#authority) applies. This file describes the
authoring and generation pipeline; it is not normative.

The process feels byzantine for one reason: **most of what looks like source is output.**
`logical_schemas.json` and the extension documents beside it are committed, readable, and edited
by nobody. `tables.md` is a document generated from the core registry. Two schemas are copied into two other packages by a build step. Once you know
which files a person writes, the rest is a straight line.

## 1. What a person writes

| file | what it is |
|---|---|
| `escapewheel_poc_docs_v0.2/00_architecture.md` | the authority framework, part subjects and statuses, normative-reference policy, and shared references |
| `escapewheel_poc_docs_v0.2/README.md` | the informational specification entry point; its tables are checked projections |
| `escapewheel_poc_docs_v0.2/01_*.md` through `10_*.md` | subject-owning numbered parts, including their local normative references; normative prose changes through an accepted revision's incorporation |
| `escapewheel_poc_docs_v0.2/CONTRIBUTING.md` | the non-normative specification style guide |
| `escapewheel_poc_docs_v0.2/Escapewheel_POC_v0.2_Implementation_Spec.md` | generated convenience rendering; never edited directly |
| `revisions/proposals/*.md` | active problem statements and alternatives; non-authoritative |
| `revisions/drafts/*.md` | candidate normative changes; non-authoritative and unnumbered |
| `revisions/accepted/R<N>-*.md` | accepted decision records explaining changes incorporated into the specification or revision process |
| `registry/core/*.toml` | the core registry's source: one file per resource, named by its resource ID, and `registry.toml` for the document's own fields |
| `registry/registry.schema.json` | the local-shape schema a registry document validates against |
| `registry/registry_contract.schema.json` | the closed shape of a registry-contract descriptor |
| `registry/registry_contracts/*.json` | phase and semantic-invariant identities, applicability, and owning anchors |
| `registry/manifest.schema.json` | the JSON Schema for `packet.json` |
| `registry/extensions/<id>/*.toml` | each extension registry's source, in the same form |
| `escapewheel-validator/.../generate.py` | how Tier 1 checks are derived from structure |

Everything else in `registry/` is output.

## 2. What a machine writes

```
registry/core/*.toml ────────────assemble.py──> registry/logical_schemas.json
registry/extensions/<id>/*.toml ─assemble.py──> registry/extensions/<id>.json
                                                 │
                                                 ├──render.py──> registry/tables.md
                                                 └──render.py──> registry/README.md (marked regions)

registry/registry.schema.json ──build.py──> escapewheel-validator/src/…/schemas/
registry/registry_contract*  ──build.py──> escapewheel-validator/src/…/schemas/
registry/manifest.schema.json ──build.py──> escapewheel-validator/src/…/schemas/
                              ├─build.py─> registry/resources.schema.json ──build.py──> escapewheel-writer/src/…/schemas/
                              └─build.py─> Part 04 §§3, 4.1, 8 and 9 field tables
```

The registry documents, `tables.md`, the README's generated regions, the delivery schema, Part 04's
field tables, and the vendored schema copies are **build artifacts that happen to be committed**.
They are committed because a packet binds the registry and a reviewer should see it change; they
are not files to edit. The delivery schema is the manifest's resource entry without
`validation_state` and `derived_from`, so change the manifest schema and rebuild.

The registry regenerates from its source: delete `logical_schemas.json` and `tables.md`, run
`uv run --project ../escapewheel-writer python build.py` from `registry/`, and both come back
byte-identical. `verify.py` asserts exactly
that on every run — snapshot the intentional candidate, regenerate, then demand that generation
preserved the snapshot. This catches an artifact drifting from its source while allowing the
pre-commit change that intentionally updates both to pass.

## 3. The one command

```bash
uv run --project escapewheel-writer python verify.py
uv run --project escapewheel-writer python verify.py --quick  # skip the test suites
uv run --project escapewheel-writer python verify.py --stage-timeout 60
```

Run it before committing anything that touches the registry, a rule, a fixture, or a generator.
It prints each stage before entering it; every stage is bounded to 300 seconds by default, and
`--stage-timeout 0` disables that bound for an intentionally long monitored run. A full run first
executes `ci/runtime_capabilities.py`, which proves its runner can wake the asynchronous thread
bridge used by Zarr, round-trip a Zarr v3 array, and bind the Unix-domain socket used by Arrow
Flight. Each healthy probe completes in well under a second; a blocked probe has a ten-second hard
limit. A runner lacking those facilities is unsuitable for the full suite and fails before
generation or a package test can hang or be mistaken for an implementation defect. CI runs the
same command and therefore exercises the same preflight.

## 3.1 Working with large packets

Cap memory for commands that read a real packet so a runaway decode fails visibly instead of
exhausting the machine. On a systemd Linux host, for example:

```bash
systemd-run --user --scope -p MemoryMax=8G -p MemorySwapMax=0 --quiet \
  uv run --project escapewheel-writer python <script>
```

Choose the cap from the work the command should require. Avoid memory-backed temporary storage for
large spills, and read large Parquet resources in batches (`ParquetFile.iter_batches`) or with a
filtered query rather than materializing a whole spike table. DuckDB also needs an on-disk spill
directory for its memory limit to be effective.

## 4. Bootstrapping in order

Nothing here needs doing by hand in normal work — `verify.py` does it — but this is the order, and
the order matters.

1. **`assemble.py`** reads each registry's source directory and writes its document. A file uses
   the published format's keys and differs from the document only in spelling: a table's fields
   sit at the top of its file, a single-column reference is written on its column, and a rule may
   invoke the `interval` template, which is expanded into plain SQL so that the registry a packet
   embeds carries no vocabulary a validator would have to learn. `canonical.py` fixes what JSON
   leaves free — keys in the order `registry.schema.json` declares them, single-column references
   in column order before multi-column ones — so how a file orders them changes nothing.

   **Column order is a convention of this registry and not a conformance requirement** — a
   validator resolves a column by name, and no clause of Part 02 or Part 03 states an order — so no
   revision mandates one. Three conventions, each chosen so a reader meets the same shape in every
   table:

   - `session_id` is the first column, being the coarsest scope a row has.
   - a `clock_id` outside the primary key sits beside the coordinates that resolve against it
     (R56 §2.2), so a reader who has found a tick has its clock. Unchecked, because which
     coordinates a clock interprets is the author's judgement.
   - `metadata` is last.

   `check.py` holds the first and the last in core and every extension.

   Each varies only where the rule says it may — a `clock_id` in the key leads because it is key,
   and a table with no coordinate has nothing to sit beside — so a placement that looks odd is
   one the rule accounts for rather than one nobody decided.
2. **`build.py`** runs `assemble.py`, then `render.py` for `tables.md` and the README's regions,
   then refreshes Part 03's and Part 04's projections and copies the hand-written schemas into
   their consuming packages.
3. **`check.py`** verifies the result: one complete registry-contract result for core and every
   extension, then repository authoring conventions, source-to-output agreement, vendored copies,
   and — with DuckDB present — execution binding against empty qualified tables built from the
   registry. The shared result is implemented in `escapewheel_validator.registry_document`, so an
   extension author and this repository receive the same answer. Section 7 counts the descriptor's
   invariant inventory.
4. **Tier 1 checks are never stored.** `escapewheel_validator.generate` derives them from the
   registry at validation time: not-null from `presence`, uniqueness from `primary_key`,
   anti-joins from `references`, membership from `enum`, and two more from each discriminator.
   Changing what Tier 1 means is a code change in `generate.py`, not a data change.
5. **`fixtures/build.py`** writes the 30-packet conformance corpus against the registry;
   `fixtures/corpus.py` runs each through the real validator and checks it produced the finding
   it was built to produce.
6. **`integration/example.py`** commits a small packet with the writer, one resource of each
   kind against every shipped extension, and fills Part 08's layout and manifest excerpt from it.
   It runs before `combine.py --check`, since the single-file rendering carries Part 08.

## 5. Changing something

| you want to | edit | then |
|---|---|---|
| add or change a column, key, type, reference | begin with a proposal or draft, then get the revision accepted and edit the table's file in `registry/core/` | `verify.py`; `revisions/CONTRIBUTING.md` has the whole sequence |
| add a Tier 2 rule | a `[[rules]]` entry in the table's file | `verify.py` |
| change how Tier 1 is derived | `escapewheel-validator/.../generate.py` | `verify.py` |
| add an extension | a directory `registry/extensions/<id>/` holding `registry.toml` and one file per resource | `verify.py` |
| change the manifest or the meta-schema | the hand-written copy in `registry/` | `build.py` re-vendors; `verify.py` |
| add a fixture variant | `fixtures/build.py` and `fixtures/corpus.py` | `verify.py` |
| change the packet Part 08 shows | `integration/example.py` | `verify.py` |

**A schema change starts with a revision.** Not as ceremony: `revisions/registry-targets.toml`
locates each accepted clause in the generated registry, so a declaration traces to the argument
that set it. A declaration changed with no revision breaks that chain silently.

Moving a draft to an accepted revision requires explicit authorization. Acceptance and
incorporation into the applicable current owner are one reviewable change; until it is complete,
the existing v0.2 text and revision-process guide remain authoritative for their respective
subjects.

## 6. Four traps, each of which has actually happened

**Editing `logical_schemas.json` or an extension's `.json`.** The next `build.py` overwrites it
from its TOML source. `verify.py`'s candidate-state comparison catches that overwrite, which is why
the comparison exists.

**A stale vendored schema.** `registry.schema.json` and `manifest.schema.json` are copied into two
other packages because a wheel cannot read a file from another distribution. A stale copy has broken
every packet three times — R48, R53 and R56 — and each time it surfaced as a hundred findings
about the *data* rather than one about the copy. `build.py` writes them and `check.py` compares
them, so the class is closed; do not edit a vendored copy.

**A maintained inventory going stale.** Three records cannot be fully derived from the generated
registry: the table ledger in `conformance/spec-sweep/tables.py`, the `NAMING_EXCEPTIONS` in
`check.py`, and `applied.toml`'s clause dispositions. Each fails a check rather than drifting. Every
naming exception must still identify a present declaration that breaks a convention, and the
clause ledger must still name real accepted clauses and existing current owners. What stays a human
judgement is *which* disposition a clause gets.

**A revision clause that never reaches the spec.** Two independent audits found normative clauses
dropped during compilation of the v0.2 prose — `R53 §2.4`'s `int64` escape, `R21`'s codec floor,
`R36 §2.2`'s prefix digest reversed into "undefined". A citation sweep cannot see these, because
the revision is cited for its *other* clauses. `revisions/ledger.py` is what sees them:
`revisions/applied.toml` records each clause's disposition and exact current owner, while
`revisions/registry-targets.toml` resolves exact JSON locations. The undisposed-clause backlog may
fall and must not rise. Current owners need not cite their accepted revisions back.

<!-- BEGIN facts: clauses -->
`ledger.py` enumerates 809 Decision clauses across the accepted revisions.
<!-- END facts: clauses -->

## 7. What each check is for

The incorporated registry-contract descriptor enumerates the invariants that apply to core and
extension documents by class. Their algorithms are owned by Parts 02 and 09 and implemented once
in `escapewheel_validator.registry_document`; `escapewheel extension check` and `check.py` consume
that complete result. `check.py` separately adds checks true only of this repository's build.
`facts.py` counts the descriptor inventory and those repository checks:

<!-- BEGIN facts: checks -->
28 registry-contract invariants, applied by class to core and each of the 4 extension registries, and 40 further checks over the whole set
<!-- END facts: checks -->

| check | catches |
|---|---|
| `revisions/stages.py` | an open or prospective accepted artifact with invalid lifecycle metadata, missing stage sections, template residue, or no exact draft clause list |
| `revisions/test_evidence.py` | regressions in owner, corpus, verifier-stage, and complete-manifest validation |
| `revisions/evidence.py` | an accepted current-format clause with no owner, projection, conformance evidence, implementation disposition, or documentation disposition |
| `revisions/check_citations.py` and `revisions/repoint.py` | a citation that does not resolve, or implementation source that names a historical decision where the current part owns the rule |
| `revisions/impact.py` | working-tree files citing a changed or explicitly queried specification section or stable anchor |
| `registry/check.py` | a registry that contradicts itself, a rule naming a removed column, a stale vendored copy, a naming convention broken without a declared reason |
| `fixtures/corpus.py` | a validator that stopped catching what it used to, or started catching what it should not |
| `revisions/ledger.py` | an accepted clause with no disposition or an unresolved current-owner or registry target |
| `escapewheel_poc_docs_v0.2/columns.py --check` | a column table in a part that no longer reproduces the registry |
| `combine.py --check` | a single-file spec rendering that no longer matches its parts |
| `facts.py` | a count in a root document that no longer matches what it counts |
| `verify.py`'s candidate-state comparison | a stale or hand-edited artifact changed by regeneration |
| the four package test suites | asserted reference-implementation behavior outside the checks above |
| `integration/` | a writer, reader, and validator that disagree with one another, or a Part 08 query that no longer runs |

## 8. Reading the result

No derived count in this repository should be typed by hand. `registry/README.md`'s are filled by
`render.py`, the root documents' by `facts.py`, and the clause ledger's undisposed high-water mark
lowers itself. Provenance exceptions are exact identities, not a count. If you find yourself
editing a number, check whether something can compute it instead:
every number that was hand-maintained here went stale, several of them twice in one day.

`registry/tables.md` is the readable registry: every table, every column, its type, presence,
what it declares about its values, and its description. Read Part 02 and the registry to see what holds
**now**; read the accepted revisions to understand why. `registry/README.md` carries the counts,
generated.
