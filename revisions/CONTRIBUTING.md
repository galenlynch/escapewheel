# Contributing specification changes

This guide defines the file-based process for opening, readying, accepting, incorporating, and
verifying a change to the Escapewheel specification. The repository-wide
[authority model](../README.md#authority) applies throughout. The shared
[specification style guide](../spec/CONTRIBUTING.md) governs prose; this guide
governs the change lifecycle. Sections 1 to 13 state its rules, and §14 is guidance that binds no
one.

<a id="ew-revision-scope" data-spec-anchor="canonical"></a>
## 1. Scope

Use this process when a change would alter any of the following:

- what a conforming packet, writer, reader, validator, or consumer is permitted or required to do;
- the meaning of a normative statement;
- which artifact owns a normative fact or how conflicts are resolved;
- the exact contract carried by an incorporated registry, rule set, or JSON Schema; or
- the composition or identity of a specification release.

Use the ordinary repository workflow for developer documentation, agent instructions,
implementation work that follows an unambiguous existing rule, tests and refactoring that do not
change the contract, and meaning-preserving editorial fixes or regeneration.

When classification is uncertain, ask whether two implementations could behave differently after
the change while both conforming before it. If so, use this process.

### 1.1 Changing this guide

This lifecycle is not required for a change to this guide, its templates or its process tools.
Such a change is an ordinary repository commit that the reviewer has approved, and it carries no
change document, revision number, ledger entry or evidence manifest. The same commit updates the
templates, tools, tests and documents that implement or describe the rule it changes. Only the
reviewer may approve a change to this guide.

Where an accepted record's ledger entry names a section of this guide, a commit that changes the
guide keeps that entry resolving. Where the commit moves the rule the entry names, it updates the
entry's destination. Where it removes that rule whole, it gives the entry the `rationale`
disposition. Where it changes the rule only in part, the entry is left as it stands. A guide
section that such an entry names keeps its canonical anchor.

<a id="ew-decision-domains" data-spec-anchor="canonical"></a>

## 2. Change documents, statuses, and gates

A specification change is carried by one change document, at `revisions/changes/<slug>.md`, from
the commit that opens it until its acceptance. Its status is Open or Ready while it is there, and
it moves from Open to Ready by being edited in place. It carries no revision number before
acceptance.

| status | location | the document | authority |
|---|---|---|---|
| Open | `changes/<slug>.md` | states the problem, the evidence, a preferred direction and the questions to answer (§4) | None |
| Ready | `changes/<slug>.md` | has answered its questions and states its Decision, impact inventory and evidence (§5) | None |
| Accepted | `accepted/R<N>-<slug>.md` | preserves the approved decision, evidence, consequences, and provenance (§7) | Historical decision record |

A document of either status is withdrawn by deleting it in a commit whose message records why,
after any finding worth keeping has been committed. Where an accepted record or another document
applies a rule to a proposal, read it as applying to an Open document, and a rule for a revision
draft as applying to a Ready one.

A change document does not declare a `Decision domain`. An accepted record keeps the domain it
declares, and one that declares none is read as `specification`. Records R120 to R166 declare one:
`specification` for a change to the packet contract or an artifact that owns part of it, and
`process` for R120 and R158, which changed this lifecycle and were incorporated into this guide
(§11). Accepted revisions below R120 that lack a domain are read as `specification`, need no change
form, and remain unedited; withdrawn records have no inferred domain and likewise remain unedited.
A process-domain record uses `Profile: not applicable`, `Change form: ordinary`, and one or more
exact repository-relative Markdown `path#anchor` values in `Amends`.

A Ready document and an accepted record from R120 onward declare `Change form: ordinary` or
`Change form: structural`; an Open document does not. `stages.py` rejects a domain in a change
document, an absent or unknown domain in an accepted record from R120 to R166, an unknown domain in
a later one, and an absent or unknown change form wherever the field applies.

The lifecycle has three gates:

1. **Ready:** the document's questions are answered and its Decision is written. No authorization
   other than those answers is required.
2. **Acceptance authorization:** the reviewer explicitly authorizes the document's text for
   incorporation.
3. **Incorporation closure:** every normative owner, generated projection, conformance artifact,
   affected implementation, and document agrees, and verification passes.

These gates are not synonyms. A Ready document accepts no rule. Acceptance does not make a
partially edited working tree authoritative. The generated v0.2 material at the last complete
commit remains authoritative until acceptance and incorporation are committed as one reviewable
change.

Roadmap work-item labels such as `P4.2` are coordination identifiers, not durable lifecycle
references. The roadmap may point to a change document, but a change document must not cite a
roadmap label or depend on roadmap prose. State the actual problem, dependency, or deferred subject
directly; name an accepted revision when it is the dependency. This relationship is one-way so a
lifecycle artifact remains intelligible if the roadmap is reorganized.

<a id="ew-baseline" data-spec-anchor="canonical"></a>
## 3. Phase A — establish the baseline

Every change document records a full `Based on` commit hash: the output of `git rev-parse HEAD`,
not an abbreviated or remembered revision. Read the root authority model, the relevant generated
v0.2 parts, and the machine-readable artifacts those parts incorporate before relying on them.
§14.2 advises on keeping a document fresh against its baseline.

<a id="ew-proposal-evaluation" data-spec-anchor="canonical"></a>
## 4. Phase B — open a change

An Open document is exploratory and non-normative. Start it from the
[change template](templates/change.md). It declares `Status: Open`, the date it was `Opened`, its
full `Based on` commit hash, and in `Affects` the concepts and current locations it affects. Its
sections are, in this order:

1. `Problem`: the problem and the boundary of the change;
2. `Evidence`: the evidence, and the alternatives considered with their costs;
3. `Preferred direction`;
4. `Questions`: the questions that must be answered before the Decision can be stated; and
5. `Consequence`: a sketch of the consequence, with each affected surface marked affected,
   unchanged with a reason, or unknown.

Each question is one numbered item under `Questions`. Its answer is recorded beneath it, in the
same item, beginning `**Answered <date>:`. An Open document does not prescribe behavior with
BCP 14 keywords.

A document may be opened Ready when its problem and direction need no question answered. An Open
document becomes Ready when its questions are answered and its Decision is written (§5). §14.4 is
a checklist for appraising a document at either status.

<a id="ew-draft-writing" data-spec-anchor="canonical"></a>
## 5. Phase C — ready a change

A Ready document declares `Status: Ready`, the date it was `Opened`, its full `Based on` commit
hash, its `Change form`, what it `Amends`, what it `Depends on`, its `Profile`, and its
`Decision clauses`. It keeps the problem, evidence and questions of §4, replaces the preferred
direction with the normative Decision as its section 3, and adds the complete impact inventory and
its conformance and implementation evidence. Its sections are `Problem`, `Evidence`, `Decision`,
`Questions`, `Consequence`, and `Conformance and implementation evidence`, numbered 1 to 6. Every
question carries its recorded answer.

`Decision clauses` enumerates every normative subsection. That exact list is what `ledger.py` will
require someone to place after acceptance; normative force is not inferred from keywords.

When Decision has subsections, its preamble introduces them and carries no independent rule; list
every subsection under §3. When the decision is not subdivided, list §3 itself. This makes the
clause set mechanically complete rather than dependent on keyword inference.

The impact inventory is part of the design, not an implementation afterthought. Each row states
the required change or why the surface is unchanged, and names the evidence expected after
incorporation.

### 5.1 Normative writing

- State which sections are normative and informative.
- Put every obligation in Decision and bind a named actor or an artifact.
- State the replacement rule, not an editing instruction.
- Introduce terms before relying on them and use one term for one concept.
- Name every amended part and section.
- Apply the specification style guide's
  [structure guidance](../spec/CONTRIBUTING.md#6-make-structure-support-lookup):
  use bullets for three or more independently checkable peers under one shared obligation, numbers
  only when order matters, and a table when entries repeat the same attributes; keep interdependent
  logic in prose.
- For a registry declaration, give every affected type, presence, role, identity, vocabulary, key,
  reference, and rule field.
- Keep deferred questions only when either answer leaves the Decision unchanged. Otherwise the
  document is not Ready.

### 5.2 Evidence and consequences

Record how each number was measured, over which population, and against which baseline. Check that
the proposed change does not move items into or out of the population used to justify it. State
compatibility, migration, rebuild, implementation, and release consequences.

A `What this does not change` subsection of Consequence is optional. A denial belongs there only
when the Decision invites the contrary inference, the body has not already answered it, and the
denial is consistent with every Decision clause.

<a id="ew-citation-context" data-spec-anchor="canonical"></a>

### 5.3 Citation context

Cite the current owner for a current rule and an accepted revision only for rationale or
provenance the owner does not carry. A numbered-part citation displays `Part NN §x.y`; once its
target has a stable anchor, a link targets that anchor and its displayed number must agree with the
anchor's current heading. A current process document links to this guide using a document-relative
Markdown `path#anchor`; a source comment or docstring uses the canonical repository-relative
target, such as `revisions/CONTRIBUTING.md#ew-citation-context`, in backticks.

A change document may cite an accepted revision, and may cite another change document by its file
name in backticks. An accepted revision never cites a document that has not been accepted.
Committed accepted revisions are immutable historical records and need not resolve against the
current working specification. Interpret a historical citation from its recorded baseline or
another exact reviewed source tree; do not make that resolution a current conformance gate or
require a current owner to cite the revision back.

<a id="ew-structural-reorganization" data-spec-anchor="canonical"></a>

### 5.4 Ordinary amendments and structural revisions

An ordinary specification change appends a new section at the end of its part or a new subsection
at the end of its containing section. A Ready document may instead declare
`Change form: structural` when moving, splitting, merging, replacing, or retiring material
materially improves ownership, dependency order, or document structure. Its Problem section
explains why append-only placement would impair the specification.

A structural change document contains a human-readable crosswalk for every affected numbered
section and every unnumbered README statement whose normative ownership changes. Each row gives the
old location, disposition, new location, semantic effect, and any Decision clause that changes
meaning. Relocation alone never authorizes a semantic change: every changed rule appears in an
enumerated Decision clause. The crosswalk is reviewed history, not a normative owner or a
machine-readable paragraph inventory.

<a id="ew-pre-acceptance-gates" data-spec-anchor="canonical"></a>
## 6. What the process tools check

The stage check, `stages.py`, fails, naming the document:

- a document under `revisions/changes/` that lacks a field or a section its status requires,
  declares a status other than Open or Ready, declares a decision domain, or carries a revision
  number;
- an Open document that prescribes behavior with a BCP 14 keyword;
- a Ready document with a question that has no answer, or with no Decision section, or whose
  `Decision clauses` do not enumerate exactly the clauses under its section 3; and
- a document under `revisions/proposals/` or `revisions/drafts/`.

The citation check, `check_citations.py`, fails a citation in a change document, or in an accepted
revision that `HEAD` does not yet hold, that does not resolve or does not use the required
spelling. It also fails a citation in an accepted record from R167 onward of a document that has
not been accepted.

The ledger check, `ledger.py`, fails, naming the clause, where a Decision clause of an accepted
revision has no ledger entry, where an entry's disposition is not one of `applied`, `registry`,
`superseded` and `rationale`, and where a destination it names does not resolve (§8.1).

Run them, with the repointing check and the quick verifier, before requesting acceptance:

```bash
uv run --project escapewheel-writer python revisions/stages.py
uv run --project escapewheel-writer python revisions/check_citations.py
uv run --project escapewheel-writer python revisions/repoint.py --quiet
uv run --project escapewheel-writer python verify.py --quick
```

Beyond these checks, the conditions of §§2, 4 and 5 and the reviewer's authorization, no
requirement governs whether a change document may be accepted. The guidance of §14 on appraising
a change, refreshing it against its baseline, ordering it against overlapping work and keeping it
focused is informative.

<a id="ew-structural-reorganization-sequence" data-spec-anchor="canonical"></a>

### 6.1 Structural-reorganization sequence

Before the final appraisal of a structural change document, identify every affected existing source
and destination that lacks a canonical anchor. If any lacks one, make a separate metadata-only
anchor bootstrap commit and use that commit as the document's `Based on`. The bootstrap may insert
only one valid canonical anchor immediately before each identified heading; it may not change
heading text or level, numbering or order, body prose, normativity, meaning, or aliases. A process
check compares that commit with its parent. When no bootstrap is needed, say so in the crosswalk.

After the bootstrap, refresh measurements, impact queries, and citation inventories; complete the
final appraisal; commit the exact document; and request acceptance. The bootstrap commit remains
source-only. In the following refresh checkpoint, regenerate informational projections whose only
change is propagation of the new anchors, before running the mechanical checks. That refresh does
not incorporate the document's substantive decision. Give a new section its anchor when it is
created. Incorporation updates every affected live citation, ledger target, evidence owner, heading
record, generated rendering, and human document atomically. An alias changes only through reviewed
structural work.

<a id="ew-acceptance" data-spec-anchor="canonical"></a>
## 7. Phase D — authorize acceptance and freeze the decision

Only the reviewer may authorize acceptance, and acceptance does not proceed without the reviewer's
explicit authorization of the document's text. After that authorization:

1. Assign the next free `R<N>` from the end of the accepted range and move the document to
   `accepted/R<N>-<slug>.md`.
2. Set `Status` to `Accepted` with the date. Preserve `Based on`, `Decision clauses`, the completed
   impact inventory, and the approved normative text.
3. Copy `templates/change-evidence.json` to `evidence/R<N>.json`. Give every Decision clause a
   record; the destinations and evidence are completed as incorporation proceeds.
4. Replace other change documents' citations of its file name with its revision number, and update
   the order in `changes/README.md`.
5. Do not commit yet. Acceptance and incorporation remain one atomic reviewable change.

An incorporation finding may correct prose or consequences without changing the approved decision.
A later change to a Decision clause, a compatibility effect, a required implementation surface, or
a feasibility claim returns the document to Ready, and acceptance then needs the reviewer's
authorization again. A numbered uncommitted candidate is not published history; do not preserve a
materially changed decision merely because a number was temporarily assigned.

## 8. Phase E — incorporate the normative contract

Work from owners to projections.

<a id="ew-current-owner-ledger" data-spec-anchor="canonical"></a>

### 8.1 Record clause destinations

Add one `applied.toml` entry for every enumerated Decision clause. `ledger.py` recognizes:

- `applied`: the rule is stated in one or more numbered part sections;
- `registry`: the exact declaration or predicate is carried by the incorporated registry;
- `superseded`: a later accepted revision replaced the clause whole; and
- `rationale`: the clause makes no current normative decision.

The ledger lives at `revisions/applied.toml`. An `applied` destination has exactly one of these
forms:

```toml
{ part = "02", section = "7.1" }
{ part = "02", anchor = "ew-session-scope" }
{ path = "revisions/CONTRIBUTING.md", anchor = "ew-decision-domains" }
```

`part` and `path` are mutually exclusive, as are `section` and `anchor`. A new process destination
uses `path` plus `anchor` and resolves to a process owner in this guide. A structurally affected
specification destination migrates to `part` plus `anchor`; untouched numeric targets may remain.
For a `registry` disposition, add the
repository-relative JSON artifact path and narrowest RFC 6901 JSON Pointer to
`revisions/registry-targets.toml`. Use multiple targets where the clause changes
multiple declarations. A pointer to a containing table or collection is appropriate only when the
clause governs the whole declaration or records a removal that has no child to point at. The ledger
resolves every pointer and requires an equality guard when the path traverses an array, so a reorder
cannot silently retarget it. It does not prove the declaration is semantically faithful, so the
incorporation review still reads both.

A `superseded` entry must carry `by`, one string naming an accepted revision as `R<N>`, and that
revision must be numbered later than the revision of the entry's own clause. The entry must not
carry `where`:

```toml
[clause."R29 §2.1"]
disposition = "superseded"
by = "R77"
```

`ledger.py` fails, naming the clause, where a `superseded` entry:

- carries no `by`;
- carries a `by` that is not one string of the form `R<N>`;
- names a revision that no accepted record states;
- names a revision numbered no later than the clause's own; or
- carries `where`.

A clause that a later revision replaced only in part is not `superseded`; its entry keeps the
disposition of the part that remains and names no later clause. The part's current text and its
history say what changed it.

A ledger entry or destination recorded for a clause of R167 or a later revision carries no `note`,
and `ledger.py` fails one that does. A later revision leaves an existing entry unchanged unless it
supersedes that entry's clause whole or moves the clause's rule to a destination the entry does not
name. A note that an existing entry carries is not maintained, and a stale one is left as it
stands.

The ledger must not record a count of undisposed clauses. `ledger.py` fails where any Decision
clause of an accepted revision has no entry, and it writes neither the ledger nor any other file.

### 8.2 Update each authoritative owner

Apply the decision to every affected owner identified in the impact inventory:

- numbered prose for meaning, processing semantics, actor obligations, and conformance;
- the registry's TOML sources for exact logical declarations and their rules;
- registry or packet meta-schemas for exact document structure;
- extension registries for extension declarations; and
- physical-profile or packet-manifest parts for profile-specific storage and manifest behavior.

State each fact once. Where another artifact needs it, generate or mechanically compare the
projection.

Place prose by subject. A profile-dependent rule belongs in the physical profile; a
profile-independent logical declaration belongs in Part 02; a concept meaning belongs in Part 01.
Apply the ordinary or structural rule in §5.4 when adding or reorganizing sections.

### 8.3 Sweep changed sections

After editing parts, run:

```bash
uv run --project escapewheel-writer python revisions/impact.py
```

Read every listed citer and update stale assumptions. Repoint citations of superseded revision
clauses. If a heading changes or a section is added, run `headings.py` and review its citer list.

<a id="ew-stable-section-anchors" data-spec-anchor="canonical"></a>

### 8.4 Stable section anchors

Every numbered section structurally affected as a source or destination has one canonical stable
anchor immediately before its heading:

```html
<a id="ew-content-classes" data-spec-anchor="canonical"></a>
```

An affected section is one whose prose, heading, level, number, or order changes, or which is
added, split, merged, replaced, or retired. Untouched sections may remain unanchored. Anchor IDs
use lowercase ASCII letters, digits, and hyphens. Canonical and alias IDs are unique in the
combined specification. A section of this guide that an `Amends` target, ledger destination,
evidence owner, or citation names carries an anchor of the same canonical form, and process
anchors are unique in this document. A moved subject preserves
its canonical ID even if its wording becomes less descriptive.

A replaced or split section may put a former ID beside one honest primary successor as an alias:

```html
<a id="ew-layer-model" data-spec-anchor="alias"></a>
```

Do not give a retired subject a misleading alias. `headings.toml` retains its numeric records and
adds a partial index for explicitly anchored numbered sections, recording the canonical ID's part,
section, title, and aliases. Process anchors resolve directly and do not enter that index. The
heading checker rejects malformed, duplicate, missing, or unreviewedly reassigned anchors; human
review decides crosswalk completeness and whether an alias names an honest successor. The impact
tool accepts an anchor and reports its current heading and live citers.

## 9. Phase F — regenerate projections and add conformance evidence

Follow the generation order in the root [contribution guide](../CONTRIBUTING.md#4-bootstrapping-in-order).
In particular:

1. Generate the registry, rendered tables, packages' copies, marked fact regions, column tables,
   and combined specification from their sources.
2. Add positive and negative conformance fixtures for every newly decidable rule.
3. Add expected findings to the corpus rather than relying on an unasserted validator run.
4. Verify extension registries under every new invariant that applies to registry documents.
5. Complete `evidence/R<N>.json`: map every clause to its owners, projections, conformance
   evidence, implementations, and documentation. Use an explicit unchanged or not-applicable
   reason instead of an empty list.
6. Inspect generated diffs. A generator producing an unexpected change is a finding, not noise.

Markdown owners use exact `path` plus `anchor`; JSON owners use exact `path` plus RFC 6901
`pointer`. Generated files are never edited directly.

## 10. Phase G — align implementations and human documentation

Update each implementation surface named by the accepted impact inventory:

- writer and adapters for production obligations and source feasibility;
- validator for generated and non-SQL checks;
- reader for resolution and interpretation obligations;
- extension tooling and packaged registries; and
- reference APIs, examples, and developer documentation.

Tests cite the owning part where the connection would otherwise be unclear. Implementation code
does not become authority by implementing the rule. A passing pre-existing suite is evidence only
for behavior it asserts; add a test or record why a requirement is not executable.

Run the affected package suites before the monorepo verifier so a failure is localized.


<a id="ew-process-incorporation-boundary" data-spec-anchor="canonical"></a>

## 11. Phase H — close drift and publish atomically

A process-domain revision, R120 or R158, was incorporated into this guide and its process tools,
templates, ledger, evidence, and human documentation; it generated no process prose into a
numbered part and changed no packet-contract owner. A later change to this guide is an ordinary
commit (§1.1).

The ledger, registry-target map, and checker live under `revisions/`. The ledger proves one-way
traceability from accepted clause to disposition to an existing current owner. It does not require
the owner to cite its revision back and does not claim semantic fidelity merely because a target
exists.

Run the focused checks, then the complete verifier:

```bash
uv run --project escapewheel-writer python revisions/check_citations.py
uv run --project escapewheel-writer python revisions/evidence.py
uv run --project escapewheel-writer python revisions/repoint.py --quiet
uv run --project escapewheel-writer python revisions/repoint.py --exempt
uv run --project escapewheel-writer python revisions/ledger.py
uv run --project spec/tools python spec/tools/headings.py --check
uv run --project escapewheel-writer python verify.py
```

`verify.py` snapshots the intentional candidate diffs before generation. It fails if a generator
changes that candidate, which catches stale or hand-edited output while allowing a correct
pre-commit change to pass. Inspect any generated change and rerun. It prints a stage before entering
it and applies a per-stage timeout; use `--stage-timeout 0` only when an intentionally long stage
has another monitor.

Commit the accepted revision, normative owners, ledger, generated projections, conformance
evidence, implementation, and documentation together. A partial commit can make the repository
internally inconsistent even when the next commit repairs it.

<a id="ew-mechanical-artifacts" data-spec-anchor="canonical"></a>
## 12. What each mechanical artifact establishes

| artifact or check | establishes | does not establish |
|---|---|---|
| `stages.py` | Change documents have the fields and sections their status requires, an Open one prescribes nothing with a BCP 14 keyword, a Ready one answers every question and enumerates its Decision clauses, and no document is left under `proposals/` or `drafts/`. | The change is wise or its Decision is semantically coherent. |
| `test_evidence.py` | The evidence checker continues to resolve prose and JSON owners, corpus findings, verifier stages, and complete manifests. | Any particular revision supplied adequate evidence. |
| `check_citations.py` | Citations resolve and use the required spelling, and an accepted record from R167 onward cites no document that has not been accepted. | The target supports the claim. |
| `repoint.py` | Implementation requirement citations name current parts rather than historical decisions. | Every requirement has an implementation or test. |
| `impact.py` | Files citing a changed section are discoverable. | Uncited consumers or duplicated facts agree. |
| `revisions/applied.toml`, `registry-targets.toml`, and `ledger.py` | Every accepted Decision clause has a disposition, every named current owner or registry target resolves, and no entry from R167 onward carries a note. | Semantic fidelity, or any need for the current owner to cite the revision back. |
| `evidence/R<N>.json` and `evidence.py` | Every current-format accepted clause maps to owners and downstream surfaces; for a revision not yet committed, paths and pointers resolve and named fixtures and pytest nodes are collected. | Evidence becomes authority, or the named test proves more than it asserts. |
| `headings.py` | Section numbering and changed heading subjects were deliberately reviewed. | The body belongs under that heading. |
| `columns.py` | Embedded column tables reproduce the registry. | Non-tabular prose agrees with the registry. |
| registry checks | Registry documents are structurally self-consistent and declared SQL is executable. | An adapter can produce every required fact or prose gives the declaration the same meaning. |
| conformance corpus | Known positive and negative packets produce their expected findings. | Every normative clause has a fixture. |
| package tests | Asserted reference-implementation behavior remains true. | The reference implementation defines conformance. |
| `verify.py` | The above tools run in order and generation preserves the candidate state. | Human ownership, placement, compatibility, and citation-meaning review occurred. |

The gaps in the third column are review responsibilities. Do not describe a checker as proving more
than it observes.

<a id="ew-failure-handling" data-spec-anchor="canonical"></a>
## 13. Failure handling

A failed check is a result. Stop advancing the lifecycle, record what it showed, and return to the
earliest affected phase:

- a mistaken problem statement returns the document to Open;
- a changed decision, compatibility cost, or feasibility claim returns it to Ready and the
  reviewer's authorization;
- a missing projection, fixture, implementation, or document remains in incorporation;
- a stale generated artifact is regenerated and reviewed; and
- an environment-specific test failure is isolated and reported with the exact command and stack,
  never relabeled as a pass.

Do not weaken a check or add an exception solely to make a candidate pass.
An exception records why the general rule does not apply and is checked to remain necessary.

<a id="ew-change-guidance" data-spec-anchor="canonical"></a>
## 14. Guidance

This section is informative and binds no one. It collects the working practice that helps a change
reach acceptance in good shape.

### 14.1 Appraise a Ready document before asking for acceptance

Appraise the Ready text critically and report the findings before requesting acceptance. Present
the reviewer with the exact document, its compatibility effects, deferred work, impact inventory,
and check results, so the authorization covers a text whose weaknesses are known.

### 14.2 Keep a document fresh against its baseline

- Run `uv run --project escapewheel-writer python verify.py --quick` at the baseline to establish
  that the generators, registries, corpus, citations, and current candidate state agree. Record a
  known environment failure explicitly rather than treating it as a pass.
- Preserve unrelated working-tree changes. The baseline hash identifies committed authority; note
  any additional working state on which the evidence depends.
- Recheck the baseline when another revision is incorporated. Rerun counts and measurements
  against the new state rather than copying them forward.
- Before asking for acceptance, confirm that the `Based on` commit is still the relevant baseline
  and that the document still describes the current authoritative rule accurately.

### 14.3 Order overlapping work

Read every open change document touching the same owner, and search accepted revisions for the
rule's provenance. If another change touches the same owner, establish their order before relying
on counts, keys, section text, or test results, and name the order in each. For known part
sections, list reverse citations with:

```bash
uv run --project escapewheel-writer python revisions/impact.py \
  --section 02:7.1 --section 05:8
```

Record whether the work depends on, supersedes, conflicts with, or should be split from another
change. Re-measure after any dependency lands.

### 14.4 An appraisal checklist

**The problem.** State the current behavior from the authoritative part, registry, schema, or rule
that owns it. Give a reproducible packet, declaration, query, measurement, or contradiction.
Distinguish a fact observed in the baseline from an inference about its cause.

**Ownership and abstraction.** Identify:

- whether the issue is semantic, logical, physical, manifest, validation/import, publication, or
  implementation-only;
- the artifact that currently owns each affected fact;
- the numbered part and subject where a prose rule belongs;
- whether core, an extension, analysis, or an adapter-specific source path is affected; and
- whether the apparent conflict is a normative disagreement, stale generated view, stale
  implementation, or misplaced duplicate statement.

Do not propose a precedence rule where one artifact is simply stale. A fact gets one owner; other
representations are checked projections. Each rule sits at the abstraction level and in the part
that owns its subject, and no duplicate statement creates a second owner.

**Every surface.** The consequence marks each of these affected, unchanged with a reason, or
unknown; a Ready inventory has no empty cell and no unknown whose answer could change the Decision:

- semantic prose;
- logical prose, registry meta-schema, registry declarations, and declarative rules;
- physical profiles;
- packet manifest and other incorporated JSON Schemas;
- validation and import;
- extension registries;
- reader, writer, validator, adapters, and code generation;
- existing packets and migration or regeneration;
- conformance fixtures and implementation tests;
- revision lifecycle, ledger, evidence, and process tooling; and
- generated publications and developer documentation.

**The Decision.** Problem, Decision, Consequence, and deferred work agree with one another. Each actor
can tell exactly what it owes, and each conformance claim is decidable at the stated boundary.

**Declarations.** Where the change touches declarations:

- every column has type, presence, role, and any required identity or vocabulary fields;
- primary keys admit every row the prose says can coexist;
- foreign keys target a unique compatible key and both sides agree in type and role;
- extension registries obey the same applicable registry invariants as core;
- naming and integer conventions are applied to the proposed declarations; and
- a declared validation rule names only data guaranteed present when it executes.

**Feasibility.** Before stating a writer obligation, identify the source data that can satisfy it
or state that no source currently can. Before asserting that rows coexist or are distinguishable,
write out the primary and foreign keys. Before assigning a fact to JSON Schema, a registry, or a
declared rule, confirm that the chosen form can express it without hiding semantics in annotations
or code. Reader and validator obligations are implementable from information the packet exposes,
and a required algorithm defines its inputs, outputs, failure behavior, and numerical boundaries. A
small implementation probe is appropriate where the change relies on a library, storage property,
or performance claim not already established; it does not change the contract and does not
substitute for normative text.

**Alternatives and compatibility.** Compare the current design and each credible alternative at the
abstraction level it changes, and reject an alternative for a concrete cost or failure. Treat
packet-shape, behavior, and interpretation compatibility separately; make regeneration, migration,
or version changes explicit; consider existing extensions and adapters, not only core and the
reference writer; and state the burden on independent implementations. Prefer the smallest
decision that leaves one coherent contract.

**Traceability and evidence.** Each Decision clause has a planned authoritative landing or a
justified registry, superseded, or rationale disposition. Superseded clauses and their downstream
citations are listed for repointing. Name the positive and negative cases that would distinguish
the rule from the current one, what the validator can decide, what remains a writer or reader
obligation, and what requires an implementation test or measurement rather than a packet fixture.
Name implementation changes and tests by package or surface; an existing suite is not assumed to
cover a new rule merely because it passes.

### 14.5 Read every citation for meaning

The citation check proves that a citation resolves and is spelled correctly. Read each one as well:
a resolved section can still say the wrong thing.

### 14.6 Record the appraisal

Record an appraisal's date, baseline, word count, dependency order, and material finding where the
reviewer will read it, such as the report requesting acceptance or the commit that revises the
document after it. `changes/README.md` keeps only each document's order and placement.

### 14.7 Commit the exact text before asking for acceptance

Commit the exact document before requesting acceptance, and confirm that both commands succeed:

```bash
git ls-files --error-unmatch revisions/changes/<slug>.md
git diff --quiet HEAD -- revisions/changes/<slug>.md
```

The acceptance-and-incorporation change then moves the document, and its parent commit preserves
the exact text the reviewer authorized.

<a id="ew-length-and-focus" data-spec-anchor="canonical"></a>

### 14.8 Length and focus

A revision is a decision record, not a transcript. Retain the evidence on which the decision
depends, the material rejected alternative, the normative decision, and the actual cost. Split a
change when independent decisions can be accepted separately. Do not split two decisions when each
would leave an unusable or contradictory contract without the other.
