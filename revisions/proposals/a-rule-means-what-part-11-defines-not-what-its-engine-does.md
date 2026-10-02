# A rule means what Part 11 defines, not what its engine does

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-10-02 |
| **Based on** | `64edc896cc77a4a2c685e053618c02389dbee633` |
| **Decision domain** | specification |
| **Affects** | Part 11 §2's admission of `BETWEEN` and its negated form; Part 11 §4's common-type rules, which name the constructs they govern and not `BETWEEN`; Part 11 §8's list of the causes that make a valid rule's evaluation incomplete; Part 05 §9.4, which restates that list; the conformance vectors of the rule language |

## 1. Problem

Part 11 defines the language a registry's Tier 2 rules are written in, and a validator evaluates
each rule on a database engine. Two places in Part 11 leave the meaning of a rule to whatever the
engine does.

The first is `BETWEEN`. Part 11 §2 admits `BETWEEN` and `NOT BETWEEN`, and Part 11 §4 gives the
common type of two numeric operands. §4 says its rules "govern comparisons, `CASE`, `COALESCE`,
set operations, and routine arguments", and `BETWEEN` has three operands, so Part 11 does not say
which pairs take a common type. ISO/IEC 9075-2, the basis Part 11 §1 selects, defines
`x BETWEEN y AND z` as `x >= y AND x <= z`: two comparisons, each taking the common type of its own
two operands. DuckDB, the engine the reference validator uses, converts all three operands to one
common type first. The two readings give different results for a row, and the reference validator
follows the engine.

The second is what a validator does when its engine cannot evaluate a valid rule as Part 11
defines it. Part 11 §4 has every exact-to-approximate conversion round once, to nearest with ties
to even; DuckDB 1.5.5 rounds some of them twice, and the reference validator corrects this by
converting such a value through its text. Where it cannot place that conversion in a rule's text,
it reports the rule's evaluation incomplete and does not run it. Part 11 §8 lists the causes that
make a valid rule's evaluation incomplete: an unreadable input, an engine failure, exact overflow,
a timestamp out of range, and a resource or timeout limit. It does not list this one, so a second
validator could equally run the rule under the engine's semantics, report the registry invalid, or
report the language unsupported.

Both gaps concern the same thing: whether a rule means what Part 11 says or what an engine does.

## 2. Evidence

Observed at the baseline commit, where the quick verifier passed all 37 of its stages. Each probe
below ran on DuckDB 1.5.5 through the reference validator's static profile check and its lowering,
over a one-row table, with each predicate wrapped in a `CASE` that reports `TRUE`, `FALSE` or
`NULL`. The pairwise result is the same query with the predicate written out as `y <= x AND
x <= z`, which every engine evaluates as two comparisons. No other proposal or draft is open.

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

Each case mixes an exact pair with an approximate operand. Pairwise, the exact pair compares
exactly and `x` is less than `y`. With one common type, the exact operands round to the approximate
domain first, `x` and `y` become equal, and `x` lies within the bounds. In case D the exact-decimal
literal compares with `x` by mathematical value, as Part 11 §4 requires of an exact-decimal literal
compared with an exact numeric; under one common type it is rounded instead.

### 2.2 Approximate operands alone, and exact operands alone, never differ

Where all three operands are approximate, converting `REAL` to `DOUBLE PRECISION` is exact, so each
pairwise comparison gives the result one common type would. Two probes agree: a `REAL` `x` of 0.1
between a `DOUBLE PRECISION` 0.1 and a `REAL` 1 gives `TRUE` both ways, and a `DOUBLE PRECISION` 0.1
between two `REAL` bounds of 0.1 and 1 gives `FALSE` both ways. Where all three operands are
exact, every exact widening preserves the value, so the readings agree as well. They differ only
where an exact operand meets another exact operand and an approximate one.

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

### 2.4 The static check admits `BETWEEN SYMMETRIC`, and the engine cannot run it

ISO/IEC 9075-2 also defines `BETWEEN SYMMETRIC`, which accepts its bounds in either order, and
`BETWEEN ASYMMETRIC`, the default the bare form implies. Part 11 §2 neither admits nor excludes
either keyword. The language descriptor lists the ISO feature E061-02, the `BETWEEN` predicate,
among its feature dependencies and does not list T461, symmetric `BETWEEN`.

The reference validator's static check admits both keywords. `x BETWEEN ASYMMETRIC y AND z` runs
and gives the bare form's result. `x BETWEEN SYMMETRIC z AND y` fails in DuckDB 1.5.5 with "Not
implemented Error: Expression type T_List", which Part 11 §8 makes an incomplete evaluation of a
rule the check called valid.

### 2.5 No shipped rule changes

The five shipped registries declare 139 Tier 2 rules: core 91, `dynamic_foraging` 12,
`vr_foraging` 24, `aind_opto` 1 and `aind_unit_qc` 11. Four of them use `BETWEEN`, six times in all.

- `core.events.within_observation` and `core.spike_events.within_observation` compare an `int64`
  tick with two `int64` bounds. Every operand is exact, so §2.2 applies.
- `dynamic_foraging.trials.a_probability_is_a_probability` and
  `dynamic_foraging.trials.a_draw_is_a_draw` test four `float64` columns against the integer
  literals 0 and 1. Each comparison pairs a `DOUBLE PRECISION` value with one exact literal, so
  each pair's common type is the one the three operands share.

None of the 42 rule-language conformance vectors uses `BETWEEN` or `IN`.

### 2.6 `IN` has the same question, and ISO answers it differently

Part 11 §2 admits `IN` over a non-empty scalar list or a one-column subquery, and §4 does not name
it either. Three probes, beside the expansion as an `OR` of `=` comparisons:

| case | operands | values | `IN` as the engine binds it | `OR` of `=` |
|---|---|---|---|---|
| G | `x` `BIGINT`; an integer and an approximate literal | x = 2^53, list (`9007199254740993`, `1e300`) | `TRUE` | `FALSE` |
| H | `x` `REAL`; two integer literals | x = 2^24, list (`16777217`, `1`) | `TRUE` | `TRUE` |
| I | `x`, `a` `BIGINT`; `b` `DOUBLE PRECISION` | x = 2^53, list (a = 2^53 + 1, b = 0) | `TRUE` | `FALSE` |
| J | `x` `DOUBLE PRECISION`; an integer literal and a `REAL` column | x = 16777217, list (`16777217`, r = 0) | `TRUE` | `TRUE` |

The engine converts `x` and every list member to one common type. ISO/IEC 9075-2 does not define
`IN` as an `OR` of comparisons: by the reading taken here of its `<in predicate>` rules, a value list is a table
value constructor whose column takes one type from all its members, and `x` is then compared with
that column. Under that reading, G and I are `TRUE` as the engine gives them, and J is `FALSE`,
because the integer 16777217 first takes the list's `REAL` type and rounds to 16777216. That
reading has not been checked against the text of the standard.

### 2.7 The reference validator already reports an unplaceable conversion incomplete

Where the reference validator cannot place a conversion through text that Part 11 §4 requires, it
reports the rule's evaluation incomplete and does not run it. Its documentation says so, and its
suite asserts both halves: four queries the conversion cannot be placed in are refused, and a
registry rule whose `USING` join converts a `DECIMAL(38,0)` column to `DOUBLE PRECISION` makes the
evaluation incomplete with no packet finding.

Part 11 §4 has stated the rounding rule since the audit restored the sentence R125 §3.4
records. The reference validator's generation was run over each of the five shipped registries; it marked
0 of the 139 rules incomplete. No shipped rule meets the case today.

## 3. Desired outcome and constraints

A rule should have one meaning that two conforming validators give it, whatever engine each uses.
`BETWEEN` should mean what the ISO basis of Part 11 §1 defines, so that a rule author can read the
predicate as the two comparisons it expands to. Where an engine cannot give a valid rule that
meaning, the validator should say so through an outcome that neither invents a finding nor charges
the registry with a defect. The ISO basis, Part 11 §4's common-type rules, its rounding rule and
three-valued logic are preserved; no shipped rule's result may change.

## 4. Options and tradeoffs

### 4.1 How `BETWEEN` takes its operands' types

- **Keep Part 11 silent.** Two conforming validators can then disagree on a row, as cases A to F
  show. This fails the outcome above.
- **One common type for all three operands,** as DuckDB binds them. This departs from the ISO
  definition Part 11 §1 selects, and it rounds an exact comparison the author wrote exactly: in case
  D it rounds the exact-decimal literal that Part 11 §4 has compare with an exact numeric by value.
- **Two comparisons, each taking its own common type,** as ISO/IEC 9075-2 defines. This is the
  preferred direction. `x BETWEEN y AND z` means `y <= x AND x <= z`, and `x NOT BETWEEN y AND z`
  means its negation. Part 11 §4's common-type and rounding rules then apply to each comparison
  without a third rule. Its rounding rule applies to each comparison's own operands, so a pair
  that is exact converts nothing.

The rule would sit in Part 11 §4, beside the sentence naming the constructs its common-type rules
govern. Part 11 §2 would say whether `SYMMETRIC` and `ASYMMETRIC` are in the profile, which open question 1 asks.
Both sections carry canonical anchors, `ew-tier-2-type-binding` and `ew-tier-2-query-profile`, so
no anchor bootstrap is needed.

Part 11 §1 requires a changed language contract to take a new language ID. Every identifier stays a
development identifier until the release-candidate field test ends (Part 02 §9.2), so the change
needs no new ID now. The preferred direction also states what the ISO basis already defines, where
Part 11 had left the binding unstated.

### 4.2 What a validator reports when it cannot give a rule Part 11's meaning

- **Run the rule with the engine's semantics.** That can report a packet finding Part 11's meaning
  would not produce, or miss one it would, which Part 11 §8 forbids for every other failure to
  evaluate.
- **Report the registry invalid.** Invalidity is a property of the rule, decided by the static
  profile, and this would bind one implementation's limitation to a rule every other validator can
  evaluate.
- **Report the language unsupported.** `unsupported` applies to a registry's whole Tier 2
  evaluation and means the validator lacks the language, which it does not.
- **Report that rule's evaluation incomplete.** This is the preferred direction. Part 11 §8 would
  add the cause: a validator that supports the language but cannot evaluate a valid rule with the
  semantics Part 11 defines reports that evaluation incomplete, and does not evaluate it with the
  engine's differing semantics instead. Part 05 §9.5 then composes the verdict as it does for any
  other incomplete evaluation.

Part 05 §9.4 restates Part 11 §8's causes in its own list. Adding the cause to both keeps two copies
of one fact. The preferred direction is for Part 05 §9.4 to refer to Part 11 §8 for the causes and
keep its own reporting obligations, which open question 3 asks.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose (Part 01) | unchanged: no concept changes |
| logical prose (Part 02), registry meta-schema and declarations | unchanged: the rules state no `BETWEEN` whose result changes (§2.5), and no declaration changes |
| declarative rules | unchanged: no shipped rule's result changes (§2.5) and none is marked incomplete (§2.7) |
| rule language (Part 11) | affected: Part 11 §4 gains the meaning of `BETWEEN`, Part 11 §2 states the keyword forms, Part 11 §8 gains a cause; the language descriptor's feature list is unchanged unless the `SYMMETRIC` answer admits T461 |
| physical profiles and packet manifest | unchanged: neither concerns rule evaluation |
| validation and import (Part 05) | affected: Part 05 §9.4's list of causes, under the answer to open question 3 |
| extension registries | unchanged: none uses `BETWEEN` with mixed exact and approximate operands |
| reader, writer and adapters | unchanged: none evaluates a rule |
| validator | affected: the lowering expands `BETWEEN` into two comparisons, converting each comparison's own operands; the static check follows the `SYMMETRIC` answer; reporting an unplaceable conversion incomplete is unchanged |
| existing packets | unchanged: no shipped rule's result changes, so no packet needs rebuilding |
| conformance fixtures and tests | affected: rule-language vectors for cases A, D and F and the null cases; a rejection vector if `SYMMETRIC` leaves the profile; validator tests for the expansion |
| revision lifecycle and tooling | unchanged |
| generated publications and documentation | affected: the combined rendering; the validator's README, which names `BETWEEN` among the conversions it places |

## 6. Open questions

1. **Are `SYMMETRIC` and `ASYMMETRIC` in the profile?** The preferred direction keeps both outside
   it. `SYMMETRIC` is a separate ISO feature the descriptor does not list and the reference engine
   cannot run. `ASYMMETRIC` adds nothing the bare form lacks, though the engine runs it. Admitting
   `ASYMMETRIC` alone is the alternative.
2. **Does `IN` get its own rule, and which?** The engine's binding of `IN` differs from an `OR` of
   `=` comparisons (cases G and I) and, by the reading in §2.6, from ISO's own definition only
   where a list mixes an exact member with a `REAL` one beside a `DOUBLE PRECISION` value (case J).
   The preferred direction is to settle `IN` in this change, on the ISO definition, once the reading
   of §2.6 is confirmed against the standard. The alternative is a separate proposal.
3. **Does Part 05 §9.4 keep its list?** The preferred direction replaces its list of causes with a
   reference to Part 11 §8, which owns them. The alternative adds the new cause to both lists.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [ ] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [ ] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.
