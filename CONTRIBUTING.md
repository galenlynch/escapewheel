# Contributing

How the registry, its schemas, the rules and the validators fit together, and what to run when
you change one.

The repository-wide [authority model](README.md#authority) applies. This file describes the
authoring and generation pipeline; it is not normative.

The process feels byzantine for one reason: **most of what looks like source is output.**
`logical_schemas.json` and the extension documents are committed, readable, and edited by nobody.
`tables.md` is a document generated from the core registry, and the packages carry copies of the
schemas and checkers they use. Once you know which files a person writes, the rest is a straight
line.

## 1. What a person writes

The specification is the directory `spec/`, its **tree**. Everything a second implementer needs
lies within it, and it depends on nothing else in the repository; the packages, extensions,
fixtures and conformance probes depend on it.

| file | what it is |
|---|---|
| `spec/parts/00_architecture.md` | the authority framework, part subjects and statuses, normative-reference policy, and shared references |
| `spec/README.md` | the informational specification entry point; its tables are checked projections |
| `spec/parts/01_*.md` through `12_*.md` | subject-owning numbered parts, including their local normative references; normative prose changes through an accepted revision's incorporation |
| `spec/CONTRIBUTING.md` | the non-normative specification style guide |
| `spec/informative/Escapewheel_POC_v0.2_Implementation_Spec.md` | generated convenience rendering; never edited directly |
| `revisions/proposals/*.md` | active problem statements and alternatives; non-authoritative |
| `revisions/drafts/*.md` | candidate normative changes; non-authoritative and unnumbered |
| `revisions/accepted/R<N>-*.md` | accepted decision records explaining changes incorporated into the specification or revision process |
| `spec/source/core/*.toml` | the core registry's source: one file per resource, named by its resource ID, and `registry.toml` for the document's own fields |
| `spec/artifacts/registry.schema.json` | the local-shape schema a registry document validates against |
| `spec/artifacts/registry_contract.schema.json` | the closed shape of a registry-contract descriptor |
| `spec/artifacts/registry_contracts/*.json` | phase and semantic-invariant identities, applicability, and owning anchors |
| `spec/artifacts/manifest.schema.json` | the JSON Schema for `packet.json` |
| `spec/tools/checkers/*.py` | the registry-document, rule-language and descriptor checkers the packages copy |
| `extensions/<id>/*.toml`, `escapewheel-aind/extensions/<id>/*.toml` | each extension registry's source, in the same form |
| `escapewheel-validator/.../generate.py` | how Tier 1 checks are derived from structure |

Everything else in `spec/artifacts/` and `spec/informative/` is output, apart from the example
documents beside the listing.

## 2. What a machine writes

```
spec/source/core/*.toml ──assemble.py──> spec/artifacts/logical_schemas.json
                                          │
                                          ├──render.py──> spec/informative/tables.md
                                          └──render.py──> spec/source/README.md (marked regions)

extensions/<id>/*.toml ───registries.py build──> extensions/<id>.json

spec/artifacts/manifest.schema.json ─build.py─> spec/artifacts/resources.schema.json
                                    └─build.py─> Part 04 §§3, 4.1, 8 and 9 field tables

spec/artifacts/physical_profiles/*.json ─build.py─> Part 03's interface and overriding-order tables

spec/artifacts/*, spec/tools/checkers/* ──tools/copies.py──> each package's copies
```

The registry documents, `tables.md`, the source guide's generated regions, the delivery schema,
Part 03's and Part 04's generated tables, and the packages' copies are **build artifacts that
happen to be committed**. They are committed because a packet binds the registry and a reviewer
should see it change; they are not files to edit. The delivery schema is the manifest's resource
entry without `validation_state` and `derived_from`, so change the manifest schema and rebuild.

The registry regenerates from its source: delete `logical_schemas.json` and `tables.md`, run
`uv run --project spec/tools python spec/tools/build.py`, and both come back byte-identical.
`verify.py` asserts exactly that on every run — snapshot the intentional candidate, regenerate,
then demand that generation preserved the snapshot. This catches an artifact drifting from its
source while allowing the pre-commit change that intentionally updates both to pass.

## 3. The tree's tools

`spec/tools/` holds the software that produces and checks the tree, and nothing else in the tree
is software. Four rules keep the tree whole, and `verify.py` checks each through `tools/tree.py`:

- **The tree regenerates from itself alone.** A copy of `spec/` in an empty directory, running its
  own tools in the environment its own lock declares, reproduces every generated file and region
  byte for byte and passes its own checks.
- **A tool in the tree imports nothing of the repository outside it.** It imports the standard
  library, the tree's own modules, and the libraries `spec/tools/pyproject.toml` declares and
  `spec/tools/uv.lock` locks; a test may also import the development group's.
- **The tree holds a tool deciding each checked projection, consistency condition and artifact
  conformance.** A column table, a generated region or the combined rendering has the tool that
  regenerates it, each explicit consistency condition has the check that decides it, and each
  incorporated artifact is checked against the schema or contract its part names.
- **A package copies what it uses and checks its copies.** A wheel cannot read a file outside it,
  so a package lists under `[tool.escapewheel.copies]` the artifacts and checkers it copies from
  the tree. `tools/copies.py` writes them, and the package's `tests/test_copies.py` fails where one
  differs. A package copying a checker admits the tree's locked version of each library the
  checker imports, which `tools/copies.py --check` confirms.

A checker locates its artifacts through the `artifacts` module beside it, which each place
supplies for itself, so a copy matches its source byte for byte. Checks needing what the tree does
not hold — the Tier 2 rules' execution in DuckDB, Git history, the frozen v0.1 documents — lie in
`conformance/`.

What the tools share lies in `spec/tools/specdoc.py`: finding the numbered parts, the heading,
anchor and citation grammars, a record's metadata rows, JSON Pointer resolution, the files Git
would commit, a registry's tables, region replacement, the check reporter, and the error a
generator raises. It imports only the standard library, so the scripts in `revisions/` and `tools/`
import it from where it sits. A helper a second script needs goes there, not into a second copy.

## 4. The one command

```bash
uv run --project escapewheel-writer python verify.py
uv run --project escapewheel-writer python verify.py --quick  # no test suite
uv run --project escapewheel-writer python verify.py --stage-timeout 60
uv run --project escapewheel-writer python verify.py --jobs 1  # one stage at a time
```

The stages that write tracked files (the generators, the root documents' counts and the corpus
build) run first, alone and in order. Every other stage only reads the tree, and those run
together, one per CPU unless `--jobs` says otherwise. A stage added to `verify.py` that writes a
tracked file is declared as a generator there, or it races the stages that read what it writes.

Run it before committing anything that touches the registry, a rule, a fixture, or a generator.
It prints each stage before entering it; every stage is bounded to 300 seconds by default, and
`--stage-timeout 0` disables that bound for an intentionally long monitored run. A full run first
executes `tools/runtime_capabilities.py`, which proves its runner can wake the asynchronous thread
bridge used by Zarr, round-trip a Zarr v3 array, and bind the Unix-domain socket used by Arrow
Flight. Each healthy probe completes in well under a second; a blocked probe has a ten-second hard
limit. A runner lacking those facilities is unsuitable for the full suite and fails before
generation or a package test can hang or be mistaken for an implementation defect. CI runs the
same command and therefore exercises the same preflight.

`--quick` runs every generator and check and skips the preflight, the package suites and the
integration tests. It runs no package suite at all, so after changing a package run that package's
suite, and those of the packages depending on it, beside it.

`tools/gate.py` wraps that routine and prints one line per step, with the full output in a log
whose path it prints last:

```bash
uv run --project escapewheel-writer python tools/gate.py             # quick
uv run --project escapewheel-writer python tools/gate.py --changed   # quick, plus the touched suites
uv run --project escapewheel-writer python tools/gate.py --full      # preflight, then the full run
```

Quick regenerates the heading record and the single-file rendering, checks citations, the ledger
and the open revision stages, and runs `verify.py --quick`. `--changed [BASE]` adds the suite of
every package differing from BASE (by default the merge-base with `main`, plus uncommitted files)
and of every package depending on one, read from the projects' uv path sources. `--full` stops
with a non-zero exit if the runtime preflight rejects the environment; rerun it unchanged with
unrestricted execution rather than retrying in the same sandbox. `GATE_TMPDIR` or `--tmpdir` sets
`TMPDIR` for every step and holds the log; the caller's `UV_CACHE_DIR` carries through.

## 4.1 Working with large packets

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

## 5. Bootstrapping in order

Nothing here needs doing by hand in normal work — `verify.py` does it — but this is the order, and
the order matters.

1. **`spec/tools/assemble.py`** reads each registry's source directory and writes its document. A
   file uses the published format's keys and differs from the document only in spelling: a
   table's fields sit at the top of its file, a single-column reference is written on its column,
   and a rule may invoke the `interval` template, which is expanded into plain SQL so that the
   registry a packet embeds carries no vocabulary a validator would have to learn. `canonical.py`
   fixes what JSON leaves free — keys in the order `registry.schema.json` declares them,
   single-column references in column order before multi-column ones — so how a file orders them
   changes nothing.

   **Column order is a convention of this registry and not a conformance requirement** — a
   validator resolves a column by name, and no clause of Part 02 or Part 03 states an order — so no
   revision mandates one. Three conventions, each chosen so a reader meets the same shape in every
   table:

   - `session_id` is the first column, being the coarsest scope a row has.
   - a `clock_id` outside the primary key sits beside the coordinates that resolve against it
     (R56 §2.2), so a reader who has found a tick has its clock. Unchecked, because which
     coordinates a clock interprets is the author's judgement.
   - `metadata` is last.

   `spec/tools/conventions.py` holds the first and the last, and the naming conventions, for core
   and every extension.

   Each varies only where the rule says it may — a `clock_id` in the key leads because it is key,
   and a table with no coordinate has nothing to sit beside — so a placement that looks odd is
   one the rule accounts for rather than one nobody decided.
2. **`spec/tools/build.py`** runs `assemble.py`, then `render.py` for `tables.md` and the source
   guide's regions, then refreshes Part 03's and Part 04's projections and the delivery schema.
   **`extensions/registries.py build`** assembles each extension where it sits.
3. **`spec/tools/check.py`** verifies the tree: one complete registry-contract result for core,
   then authoring conventions, source-to-output agreement, each artifact's schema, and the static
   Tier 2 profile. The result is implemented in `spec/tools/checkers/registry_document.py` and the
   three `registry_*` modules it imports (the result model, the invariants and the rule and unit
   phases), which the validator copies, so an extension author and this repository receive the
   same answer.
   **`extensions/registries.py check`** requires the same result of each extension, under the core
   registry's context, with the same conventions. Section 8 counts the descriptor's invariant
   inventory.
4. **Tier 1 checks are never stored.** `escapewheel_validator.generate` derives them from the
   registry at validation time: not-null from `presence`, uniqueness from `primary_key`,
   anti-joins from `references`, membership from `enum`, and two more from each discriminator.
   Changing what Tier 1 means is a code change in `generate.py`, not a data change.
5. **`fixtures/build.py`** writes the conformance corpus against the registry, one packet for
   each record `fixtures/corpus_packets/` declares; `fixtures/corpus.py` runs each through the
   real validator and checks it produced the finding it was built to produce.
6. **`integration/example.py`** commits a small packet with the writer, one resource of each
   kind against every repository extension, and fails where Part 08's layout and manifest excerpt
   differ from it, printing the text Part 08 should carry.

## 6. Changing something

| you want to | edit | then |
|---|---|---|
| add or change a column, key, type, reference | begin with a proposal or draft, then get the revision accepted and edit the table's file in `spec/source/core/` | `verify.py`; `revisions/CONTRIBUTING.md` has the whole sequence |
| add a Tier 2 rule | a `[[rules]]` entry in the table's file | `verify.py` |
| change how Tier 1 is derived | `escapewheel-validator/.../generate.py` | `verify.py` |
| add an extension | a directory `extensions/<id>/` holding `registry.toml` and one file per resource | `extensions/registries.py build extensions`; `verify.py` |
| change the manifest or the meta-schema | the hand-written copy in `spec/artifacts/` | `spec/tools/build.py`, then `tools/copies.py`; `verify.py` |
| change a checker | `spec/tools/checkers/`, with its tests in `spec/tools/tests/` | `tools/copies.py`; `verify.py` |
| add a fixture variant | its subject's module in `fixtures/corpus_packets/`, and `EXPECTED` in `fixtures/corpus.py` | `verify.py` |
| change the packet Part 08 shows | `integration/example.py`, then Part 08's text to match | `verify.py` |

**A schema change starts with a revision.** Not as ceremony: `revisions/registry-targets.toml`
locates each accepted clause in the generated registry, so a declaration traces to the argument
that set it. A declaration changed with no revision breaks that chain silently.

Moving a draft to an accepted revision requires explicit authorization. Acceptance and
incorporation into the applicable current owner are one reviewable change; until it is complete,
the existing v0.2 text and revision-process guide remain authoritative for their respective
subjects.

## 7. Four traps, each of which has actually happened

**Editing `logical_schemas.json` or an extension's `.json`.** The next build overwrites it from its
TOML source. `verify.py`'s candidate-state comparison catches that overwrite, which is why the
comparison exists.

**A stale package copy.** The schemas and checkers are copied into the packages because a wheel
cannot read a file from another distribution. A stale copy has broken every packet three times —
R48, R53 and R56 — and each time it surfaced as a hundred findings about the *data* rather than one
about the copy. `tools/copies.py` writes them and each package's `test_copies.py` compares them, so the
class is closed; do not edit a copy.

**A maintained inventory going stale.** Three records cannot be fully derived from the generated
registry: the table ledger in `conformance/spec-sweep/tables.py`, the naming exceptions in
`spec/tools/conventions.py` and each extension directory's `conventions.toml`, and
`applied.toml`'s clause dispositions. Each fails a check rather than drifting. Every naming
exception must still identify a present declaration that breaks a convention, and the clause ledger
must still name real accepted clauses and existing current owners. What stays a human judgement is
*which* disposition a clause gets.

**A revision clause that never reaches the spec.** Two independent audits found normative clauses
dropped during compilation of the v0.2 prose — `R53 §2.4`'s `int64` escape, `R21`'s codec floor,
`R36 §2.2`'s prefix digest reversed into "undefined". A citation sweep cannot see these, because
the revision is cited for its *other* clauses. `revisions/ledger.py` is what sees them:
`revisions/applied.toml` records each clause's disposition and exact current owner, while
`revisions/registry-targets.toml` resolves exact JSON locations. The check fails while any
accepted clause has no entry. Current owners need not cite their accepted revisions back.

<!-- BEGIN facts: clauses -->
`ledger.py` enumerates 885 Decision clauses across the accepted revisions.
<!-- END facts: clauses -->

## 8. What each check is for

The incorporated registry-contract descriptor enumerates the invariants that apply to core and
extension documents by class. Their algorithms are owned by Parts 02 and 09 and implemented once
in `spec/tools/checkers/registry_invariants.py`, whose one table registers each semantic invariant
with its ID, the universe it resolves names in and whether it needs a usable core;
`escapewheel extension check`,
`spec/tools/check.py` and `extensions/registries.py` consume that complete result. `check.py`
separately adds checks of the tree's other artifacts. `tools/facts.py` counts the descriptor inventory
and those checks:

<!-- BEGIN facts: checks -->
29 registry-contract invariants, applied by class to core and each of the 4 extension registries, and 38 further checks of the specification's tree
<!-- END facts: checks -->

| check | catches |
|---|---|
| `revisions/stages.py` | an open or prospective accepted artifact with invalid lifecycle metadata, missing stage sections, template residue, or no exact draft clause list |
| `revisions/test_evidence.py` | regressions in owner, corpus, verifier-stage, and complete-manifest validation |
| `revisions/evidence.py` | an accepted current-format clause with no owner, projection, conformance evidence, implementation disposition, or documentation disposition |
| `revisions/check_citations.py` and `revisions/repoint.py` | a citation that does not resolve, or implementation source that names a historical decision where the current part owns the rule |
| `revisions/impact.py` | working-tree files citing a changed or explicitly queried specification section or stable anchor |
| `spec/tools/check.py` | a registry that contradicts itself, an artifact failing its schema, a naming convention broken without a declared reason |
| `spec/tools/tests/` | a checker deciding a case differently from the contract it implements |
| `tools/tree.py` | a tree that cannot regenerate itself alone, or a tree tool importing what the tree does not declare |
| `tools/copies.py --check` | a package copy differing from the tree, or a package not admitting the tree's locked library |
| `extensions/registries.py check` | an extension registry failing the contract or the conventions where it sits |
| `conformance/registries/check.py` | a core table set departing from the Part 02 ledger, a Tier 2 rule that does not execute, or a valid rule the reference validator cannot evaluate |
| `fixtures/corpus.py` | a validator that stopped catching what it used to, or started catching what it should not |
| `revisions/ledger.py` | an accepted clause with no disposition or an unresolved current-owner or registry target |
| `spec/tools/build.py --check` | a file `build.py` writes that no longer reproduces its source; `check.py` makes the same comparison of each |
| `spec/tools/columns.py --check` | a column table in a part that no longer reproduces the registry |
| `spec/tools/combine.py --check` | a single-file spec rendering that no longer matches its parts |
| `tools/facts.py` | a count in a root document that no longer matches what it counts |
| `verify.py`'s candidate-state comparison | a stale or hand-edited artifact changed by regeneration |
| the package test suites | asserted reference-implementation behavior outside the checks above |
| `escapewheel-dev/` tests | a development query that no longer reads the current parts, registries, schemas or packets |
| `integration/` | a writer, reader, and validator that disagree with one another, a Part 08 excerpt the writer no longer reproduces, or a Part 08 query that no longer runs |

## 9. Reading the result

No derived count in this repository should be typed by hand. `spec/source/README.md`'s are filled
by `render.py` and the root documents' by `tools/facts.py`. Provenance exceptions are exact
identities, not a count. If you find yourself editing a number, check whether something can compute
it instead: every number that was hand-maintained here went stale, several of them twice in one
day.

`spec/informative/tables.md` is the readable registry: every table, every column, its type,
presence, what it declares about its values, and its description. Read Part 02 and the registry to
see what holds **now**; read the accepted revisions to understand why. `spec/source/README.md`
carries the counts, generated.
