# Developing

How the registry, its schemas, the rules and the validators fit together, and what to run when
you change one.

The process feels byzantine for one reason: **most of what looks like source is output.**
`logical_schemas.json` is committed, readable, and edited by nobody. `tables.md` is a document
generated from it. Two schemas are copied into two other packages by a build step. Once you know
which files a person writes, the rest is a straight line.

## 1. What a person writes

| file | what it is |
|---|---|
| `nwb_lake_poc_docs/02_core_logical_schemas.md` | the **frozen** starting point. Never edited, including to fix errors |
| `revisions/R<N>-*.md` | every change to the schema since, as an argued document |
| `registry/build.py` | one block per revision, applying it to the parsed `02` |
| `registry/rules.json` | Tier 2 rules — the checks structure cannot imply |
| `registry/registry.schema.json` | the meta-schema a registry document validates against |
| `registry/manifest.schema.json` | the JSON Schema for `packet.json` |
| `registry/extensions/*.json` | extension registries, in the same format, hand-written |
| `escapewheel-validator/.../generate.py` | how Tier 1 checks are derived from structure |

Everything else in `registry/` is output.

## 2. What a machine writes

```
nwb_lake_poc_docs/02_…md ──parse02.py──┐
registry/build.py  (revision blocks) ──┼──> registry/logical_schemas.json
registry/rules.json (+ R24 templates) ─┘         │
                                                 ├──render.py──> registry/tables.md
                                                 └──render.py──> registry/README.md (marked regions)

registry/registry.schema.json ──build.py──> escapewheel-validator/src/…/schemas/
registry/manifest.schema.json ──build.py──> escapewheel-reader/src/…/schemas/
```

`logical_schemas.json`, `tables.md`, the README's generated regions, and the two vendored schema
copies are **build artifacts that happen to be committed**. They are committed because a packet
embeds the registry and a reviewer should see it change; they are not files to edit.

The whole thing regenerates from the frozen spec plus code: delete `logical_schemas.json` and
`tables.md`, run `python build.py`, and both come back byte-identical. `verify.py` asserts exactly
that on every run — regenerate, then demand a clean git tree — which is the check that catches a
committed artifact drifting from the code that produces it.

## 3. The one command

```bash
python verify.py            # every generator and every check, ~25 s
python verify.py --quick    # skip the test suites
```

Run it before committing anything that touches the registry, a rule, a fixture, or a generator.
CI runs the same command.

## 4. Bootstrapping in order

Nothing here needs doing by hand in normal work — `verify.py` does it — but this is the order, and
the order matters.

1. **`parse02.py`** reads the frozen `02` and returns its tables as structure. This is the only
   thing that ever reads `02`.
2. **`build.py`** applies each accepted revision's block, in revision order, to that structure.
   Each block sets `SINCE[0] = "R<N> §<x>"` first, which stamps every column it creates or amends
   (R29) *and* records that the revision was applied, so `derived_from` cannot omit it.
3. **`build.py`** runs the two passes that apply a rule rather than one revision's decision, after
   every block so that both see the final primary keys: R97 §3.1 emits a `metadata` column wherever
   the key decides it and strikes one where the key forbids it, and `session_id` moves to the front
   of every table carrying it.

   **Column order is a convention of this registry and not a conformance requirement** — a
   validator resolves a column by name, and no clause of `02` or `03` states an order — so no
   revision mandates one and `check.py` is what holds it. Three conventions, each chosen so a
   reader meets the same shape in every table:

   - `session_id` is the first column, being the coarsest scope a row has. Placed by the pass
     above, so a revision cannot leave a new table out.
   - a `clock_id` outside the primary key sits beside the coordinates that resolve against it
     (R56 §2.2), so a reader who has found a tick has its clock. Not placed automatically: which
     coordinates a clock interprets is the revision's decision, so `check.py` reports a stranded
     one rather than guessing where to move it.
   - `metadata` is last, which follows from the R97 §3.1 pass appending it.

   Each varies only where the rule says it may — a `clock_id` in the key leads because it is key,
   and a table with no coordinate has nothing to sit beside — so a placement that looks odd is
   one the rule accounts for rather than one nobody decided.
4. **`build.py`** merges `rules.json`, expanding any R24 template invocation into plain SQL —
   templates are a build-time device, so the registry a packet embeds carries no vocabulary a
   validator would have to learn.
5. **`build.py`** writes `logical_schemas.json`, then calls `render.py` for `tables.md` and the
   README's regions, then copies the two hand-written schemas into the validator and the reader.
6. **`check.py`** verifies the result: the structural invariants, each applied to core and to
   every extension registry, then the meta-schema, the naming conventions, and — with DuckDB
   present — that every Tier 2 rule is executable SQL against empty tables built from the
   registry. Section 7 counts them.
7. **Tier 1 checks are never stored.** `escapewheel_validator.generate` derives them from the
   registry at validation time: not-null from `presence`, uniqueness from `primary_key`,
   anti-joins from `references`, membership from `enum`, and two more from each discriminator.
   Changing what Tier 1 means is a code change in `generate.py`, not a data change.
8. **`fixtures/build.py`** writes the 26-packet conformance corpus against the registry;
   `fixtures/corpus.py` runs each through the real validator and checks it produced the finding
   it was built to produce.

## 5. Changing something

| you want to | edit | then |
|---|---|---|
| add or change a column, key, type, reference | write a revision, get it accepted, add a block to `build.py` | `verify.py`; `revisions/CLAUDE.md` has the whole sequence |
| add a Tier 2 rule | `registry/rules.json` | `verify.py` |
| change how Tier 1 is derived | `escapewheel-validator/.../generate.py` | `verify.py` |
| add an extension | `registry/extensions/<id>.json` | `verify.py` |
| change the manifest or the meta-schema | the hand-written copy in `registry/` | `build.py` re-vendors; `verify.py` |
| add a fixture variant | `fixtures/build.py` and `fixtures/corpus.py` | `verify.py` |

**A schema change starts with a revision.** Not as ceremony: `build.py`'s blocks are labelled with
the revision that mandates them, so a column's type traces to the argument that set it, and
`registry/tables.md` answers both what a table is and why. A block with no revision breaks that
chain silently.

Only the user moves a revision from Proposed to Accepted.

## 6. Four traps, each of which has actually happened

**Editing `logical_schemas.json`.** The next `build.py` overwrites it. `verify.py`'s clean-tree
stage catches this, which is why that stage exists.

**A stale vendored schema.** `registry.schema.json` and `manifest.schema.json` are copied into two
other packages because a wheel cannot read a file from another repository. A stale copy has broken
every packet three times — R48, R53 and R56 — and each time it surfaced as a hundred findings
about the *data* rather than one about the copy. `build.py` writes them and `check.py` compares
them, so the class is closed; do not edit a vendored copy.

**A ledger going stale.** Four lists track the registry and cannot be fully derived from it:
`derived_from` in `build.py`, the R9 §2 table ledger in `conformance/spec-sweep/tables.py`, the
`NAMING_EXCEPTIONS` in `check.py`, and `applied.toml`'s dispositions. Every one now fails a check
rather than drifting: `derived_from` is verified in **both** directions (each accepted revision
appears, and nothing appears that is not accepted — the missing direction is what let R54, R65 and
R66 be applied and left out for several revisions each), each naming exception is checked to still
break a convention, and the clause ledger is checked for entries naming clauses that no longer
exist. What stays a human judgement is *which* disposition a clause gets, which is the part that
should be.

**A revision clause that never reaches the spec.** Two independent audits found normative clauses
dropped during compilation of the v0.2 prose — `R53 §2.4`'s `int64` escape, `R21`'s codec floor,
`R36 §2.2`'s prefix digest reversed into "undefined". A citation sweep cannot see these, because
the revision is cited for its *other* clauses. `escapewheel_poc_docs_v0.2/ledger.py` is what
sees them: `applied.toml` records where each clause went, and the count of undisposed ones may
fall and must not rise.

<!-- BEGIN facts: clauses -->
`ledger.py` enumerates 468 Decision clauses across the accepted revisions.
<!-- END facts: clauses -->

## 7. What each check is for

How many there are is counted from the source that holds them, by `facts.py` parsing `check.py`:

<!-- BEGIN facts: checks -->
28 structural invariants, each applied to core and to each of the 4 extension registries, and 38 further checks over the whole set
<!-- END facts: checks -->

| check | catches |
|---|---|
| `registry/check.py` | a registry that contradicts itself, a rule naming a removed column, a stale vendored copy, a naming convention broken without a declared reason |
| `fixtures/corpus.py` | a validator that stopped catching what it used to, or started catching what it should not |
| `escapewheel_poc_docs_v0.2/ledger.py` | an accepted clause with nowhere recorded that it went |
| `combine.py --check` | a single-file spec rendering that no longer matches its parts |
| `facts.py` | a count in a root document that no longer matches what it counts |
| `verify.py`'s clean-tree stage | a committed artifact that is not what the code produces |
| the three test suites | everything else |

## 8. Reading the result

No count in this repository should be typed by hand. `registry/README.md`'s are filled by
`render.py`, the root documents' by `facts.py`, and the clause ledger's high-water mark lowers
itself. If you find yourself editing a number, check whether something can compute it instead:
every number that was hand-maintained here went stale, several of them twice in one day.

`registry/tables.md` is the readable registry: every table, every column, its type, presence,
role, unit, and the revision that introduced it. Read it to see what a table is **now**; read `02`
plus the revisions to see **why**. `registry/README.md` carries the counts, generated.
