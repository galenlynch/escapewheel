# Contributing specification changes

This guide defines the file-based process for proposing, appraising, accepting, incorporating, and
verifying a change to the Escapewheel specification. The repository-wide
[authority model](../README.md#authority) applies throughout. The shared
[specification style guide](../spec/CONTRIBUTING.md) governs prose; this guide
governs the change lifecycle.

## 1. Scope

Use this process when a change would alter any of the following:

- what a conforming packet, writer, reader, validator, or consumer is permitted or required to do;
- the meaning of a normative statement;
- which artifact owns a normative fact or how conflicts are resolved;
- the exact contract carried by an incorporated registry, rule set, or JSON Schema; or
- the composition or identity of a specification release; or
- a lifecycle gate, process authority, structural-editing permission, ledger disposition, or
  evidence meaning defined by this guide.

Use the ordinary repository workflow for developer documentation, agent instructions,
implementation work that follows an unambiguous existing rule, tests and refactoring that do not
change the contract, and meaning-preserving editorial fixes or regeneration.

When classification is uncertain, ask whether two implementations could behave differently after
the change while both conforming before it. If so, use this process.

<a id="ew-decision-domains" data-spec-anchor="canonical"></a>

## 2. Decision domains, artifacts, and gates

Every lifecycle artifact declares one `Decision domain`:

- `specification` changes the packet contract or an artifact that owns part of it; and
- `process` changes this lifecycle, its authority, structural-editing permission, ledger
  semantics, or evidence meaning.

Both domains use this lifecycle and the same `R<N>` incorporation sequence. A process decision's
current owner is this guide; acceptance makes its revision a historical record, not a second
owner. The former editing-procedure material in Part 00 has been retired, so this guide is the sole
current owner of repository-change procedure.

Proposals, drafts, and accepted revisions declare `Decision domain`. Drafts and accepted revisions
also declare `Change form: ordinary` or `Change form: structural`; a proposal does not. A
process-domain draft uses `Profile: not applicable`, `Change form: ordinary`, and one or more exact
repository-relative Markdown `path#anchor` values in `Amends`. A specification-domain artifact
uses the existing profile and part-or-artifact forms. Accepted revisions below R120 that lack a
domain are interpreted as `specification`, need no change form, and remain unedited; withdrawn
records have no inferred domain. Every open artifact and every artifact created or promoted from
R120 onward declares its applicable fields.

The lifecycle has three authored artifacts and three separate gates:

| artifact | location | purpose | authority |
|---|---|---|---|
| proposal | `proposals/<slug>.md` | Establish the problem, ownership, evidence, alternatives, impact, and questions. | None |
| revision draft | `drafts/<slug>.md` | State one candidate decision and its incorporation and evidence plan. | None |
| accepted revision | `accepted/R<N>-<slug>.md` | Preserve the approved decision, evidence, consequences, and provenance. | Historical decision record |

The gates are:

1. **Proposal promotion:** the problem, scope, ownership, and direction are settled well enough to
   write candidate normative text.
2. **Acceptance authorization:** the exact appraised draft is approved for incorporation.
3. **Incorporation closure:** every normative owner, generated projection, conformance artifact,
   affected implementation, and document agrees, and verification passes.

These gates are not synonyms. Promotion does not accept a rule. Acceptance does not make a
partially edited working tree authoritative. The generated v0.2 material at the last complete
commit remains authoritative until acceptance and incorporation are committed as one reviewable
change.

Acceptance requires explicit authorization. A proposal or draft carries no `R<N>`.

Roadmap work-item labels such as `P4.2` are coordination identifiers, not durable lifecycle
references. The roadmap may point to a proposal or draft, but a proposal or draft must not cite a
roadmap label or depend on roadmap prose. State the actual problem, dependency, or deferred subject
directly; name an accepted revision when it is the dependency. This relationship is one-way so a
lifecycle artifact remains intelligible if the roadmap is reorganized.

## 3. Phase A — establish the baseline

Every proposal and draft records a full `Based on` commit hash. Before evaluating it:

1. Read the root authority model, the relevant generated v0.2 parts, and the machine-readable
   artifacts those parts incorporate.
2. Record `git rev-parse HEAD`, not an abbreviated or remembered revision.
3. Run `uv run --project escapewheel-writer python verify.py --quick` to establish that the
   generators, registries, corpus, citations, and current candidate state agree. A known
   environment failure is recorded explicitly; it is not silently treated as a pass.
4. Inventory open proposals and drafts. If another change touches the same owner, establish their
   order before relying on counts, keys, section text, or test results.
5. Preserve unrelated working-tree changes. The baseline hash identifies committed authority;
   the appraisal notes any additional working state on which its evidence depends.

Recheck the baseline when another revision is incorporated. Counts and measurements are rerun
against the new state rather than copied forward.

## 4. Phase B — evaluate a proposal

A proposal is exploratory and non-normative. Use the proposal template and evaluate it in this
order.

### 4.1 Reproduce the problem

State the current behavior from the authoritative part, registry, schema, or rule that owns it.
Give a reproducible packet, declaration, query, measurement, or contradiction. Distinguish a fact
observed in the baseline from an inference about its cause.

### 4.2 Classify ownership and abstraction

Identify:

- whether the issue is semantic, logical, physical, manifest, validation/import, publication, or
  implementation-only;
- the artifact that currently owns each affected fact;
- the numbered part and subject where a prose rule belongs;
- whether core, an extension, analysis, or an adapter-specific source path is affected; and
- whether the apparent conflict is a normative disagreement, stale generated view, stale
  implementation, or misplaced duplicate statement.

Do not propose a precedence rule where one artifact is simply stale. A fact gets one owner; other
representations are checked projections.

### 4.3 Inventory every surface

The proposal's impact sketch marks each of these affected, unchanged with a reason, or unknown:

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

An unknown is acceptable in a proposal, but it remains a promotion blocker when its answer could
change the decision.

### 4.4 Scan overlap and dependencies

Read every open proposal and draft touching the same owner. Search accepted revisions for the rule's
provenance. For known part sections, list reverse citations with:

```bash
uv run --project escapewheel-writer python revisions/impact.py \
  --section 02:7.1 --section 05:8
```

Record whether the work depends on, supersedes, conflicts with, or should be split from another
change. Re-measure after any dependency lands.

### 4.5 Compare alternatives and compatibility

Compare the current design and each credible alternative at the abstraction level it changes.
State packet compatibility, migration or regeneration, release-version impact, and the burden on
independent implementations. Prefer the smallest decision that leaves one coherent contract.

### 4.6 Probe feasibility

Before promoting a writer obligation, identify the source data that can satisfy it or state that no
source currently can. Before asserting that rows coexist or are distinguishable, write out the
primary and foreign keys. Before assigning a fact to JSON Schema, a registry, or a declared rule,
confirm that the chosen form can express it without hiding semantics in annotations or code.

A small implementation probe is appropriate when feasibility is uncertain. It does not change the
contract and does not substitute for normative text.

### 4.7 Define the conformance evidence

Name the positive and negative cases that would distinguish the proposed rule from the current
one. Identify what the validator can decide, what remains a writer or reader obligation, and what
requires an implementation test or measurement rather than a packet fixture.

### 4.8 Choose a disposition

The result is one of:

- abandon the proposal because the current contract already answers it;
- revise it because the problem or evidence is incomplete;
- split it because independent decisions or unresolved compatibility questions were combined; or
- promote it because every item in the template's promotion criteria is satisfied and the user
  agrees to drafting.

Run the open-stage and citation checks before promotion:

```bash
uv run --project escapewheel-writer python revisions/stages.py
uv run --project escapewheel-writer python revisions/check_citations.py
```

Before promotion, the exact proposal being promoted must exist in the current commit. Check both
that the path is tracked and that its bytes agree with `HEAD`:

```bash
git ls-files --error-unmatch revisions/proposals/<slug>.md
git diff --quiet HEAD -- revisions/proposals/<slug>.md
```

If either command fails, commit the completed proposal and its appraisal or coordination updates
before changing its stage. Promotion authorization is not permission to discard an uncommitted
proposal state. The promotion change then carries the surviving facts into a draft and deletes the
proposal. Its parent commit preserves the exact proposal that reviewers authorized for promotion.

## 5. Phase C — write and appraise a revision draft

A draft states one candidate decision. It uses the draft template, keeps the proposal's baseline or
records a newer one, and enumerates every normative subsection in `Decision clauses`. That exact
list is what `ledger.py` will require someone to place after acceptance; normative force is not
inferred from keywords.

When Decision has subsections, its preamble introduces them and carries no independent rule; list
every subsection under §3. When the decision is not subdivided, list §3 itself. This makes the
clause set mechanically complete rather than dependent on keyword inference.

The draft's impact inventory is part of the design, not an implementation afterthought. Each row
states the required change or why the surface is unchanged, and names the evidence expected after
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
  draft is not ready.

### 5.2 Evidence and consequences

Record how each number was measured, over which population, and against which baseline. Check that
the proposed change does not move items into or out of the population used to justify it. State
compatibility, migration, rebuild, implementation, and release consequences.

`What this does not change` is optional. A denial belongs there only when the Decision invites the
contrary inference, the body has not already answered it, and the denial is consistent with every
Decision clause.

<a id="ew-citation-context" data-spec-anchor="canonical"></a>

### 5.3 Citation context

Cite the current owner for a current rule and an accepted revision only for rationale or
provenance the owner does not carry. A numbered-part citation displays `Part NN §x.y`; once its
target has a stable anchor, a link targets that anchor and its displayed number must agree with the
anchor's current heading. A current process document links to this guide using a document-relative
Markdown `path#anchor`; a source comment or docstring uses the canonical repository-relative
target, such as `revisions/CONTRIBUTING.md#ew-citation-context`, in backticks.

A draft may cite an accepted revision. An accepted revision never cites a proposal or draft.
Committed accepted revisions are immutable historical records and need not resolve against the
current working specification. Interpret a historical citation from its recorded baseline or
another exact reviewed source tree; do not make that resolution a current conformance gate or
require a current owner to cite the revision back.

<a id="ew-structural-reorganization" data-spec-anchor="canonical"></a>

### 5.4 Ordinary amendments and structural revisions

An ordinary specification-domain draft appends a new section at the end of its part or a new
subsection at the end of its containing section. A specification-domain draft may instead declare
`Change form: structural` when moving, splitting, merging, replacing, or retiring material
materially improves ownership, dependency order, or document structure. Its Scope explains why
append-only placement would impair the specification.

A structural draft contains a human-readable crosswalk for every affected numbered section and
every unnumbered README statement whose normative ownership changes. Each row gives the old
location, disposition, new location, semantic effect, and any Decision clause that changes
meaning. Relocation alone never authorizes a semantic change: every changed rule appears in an
enumerated Decision clause. The crosswalk is reviewed history, not a normative owner or a
machine-readable paragraph inventory.

## 6. Draft pre-acceptance gates

Appraise a draft in the following order. A later gate does not excuse an earlier failure.

### 6.1 Freshness gate

- The `Based on` commit exists and remains the relevant baseline.
- Every measurement and count has been rerun.
- Overlapping proposals and drafts are named and ordered.
- The draft still describes the current authoritative rule accurately.

### 6.2 Decision gate

- Scope, Decision, Consequence, and deferred work agree with one another.
- Every `Decision clauses` entry exists under §3 and every normative subsection is listed.
- Each rule is placed at the abstraction level and in the part that owns its subject.
- No duplicate statement creates a second owner.
- Each actor can tell exactly what it owes and each conformance claim is decidable at the stated
  boundary.

### 6.3 Structural gate

Where the draft changes declarations:

- every column has type, presence, role, and any required identity or vocabulary fields;
- primary keys admit every row the prose says can coexist;
- foreign keys target a unique compatible key and both sides agree in type and role;
- extension registries obey the same applicable registry invariants as core;
- naming and integer conventions are applied to the proposed declarations; and
- a declared validation rule names only data guaranteed present when it executes.

### 6.4 Feasibility gate

- Every writer obligation identifies a source field or explicitly records the current absence of
  one.
- Reader and validator obligations are implementable from information the packet exposes.
- Required algorithms define inputs, outputs, failure behavior, and numerical boundaries.
- A feasibility probe has been run where the draft relies on a library, storage property, or
  performance claim not already established.

### 6.5 Compatibility and migration gate

- Packet-shape, behavior, and interpretation compatibility are treated separately.
- Required regeneration, migration, or version changes are explicit.
- Existing extensions and adapters are considered, not only core and the reference writer.
- Rejected alternatives are rejected for a concrete cost or failure.

### 6.6 Traceability and evidence gate

- The impact inventory has no empty cell.
- Each Decision clause has a planned authoritative landing or a justified registry, superseded, or
  rationale disposition.
- Superseded clauses and their downstream citations are listed for repointing.
- Positive and negative conformance cases are named.
- Implementation changes and tests are named by package or surface; an existing test suite is not
  assumed to cover a new rule merely because it passes.

### 6.7 Mechanical gate

Run:

```bash
uv run --project escapewheel-writer python revisions/stages.py
uv run --project escapewheel-writer python revisions/check_citations.py
uv run --project escapewheel-writer python revisions/repoint.py --quiet
uv run --project escapewheel-writer python verify.py --quick
```

Then read every citation, not merely whether it resolves. A resolved section can still say the
wrong thing.

Record the appraisal date, baseline, word count, dependency order, and material finding in
`drafts/README.md`. Present reviewers with the exact draft, compatibility effects, deferred work,
impact inventory, and check results. Before requesting acceptance authorization, commit that exact
appraised draft and confirm that both commands below succeed:

```bash
git ls-files --error-unmatch revisions/drafts/<slug>.md
git diff --quiet HEAD -- revisions/drafts/<slug>.md
```

Only then request acceptance authorization. The acceptance-and-incorporation change may remove the
draft because its parent commit preserves the exact candidate the user reviewed.

<a id="ew-structural-reorganization-sequence" data-spec-anchor="canonical"></a>

### 6.8 Structural-reorganization sequence

Before the final appraisal of a structural draft, identify every affected existing source and
destination that lacks a canonical anchor. If any lacks one, make a separate metadata-only anchor
bootstrap commit and use that commit as the draft's `Based on`. The bootstrap may insert only one
valid canonical anchor immediately before each identified heading; it may not change heading text
or level, numbering or order, body prose, normativity, meaning, or aliases. A process check compares
that commit with its parent. When no bootstrap is needed, say so in the crosswalk.

After the bootstrap, refresh measurements, impact queries, and citation inventories; complete the
final appraisal; commit the exact draft; and request acceptance. The bootstrap commit remains
source-only. In the following draft-refresh checkpoint, regenerate informational projections whose
only change is propagation of the new anchors, before running the mechanical gates. That refresh
does not incorporate the draft's substantive decision. Give a new section its anchor when it is
created. Incorporation updates every affected live citation, ledger target, evidence owner, heading
record, generated rendering, and human document atomically. An alias changes only through reviewed
structural work.

## 7. Phase D — authorize acceptance and freeze the decision

After explicit acceptance authorization:

1. Assign the next free `R<N>` and move the draft to `accepted/R<N>-<slug>.md`.
2. Set `Status` to `Accepted` with the date. Preserve `Based on`, `Decision clauses`, the completed
   impact inventory, and the approved normative text.
3. Copy `templates/change-evidence.json` to `evidence/R<N>.json`. Give every Decision clause a
   record; the destinations and evidence are completed as incorporation proceeds.
4. Replace citations of the draft slug with its revision number and update the draft order.
5. Do not commit yet. Acceptance and incorporation remain one atomic reviewable change.

An incorporation finding may correct prose or consequences without changing the approved decision.
If it changes a Decision clause, compatibility effect, required implementation surface, or claimed
feasibility, return the file to Draft and obtain renewed approval. A numbered uncommitted candidate
is not published history; do not preserve a materially changed decision merely because a number was
temporarily assigned.

## 8. Phase E — incorporate the normative contract

Work from owners to projections.

<a id="ew-current-owner-ledger" data-spec-anchor="canonical"></a>

### 8.1 Record clause destinations

Add one `applied.toml` entry for every enumerated Decision clause. `ledger.py` recognizes:

- `applied`: the rule is stated in one or more numbered part sections;
- `registry`: the exact declaration or predicate is carried by the incorporated registry;
- `superseded`: a later accepted revision replaced the clause; and
- `rationale`: the clause makes no current normative decision.

The ledger lives at `revisions/applied.toml`. An `applied` destination has exactly one of these
forms, with `note` as its only optional additional field:

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
combined specification; process anchors are unique in this document. A moved subject preserves
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

A process-domain revision incorporates into this guide and its process tools, templates, ledger,
evidence, and human documentation; it does not generate process prose into a numbered part. A
process incorporation changes no packet-contract owner unless its Decision explicitly contains a
separately appraised specification-domain change.

The ledger, registry-target map, and checker live under `revisions/`. The ledger proves one-way
traceability from accepted clause to disposition to an existing current owner. It does not require
the owner to cite its revision back and does not claim semantic fidelity merely because a target
exists. `prototype/release-bundle/probe.py` is a non-writing experiment that includes
`revisions/applied.toml` in one candidate inventory; it is not publication machinery and produces
no tracked release snapshot.

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

## 12. What each mechanical artifact establishes

| artifact or check | establishes | does not establish |
|---|---|---|
| `stages.py` | Open documents have the required status, baseline, sections, and explicit draft clause list. | The proposal is wise or the draft is semantically coherent. |
| `test_evidence.py` | The evidence checker continues to resolve prose and JSON owners, corpus findings, verifier stages, and complete manifests. | Any particular revision supplied adequate evidence. |
| `check_citations.py` | Citations resolve and use the required spelling. | The target supports the claim. |
| `repoint.py` | Implementation requirement citations name current parts rather than historical decisions. | Every requirement has an implementation or test. |
| `impact.py` | Files citing a changed section are discoverable. | Uncited consumers or duplicated facts agree. |
| `revisions/applied.toml`, `registry-targets.toml`, and `ledger.py` | Every accepted Decision clause has a disposition and every named current owner or registry target resolves. | Semantic fidelity, or any need for the current owner to cite the revision back. |
| `evidence/R<N>.json` and `evidence.py` | Every current-format accepted clause maps to owners and downstream surfaces; for a revision not yet committed, paths and pointers resolve and named fixtures and pytest nodes are collected. | Evidence becomes authority, or the named test proves more than it asserts. |
| `headings.py` | Section numbering and changed heading subjects were deliberately reviewed. | The body belongs under that heading. |
| `columns.py` | Embedded column tables reproduce the registry. | Non-tabular prose agrees with the registry. |
| registry checks | Registry documents are structurally self-consistent and declared SQL is executable. | An adapter can produce every required fact or prose gives the declaration the same meaning. |
| conformance corpus | Known positive and negative packets produce their expected findings. | Every normative clause has a fixture. |
| package tests | Asserted reference-implementation behavior remains true. | The reference implementation defines conformance. |
| `verify.py` | The above tools run in order and generation preserves the candidate state. | Human ownership, placement, compatibility, and citation-meaning review occurred. |

The gaps in the third column are review responsibilities. Do not describe a checker as proving more
than it observes.

## 13. Failure handling

A failed gate is a result. Stop advancing the lifecycle, record what it showed, and return to the
earliest affected phase:

- a mistaken problem statement returns to the proposal;
- a changed decision, compatibility cost, or feasibility claim returns to draft appraisal and user
  authorization;
- a missing projection, fixture, implementation, or document remains in incorporation;
- a stale generated artifact is regenerated and reviewed; and
- an environment-specific test failure is isolated and reported with the exact command and stack,
  never relabeled as a pass.

Do not weaken a check, raise a ledger ratchet, or add an exception solely to make a candidate pass.
An exception records why the general rule does not apply and is checked to remain necessary.

## 14. Length and focus

A revision is a decision record, not a transcript. Retain the evidence on which the decision
depends, the material rejected alternative, the normative decision, and the actual cost. Split a
draft when independent decisions can be accepted separately. Do not split two decisions when each
would leave an unusable or contradictory contract without the other.
