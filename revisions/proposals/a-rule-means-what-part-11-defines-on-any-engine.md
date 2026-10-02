# A rule means what Part 11 defines on any engine

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-10-02 |
| **Based on** | `1f2025b8afff1ab08c7d73d8623b4f646c4df267` |
| **Decision domain** | specification |
| **Affects** | Part 11 §1's requirement that a supporting validator give every rule its defined meaning; Part 11 §4's common-type rules, which name the constructs they govern and name neither `BETWEEN` nor `IN`; Part 11 §8's list of the causes that make a valid rule's evaluation incomplete; Part 05 §9.4, which restates that list; the conformance vectors of the rule language |

## 1. Problem

Part 11 defines the language a registry's Tier 2 rules are written in, and a validator evaluates
each rule on a database engine. Part 11 §1 makes the language's contract every statement of
§§2–8 on the ISO basis it selects, and requires a validator claiming support to give a rule the
meaning those sections define. In three places the reference validator gives a rule its engine's meaning instead,
or could, because Part 11 states the meaning only through its basis or does not state it.

The first is `BETWEEN`. The language descriptor depends on ISO feature E061-02, the `BETWEEN`
predicate, and ISO/IEC 9075 defines `X BETWEEN Y AND Z` as `X >= Y AND X <= Z`: two comparisons,
each taking the common type of its own two operands. Part 11 §4's common-type rules govern
comparisons. Through its basis, then, Part 11 already gives `BETWEEN` the pairwise meaning.
DuckDB, the engine the reference validator uses, converts all three operands to one common type
first, and the reference validator follows the engine, so it departs from the contract today.
What Part 11 lacks is a statement of the meaning in its own text: §4 lists the constructs its rules
govern as "comparisons, `CASE`, `COALESCE`, set operations, and routine arguments", and that list
reads as closed, so a reader cannot tell from Part 11 that `BETWEEN` is two comparisons.

The second is `IN`, which has the same shape. The descriptor depends on E061-03 and E061-11, the
`IN` predicate over a list and over a subquery. ISO/IEC 9075 makes a value list a table value
constructor and defines `IN` as `= ANY` over it. DuckDB converts the left operand and every list
member to one common type, which differs from the ISO meaning for one combination of operands.

The third is what a validator does when its engine cannot evaluate a valid rule as Part 11 defines
it. Part 11 §4 has every exact-to-approximate conversion round once, to nearest with ties to even;
DuckDB 1.5.5 rounds some of them twice, and the reference validator corrects this by converting
such a value through its text. Where it cannot place that conversion in a rule's text, it reports
the rule's evaluation incomplete and does not run it. Part 11 §8 lists the causes that make a valid
rule's evaluation incomplete: an unreadable input, an engine failure, exact overflow, a timestamp
out of range, and a resource or timeout limit. This cause is not among them, so a second validator
could equally run the rule under its engine's semantics, report the registry invalid, or report the
language unsupported. Part 11 §1 sharpens the question: read literally, its requirement that a
supporting validator give every rule its meaning is broken by any incomplete evaluation, a timeout
included.

## 2. Evidence

Observed at the baseline commit, which makes the reference static check reject `BETWEEN SYMMETRIC`
and `BETWEEN ASYMMETRIC` (§2.5); the quick verifier passed all 37 of its stages there. Each probe
below ran on DuckDB 1.5.5 through the reference validator's static profile check and its lowering,
over a one-row table, with each predicate wrapped in a `CASE` that reports `TRUE`, `FALSE` or
`NULL`. The pairwise result is the same query with the predicate written `x >= y AND x <= z`. No
other proposal or draft is open.

### 2.1 One common type and two pairwise comparisons give different results

| case | operands | values | `BETWEEN` as the engine binds it | pairwise |
|---|---|---|---|---|
| A | `x`, `y` `BIGINT`; `z` `DOUBLE PRECISION` | x = 2^53, y = 2^53 + 1, z = 1e300 | `TRUE` | `FALSE` |
| A, negated | the same, `NOT BETWEEN` | the same | `FALSE` | `TRUE` |
| B | `x`, `y` `BIGINT`; `z` `REAL` | x = 2^24, y = 2^24 + 1, z = 1e30 | `TRUE` | `FALSE` |
| C | `x`, `z` `INTEGER`; `y` `REAL` | x = 2^24 + 1, y = z = 2^24 | `TRUE` | `FALSE` |
| D | `x` `BIGINT`; an exact-decimal and an approximate literal | x = 2^53, y = `9007199254740992.5`, z = `1e300` | `TRUE` | `FALSE` |
| E | `x` `BIGINT`; an integer and an approximate literal | x = 2^53, y = `9007199254740993`, z = `1e300` | `TRUE` | `FALSE` |
| F | `x` cast to `DECIMAL(38,0)`; an integer literal; `z` `DOUBLE PRECISION` | x = 2^53, y = `9007199254740993`, z = 1e300 | `TRUE` | `FALSE` |

Each case mixes two exact operands with an approximate one. Pairwise, the comparison between the
two exact operands is exact, and in every case it fails: `x` is below `y` in A, B, D, E and F, and
above `z` in C. Under one common type both exact operands round to the approximate domain first,
become equal, and `x` falls within the bounds. In case D the exact-decimal literal compares with `x`
by mathematical value, as Part 11 §4 requires of an exact-decimal literal compared with an exact
numeric; under one common type it is rounded instead.

### 2.2 Approximate operands alone, and exact operands alone, give the same result

Where all three operands are approximate, converting `REAL` to `DOUBLE PRECISION` is exact, so each
pairwise comparison gives the result one common type would. Two probes agree: a `REAL` `x` of 0.1
between a `DOUBLE PRECISION` 0.1 and a `REAL` 1 gives `TRUE` both ways, and a `DOUBLE PRECISION` 0.1
between two `REAL` bounds of 0.1 and 1 gives `FALSE` both ways.

Where all three operands are exact, the two readings give the same result whenever the engine
completes. It does not always complete. DuckDB compares a `DECIMAL(38,0)` value with the 38-digit
literal `9999999999999999999999999999999999999.5` in that literal's `DECIMAL(38,1)`, which holds no
value of magnitude 10^37 or more: comparing `99999999999999999999999999999999999999` with it fails
with "Conversion Error: … to type DECIMAL(38,1) failed: value is out of range", while the same
comparison of `9999999999999999999999999999999999999` returns the correct `TRUE`. No probe gave a
wrong result. The failure is an engine failure, which Part 11 §8 already makes an incomplete
evaluation.

### 2.3 Both readings keep three-valued logic

| case | values | `BETWEEN` | pairwise |
|---|---|---|---|
| null lower bound, `x` above the upper | x = 5, y = null, z = 1 | `FALSE` | `FALSE` |
| null lower bound, `x` within the upper | x = 5, y = null, z = 10 | `NULL` | `NULL` |
| the first, `NOT BETWEEN` | x = 5, y = null, z = 1 | `TRUE` | `TRUE` |
| null `x` | x = null, y = 1, z = 10 | `NULL` | `NULL` |
| reversed bounds | x = 5, y = 10, z = 1 | `FALSE` | `FALSE` |

The engine evaluates `BETWEEN` as a conjunction under null semantics; only its binding of the
operands differs.

### 2.4 ISO types an `IN` list as a table, and the engine differs in one case

The public working draft of ISO/IEC 9075:1992 (X3H2-92-154/DBL CBR-002, preserved as plain text at
contrib.andrew.cmu.edu/~shadow/sql/sql1992.txt) states the rules this proposal relies on:

- Subclause 8.3, Syntax Rule 6: "X BETWEEN Y AND Z" is equivalent to "X>=Y AND X<=Z", and Syntax Rule 5
  makes `NOT BETWEEN` its negation;
- Subclause 8.4, Syntax Rule 1: `( IVL )` "is equivalent to the <table value constructor>: ( VALUES IVL )";
  Syntax Rule 4: `RVC IN IPV` "is equivalent to `RVC = ANY IPV`"; Syntax Rule 3 makes `NOT IN` its
  negation;
- Subclause 7.2, General Rule 2: a table value constructor's result is that of `T1 UNION ALL T2 …`, one
  single-row table per member, so its column takes the type Subclause 9.3 gives a set operation;
- Subclause 9.3, Syntax Rule 3d: where any type is approximate numeric, the result is approximate numeric
  "with implementation-defined precision".

The 1999 edition, ISO/IEC 9075-2:1999 (a copy is hosted at
web.cecs.pdx.edu/~len/sql1999.pdf), states the same rules with the keyword forms added:

- Subclause 8.3, Syntax Rule 1: where neither `SYMMETRIC` nor `ASYMMETRIC` is specified,
  `ASYMMETRIC` is implicit; Syntax Rule 6: "X BETWEEN ASYMMETRIC Y AND Z" is equivalent to
  "X>=Y AND X<=Z"; Syntax Rule 5 makes the negated form its negation; Conformance Rule 1: without
  Feature T461, conforming SQL language does not specify `SYMMETRIC` or `ASYMMETRIC`;
- Subclause 8.4, Syntax Rules 1, 3 and 4, worded as in 1992;
- Subclause 7.3, Syntax Rule 4: a table value constructor's row type is that Subclause 9.3 gives
  its rows, directly rather than through `UNION ALL`;
- Subclause 9.3, Syntax Rule 3e: where any type is approximate numeric, the result is approximate
  numeric "with implementation-defined precision".

Neither text is ISO/IEC 9075-2:2023, the edition Part 11 §9 selects. No later edition or public
working draft of 2003, 2011, 2016 or 2023 was reachable on 2026-10-02, and no vendor document found
quotes these Syntax Rules from one. Confirming them in 2023 is a promotion criterion (§7).

The ISO precision is implementation-defined, so ISO alone does not fix an `IN` list's type. Part
11 §4 does: its rules govern set operations, and "an exact with an approximate numeric yields the
approximate domain, widened to `DOUBLE PRECISION` if either operand has it". Under ISO's structure
and §4's types, the list takes one type from its members, and `x` is then compared with that type.

| case | operands | values | engine | ISO with Part 11 §4 | `OR` of `=` |
|---|---|---|---|---|---|
| G | `x` `BIGINT`; an integer and an approximate literal | x = 2^53, list (`9007199254740993`, `1e300`) | `TRUE` | `TRUE` | `FALSE` |
| H | `x` `REAL`; two integer literals | x = 2^24, list (`16777217`, `1`) | `TRUE` | `TRUE` | `TRUE` |
| I | `x`, `a` `BIGINT`; `b` `DOUBLE PRECISION` | x = 2^53, list (a = 2^53 + 1, b = 0) | `TRUE` | `TRUE` | `FALSE` |
| J | `x` `DOUBLE PRECISION`; an integer literal and a `REAL` column | x = 16777217, list (`16777217`, r = 0) | `TRUE` | `FALSE` | `TRUE` |

The engine and `OR` of `=` columns are probe results. The ISO column is derived: in G and I the
list takes `DOUBLE PRECISION`, 2^53 + 1 rounds to 2^53, and `x` equals it; in H the list stays
`INTEGER`, and `x` and 16777217 meet in `REAL`, where 16777217 rounds to 16777216; in J the list
takes `REAL` from its `REAL` member, 16777217 rounds to 16777216 there, and `x` then compares with
16777216 in `DOUBLE PRECISION` and is not equal to it. The engine differs from the ISO meaning in J
alone, because it brings `x` into the list's common type and so keeps the list in
`DOUBLE PRECISION`.

### 2.5 The profile already excludes the keyword forms of `BETWEEN`

Part 11 §2 lists its admitted operators, including "`BETWEEN`, `IN`, `LIKE`, `EXISTS`, and their
negated forms", and puts "other engine spellings" outside the profile. ISO's
`BETWEEN SYMMETRIC` and `BETWEEN ASYMMETRIC` are such spellings, and the descriptor lists E061-02
and not T461, symmetric `BETWEEN`. The reference static check nevertheless admitted both; DuckDB
1.5.5 then failed on `SYMMETRIC` with "Not implemented Error: Expression type T_List". The baseline
commit fixes the check as maintenance: it rejects both forms as outside the profile, with two
rejection vectors. No specification question remains.

### 2.6 No shipped rule changes

The five shipped registries declare 139 Tier 2 rules: core 91, `dynamic_foraging` 12,
`vr_foraging` 24, `aind_opto` 1 and `aind_unit_qc` 11. Four of them use `BETWEEN`, six times in
all, and none uses `IN`.

- `core.events.within_observation` and `core.spike_events.within_observation` compare an `int64`
  tick with two `int64` bounds. Every operand is exact, so §2.2 applies.
- `dynamic_foraging.trials.a_probability_is_a_probability` and
  `dynamic_foraging.trials.a_draw_is_a_draw` test four `float64` columns against the integer
  literals 0 and 1. Each comparison pairs a `DOUBLE PRECISION` value with one exact literal, so
  each pair's common type is the one the three operands share.

Of the 44 rule-language conformance vectors, only the two rejection vectors of §2.5 use `BETWEEN`,
and none uses `IN`.

### 2.7 The reference validator already reports an unplaceable conversion incomplete

Where the reference validator cannot place a conversion through text that Part 11 §4 requires, it
reports the rule's evaluation incomplete and does not run it. Its suite asserts both halves: the
queries a conversion cannot be placed in are refused, and a registry rule whose `USING` join
converts a `DECIMAL(38,0)` column to `DOUBLE PRECISION` makes the evaluation incomplete with no
packet finding. The repository's registry check, run over core and every repository extension,
reports such a rule by its ID and reason apart from a broken rule, and accepts an author's own
extension document, so an author learns of it before a packet binds the registry. Run over the
five shipped registries, the reference validator's generation marks 0 of the 139 rules incomplete.

## 3. Desired outcome and constraints

A rule should have one meaning that two conforming validators give it, whatever engine each uses,
and a reader of Part 11 should be able to find that meaning in Part 11. `BETWEEN` and `IN` should
mean what the ISO basis of Part 11 §1 defines. Where an engine cannot give a valid rule that
meaning, the validator should say so through an outcome that neither invents a finding nor charges
the registry with a defect, and Part 11 §1 should not then call the validator nonconforming. The
ISO basis, Part 11 §4's common-type rules, its rounding rule and three-valued logic are preserved;
no shipped rule's result may change.

## 4. Options and tradeoffs

### 4.1 How `BETWEEN` takes its operands' types

- **Keep Part 11's text as it is.** The basis already gives the pairwise meaning, but §4's list
  reads as closed, so a reader or implementer who does not consult the standard can take the
  engine's binding, as the reference validator did.
- **One common type for all three operands,** as DuckDB binds them. This would change the language
  away from its basis, and it rounds a comparison the author wrote exactly: in case D it rounds the
  exact-decimal literal that Part 11 §4 has compare with an exact numeric by value.
- **State the pairwise meaning in Part 11 §4.** This is the preferred direction. `x BETWEEN y AND z`
  means `x >= y AND x <= z`, `x NOT BETWEEN y AND z` means its negation, and §4's common-type and
  rounding rules apply to each comparison, so a comparison between two exact operands converts
  nothing.

The statement adds no meaning the contract lacks; it states in Part 11 what the selected basis
defines. Part 11 §1 requires a changed language contract to take a new language ID, and this
contract does not change, so no new ID is owed. The reference validator's binding is a defect
against the current contract, which a fix to its lowering corrects whatever form this proposal
takes.

The sentence sits in Part 11 §4, beside the one naming the constructs its common-type rules govern.
Part 11 §2 needs no sentence on the keyword forms: its operator list and its exclusion of other
spellings already put them outside the profile, and the static check now enforces it (§2.5). Part
11 §4 carries the canonical anchor `ew-tier-2-type-binding`, so no anchor bootstrap is needed.

### 4.2 How `IN` takes its operands' types

- **One common type for the left operand and every member,** as DuckDB binds them. This departs
  from the basis in case J.
- **An `OR` of `=` comparisons.** This reads most naturally, but it departs from the basis, which
  makes the list a table with one column type, and it changes the result of cases G and I.
- **The ISO meaning, stated in Part 11 §4.** This is the preferred direction. An `IN` value list is
  a table value constructor whose one column takes the type §4's set-operation rule gives its
  members, and `x IN (list)` means `x = ANY` over that column; `x NOT IN (list)` means its negation.
  `x IN (subquery)` compares `x` with the subquery's one column under §4's comparison rule.

The preferred direction has a consequence an author may not expect, and Part 11 would state it
rather than leave it to be discovered: a list's members are typed together before `x` is compared
with them. In case J, `x IN (16777217, r)` is `FALSE` for a `DOUBLE PRECISION` `x` holding
16777217, because the `REAL` member `r` gives the list `REAL`, in which 16777217 is 16777216. The
case needs an exact member, a `REAL` member and a `DOUBLE PRECISION` `x` together; no shipped rule
uses `IN`.

The sentence sits in Part 11 §4 beside the one on `BETWEEN`. Part 11 §2's `IN` sentence, which
admits a non-empty scalar list or a one-column subquery, is unchanged. Like `BETWEEN`, this states
the basis and owes no new language ID.

### 4.3 What a validator reports when it cannot give a rule Part 11's meaning

- **Run the rule with the engine's semantics.** That can report a packet finding Part 11's meaning
  would not produce, or miss one it would, which Part 11 §8 forbids for every other failure to
  evaluate.
- **Report the registry invalid.** Invalidity is a property of the rule, decided by the static
  profile, and this would bind one implementation's limitation to a rule another validator can
  evaluate.
- **Report the language unsupported.** `unsupported` applies to a registry's whole Tier 2
  evaluation and means the validator lacks the language, which it does not; it would also withhold
  every other rule's result.
- **Report that rule's evaluation incomplete.** This is the preferred direction. Part 11 §8 gains
  the cause: a validator that supports the language but cannot evaluate a valid rule with the
  semantics Part 11 defines reports that evaluation incomplete, and does not evaluate it with its
  engine's differing semantics instead. Part 05 §9.5 then composes the verdict as it does for any
  other incomplete evaluation.

Part 11 §1 has to agree with that cause. Two ways to reconcile them:

- **Treat the cause as a limit like a timeout and leave §1 unchanged.** The new cause would then
  stand where every existing cause stands, but §1, read literally, already conflicts with a
  timeout, since a validator that times out gives the rule no meaning; this keeps that conflict for
  every cause.
- **Bind §1's requirement to the evaluations a validator completes.** This is the preferred
  direction. §1 would require a supporting validator to give a rule the meaning §§2–8 define in
  every evaluation it completes, and point to §8 for when an evaluation may end incomplete. It
  repairs the conflict §1 already has with timeouts and resource limits, which the new cause only
  sharpens.

A validator could report incomplete for a rule it could have evaluated. That is conservative: an
incomplete required evaluation cannot support a claim that the registry passed (Part 11 §8 and
Part 05 §9.5), so over-reporting costs a verdict and never produces a false finding. Whether a validator
could have evaluated a rule it reported incomplete is something no tool checks in general, and a
draft would label that part of the obligation unchecked. The other part is checkable: a vector
whose admissible outcomes are the correct finding or an incomplete evaluation, and never the
engine's differing result, fails a validator that runs the rule on its engine's semantics. The
rule-language vectors have no such form yet; a `USING` join between a `DECIMAL(38,0)` column and a
`DOUBLE PRECISION` column, over a value above 2^64 that DuckDB converts to the neighbouring binary64
value, is a candidate whose engine result differs from Part 11's.

### 4.4 Where the list of causes lives

Part 05 §9.4 restates Part 11 §8's causes in its own list. Adding the cause to both keeps two copies
of one fact. Part 05 §9.4 refers to Part 11 §8 for the causes and keeps its own reporting
obligations (§6, question 3).

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose (Part 01) | unchanged: no concept changes |
| logical prose (Part 02), registry meta-schema and declarations | unchanged: no declaration changes, and no rule's result changes (§2.6) |
| declarative rules | unchanged: no shipped rule's result changes (§2.6) and none is marked incomplete (§2.7) |
| rule language (Part 11) | affected: §1 binds its meaning requirement to completed evaluations; §4 states the meaning of `BETWEEN` and of `IN`; §8 gains a cause; §2 and the language descriptor are unchanged, and the language ID with them |
| physical profiles and packet manifest | unchanged: neither concerns rule evaluation |
| validation and import (Part 05) | affected: Part 05 §9.4 refers to Part 11 §8 for the causes |
| extension registries | unchanged: none uses `BETWEEN` with mixed exact and approximate operands, and none uses `IN` |
| reader, writer and adapters | unchanged: none evaluates a rule |
| validator | affected: the lowering gives `BETWEEN` two comparisons, each converting its own operands, and types an `IN` list from its members before comparing; the static check's rejection of the keyword forms is already in the baseline; reporting an unplaceable conversion incomplete is unchanged |
| existing packets | unchanged: no shipped rule's result changes, so no packet needs rebuilding |
| conformance fixtures and tests | affected: execution vectors for cases A, D, F, G, J and the null cases; a new vector form with two admissible outcomes, the correct result or an incomplete evaluation, and one vector in it; validator tests for the lowering |
| revision lifecycle and tooling | unchanged |
| generated publications and documentation | affected: the combined rendering; the validator's README, which lists where it gives the engine a rule other than as authored |

## 6. Open questions

1. **Are `SYMMETRIC` and `ASYMMETRIC` in the profile?** **Resolved 2026-10-02: no.** Part 11 §2
   already excludes them, and the static check's admission of them was a checker defect, fixed as
   maintenance in the baseline commit (§2.5).
2. **Does `IN` get its own rule, and which?** **Answered 2026-10-02: the ISO meaning, settled in
   this change** (§4.2). The alternative, an `OR` of `=` comparisons, departs from the basis.
3. **Does Part 05 §9.4 keep its list?** **Answered 2026-10-02: it refers to Part 11 §8,** which owns
   the causes.

4. **How does Part 11 §1 agree with an incomplete evaluation?** **Answered 2026-10-02: §1's
   requirement applies to the evaluations a validator completes,** and points to §8 for when an
   evaluation may end incomplete (§4.3).
5. **Does Part 11 §2 name the bare `BETWEEN` form?** **Answered 2026-10-02: no.** The static check
   enforces §2's closed operator list, which already puts the keyword forms outside the profile
   (§4.1).

No question that would change the decision is open.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [x] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [ ] The ISO rules §2.4 cites are confirmed in ISO/IEC 9075-2:2023, the edition Part 11 §9 selects.
  Not met: they are confirmed in the 1992 draft and the 1999 edition only. The reviewer authorized
  promotion with this criterion open on 2026-10-02, and the draft states the 2023 reading as an
  unverified basis.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [x] The exact proposal and its final appraisal state are tracked in the current commit.
- [x] The proposal has explicit approval to advance to a revision draft.
