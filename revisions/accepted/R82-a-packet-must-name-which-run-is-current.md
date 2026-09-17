# R82 — A Packet Must Name Which Run Is Current

| | |
|---|---|
| **Status** | **Accepted** 2026-09-05 |
| **Amends** | R41 §2.4 (a consumer MUST NOT silently choose), R44 §2.3 (the undeterminable state), R26 §2 (as applied to two rules) |
| **Depends on** | R41 (currency is not a version), R44 (a run declares its scope), R49 (a scope names its kind), R74 (a commit is a publication) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

### 1.1 Only the writer knows which run is current

R41 §2.4 gives the rule to the consumer: where two runs share an `(activity_type, scope)` and no
preference is declared, a consumer MUST NOT silently choose.

The producer is the one who knows. Someone re-sorted a probe or re-curated it and knows which
result they mean. The consumer meets two sets of units and a specification telling it to refuse, so
every reader of every packet carries handling for a case the writer could have closed at commit.
R74 §2.1 makes a commit a publication, which is the moment where having chosen is what publishing
means.

### 1.2 An advisory rule cannot fail a packet

The checks exist and say the right thing. `core.processing_runs.undeclared_currency` finds runs
sharing an `(activity_type, scope)` with no `core.preferred_runs` row naming one, and
`core.processing_runs.scope_undeclared` finds an activity whose runs do not all declare a scope.

Both are **advisory**. R26 §2 makes an advisory rule off by default and states that it MUST NOT be
`error`, so neither can fail a packet — not by oversight, but by construction. Four of the
registry's 66 Tier 2 rules are advisory and these are two of them.

A writer may therefore produce an unresolved alternative, and the packet passes validation whether
or not anyone enables the rule that noticed.

### 1.3 The rule has misfired twice

**R44 exists because of it.** R41 §2.4 groups runs by activity, twelve probes sorted once each all
share `spike_sorting`, and the rule fired on a packet holding no alternative at all. Every packet
adopting R41 §2.1 became unreadable until `scope` was added.

**R60 is a retraction because of it.** R58 §2.3 reasoned that two histology registrations of one
probe are alternatives R41 arbitrates. The coordinate key admits one row per
`(electrode_id, frame, basis)`, so the second cannot be stored, and the clause had to be withdrawn.

Both cost a revision, and neither packet involved held an alternative.

### 1.4 Every probe has been sorted once

`core.preferred_runs` is **absent from both** measured packets — the table has never been written.
Every `parent_curation_id` is null and every `supersedes_run_id` is null. One session holds 12
sorting runs over 12 probes, the other 10 over 10, and the 27-packet conformance corpus uses a
single sorting run throughout.

Every run in both packets declares a scope: 26 of 26, and 22 of 22. So what §2 asks for costs
nothing on the data that exists.

## 2. Decision

### 2.1 The currency rule becomes an error

`core.processing_runs.undeclared_currency` stops being advisory and becomes a mandatory rule at
level `error`. Where two or more runs share `(session_id, activity_type, scope_kind, scope)`, the
packet MUST carry a `core.preferred_runs` row naming one, and a writer MUST refuse to commit one
that does not.

R26 §2's reasoning does not cover this rule. An advisory rule is one whose enabling "cannot change
whether a packet passed", which is right for a rule expressing a preference about completeness and
wrong for one expressing a defect. Two complete sets of units with nothing saying which is meant is
not an incomplete packet; it is a packet that will be read wrongly.

This is R63's shape applied a level up. A recipe that contradicts itself is refused rather than
built, because the alternative is a defect surfacing ninety seconds into a build as a rule failure
about some other table. An unresolved alternative is the same thing deferred further: it surfaces
in someone's analysis, as two complete sets of units and a count taken over both.

### 2.2 The scope rule becomes an error

`core.processing_runs.scope_undeclared` stops being advisory and becomes a mandatory rule at level
`error`. Where an activity has more than one run in a session, every one of those runs MUST declare
`scope` and `scope_kind`.

That is what makes §2.1 checkable. Without a scope, runs cannot be grouped, so an ambiguity cannot
be found rather than not existing — and a rule that silently matches nothing is the failure R55 §2
was written about. Both columns stay nullable, because a run whose activity nothing shares has
nothing to be confused with.

### 2.3 R41 §2.4 stops firing

The consumer rule stands and becomes unreachable on a conforming packet, because §2.1 makes an
unresolved alternative a validation error. A consumer that meets one is holding a packet that
failed validation and MUST report that, rather than treating it as a state to design around.

The distinction decides what a reader must implement. Refusing an ambiguous read stays correct.
Building an interface around choosing between alternatives at read time does not, because a
conforming packet never presents the choice.

### 2.4 A packet may still hold two sortings

Nothing here forbids two sortings of one probe or two curations of one sorting. Comparing two
sorters on one recording is a real analysis, and R1 makes single-session packets primary while
leaving multi-packet comparison undefined, so in-packet is the only place that comparison can
currently happen. Iterative curation is the same case arriving from the other direction: a merge or
a split produces units the previous pass did not have, and both passes may be worth keeping.

What changes is that the packet says which one is meant. Both stay readable, both stay canonical
(R71 §2.1), and neither is hidden.

## 3. What this does not change

- **No new table, column or rule.** `core.preferred_runs`, `scope`, `scope_kind` and both rules
  already exist. Two rules change level and nothing else is added.
- **No capability is removed.** A packet holding two interpretations stays conforming; it gains an
  obligation to say which is current.
- **No change to R32 or R61.** Versioning the bundle and retaining superseded manifests are a
  different axis, as R41 §1 says: a snapshot cannot express currency because all of the
  alternatives are inside it.
- **No change to R81.** The two compose. R81 makes a second curation cost rows rather than key
  width, and this makes the packet say which curation is meant.
- **No packet becomes invalid.** Both measured packets declare a scope on every run and carry no
  ambiguity, and the conformance corpus carries one sorting run.

## 4. Consequence

**No rule is added.** Two change level, from advisory `info` to mandatory `error`, so the count of
advisory rules goes from four to two and the total is untouched. The SQL of both is unchanged:
they already return exactly the offending rows.

The writer refuses such a commit, which puts the refusal where R63 §2 puts a contradictory recipe.
`escapewheel-reader` keeps `runs.py`'s `ambiguities()` and `preferred_run()`; what changes is that
`check()` becomes a validator's instrument rather than something every accessor runs on the chance
that a packet is ambiguous.

Migration is nothing. No packet carries an unresolved set, and every run in both measured packets
already declares a scope.

## 5. Open

- **Whether the capability should be withdrawn instead.** The stricter reading is that a packet
  holds one interpretation and a second is a second packet, which R32, R61 and R74 already make
  cheap — a rebuild is 306 s and re-reads no external resource. That would withdraw
  `core.preferred_runs` and take core from 34 tables to 33. This revision does not, because
  tightening later costs one revision and no migration while loosening later costs a table, a
  rule, a consumer obligation, and every packet built in between. The evidence for withdrawal is
  that nothing has used it; the evidence against is that merge and split curation is expected and
  is exactly where a second interpretation appears.
- **Whether a curation needs the same rule.** `core.curation_versions` has no `preferred_runs`
  equivalent, and §2.1 constrains `core.processing_runs` rather than curations directly. A curation
  names a `processing_run_id` (R41 §2.1), so the constraint should reach it, and no packet has two
  to test the claim on.
- **Whether `scope_kind` should be required wherever `scope` is.** R49 §2.2 makes the kind what
  resolves a scope to a table, so a scope without one is unresolvable by construction. Both are
  nullable today and both are populated in both packets, so the requirement would cost nothing. It
  is left out because it is R49's question rather than this one's.
