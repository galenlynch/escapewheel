# Part 11 — Tier 2 rule language

Normative.

<a id="ew-tier-2-language-selection" data-spec-anchor="canonical"></a>
## 1. Language identity, authority, and selection

This part defines the portable language and execution semantics for registry-declared Tier 2
rules. It maps the logical resources and types of Part 02 into rule evaluation. Part 02 owns
registry selection and rule declarations; Part 05 owns validation and reporting workflow. This
part MUST NOT redefine either subject.

The language identified by `escapewheel-rule-sql-v0.2` is based on the SQL framework and
SQL/Foundation editions, corrigenda, and IEEE floating-point edition identified in §9. Those
authorities apply to the SQL and numerical requirements in §§2–7 only to the extent selected here.
The narrower Escapewheel rules in this part govern where the external standards permit choices or
additional features.

This part expressly incorporates `registry/rule_language.schema.json`, which defines the closed
shape of a rule-language profile, and
`registry/rule_languages/escapewheel-rule-sql-v0.2.json`, which assigns the exact external basis,
ISO feature dependencies, contract clauses, type bindings, and execution settings of this
language. The JSON artifacts MUST conform to the incorporated profile schema. Their fields carry
the meanings defined here; neither artifact makes a parser, abstract syntax tree, database engine,
or validator implementation authoritative.

A validator claiming support for this language MUST support the identified contract as a whole.
It MUST NOT construct a different language by independently toggling profile dependencies or
settings. A changed language contract MUST receive a new language ID. A registry may change its
rules without changing the language ID only when the registry version changes and the rules retain
this contract's meaning.

<a id="ew-tier-2-query-profile" data-spec-anchor="canonical"></a>
## 2. Query profile

A rule MUST contain exactly one SQL/Foundation query expression and no second statement. The
profile admits:

- query specifications with expression select lists, `WHERE`, `SELECT DISTINCT`, column-reference
  `GROUP BY`, and `HAVING`;
- derived tables, one-column scalar subqueries, `EXISTS`, and correlated subqueries;
- one optional top-level `WITH` containing ordinary common table expressions or §6's bounded
  recursive form;
- explicit inner and left outer joins qualified by `ON` or `USING`;
- `UNION` and `UNION ALL`;
- searched `CASE`, aggregate `DISTINCT`, and aggregate `FILTER (WHERE ...)`;
- window partitioning and ordering for the routines below, using ascending column references; and
- `PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY expression)` with implicit ascending order.

A comma, cross, natural, right, or full join is outside the profile. So are nested `WITH`, a
top-level result `ORDER BY`, window frames, order ordinals, `DESC`, and explicit `NULLS FIRST` or
`NULLS LAST`. An unqualified `*` is admitted only in `COUNT(*)` or an intermediate query whose
expanded names are unique; a final result MUST NOT project `*`. A derived table MUST have an
explicit `AS` correlation name. ISO line comments beginning with `--` are admitted; bracketed
comments are not.

Every window invocation MUST have a non-empty `ORDER BY`. For `LAG` and `ROW_NUMBER`, a validator
MUST establish statically that the partition and ordering columns together identify one input row;
otherwise the rule is invalid. Ties in `DENSE_RANK` intentionally receive the same rank.

The admitted literals are an ISO character string, `NULL`, an unsigned base-10 integer, an
unsigned base-10 decimal with digits on both sides of the point, an approximate numeric literal
using `e` or `E` and an optionally signed decimal exponent, and
`INTERVAL '<unsigned-base-10-integer>' DAY`. Unary minus is a separate operator. An exact numeric
literal MUST have no more than 38 digits.

The admitted operators are unary minus; numeric `+`, `-`, `*`, and `/`; a timestamp left operand
plus or minus a day interval; `=`, `<>`, `<`, `<=`, `>`, and `>=`; `IS NULL`, `IS NOT NULL`, and
`IS DISTINCT FROM`; `BETWEEN`, `IN`, `LIKE`, `EXISTS`, and their negated forms; and `AND`, `OR`,
and `NOT`. `IN` takes a non-empty scalar list or a one-column subquery. Other engine spellings,
including `!=`, are outside the profile.

| class | admitted routines |
|---|---|
| scalar | `ABS` over one approximate numeric; `COALESCE` over two or more common-type arguments; `CAST` only to `DOUBLE PRECISION` or `DECIMAL(38,0)`; one-argument `CHARACTER_LENGTH` over a `CHARACTER VARYING` value; one-argument `isnan` and `isfinite` over an approximate numeric |
| aggregate | `COUNT(*)`, one-argument `COUNT`, `COUNT(DISTINCT expression)`, one-argument `MIN` and `MAX`, and the ordered-set `PERCENTILE_CONT` form above |
| window | one-argument `LAG`, zero-argument `ROW_NUMBER`, and zero-argument `DENSE_RANK` |

`ABS`, `MIN`, `MAX`, and `LAG` return their argument's domain. `COALESCE` returns its arguments'
common domain, and `CAST` returns its target domain. `COUNT`, `ROW_NUMBER`, `DENSE_RANK`, and
`CHARACTER_LENGTH` return `BIGINT`; `PERCENTILE_CONT` returns `DOUBLE PRECISION`. Comparisons,
predicates, Boolean operators, `isnan`, and `isfinite` return `BOOLEAN`. An aggregate MUST NOT be
used as a window routine, and a window routine MUST carry `OVER`. SQL keywords and routine names are
case-insensitive; identifiers follow §3. `CHARACTER_LENGTH` is admitted in that spelling alone:
`CHAR_LENGTH`, `LENGTH`, and a `USING` clause are outside the profile.

A validator MUST parse and statically check a rule before executing it. It MUST reject a second
statement, any surface outside this positive profile, and every DDL, DML, transaction, catalog,
configuration, attachment, import/export, extension, macro, filesystem, network, parameter,
volatile, or environment-dependent surface before execution. An engine feature does not enter the
language merely because the engine implements it.

<a id="ew-tier-2-relation-environment" data-spec-anchor="canonical"></a>
## 3. Relation environment, names, and dependencies

A base relation MUST use its canonical two-part registry resource ID, such as `core.units` or
`dynamic_foraging.trials`, with the exact lowercase spelling in the registry. A validator MUST NOT
expose flattened names as part of this language or resolve alternate spelling by case folding.

A core rule may name only core and analysis resources in the core registry. An extension rule may
name those resources and resources in its own extension registry, and MUST NOT name another
extension. Local aliases and common-table-expression names are one-part names. Every identifier
MUST match `^[a-z][a-z0-9_]*$`, be unique in its resolution scope, and compare code point for code
point. Delimiting an identifier does not admit another spelling or a keyword. Every other base
relation, including a system catalog or validator-created relation, makes the registry invalid.

Each visible table exposes exactly its registry-declared columns under §4. A resource absent from
the packet binds as an empty relation of that shape. A declared resource that cannot be read MUST
NOT be substituted with an empty relation for a rule that depends on it; that rule is incomplete
under §8.

Static validation MUST return the complete set of base registry resources named by a rule. Local
aliases, common table expressions, derived tables, literals, and comments do not enter that set. A
registry MUST NOT maintain a second dependency list for the same fact.

<a id="ew-tier-2-type-binding" data-spec-anchor="canonical"></a>
## 4. Logical type binding and general expression semantics

The complete registry-to-SQL binding is:

| registry type | SQL domain |
|---|---|
| `int32` | `INTEGER` |
| `int64` | `BIGINT` |
| `float32` | `REAL` |
| `float64` | `DOUBLE PRECISION` |
| `bool` | `BOOLEAN` |
| `date` | `DATE` |
| `timestamp` | `TIMESTAMP(6) WITH TIME ZONE` |
| `string` | unbounded `CHARACTER VARYING` |
| `json_string` | unbounded `CHARACTER VARYING` |

`INTEGER` and `BIGINT` are signed 32-bit and signed 64-bit domains. `REAL` and
`DOUBLE PRECISION` are IEEE 754 binary32 and binary64. `DECIMAL(p,s)` denotes exact multiples of
10^-s with at most `p` digits, where 1 ≤ `p` ≤ 38 and 0 ≤ `s` ≤ `p`. The profile additionally
admits the domain of an exact-decimal literal and `DECIMAL(38,0)` as an explicit cast target. It
provides no JSON parsing or implicit distinction between `string` and `json_string`.

A cast to `DECIMAL(38,0)` accepts an integer or scale-zero decimal and preserves its mathematical
value. A cast to `DOUBLE PRECISION` accepts an exact or approximate numeric and rounds to nearest,
ties to even. No other explicit cast is admitted. An implementation may lower these domains to
engine-native representations only when values and operations retain the specified semantics.

ISO SQL null and three-valued Boolean semantics apply except where this part narrows them.
`COUNT` follows ISO SQL; `MIN`, `MAX`, and `PERCENTILE_CONT` ignore null inputs; grouping,
`DISTINCT`, and set operations treat nulls on ISO terms. Window and ordered-set ordering places
null after every non-null value.

A validator MUST bind and type-check the complete query before execution. No implicit cast may
convert character, Boolean, date, or timestamp values to or from a numeric domain. Identical
domains retain that domain. `INTEGER` with `BIGINT` yields `BIGINT`; an integer with
`DECIMAL(38,0)` yields `DECIMAL(38,0)`; `REAL` with `DOUBLE PRECISION` yields
`DOUBLE PRECISION`; and an exact with an approximate numeric yields the approximate domain,
widened to `DOUBLE PRECISION` if either operand has it. No other pair has an implicit common type.
These rules govern comparisons, `CASE`, `COALESCE`, set operations, and routine arguments. An
exact-decimal literal may instead compare with an exact numeric by mathematical value.

<a id="ew-tier-2-deterministic-semantics" data-spec-anchor="canonical"></a>
## 5. Numeric, timestamp, and character semantics

Approximate values use this total order for comparison, grouping, distinctness, set operations,
`MIN`, `MAX`, and ordering:

```text
-infinity < finite values < +infinity < NaN
```

All NaN encodings compare equal for those operations; positive and negative zero compare equal.
Null retains §4's semantics. `isnan` and `isfinite` accept either approximate domain, return null
for null, and otherwise identify NaN and finite values respectively.

An exact-integer literal takes the first containing domain in the order `INTEGER`, `BIGINT`,
`DECIMAL(38,0)` and is invalid outside that range. An exact decimal with `p` digits and `s`
fractional digits takes `DECIMAL(p,s)`. A non-zero-scale exact decimal is admitted only in an
exact comparison, through conversion to an approximate common type, or as `PERCENTILE_CONT`'s
fixed `0.5`. An approximate literal converts to `DOUBLE PRECISION` with round-to-nearest,
ties-to-even.

Approximate arithmetic and `ABS` use the corresponding IEEE binary operation with
round-to-nearest, ties-to-even. Mixed approximate expressions use the wider domain; an exact value
combined with an approximate value converts to the approximate domain. IEEE infinity, NaN, and
signed zero result from overflow, invalid operations, and zero division rather than a host
exception.

Division MUST have at least one operand explicitly cast to `DOUBLE PRECISION` and returns
`DOUBLE PRECISION`. `PERCENTILE_CONT(0.5)` converts its ordering value to binary64, performs
linear interpolation there, and returns binary64.

Exact integer and scale-zero decimal addition, subtraction, multiplication, and unary minus are
mathematical over the common result domain. A rule whose admitted values can overflow `INTEGER` or
`BIGINT` MUST cast its operands to `DECIMAL(38,0)` first. Static validation MUST reject an
expression that can overflow without that widening. Overflow of `DECIMAL(38,0)` is incomplete
evaluation; wraparound, saturation, and truncation are forbidden.

The execution time zone is UTC. `TIMESTAMP(6) WITH TIME ZONE` denotes an instant at microsecond
precision. `INTERVAL '<digits>' DAY` denotes the stated integer multiplied by 86,400 elapsed
seconds. Only a timestamp left operand plus or minus such an interval is admitted and returns the
timestamp domain. A result outside the supported timestamp range makes evaluation incomplete and
MUST NOT wrap, clamp, saturate, or truncate.

Character operations compare stored Unicode scalar sequences in ascending scalar-value order,
without case folding or normalization. A scalar is in U+0000–U+D7FF or U+E000–U+10FFFF. In
`LIKE`, `_` matches one scalar and `%` matches zero or more scalars. `CHARACTER_LENGTH` returns
the number of scalars in its argument, and null for a null argument.

<a id="ew-tier-2-bounded-recursion" data-spec-anchor="canonical"></a>
## 6. Bounded recursive common table expressions

A recursive common table expression is admitted only when a validator can establish that it:

1. declares an integer depth column;
2. assigns a non-negative integer literal to depth in every seed arm;
3. contains exactly one self-reference in the recursive arm joined through `UNION ALL`;
4. assigns the next depth as prior depth plus a positive integer literal; and
5. guards the recursive arm by comparing prior depth with a finite integer-literal upper bound.

Mutual recursion, multiple self-references, data-dependent bounds, non-increasing depth, and any
other recursive form make the registry invalid before execution. An execution limit is only a
backstop and does not prove that a query conforms.

<a id="ew-tier-2-finding-relation" data-spec-anchor="canonical"></a>
## 7. Finding-relation semantics

A completed rule produces a typed, unordered bag of rows. Row order carries no meaning; duplicate
multiplicity does. An empty bag passes, and every row of a non-empty bag is an offending row for
the declared finding.

Every final column MUST have a unique lower-snake-case name. A simple reference may inherit its
declared name when unique. Every other expression, and either of two references with the same
inherited name, MUST use an explicit alias. Static validation rejects duplicate, unnamed, or
nonconforming final names before execution.

A report may serialize or sample fewer rows only under its reporting contract. Sampling MUST NOT
redefine the complete result or imply that omitted rows do not exist.

<a id="ew-tier-2-evaluation-outcomes" data-spec-anchor="canonical"></a>
## 8. Evaluation outcomes

SQL outside the selected profile makes its registry invalid. A validator MUST reject it before
execution and MUST NOT report that language defect as an offending packet row.

A validator lacking the exact selected language reports the registry's Tier 2 evaluation as
**unsupported**. A validator that supports the language but cannot complete a valid rule because
an input is unreadable, the engine fails, exact arithmetic overflows, a timestamp exceeds the
supported range, or a resource or timeout limit is reached reports that evaluation as
**incomplete**. It MUST NOT fabricate a packet finding from its inability to evaluate.

Only a completed query returning rows produces the rule's declared finding. An invalid,
unsupported, or incomplete required evaluation cannot support a claim that the affected core or
extension registry passed. Core and each extension retain separate evaluation state; one state
MUST NOT be attributed to another, relabeled as a rule failure, or omitted from a complete-packet
claim. Part 05 owns the reporting workflow and eventual report representation.

<a id="ew-rule-language-normative-references" data-spec-anchor="canonical"></a>
## 9. Normative references

| reference | candidate edition | application |
|---|---|---|
| [ISO/IEC 9075-1:2023](https://www.iso.org/standard/76583.html) | exact | SQL framework, terminology, and feature identification |
| [ISO/IEC 9075-1:2023/Cor 1:2026](https://www.iso.org/standard/93690.html) | exact | corrections to the SQL framework edition |
| [ISO/IEC 9075-2:2023](https://www.iso.org/standard/76584.html) | exact | SQL/Foundation grammar and semantics selected by the profile |
| [ISO/IEC 9075-2:2023/Cor 1:2026](https://www.iso.org/standard/93691.html) | exact | corrections to the SQL/Foundation edition |
| [IEEE 754-2019](https://standards.ieee.org/ieee/754/6210/) | exact | binary32, binary64, rounding, exceptional values, and approximate arithmetic |
