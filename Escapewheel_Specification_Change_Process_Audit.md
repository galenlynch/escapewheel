# Escapewheel Specification Change Process Audit

| | |
|---|---|
| **Status** | Workflow evaluation and implementation handoff |
| **Date** | 2026-09-17 |
| **Baseline** | `a201ef8344844bee0116c84c587c6776c30b268a` |
| **Scope** | Proposals, draft appraisal, acceptance, specification incorporation, generation, conformance, implementation alignment, and monorepo verification |

## Executive assessment

The repository already has unusually strong individual controls: generated registries and column
tables, a clause-disposition ledger, citation resolution and repointing, changed-section impact
search, heading review, structural registry checks, a conformance corpus, package tests, and a
monorepo verifier. The weakness is coordination rather than absence. The controls grew around
specific failures and were presented as a long checklist before acceptance and a long mutation
sequence afterward. They did not form explicit gates with recorded inputs and outputs.

That organization left four important gaps:

1. proposals had promotion criteria but no ordered evaluation procedure;
2. draft appraisal mixed semantic review, data-model review, feasibility, and mechanical checks;
3. acceptance began by numbering the revision before every affected normative and implementation
   surface had been inventoried; and
4. `verify.py` compared generated files with `HEAD`, so it rejected the intentional pre-commit
   generated changes it was meant to verify.

The revised workflow now separates baseline establishment, proposal evaluation, draft appraisal,
acceptance authorization, normative incorporation, regeneration and conformance, implementation
alignment, and atomic closure. At the audited baseline, the remaining high-value work was to make
ledger destinations more precise and to add mechanical coverage between new Decision clauses and
their conformance evidence.

No change in this audit alters the packet contract or the normative v0.2 rules.

### Follow-up implementation status

R120 subsequently replaced reverse corroboration with one-way traceability from each accepted
clause to an exact current owner. The ledger and its registry-target map now live under
`revisions/`; stable anchored Markdown owners replace numeric evidence-owner sections; and current
owners no longer carry revision backlinks merely to satisfy the ledger. The numbered specification
parts and packet contract were unchanged by that process decision.

The follow-up candidate based on checkpoint
`a9edb7c3b8885fbbdb7699927c4c9270ecf783f4` implements the four process improvements identified
after this audit:

1. `registry-targets.toml` gives every registry disposition one or more checked artifact paths and
   RFC 6901 JSON Pointers. `ledger.py` rejects a missing, stale, malformed, or unresolved target and
   rejects the former free-text `where` field on a registry disposition.
2. The then-current `corroboration-exceptions.toml` replaced the numeric uncorroborated-target
   ratchet with exact reviewed triples. R120 later removed that transitional reverse condition and
   the exception file.
3. `revisions/evidence.py` and `revisions/evidence/R<N>.json` map each current-format accepted
   Decision clause to authoritative owners, generated projections, collected conformance evidence,
   implementation paths, and documentation paths or explicit unchanged reasons.
4. CI runs `ci/runtime_capabilities.py` before full verification, proving that its runner can wake
   the asynchronous thread bridge, round-trip Zarr v3, and bind the Arrow Flight Unix-domain
   socket. A runner missing one of these facilities fails in a bounded probe rather than hanging a
   package suite.

## 1. Verifier diagnosis

### 1.1 The apparent silence had two causes

`verify.py` captured every child process and printed only after a stage returned. Python also
buffered the verifier's own output when stdout was a pipe. A long or hung stage therefore looked
like a completely silent verifier.

With unbuffered output, the quick path completed all functional stages in about 12 seconds. The
full path reached the `escapewheel-reader` suite and stopped making progress.

### 1.2 The full-suite stall is in the execution environment

The reader suite reaches `tests/test_resources.py::test_array_opens_a_declared_array`, but the test
body is not the point of the stall. Its fixture hangs in Zarr 3.3.0 while creating the small test
array:

```text
zarr.create_array(...)
  -> zarr.core.sync.sync(...)
  -> concurrent.futures.wait(...)
```

The Zarr event-loop thread is alive in `selectors.select`, while the main thread waits for the
submitted coroutine. A minimal background `asyncio` event-loop test and a minimal
`asyncio.to_thread` test also time out inside this sandbox. The failure therefore precedes
Escapewheel's reader code and reproduces without a packet.

The correct response is not to skip the array test. The verifier now announces a stage before
entering it and bounds each stage, so the failure is named and eventually returned instead of
looking like an indefinite repository hang. The environment-specific failure remains visible.

The writer suite exposes a second sandbox boundary independently: its Flight delivery test cannot
bind the Unix-domain socket requested by PyArrow Flight (`Failed to add port to server`). Running
the suite with `-x` isolates that failure after 77 passing tests. Validator and AIND suites complete
normally. These results distinguish repository failures from two denied or non-waking execution
primitives in this environment; neither test should be weakened to make the sandbox green.

### 1.3 The pre-commit cleanliness rule was wrong

The prior final check asked whether generated paths differed from `HEAD`. A correctly incorporated
revision necessarily changes generated files before it is committed, so the documented pre-commit
command could not pass. The quick verifier demonstrated this: all generators and checks passed,
then the expected proposal-count changes in `STATUS.md`, `TODO.md`, and the specification
publication were reported as failures solely because they were not committed.

The correct invariant is:

> Regeneration preserves the candidate working-tree state.

The verifier now snapshots Git-visible changes under every generated path before running the
generators and compares path content and modes afterward. This distinguishes three cases:

- a correctly regenerated candidate is unchanged and passes;
- a stale candidate gains or changes a generated diff and fails; and
- a hand-edited generated artifact is overwritten and fails.

This is a stronger pre-commit test than comparing with `HEAD`, because it checks reproducibility
without requiring the change to be published first.

## 2. Strengths of the existing system

### 2.1 Authority is not assigned to implementations

The root authority model correctly makes generated v0.2 prose and the incorporated logical
registry authoritative and treats implementations, tests, examples, and revision history as
non-normative. This prevents a reference implementation from silently becoming the standard.

### 2.2 Generation is explicit

The registry, rendered tables, vendored schemas, specification column tables, fact regions, packet
fixtures, and combined publication all have identified generators. Committing derived artifacts
makes contract changes reviewable, while regeneration detects stale copies.

### 2.3 The clause ledger addresses a real failure mode

`applied.toml` and `ledger.py` answer a question citation checking cannot: where did each accepted
Decision clause go? This has already caught clauses dropped or changed during compilation into the
current parts. Retaining this ledger is essential.

### 2.4 Forward and reverse citation checks are separate

`check_citations.py` establishes that a citation resolves. `impact.py` starts from a changed part
section and finds its citers. `repoint.py` detects implementation comments that cite historical
requirements instead of the current part. These are distinct questions and should remain distinct
tools.

### 2.5 Conformance and implementation tests are distinct

The fixture corpus checks packet findings against expected data. Package suites check reference
implementation behavior. The separation is sound: a conformance fixture is not merely a unit test,
and a reference implementation test does not define the packet contract.

## 3. Proposal-stage findings

### 3.1 The prior process had a template but not an evaluation sequence

The proposal template asked for a problem, evidence, alternatives, impact, and promotion criteria.
It did not say in which order to evaluate ownership, abstraction level, overlap, feasibility, and
conformance evidence. As a result, an apparently complete proposal could still be based on a stale
count, assign a fact to the wrong layer, or defer a question that would change its normative result.

The new sequence requires:

1. a full baseline commit;
2. reproduction against the current owner;
3. authority and abstraction classification;
4. a complete surface inventory;
5. overlap and dependency review;
6. alternatives and compatibility analysis;
7. source and structural feasibility probes;
8. a conformance-evidence plan; and
9. an explicit abandon, revise, split, or promote result.

### 3.2 Untracked proposals were outside citation checking

`facts.py` counted an untracked proposal immediately, but `check_citations.py` read accepted
revisions, drafts, and files returned by `git ls-files`. A newly created proposal was therefore
visible in generated project status but absent from citation validation until staged or committed.

The citation, impact, repointing, and fact-discovery tools now use tracked plus untracked,
non-ignored working-tree files. Proposals are also an explicit citation-check input.

### 3.3 Proposal structure is now mechanically checked

`revisions/stages.py` checks that each proposal names a real full baseline commit, has the required
sections and metadata, contains no leftover template instructions, and uses no BCP 14 keyword to
prescribe behavior. This establishes structural readiness only; promotion remains a semantic and
user decision.

## 4. Draft appraisal findings

### 4.1 The old checklist mixed universal and conditional checks

The prior pre-acceptance section interleaved citation review, primary-key reasoning, source
feasibility, measurement hygiene, prose consistency, naming, and historical examples. Each point
was useful, but the list gave no entry criteria, no ordering, and no durable indication of which
checks applied to a particular draft.

The new appraisal has ordered gates:

- freshness;
- normative decision and placement;
- registry/data-model structure;
- feasibility;
- compatibility and migration;
- traceability and evidence; and
- mechanical checks.

Conditional checks sit inside the relevant gate. A draft that changes no registry declaration can
say why the structural declarations are unchanged rather than silently skipping the subject.

### 4.2 Drafts did not enumerate their normative clauses

The historical ledger infers clauses from section positions and BCP 14 keywords. That inference was
already known to be imperfect: a declarative “becomes” can bind without a keyword. The current
draft template puts Decision in §3, while the historical inference treats every §2 subsection as a
decision but treats later sections as binding only when selected keywords occur. A MAY-only or
declarative §3 clause could therefore disappear before the ledger saw it.

New drafts and accepted revisions carry an exact `Decision clauses` metadata field. `stages.py`
checks it against §3 headings, and `ledger.py` uses that exact set for new accepted revisions while
retaining the historical fallback for old documents.

### 4.3 Impact and evidence were free prose

A Consequence section could mention the obvious implementation and omit extensions, schemas,
existing packets, or generated documentation. Passing existing tests would not reveal an omitted
new test.

The draft template now contains a standard surface inventory and a separate conformance and
implementation evidence section. Empty cells are pre-acceptance failures. An unaffected surface
is recorded as unchanged with a reason.

## 5. Acceptance and incorporation findings

### 5.1 One mutation sequence hid distinct responsibilities

The previous sequence moved and numbered the draft, edited registry build code, rules, extensions,
parts, the ledger, headings, and the combined specification, then ran the verifier. It did not
separate:

- approval of the normative decision;
- placement in authoritative owners;
- regeneration of projections;
- creation of conformance evidence; and
- alignment of non-normative implementations.

The revised process treats them as separate phases in one uncommitted atomic candidate. A material
finding returns to draft appraisal and user authorization. The repository does not preserve a
numbered partial decision merely because incorporation had begun.

### 5.2 The sequence did not require every implementation surface

The old sequence named the registry, rules, extensions, parts, and generated specification, but it
did not explicitly require reader, writer, validator, adapters, API documentation, fixtures, and
tests according to the draft's consequences. The final verifier could only run tests that already
existed.

The accepted impact inventory now controls implementation alignment. Each newly observable rule
needs conformance or implementation evidence, or a recorded reason it cannot be executed.

### 5.3 Atomicity was stated but not operationally clear

“Acceptance and incorporation are one reviewable change” was correct, but the guide also said the
clean-tree verifier passed only after the commit. That made it impossible to establish closure
before publication. Candidate-state verification repairs that contradiction: the complete change
can pass before its atomic commit.

## 6. Artifact-by-artifact limitations

### 6.1 `applied.toml` and `ledger.py`

The ledger's direction is correct: accepted Decision clause to normative disposition. Three
limitations remain:

1. historical `registry` dispositions commonly name `registry/logical_schemas.json` as a whole,
   not an exact table, column, reference, or rule;
2. the `uncorroborated` safeguard is a count ratchet, so fixing one old site could mask one new
   uncorroborated site without changing the count; and
3. the ledger does not map a clause to conformance evidence or implementation surfaces.

The first improvement for new revisions is procedural: use the narrowest available registry
location. The stronger follow-up is a structured artifact target, such as a path plus JSON Pointer,
validated by `ledger.py`. The count ratchet should become an explicit allowlist of known
uncorroborated clause/target pairs. Conformance evidence should be recorded separately from
normative disposition so tests do not become authority.

### 6.2 `impact.py`

The tool finds reverse citations, not every semantic dependency. An uncited duplicate statement or
hard-coded implementation assumption remains invisible. The new `--section PART:SECTION` option
allows proposal and draft reviewers to inspect known sections before editing them. The surface
inventory remains necessary for uncited dependencies.

### 6.3 `headings.py`

Recording that a changed heading was reviewed is useful, but it does not establish that every
sentence under it belongs to that subject. Placement remains a semantic review against Part 00's
ownership model.

### 6.4 Registry checks and generated column tables

These strongly protect structural consistency and exact column projections. They do not compare
non-tabular prose semantics with registry fields, and they do not prove that a source adapter can
satisfy a writer obligation. Draft feasibility and ownership review cover those gaps.

### 6.5 Conformance corpus and package suites

The corpus protects expected validator outcomes but has no mechanical one-to-one coverage map from
new Decision clauses. Package suites likewise cover asserted code paths, not every normative rule.
A future change manifest should record, for each new clause, the fixture or test that distinguishes
it or the reason no executable test applies.

### 6.6 `drafts/README.md`

It currently mixes the active application order with long narrative histories of drafts that have
already left. Git and accepted revisions preserve that history. The active section should converge
on a compact table containing slug, baseline, appraisal date, word count, dependencies, and one
material finding; historical narratives can move to a separate archive or be removed in a later
editorial change.

## 7. Implemented workflow changes

This audit produced the following non-normative repository changes:

- explicit phases and gates in `revisions/CONTRIBUTING.md`;
- a complete proposal evaluation sequence;
- ordered draft pre-acceptance gates;
- separate normative incorporation, regeneration/conformance, implementation, and closure phases;
- baseline and exact Decision-clause fields in templates;
- a standard draft impact inventory and evidence section;
- structural checking of open proposals and drafts;
- exact future clause enumeration in the ledger;
- explicit-section queries in `impact.py`;
- working-tree rather than tracked-only discovery in citation and impact tools;
- stage announcements and timeouts in `verify.py`; and
- candidate-state regeneration checks that can pass before commit.

## 8. Recommended follow-up order

### P0 — before accepting the authority proposal

1. Exercise the new process by appraising the open authority proposal from start to finish.
2. Add focused tests for `stages.py`, explicit-section impact queries, and verifier candidate-state
   comparison.
3. Decide whether the environment running CI can execute Zarr's synchronous thread bridge; retain
   the full array test either way.

### P1 — before the next contract-changing revision

4. Add structured registry/schema/rule targets to the clause ledger for new revisions.
5. Replace the numeric uncorroborated ratchet with an exact reviewed allowlist.
6. Add a per-revision change manifest mapping Decision clauses to authoritative owners,
   conformance evidence, implementation packages, generated projections, and documentation.
7. Make verification check that every manifest path exists and every declared evidence identifier
   is collected by its suite.

### P2 — with the authority and publication revision

8. Bind normative artifacts with the proposed specification release manifest.
9. Have the release manifest and change manifest provide the exact owner inventory used by
   publication checks.
10. Replace historical executable registry replay with reviewed declarative current state after a
    byte- or canonical-form-equivalent baseline is frozen.

## 9. Conclusion

The project does not need one omnibus checker that claims to prove agreement. It needs a disciplined
chain in which each artifact answers one question and the gaps are explicit:

```text
baseline
  -> evaluated proposal
  -> appraised draft
  -> user-authorized decision
  -> normative owners
  -> generated projections and conformance evidence
  -> aligned implementations and documentation
  -> reproducible candidate
  -> atomic commit
```

The ledger remains central, but it is one link: it prevents accepted clauses from disappearing into
the revision history. Ownership review prevents clauses from landing in the wrong abstraction.
Generation prevents projections from drifting. Fixtures and tests establish observable behavior.
Impact and citation tools keep downstream statements connected. The verifier orchestrates those
controls without pretending to replace the reviews between them.
