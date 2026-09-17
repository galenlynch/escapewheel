# Contributing specification changes

This guide defines the file-based process for proposing, appraising, accepting, incorporating, and
verifying a change to the Escapewheel specification. The repository-wide
[authority model](../README.md#authority) applies throughout. The shared
[specification style guide](../escapewheel_poc_docs_v0.2/CONTRIBUTING.md) governs prose; this guide
governs the change lifecycle.

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

## 2. Artifacts and gates

The lifecycle has three authored artifacts and three separate gates:

| artifact | location | purpose | authority |
|---|---|---|---|
| proposal | `proposals/<slug>.md` | Establish the problem, ownership, evidence, alternatives, impact, and questions. | None |
| revision draft | `drafts/<slug>.md` | State one candidate decision and its incorporation and evidence plan. | None |
| accepted revision | `R<N>-<slug>.md` | Preserve the approved decision, evidence, consequences, and provenance. | Historical decision record |

The gates are:

1. **Proposal promotion:** the problem, scope, ownership, and direction are settled well enough to
   write candidate normative text.
2. **Acceptance authorization:** the user approves the exact appraised draft and authorizes its
   incorporation.
3. **Incorporation closure:** every normative owner, generated projection, conformance artifact,
   affected implementation, and document agrees, and verification passes.

These gates are not synonyms. Promotion does not accept a rule. Acceptance does not make a
partially edited working tree authoritative. The generated v0.2 material at the last complete
commit remains authoritative until acceptance and incorporation are committed as one reviewable
change.

Only the user authorizes acceptance. A proposal or draft carries no `R<N>`.

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

- whether the issue is semantic, logical, physical, catalog, validation/import, publication, or
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
- packet catalog and other incorporated JSON Schemas;
- validation and import;
- extension registries;
- reader, writer, validator, adapters, and code generation;
- existing packets and migration or regeneration;
- conformance fixtures and implementation tests; and
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

Promotion carries the surviving facts into a draft and deletes the proposal in the same change.
Git retains the superseded discussion.

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

### 5.3 Citation discipline

Cite the current part for a current rule and an accepted revision only for rationale or provenance
the part does not carry. A draft may cite an accepted revision. An accepted revision never cites a
proposal or draft. No specification-change artifact cites an instruction or contribution guide.

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
`drafts/README.md`. Present the user with the exact draft, compatibility effects, deferred work,
impact inventory, and check results. Only then request acceptance authorization.

## 7. Phase D — authorize acceptance and freeze the decision

After explicit user authorization:

1. Assign the next free `R<N>` and move the draft to `R<N>-<slug>.md`.
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

### 8.1 Record clause destinations

Add one `applied.toml` entry for every enumerated Decision clause. `ledger.py` recognizes:

- `applied`: the rule is stated in one or more numbered part sections;
- `registry`: the exact declaration or predicate is carried by the incorporated registry;
- `superseded`: a later accepted revision replaced the clause; and
- `rationale`: the clause makes no current normative decision.

Use structured part and section targets for `applied`. For a `registry` disposition, add the
repository-relative JSON artifact path and narrowest RFC 6901 JSON Pointer to
`escapewheel_poc_docs_v0.2/registry-targets.toml`. Use multiple targets where the clause changes
multiple declarations. A pointer to a containing table or collection is appropriate only when the
clause governs the whole declaration or records a removal that has no child to point at. The ledger
resolves every pointer and requires an equality guard when the path traverses an array, so a reorder
cannot silently retarget it. It does not prove the declaration is semantically faithful, so the
incorporation review still reads both.

### 8.2 Update each authoritative owner

Apply the decision to every affected owner identified in the impact inventory:

- numbered prose for meaning, processing semantics, actor obligations, and conformance;
- registry build sources and rule sources for exact logical declarations;
- registry or packet meta-schemas for exact document structure;
- extension registries for extension declarations; and
- physical-profile or packet-catalog parts for profile-specific storage and catalog behavior.

State each fact once. Where another artifact needs it, generate or mechanically compare the
projection.

Place prose by subject. A profile-dependent rule belongs in the physical profile; a
profile-independent logical declaration belongs in Part 02; a concept meaning belongs in Part 01.
Append new sections or subsections so existing citations retain their numbers.

### 8.3 Sweep changed sections

After editing parts, run:

```bash
uv run --project escapewheel-writer python revisions/impact.py
```

Read every listed citer and update stale assumptions. Repoint citations of superseded revision
clauses. If a heading changes or a section is added, run `headings.py` and review its citer list.

## 9. Phase F — regenerate projections and add conformance evidence

Follow the generation order in the root [contribution guide](../CONTRIBUTING.md#4-bootstrapping-in-order).
In particular:

1. Generate the registry, rendered tables, vendored schemas, marked fact regions, column tables,
   and combined specification from their sources.
2. Add positive and negative conformance fixtures for every newly decidable rule.
3. Add expected findings to the corpus rather than relying on an unasserted validator run.
4. Verify extension registries under every new invariant that applies to registry documents.
5. Complete `evidence/R<N>.json`: map every clause to its owners, projections, conformance
   evidence, implementations, and documentation. Use an explicit unchanged or not-applicable
   reason instead of an empty list.
6. Inspect generated diffs. A generator producing an unexpected change is a finding, not noise.

Generated files are never edited directly.

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

## 11. Phase H — close drift and publish atomically

Run the focused checks, then the complete verifier:

```bash
uv run --project escapewheel-writer python revisions/check_citations.py
uv run --project escapewheel-writer python revisions/evidence.py
uv run --project escapewheel-writer python revisions/repoint.py --quiet
uv run --project escapewheel-writer python revisions/repoint.py --exempt
uv run --project escapewheel-writer python escapewheel_poc_docs_v0.2/ledger.py
uv run --project escapewheel-writer python escapewheel_poc_docs_v0.2/headings.py --check
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
| `applied.toml`, `registry-targets.toml`, and `ledger.py` | Every accepted Decision clause has a disposition; every registry disposition resolves to exact JSON locations; missing provenance matches an exact reviewed exception. | The destination is semantically faithful. |
| `evidence/R<N>.json` and `evidence.py` | Every current-format accepted clause maps to owners and downstream surfaces; paths and pointers resolve; named fixtures and pytest nodes are collected. | Evidence becomes authority, or the named test proves more than it asserts. |
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
