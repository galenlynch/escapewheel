# A rule means what Part 11 defines on any engine

| | |
|---|---|
| **Status** | **Accepted** 2026-10-02 |
| **Based on** | `5a1c47b7d496d3856e993551c66bdfe4491f85e3` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 11 §§1, 4 and 8; Part 05 §9.4 |
| **Depends on** | None |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5 |

Section 3 is normative. Sections 1, 2, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

Part 11 defines the language of Tier 2 rules, and a validator evaluates each rule on a database
engine. Part 11 §1 makes the language's contract every statement of §§2–8 on the ISO basis it
selects, and requires a validator claiming support to give a rule the meaning those sections
define. The specification leaves three gaps through which a validator can give a rule its engine's
meaning instead.

`BETWEEN` and `IN` take their meaning from the ISO basis alone. Part 11 §4 lists the constructs its
common-type rules govern as "comparisons, `CASE`, `COALESCE`, set operations, and routine
arguments", a list that reads as closed and names neither predicate. DuckDB, the reference
validator's engine, converts every operand of either predicate to one common type, and the
reference validator follows it, so it gives `BETWEEN` a meaning the basis does not and gives `IN` a
different one for one combination of operands.

Part 11 §8 lists what makes a valid rule's evaluation incomplete, and an engine that cannot evaluate
a rule with Part 11's semantics is not on the list. Part 11 §1, read literally, is broken by every
incomplete evaluation, a timeout included.

This revision states the meaning of `BETWEEN` and of `IN` in Part 11 §4, adds the cause to Part 11
§8, binds Part 11 §1's requirement to the evaluations a validator completes, and has Part 05 §9.4
take a rule's causes from Part 11 §8. No shipped rule's result changes and the language ID is
unchanged.

The change is structural because it revises sentences in place in Part 11 §§1, 4 and 8 and Part 05
§9.4. An appended section would leave §4's list reading as closed, §8's list incomplete beside the
new cause, §1 in conflict with §8, and Part 05 §9.4 with a second copy of the causes.

### 1.1 Structural crosswalk

Every affected section carries a canonical anchor at the baseline, so no bootstrap is needed.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 11 §1, the sentence requiring a validator to give a rule the meaning §§2–8 define | revise in place | same section (`ew-tier-2-language-selection`) | the requirement applies to every evaluation the validator completes, and §8 states when one ends incomplete; §1's other sentences are unchanged | §3.1 |
| Part 11 §4, after the sentence naming the constructs the common-type rules govern | extend in place | same section (`ew-tier-2-type-binding`) | `BETWEEN` is two comparisons, each typed on its own | §3.2 |
| Part 11 §4, after the `BETWEEN` statement | extend in place | same section (`ew-tier-2-type-binding`) | an `IN` list is typed as a table before its left operand is compared with it, and a list of exact members is compared member by member by value | §3.3 |
| Part 11 §8, the list of the causes of an incomplete evaluation | revise in place | same section (`ew-tier-2-evaluation-outcomes`) | an engine unable to give a valid rule Part 11's semantics is a cause, and running the rule with differing semantics is forbidden | §3.4 |
| Part 05 §9.4, the list of the causes of an incomplete evaluation | replace in place | same section (`ew-incomplete-validation`) | a rule's causes are Part 11 §8's; other evaluations keep the causes they can reach; §9.4's other sentences are unchanged | §3.5 |

## 2. Background

Section 2 is informative. The probes ran on DuckDB 1.5.5, the version the reference validator pins,
through the reference validator's static check and its lowering, over one-row tables, each
predicate wrapped in a `CASE` reporting `TRUE`, `FALSE` or `NULL`. Every case of §§2.1, 2.2 and
2.4 but case B is one of §6's execution vectors, and each, given to the engine as authored at the
baseline, returned the result in its engine column.

### 2.1 One common type for `BETWEEN` makes two exact operands equal

The pairwise result is the same query written `x >= y AND x <= z`.

| case | operands | values | engine | pairwise |
|---|---|---|---|---|
| A | `x`, `y` `BIGINT`; `z` `DOUBLE PRECISION` | x = 2^53, y = 2^53 + 1, z = 1e300 | `TRUE` | `FALSE` |
| B | `x`, `y` `BIGINT`; `z` `REAL` | x = 2^24, y = 2^24 + 1, z = 1e30 | `TRUE` | `FALSE` |
| C | `x`, `z` `INTEGER`; `y` `REAL` | x = 2^24 + 1, y = z = 2^24 | `TRUE` | `FALSE` |
| D | `x` `BIGINT`; an exact-decimal and an approximate literal | x = 2^53, y = `9007199254740992.5`, z = `1e300` | `TRUE` | `FALSE` |
| F | `x` cast to `DECIMAL(38,0)`; an integer literal; `z` `DOUBLE PRECISION` | x = 2^53, y = `9007199254740993`, z = 1e300 | `TRUE` | `FALSE` |

`NOT BETWEEN` over case A gives the negations. Each case mixes two exact operands with an
approximate one: pairwise, the exact comparison fails, while one common type rounds both exact
operands to the approximate domain, where they are equal. In case D the engine rounds an
exact-decimal literal that Part 11 §4 has compare with an exact numeric by value.

The two readings agree where every operand is approximate, since `REAL` converts to
`DOUBLE PRECISION` exactly, and where every operand is exact and the engine completes. A null bound
gives `FALSE` where the other bound already fails and `NULL` otherwise, under both readings;
reversed bounds give `FALSE`. The engine fails rather than answering wrongly on one exact case: it
compares a `DECIMAL(38,0)` value with a 38-digit literal of scale 1 in that literal's
`DECIMAL(38,1)`, which raises an out-of-range error for a value of magnitude 10^37 or more. That
failure is already incomplete under Part 11 §8.

### 2.2 The ISO basis types an `IN` list before comparing with it

ISO makes `( IVL )` the table value constructor `( VALUES IVL )` and `RVC IN IPV` equivalent to
`RVC = ANY IPV`. The constructor's column takes one type from all its members, which Part 11 §4's
set-operation rule fixes where ISO leaves the precision implementation-defined.

| case | operands | values | engine | ISO with Part 11 §4 | `OR` of `=` |
|---|---|---|---|---|---|
| G | `x` `BIGINT`; an integer and an approximate literal | x = 2^53, list (`9007199254740993`, `1e300`) | `TRUE` | `TRUE` | `FALSE` |
| H | `x` `REAL`; two integer literals | x = 2^24, list (`16777217`, `1`) | `TRUE` | `TRUE` | `TRUE` |
| I | `x`, `a` `BIGINT`; `b` `DOUBLE PRECISION` | x = 2^53, list (a = 2^53 + 1, b = 0) | `TRUE` | `TRUE` | `FALSE` |
| J | `x` `DOUBLE PRECISION`; an integer literal and a `REAL` column | x = 16777217, list (`16777217`, r = 0) | `TRUE` | `FALSE` | `TRUE` |

The engine and `OR` of `=` columns are probe results; the ISO column is derived. In case J the
`REAL` member gives the list `REAL`, in which 16777217 rounds to 16777216, and `x` then differs from
it in `DOUBLE PRECISION`. The engine brings `x` into the list's common type, keeps the list in
`DOUBLE PRECISION`, and differs from the basis in that case alone. An `OR` of `=` differs in G and I.

Where every member is exact, the engine compares `x` with each member by mathematical value: an
`INTEGER` `x` of 2 is not in (`1`, `2.5`) and is in (`2.0`, `3`). An exact common type holds each
member's value exactly, so the basis gives the same results, and no member need convert.

### 2.3 The ISO rules were read in the 1992 draft and the 1999 edition

Part 11 §9 selects ISO/IEC 9075-2:2023, which was not available to read. The rules above were read
in two earlier texts:

| rule | ISO/IEC 9075:1992 public draft (X3H2-92-154) | ISO/IEC 9075-2:1999 |
|---|---|---|
| `X BETWEEN Y AND Z` is `X>=Y AND X<=Z`; the negated form is its negation | Subclause 8.3, Syntax Rules 5 and 6 | Subclause 8.3, Syntax Rules 1, 5 and 6, the bare form being `ASYMMETRIC` |
| `( IVL )` is `( VALUES IVL )`; `IN` is `= ANY`; `NOT IN` is its negation | Subclause 8.4, Syntax Rules 1, 3 and 4 | the same |
| a table value constructor's column takes one type from its members | Subclause 7.2, General Rule 2, through `UNION ALL` | Subclause 7.3, Syntax Rule 4, through Subclause 9.3 |
| an approximate member makes the type approximate, of implementation-defined precision | Subclause 9.3, Syntax Rule 3d | Subclause 9.3, Syntax Rule 3e |

The 1992 draft is preserved as plain text at contrib.andrew.cmu.edu/~shadow/sql/sql1992.txt, and a
copy of the 1999 edition is hosted at web.cecs.pdx.edu/~len/sql1999.pdf. No text of the 2003, 2011,
2016 or 2023 edition, public draft or vendor quotation of these Syntax Rules was reachable on
2026-10-02. That §§3.2 and 3.3 state what ISO/IEC 9075-2:2023 defines is therefore an unverified
basis of this revision.

### 2.4 An unplaceable conversion already ends incomplete in the reference validator

Part 11 §4 has every exact-to-approximate conversion round once, to nearest with ties to even.
DuckDB 1.5.5 does not always: of 3,006 `DECIMAL(38,0)` values drawn between 2^64 and 10^37, 73
converted to `DOUBLE PRECISION` landed on a binary64 neighbour of the correctly rounded value, one being
237369399564062458235467982671442745. A `USING` join of a `DECIMAL(38,0)` column holding that value
with a `DOUBLE PRECISION` column holding its correctly rounded binary64 value matches one row under
Part 11 and none on the engine.

The reference validator converts such a value through its text. Where it cannot place that
conversion in a rule's text, as in a `USING` join, it reports the rule's evaluation incomplete and
does not run it, and its suite asserts both. The repository's registry check reports such a rule
apart from a broken one. Over the five shipped registries the validator marks 0 of 140 rules
incomplete.

### 2.5 Part 05 §9.4's list covers more than rules

Part 05 §9.4 lists an unreadable input, engine failure, exact overflow, out-of-range timestamp,
timeout and resource limit as making "the affected required evaluation incomplete", without
restricting the list to rules. The reference validator relies on it outside Tier 2: an unreadable
retained manifest leaves the comparison against a prior packet incomplete, an unreadable
`core.sessions` leaves the comparison of the manifest's sessions with it incomplete, and an engine
failure while comparing an amendment with its predecessor leaves that comparison incomplete. Its
Parquet storage-floor comparison skipped a table whose footer it could not read and recorded no
evaluation, a defect corrected beside this revision. Exact overflow and an out-of-range
timestamp arise only in rule arithmetic; the validator checks overflow in its rule-language module
alone.

### 2.6 No shipped rule changes

The five shipped registries declare 140 Tier 2 rules: core 91, `dynamic_foraging` 13,
`vr_foraging` 24, `aind_opto` 1 and `aind_unit_qc` 11. Four use `BETWEEN`, six times in all, and
none uses `IN`. `core.events.within_observation` and `core.spike_events.within_observation`
compare an `int64` tick with two `int64` bounds, so every operand is exact.
`dynamic_foraging.trials.a_probability_is_a_probability` and `dynamic_foraging.trials.a_draw_is_a_draw`
compare `float64` columns with the integer literals 0 and 1, so each pair's common type is the
one the three operands share. Of the 44 rule-language vectors at the baseline, two use `BETWEEN`,
both rejecting its keyword forms, and none uses `IN`.

### 2.7 Alternatives

| alternative | why it falls short |
|---|---|
| keep Part 11's text and rely on the basis | §4's list reads as closed, and the reference validator took the engine's binding |
| one common type for every `BETWEEN` operand, as the engine binds them | it changes the language away from its basis and rounds the exact-decimal literal of case D |
| an `OR` of `=` comparisons for `IN` | it departs from the basis, which types the list as a table, and changes cases G and I |
| run a rule the engine cannot evaluate as Part 11 defines with the engine's semantics | it reports findings Part 11's meaning would not produce, or misses ones it would |
| report the registry invalid | invalidity is a property of the rule, and another validator can evaluate it |
| report the language unsupported | it applies to a registry's whole Tier 2 evaluation and withholds every other rule's result |
| leave Part 11 §1 unchanged and treat the cause as a limit like a timeout | §1 then stays in conflict with every cause §8 lists |
| add the cause to Part 05 §9.4's list as well | two lists of one fact |

## 3. Decision

Five subsections bind Part 11 §1's meaning requirement to completed evaluations, state the meaning
of `BETWEEN` and of `IN`, add a cause of incomplete evaluation, and make Part 11 §8 the owner of a
rule's causes. The crosswalk in §1.1 places each. Sections 3.2 and 3.3 define the language in the
indicative, as Part 11 does; Part 11 §1 binds a validator to them.

### 3.1 A validator gives a rule its meaning in every evaluation it completes

Part 11 §1 (`ew-tier-2-language-selection`): a validator claiming support for the language MUST
support the identified contract as a whole. The contract is every statement of §§2–8, whether or
not it carries a keyword. In every evaluation of a rule that it completes, a validator claiming
support MUST give the rule the meaning those sections define. Part 11 §8 states when an evaluation
ends incomplete instead.

### 3.2 `BETWEEN` is two comparisons

Part 11 §4 (`ew-tier-2-type-binding`): `x BETWEEN y AND z` means `x >= y AND x <= z`, and
`x NOT BETWEEN y AND z` means `NOT (x BETWEEN y AND z)`. Each of the two comparisons takes the
common type of its own two operands under §4's rules, and no third operand enters it. A comparison
between two exact operands therefore rounds neither, and an exact-decimal literal bound compares
with an exact numeric `x` by mathematical value.

### 3.3 An `IN` list takes one type before its left operand is compared with it

Part 11 §4 (`ew-tier-2-type-binding`): an `IN` value list `(v1, …, vn)` is the table value
constructor `VALUES (v1), …, (vn)`. Its one column takes the common type of its members under §4's
rule for set operations, and each member converts to that type, except that a list whose members
are all exact numerics takes no common type: no member converts, and `x` compares with each member
under §4's rule for comparisons, so an exact `x` compares with each by mathematical value and
`x IN (2.5)` means `x = 2.5`. `x IN (v1, …, vn)` means
`x = ANY` over that column, comparing `x` with the column under §4's rule for comparisons, and
`x NOT IN (v1, …, vn)` means `NOT (x IN (v1, …, vn))`. `x IN (subquery)` means `x = ANY (subquery)`,
comparing `x` with the subquery's one column under the same rule.

A member converted to the list's type is compared with `x` in that type's value, so an exact member
that an approximate member makes approximate is rounded before the comparison.

### 3.4 A validator reports incomplete where its engine cannot give a rule Part 11's meaning

Part 11 §8 (`ew-tier-2-evaluation-outcomes`): a validator that supports the language but cannot
complete a valid rule because an input is unreadable, the engine fails, exact arithmetic overflows,
a timestamp exceeds the supported range, a resource or timeout limit is reached, or it cannot
evaluate the rule with the semantics §§2–7 define reports that evaluation as **incomplete**. It
MUST NOT evaluate a rule with semantics that differ from those §§2–7 define, and MUST NOT fabricate
a packet finding from its inability to evaluate.

No tool checks whether a validator could have evaluated a rule it reports incomplete for the last
cause. Execution vectors check the prohibition for the cases they hold; no tool checks it in
general.

### 3.5 Part 11 §8 states a rule's causes of incomplete evaluation

Part 05 §9.4 (`ew-incomplete-validation`): a Tier 2 rule's evaluation is incomplete for a cause
Part 11 §8 states. Any other evaluation a subject requires is incomplete where an input it needs is
unreadable, the engine evaluating it fails, or a timeout or resource limit is reached.

## 5. Consequence

No shipped rule's result changes (§2.6), so no registry version changes and no packet is rebuilt.
A rule with two exact `BETWEEN` operands and an approximate one, or an `IN` list mixing an exact
member, an approximate member and an approximate `x` of a wider domain, can change result on the
reference validator once its lowering is corrected; no shipped rule is such a rule.

The language ID stays `escapewheel-rule-sql-v0.2`. Part 11 §1 gives a changed language contract a
new ID, and §§3.2 and 3.3 state the meaning the selected basis already gives, so the contract does
not change through them, provided the 2023 edition reads as the 1992 and 1999 texts do (§2.3).
Sections 3.1, 3.4 and 3.5 change no rule's meaning in any completed evaluation: they say which
outcome a validator reports when it gives none, which §1 and §8 left in conflict. Were the contract
nonetheless read as changed, the language ID is a development identifier, which Part 02 §9.2 forbids
reusing only for an incompatible contract, and every rule keeps its meaning under this revision.

A validator that ran a rule with its engine's differing semantics was already nonconforming under
Part 11 §1 and still is. A validator that reported such a rule incomplete now conforms where §8 did
not list the cause.

R125 §§3.2, 3.3, 3.4 and 3.8 and R149 §3.2 keep their ledger entries unchanged: each stays
`applied` at the destinations it names, where this revision's text now stands beside it. No clause
is superseded. R125 §3.1's language-ID rule, R125 §3.11 and R149 §3.3 land at
`ew-tier-2-language-selection` and are unchanged.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. No concept changes. | None required. |
| logical prose and registry | Unchanged. No declaration or rule changes (§2.6), and the language descriptor, whose `contract_clauses` already names §§1, 4 and 8, is unchanged. | The registry check passes over every shipped registry. |
| physical profiles | Unchanged. Neither concerns rule evaluation. | None required. |
| packet manifest and JSON Schemas | Unchanged. The rule-language schema and descriptor keep their content. | None required. |
| validation and import | Part 05 §9.4 takes §3.5. Part 05 §9.5 composes the verdict as it stands. The reference validator's storage-floor comparison records a table whose footer it cannot read as an incomplete evaluation. | The validator suite's tests of an unreadable footer, an unreadable retained manifest and a superseded version whose files were removed each report incomplete. |
| extensions | Unchanged. No repository extension uses `BETWEEN` with mixed exact and approximate operands, and none uses `IN`. | The registry check over every extension registry. |
| reader, writer, validator, adapters | The reference validator's lowering gives `BETWEEN` two comparisons, each converting its own operands, and types an `IN` value list or `IN` subquery from its members before comparing `x` with it, comparing an all-exact list member by member. Its reporting of an unplaceable conversion as incomplete is unchanged. The reader, writer and adapters evaluate no rule. | The validator suite, with tests for both lowerings and for the unreadable footer. |
| conformance fixtures and tests | The rule-language vectors gain §6's execution vectors and an `execute-or-incomplete` mode whose admissible outcomes are a stated result or an incomplete evaluation, and the probe runs it. | The rule-language probe in `verify.py`. |
| revision process and tooling | The ordinary ledger and evidence records. | `ledger.py`, `evidence.py` and `verify.py`. |
| generated publications and developer documentation | The combined specification regenerates. The validator's README, which lists where it gives the engine a rule other than as authored, adds both lowerings; the rule-language vectors' README describes the new form. | `verify.py`. |

## 6. Conformance and implementation evidence

§3.1 is `applied` at Part 11 §1 (`ew-tier-2-language-selection`). §§3.2 and 3.3 are `applied` at
Part 11 §4 (`ew-tier-2-type-binding`). §3.4 is `applied` at Part 11 §8
(`ew-tier-2-evaluation-outcomes`). §3.5 is `applied` at Part 05 §9.4 (`ew-incomplete-validation`).

These cases distinguish the new rules from the current reference behaviour:

- §3.2: execution vectors for cases A, C, D and F of §2.1 return `FALSE`, and `NOT BETWEEN` over
  case A returns `TRUE`; vectors with a null lower bound return `FALSE` where `x` exceeds the upper
  bound and `NULL` where it does not, a null `x` returns `NULL`, and reversed bounds return
  `FALSE`; a vector with three approximate operands returns the same result both readings give.
- §3.3: execution vectors for cases G, H and I of §2.2 return `TRUE` and case J returns `FALSE`;
  a list holding a null member and no match returns `NULL`, one holding a null member and a match
  returns `TRUE`, and the negation of the first returns `NULL`; a subquery vector compares a
  `BIGINT` `x` with a `DOUBLE PRECISION` column under §4's comparison rule; a null `x` is not in an
  empty subquery, returning `FALSE`, and its negation returns `TRUE`; an `INTEGER` `x` of 2 is not in
  (`1`, `2.5`) and is in (`2.0`, `3`).
- §3.4: the `USING` join of §2.4 is a vector of the two-outcome form, admitting its one-row result
  or an incomplete evaluation and failing the engine's empty result. The validator suite's existing
  test that such a join ends incomplete with no packet finding continues to pass.
- §§3.1 and 3.5 add no packet-observable behaviour beyond §3.4's: the same vector shows an
  incomplete evaluation conforming, and the validator tests of §5's inventory show the causes Part
  05 §9.4 keeps for other evaluations.

At acceptance, each clause needs its ledger entry and evidence record; §§3.2 and 3.3 also need
either a reading of ISO/IEC 9075-2:2023 Subclauses 8.3, 8.4 and the table value constructor's
Syntax Rules, or the record that the 2023 basis stays unverified (§2.3). The revision was accepted
with the 2023 basis unverified: §§3.2 and 3.3 rest on the 1992 and 1999 texts. The null-member, subquery
and all-exact `IN` vectors were derived from ISO's quantified comparison and agree with the engine.
