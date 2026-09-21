# Tier 2 Rules Use a Versioned Escapewheel SQL Profile

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `b78fd3fc246469e2c8d1fb78a277c4ec9fe16595` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 00 §10; Part 02 §§1, 9.1–9.2, and 10.2; Part 03 §9.4; Part 05 §§5.2–5.3 and §10, plus a new subsection under §9; Part 09 §5.4; registry meta-schema, registries, Tier 2 rules, and the new rule-language profile |
| **Depends on** | R2 §§7.2–7.3 and §§8–9; R24 §§3–4; R26 §§3–5; R35 §5; R94 §3; R121 §3.2; R122 §§3.2–3.3, §3.6, and §3.9 |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6; §3.7; §3.8; §3.9; §3.10; §3.11 |

Section 3 is normative. Sections 1–2 and 4–7 are informative.

Normative keywords follow BCP 14.

## 1. Scope

This revision defines the language and evaluation boundary of registry-declared Tier 2 rules. It
replaces unspecified “SQL” with a versioned Escapewheel profile of ISO SQL/Foundation, selected
once by each registry document and represented by a directly maintained, schema-validated JSON
profile. It defines the visible relations, type binding, allowed query surface, deterministic edge
semantics, bounded recursion, result relation, failure classes, and dependency extraction needed
by independent validators.

The revision keeps DuckDB as the reference implementation without making DuckDB's full dialect,
parser representation, defaults, or release cycle normative. It also removes the one hidden
validator relation from Tier 2 by moving the catalog-to-`core.sessions` comparison to the existing
Part 05 shim boundary.

This is a structural revision. Append-only text would leave Part 02 §10.2's unspecified language,
Part 03 §9.4's flattened textual dependency test, and the hidden catalog relation in their current
owners while placing incompatible replacement rules later. The existing clauses and one registry
rule must instead be replaced or moved under stable anchors.

### 1.1 Structural crosswalk

| old location or artifact | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 00 §10 `ew-normative-references` — missing Tier 2 language remains a release blocker | replace the omission with exact SQL and floating-arithmetic references after the language is incorporated | Part 00 §10 retains the bibliography; Part 02 owns the language semantics | resolves the named candidate defect | §§3.1, 3.5 |
| Part 02 §1 `ew-core-logical-schema-scope` — incorporated logical registry only | retain and extend | Part 02 §1 expressly incorporates the rule-language profile and its schema for exact assignments | gives the machine profile bounded authority without moving semantic ownership out of Part 02 | §3.1 |
| Part 02 §§9.1–9.2 `ew-registry-document` and `ew-registry-self-description` | amend | the same sections | adds one required registry-level language selection and updates changed document identities | §§3.1, 3.11 |
| Part 02 §10.2 — Tier 2 is unspecified SQL returning offending rows | replace and subdivide under planned anchor `ew-tier-2-rules` | Part 02 §10.2 and new child subsections | defines the language, binding, semantics, result, and rule-validity boundary | §§3.1–3.8 |
| Part 02 §10.3 — physical facts are outside SQL | retain | Part 02 §10.3 and Part 05 §5.3 | none; the new profile narrows rather than expands the observable domain | §§3.2–3.3, 3.9 |
| Part 03 §9.4 — revalidation searches flattened SQL text | replace under planned anchor `ew-incremental-revalidation` | Part 03 §9.4 | dependencies come from the validated query's base relations | §3.10 |
| Part 05 §5.2 — validator invokes unspecified SQL | replace under planned anchor `ew-tier-2-validation` | Part 05 §5.2 | validator checks language support and profile conformance before execution | §§3.1–3.8 |
| Part 05 §5.3 — non-SQL shim boundary | retain and extend under planned anchor `ew-validation-shim` | Part 05 §5.3 | moves the catalog-to-table session check to the layer that can observe both inputs | §3.9 |
| Part 05 §9 — findings only | add a new subsection with planned anchor `ew-incomplete-validation` | Part 05 reporting | distinguishes packet findings from invalid, unsupported, or incomplete rule evaluation | §3.8 |
| Part 05 §10 `ew-conformance-classes` — no error finding is sufficient for a conformance claim | amend | Part 05 §10 | an incomplete required evaluation cannot support a conformance claim | §3.8 |
| Part 09 §5.4 — extension failures and verdicts | amend under planned anchor `ew-extension-verdicts` | Part 09 §5.4 | unsupported or incomplete extension evaluation is not fabricated as a rule failure | §3.8 |
| `registry/registry.schema.json` | replace its current shape and identity | the registry meta-schema incorporated through Part 02 | requires one non-empty `rule_language` string per registry document | §§3.1, 3.11 |
| core rule `core.sessions.manifest_sessions_match` | remove from Tier 2 | Part 05 §5.3 shim check with the same check identity | removes the undeclared `manifest_sessions` relation while preserving the compared values and corpus outcome | §3.9 |
| the other 121 core and extension Tier 2 rules | rewrite in place | their core or extension registry documents | uses qualified resource names, standard spellings, safe arithmetic, and unique result names without changing predicates or pass/fail meaning | §§3.2–3.7, 3.11 |
| no present rule-language profile | add `registry/rule_language.schema.json` and `registry/rule_languages/escapewheel-rule-sql-v0.1.json` | Part 02 semantics plus the incorporated machine assignments | creates a language-neutral, data-driven contract | §§3.1–3.6 |

The specification README, registry README, validator and package documentation, rendered tables,
and combined specification are projections or human guidance. They change during incorporation
but do not become additional normative owners.

## 2. Background

### 2.1 Current authority does not identify an executable language

Part 02 §10.2 says that a Tier 2 rule is SQL returning offending rows and defines empty as pass and
non-empty as failure. It does not identify a SQL edition or dialect, define the relations visible
to a query, map registry types to SQL domains, restrict statements and routines, or settle null,
NaN, arithmetic, timestamp, collation, result, and execution-error semantics. Part 00 §10 therefore
correctly lists the Tier 2 language as a release-blocking omission.

The registry meta-schema requires `id`, `level`, `message`, and `sql` for a rule, but no field says
which language interprets `sql`. The reference validator passes that string to DuckDB. Its table
names are implementation-created flattened aliases, its connection inherits host settings, and
engine errors become error-level packet findings. Those choices are observable implementation
behavior, not an incorporated contract.

### 2.2 The released surface is small enough to profile

At the baseline, the generated core registry contains 77 Tier 2 rules over 27 of 43 tables. Four
extension registries contain 45 more rules over 10 of 11 extension tables. The complete authored
surface of the 122 rules is:

```text
arithmetic       +  -  *  /
scalar           abs  coalesce  cast
aggregate        count  min  max  median
window           lag  row_number  dense_rank
predicate        comparisons  between  distinct-from  null  in  like  exists
relational       select  join  group/having  distinct  subquery
                 union/union-all  with  with-recursive
```

The corpus uses no file function, macro, nested type, `QUALIFY`, `GROUP BY ALL`, data-changing
statement, or catalog operation. Replacing `median(gap)` with the standard ordered-set form
`percentile_cont(0.5) WITHIN GROUP (ORDER BY gap)` and `INTERVAL 1 DAY` with
`INTERVAL '1' DAY` removes the two principal spelling dependencies.

A non-writing feasibility probe registered resources under SQL schemas named from their canonical
dotted IDs, made those spelling substitutions, and executed every table-only rule against empty
relations under DuckDB 1.5.5. All 121 table-only rules parsed and bound. The excluded rule was the
one that reads the validator-created `manifest_sessions` relation. Empty inputs establish syntax
and binding feasibility, not data semantics.

### 2.3 Engine and host defaults change results

DuckDB documents its language as PostgreSQL-derived rather than identical to ISO SQL or
PostgreSQL. Reproducible baseline probes found that DuckDB 1.5.5 evaluates integer division as
fractional, orders NaN above ordinary numbers and equal to itself, and raises on overflowing signed
integer subtraction. Other SQL implementations make different choices.

The validator connection also inherits the host time zone. Identical rows around the 2026 spring
daylight-saving transition made `core.clocks.tick_zero_plausible` return no row under UTC and one
row under `America/Los_Angeles`. Its “one day” interval denoted 24 elapsed hours in one session and
23 in the other. The present packet verdict can therefore depend on the validating host.

The empty-table registry check cannot exercise nulls, non-finite values, overflow, zero division,
time-zone boundaries, collation, window ties, duplicate results, or runtime failure. Typed semantic
vectors are needed in addition to syntax and binding checks.

### 2.4 Unrestricted SQL is broader than validation

DuckDB's security guidance documents SQL functions that read arbitrary files and statements that
write files. The current meta-schema accepts any non-empty SQL string, and the reference validator
does not first require one query, reject side effects and table functions, restrict relation
references, or disable environment-dependent routines. Memory and thread limits do not make an
unrestricted language packet-local or read-only.

The current flattened relation mapping is also non-injective for names admitted by the registry:
`a.b_c` and `a_b.c` both become `a_b_c`. Canonical schema-qualified resource IDs preserve the
declared identity and make the query's base-relation dependencies available from its parsed form.

Eight rules currently emit duplicate result names. Six interval-template expansions repeat
`start_tick`; two `core.preferred_runs` rules project distinct values under duplicate
`activity_type` or `session_id` names. The validator discards result names and retains only five
stringified rows, so the empty/non-empty verdict is defined while the finding relation is not.

### 2.5 Standards, compatibility, and dependency order

The language basis is ISO/IEC 9075-1:2023 and ISO/IEC 9075-2:2023 as corrected by ISO/IEC
9075-2:2023/Cor 1:2026. ISO SQL is feature-based and deliberately broad; citing it does not itself
select a safe query subset or settle the numerical and environmental choices exposed above. The
machine profile makes that selection, while Part 02 supplies the Escapewheel-specific meaning.

There are no released packets, external consumers, or remote compatibility commitments.
Development registries and packets can be regenerated. This permits correcting names, registry
shape, and results rather than preserving prototype aliases.

P4 remains downstream because it applies all registry-document invariants uniformly after P3
supplies a rule language. P6 later reconciles packet-to-registry binding, P7 defines the complete
report-composition model, and P10 confirms final release identifiers. None can substitute for a
defined executable language now.

## 3. Decision

### 3.1 Language authority and registry-level selection

Part 02 **MUST** define the semantic interpretation of the Tier 2 rule language identified by
`escapewheel-rule-sql-v0.1`. Part 00 **MUST** cite ISO/IEC 9075-1:2023, ISO/IEC 9075-2:2023,
ISO/IEC 9075-2:2023/Cor 1:2026, and IEEE 754-2019 as exact normative references to the extent Part
02 invokes them.

Part 02 **MUST** expressly incorporate:

- `registry/rule_language.schema.json` for the exact closed shape of a rule-language profile; and
- `registry/rule_languages/escapewheel-rule-sql-v0.1.json` for the exact feature, operator,
  routine, type-binding, and execution-setting assignments of this profile.

Part 02 **MUST** remain the owner of the fields' meanings, query semantics, actor obligations, and
failure boundaries. The incorporated JSON artifacts **MUST NOT** make a particular parser, AST,
database engine, or validator implementation authoritative.

Every core or extension registry document **MUST** carry one required top-level `rule_language`
string. For the registries published with this candidate its value **MUST** be
`escapewheel-rule-sql-v0.1`. The selection **MUST** apply atomically to every Tier 2 rule in that
document. A rule **MUST NOT** repeat or override it, and one registry document **MUST NOT** mix rule
languages.

A new language contract **MUST** receive a new language ID. A change only to one registry's
declarations or queries **MUST** change that registry's version and **MUST NOT** silently change
the meaning of the selected language ID.

### 3.2 Machine profile and permitted query surface

The rule-language profile schema **MUST** define a closed JSON object with required `$schema`,
`id`, `basis`, `statements`, `features`, `operators`, `routines`, `type_bindings`, and `execution`
members. The profile document **MUST** identify its schema as
`https://escapewheel.org/schemas/rule-language/0.1.0`, identify itself as
`escapewheel-rule-sql-v0.1`, and identify the three ISO SQL documents in §3.1 as its basis.

The profile **MUST** admit exactly one SQL query expression and no second statement. Its positive
feature set **MUST** comprise query specification, derived tables, scalar and existence subqueries,
ordinary and bounded-recursive common table expressions, `WHERE`, searched `CASE`, `DISTINCT`,
`GROUP BY`, `HAVING`, aggregate `FILTER`, inner and left joins with `ON` or `USING`, `UNION`,
`UNION ALL`, window partitioning and ordering, and the ordered-set form required by §3.5. It
**MAY** admit `*` in `COUNT(*)` and in an intermediate query whose expanded names are unique; the
outer result **MUST NOT** project `*`.

The permitted operators **MUST** be unary minus; numeric addition, subtraction, multiplication,
and division; `=`, `<>`, `<`, `<=`, `>`, and `>=`; `IS NULL`, `IS NOT NULL`, and
`IS DISTINCT FROM`; `BETWEEN`, `IN`, `LIKE`, `EXISTS`, and their present negated forms; and the
Boolean operators `AND`, `OR`, and `NOT` under ISO three-valued logic.

The permitted routines **MUST** be:

| class | routines |
|---|---|
| scalar | `ABS`, `COALESCE`, `CAST`, `isnan`, `isfinite` |
| aggregate | `COUNT`, `MIN`, `MAX`, and `PERCENTILE_CONT` restricted to fraction `0.5` |
| window | one-argument `LAG`, `ROW_NUMBER`, and `DENSE_RANK` |

Routine names are case-insensitive SQL names; `isnan` and `isfinite` are the two
Escapewheel-defined additions. A validator **MUST** reject before execution a second statement, a
construct, operator, routine, table function, or type outside the profile, or any DDL, DML,
transaction, catalog, configuration, attachment, import/export, extension, macro, filesystem,
network, parameter, volatile, or environment-dependent surface. An engine feature **MUST NOT**
enter the language merely because the engine implements it.

A validator **MUST** parse and statically check a rule against this positive profile before
executing it. It **MUST NOT** execute a rule that fails the check. An implementation **MAY** use an
engine parser, but the normative profile **MUST NOT** contain that parser's node names or depend on
unpublished AST behavior.

### 3.3 Relation environment, names, and dependencies

A Tier 2 base relation **MUST** be named by the canonical two-part registry resource ID, such as
`core.units` or `dynamic_foraging.trials`. A validator **MUST NOT** expose flattened names such as
`core_units` as part of the rule language.

A core rule **MUST** be able to name only core and analysis resources in the core registry. A rule
in an extension registry **MUST** be able to name core and analysis resources plus resources in
that same extension registry, and **MUST NOT** name another extension. A query **MAY** use local
one-part aliases and common-table-expression names. Every other base relation, including a system
catalog or validator-created relation, **MUST** make the registry document non-conforming.

Each visible registry table **MUST** expose exactly its declared columns under the mapping in
§3.4. A resource absent from the packet **MUST** bind as an empty relation with that declared
shape. A resource the packet declares but the validator cannot read **MUST NOT** be substituted
with an empty relation for a rule that depends on it; that rule's evaluation is incomplete under
§3.8.

The static profile check **MUST** return the set of base registry resource IDs a rule names. Local
aliases, common table expressions, derived tables, and relation names inside literals or comments
**MUST NOT** enter that set. A registry **MUST NOT** carry a second hand-maintained dependency list
for the same fact.

SQL regular and delimited identifiers **MAY** be used for declared columns, aliases, and resources.
A delimited identifier **MUST** contain the exact registry or local name it denotes; quoting
**MUST NOT** introduce a case-folded alternate identity. Every final result name remains subject
to §3.7.

### 3.4 Logical type binding and general expression semantics

The rule-language profile **MUST** carry this complete registry-to-SQL binding:

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

The profile **MUST** additionally admit `DECIMAL(38,0)` only as an expression type used by an
explicit `CAST`; it **MUST NOT** change a stored column's declared type. The profile **MUST NOT**
supply JSON parsing or any implicit semantic distinction between `string` and `json_string`.

ISO SQL null and three-valued Boolean semantics **MUST** apply except where this revision states a
narrower rule. `COUNT` **MUST** count as ISO SQL defines; `MIN`, `MAX`, and
`PERCENTILE_CONT` **MUST** ignore null inputs; grouping, `DISTINCT`, and set operations **MUST**
treat nulls on ISO SQL terms. A window or ordered-set ordering **MUST** place null after every
non-null value unless the expression explicitly states another permitted placement.

An implementation **MUST** bind and type-check the complete query before execution. No implicit
cast **MAY** convert character, Boolean, date, or timestamp values to or from a numeric domain.
Numeric common-type selection **MUST** follow the explicit rules in §3.5 rather than an engine's
more permissive coercion table.

### 3.5 Numeric, timestamp, and character semantics

For SQL comparison, grouping, distinctness, set operations, `MIN`, `MAX`, and ordering, the rule
language **MUST** use this total order for each approximate numeric domain:

```text
-infinity < finite values < +infinity < NaN
```

All NaN encodings **MUST** compare equal to one another for those operations. Positive and
negative zero **MUST** compare equal. Null remains outside the order and retains §3.4's semantics.

`isnan(value)` and `isfinite(value)` **MUST** accept `REAL` or `DOUBLE PRECISION`. Each **MUST**
return null for null. `isnan` **MUST** be true only for NaN; `isfinite` **MUST** be true only for a
finite value.

Approximate addition, subtraction, multiplication, division, and `ABS` **MUST** use the
corresponding IEEE 754 binary32 or binary64 operation with round-to-nearest, ties-to-even. A mixed
approximate expression **MUST** use the wider operand domain. An exact numeric combined with an
approximate numeric **MUST** convert to the approximate operand's domain. IEEE infinities, NaN,
and signed zero **MUST** result from approximate overflow, invalid operations, and zero division;
an implementation **MUST NOT** replace those results with a host-specific exception.

The division operator **MUST** have at least one operand explicitly cast to `DOUBLE PRECISION`.
The result **MUST** be `DOUBLE PRECISION`; integer division and an engine's implicit fractional
division are outside the profile. `PERCENTILE_CONT(0.5)` **MUST** convert its ordering value to
`DOUBLE PRECISION`, perform linear interpolation in binary64, and return `DOUBLE PRECISION`.

Exact integer and decimal addition, subtraction, and multiplication **MUST** be mathematical over
the result domain. A rule whose admitted inputs can exceed `INTEGER` or `BIGINT` **MUST** cast its
operands to `DECIMAL(38,0)` before the operation. Overflow of the selected exact result domain is
an execution failure under §3.8; wraparound, saturation, and truncation **MUST NOT** occur.

The execution session time zone **MUST** be UTC. A `TIMESTAMP(6) WITH TIME ZONE` **MUST** denote an
instant at microsecond precision, and `INTERVAL '1' DAY` in this profile **MUST** add or subtract
86,400 elapsed seconds. The current plausibility rule **MUST NOT** inherit a host daylight-saving
transition.

Character comparison, grouping, `DISTINCT`, set operations, ordering, and `LIKE` literal matching
**MUST** operate on the stored Unicode scalar sequence in ascending scalar-value order, without
case folding or normalization. `%` and `_` retain their ISO `LIKE` wildcard meanings.

### 3.6 Bounded recursive common table expressions

The profile **MUST** admit a recursive common table expression only in a statically recognizable
bounded form. It **MUST**:

1. declare an integer depth column;
2. assign that column a non-negative integer literal in every non-recursive seed arm;
3. contain one self-reference in the recursive arm joined through `UNION ALL`;
4. assign the next depth as the prior depth plus a positive integer literal; and
5. guard the recursive arm by comparing the prior depth with a finite integer-literal upper bound.

Mutual recursion, more than one self-reference, a data-dependent bound, a non-increasing depth,
and another recursive form **MUST** make the registry document non-conforming before execution.
The four current recursive rules use the admitted depth-counter form and retain their rule-level
bound of 64. An execution resource limit remains a backstop and **MUST NOT** be treated as proof
that an otherwise unbounded query conforms.

### 3.7 Finding-relation semantics

A completed Tier 2 query **MUST** produce a typed, unordered bag of rows. Row order **MUST NOT**
carry meaning; duplicate multiplicity **MUST** carry meaning. An empty bag **MUST** pass that rule,
and every row of a non-empty bag **MUST** be an offending row for the rule's declared finding.

Every final projected column **MUST** have one unique lower-snake-case name. A simple column
reference **MAY** inherit its declared name when that name is unique in the result. Every other
expression, and either of two references with the same inherited name, **MUST** use an explicit
alias. The static profile check **MUST** reject a duplicate, unnamed, or nonconforming final name
before execution.

The six current interval-template results that repeat `start_tick` **MUST** project it once. In
`core.preferred_runs.activity_matches_run`, the preferred-row and processing-run activity values
**MUST** have distinct names. In `core.preferred_runs.run_in_session`, the preferred-row and
processing-run session values **MUST** have distinct names. These changes **MUST NOT** alter a
predicate, rule ID, level, message, violating source-row set, duplicate multiplicity, or pass/fail
outcome.

A report **MAY** serialize or sample fewer rows only under the later report contract. A sample
**MUST NOT** redefine the complete rule result or silently imply that omitted rows do not exist.

### 3.8 Invalid, unsupported, incomplete, and finding outcomes

SQL outside the selected profile **MUST** make its registry document non-conforming. A validator
**MUST** reject it before execution and **MUST NOT** report the parser or profile defect as an
offending packet row from that rule.

A validator that does not support the registry's exact `rule_language` **MUST** report that the
registry's Tier 2 evaluation is unsupported. A validator that supports the language but cannot
complete a valid rule because an input is unreadable, the engine fails, an exact arithmetic result
overflows, or a resource or timeout limit is reached **MUST** report that evaluation as incomplete.
It **MUST NOT** fabricate an error-level packet finding from its own inability to evaluate the
rule.

Only a completed query returning rows **MUST** produce that query's declared finding. A required
Tier 2 evaluation that is invalid, unsupported, or incomplete **MUST NOT** support a claim that the
affected core or extension registry passed, and a validator **MUST NOT** report the complete packet
as conforming from the mere absence of an error-level finding. P7 **MUST** remain responsible for
the final report representation and the composition of complete, incomplete, core, and extension
results.

Core and each extension **MUST** retain separate evaluation state. An unsupported or incomplete
extension evaluation **MUST NOT** be attributed to core and **MUST NOT** be relabeled as an
extension rule failure. It also **MUST NOT** be silently omitted from a complete-packet claim.

### 3.9 The catalog-to-session comparison is a shim check

`core.sessions.manifest_sessions_match` **MUST** cease to be a Tier 2 SQL rule. Part 05 §5.3's
shim **MUST** compare the packet catalog's session inventory with the values of
`core.sessions.session_name`, because only that boundary can observe both artifacts.

The shim check **MUST** retain the exact check ID, `error` level, message, and offending string
values. It **MUST** report each `core.sessions` row whose non-null `session_name` is absent from the
catalog inventory and each catalog session string absent from every `core.sessions` row. It
**MUST** preserve duplicate unmatched table values and **MUST NOT** add the catalog as a hidden SQL
relation. The existing Tier 1 non-null check remains responsible for a null required
`session_name`.

P6 **MAY** later replace or generalize this shim when it reconciles manifest requiredness and
registry binding, but no Tier 2 rule **MAY** depend on the interim implementation mechanism.

### 3.10 Incremental revalidation uses parsed dependencies

For Part 03 §9.4, a Tier 2 rule **MUST** be re-run when it is attached to a resource an amendment
writes or when the base-relation set produced under §3.3 contains a resource the amendment writes.
A validator **MUST NOT** decide that dependency by searching query text for a flattened name.

A syntactically valid local alias, common table expression, string literal, or comment **MUST NOT**
create a dependency. Where static profile validation cannot establish a rule's complete base-
relation set, the registry document is non-conforming; a validator **MUST NOT** use uncertainty to
skip the rule. Part 03's existing over-inclusive fallback for any other uncertain input **MUST**
remain.

### 3.11 Registry and rule migration

The registry meta-schema `$id` and every shipped registry's `$schema` **MUST** change to
`https://escapewheel.org/schemas/registry/0.3.0`. The meta-schema **MUST** require
`rule_language` as a non-empty string and **MUST NOT** add a per-rule language or dependency field.

The candidate registry documents **MUST** carry these versions after their shape and rule text
change:

| registry | current version after incorporation |
|---|---|
| core | `0.3.0` |
| `aind_opto` | `0.3.0` |
| `aind_unit_qc` | `0.2.0` |
| `dynamic_foraging` | `0.4.0` |
| `vr_foraging` | `0.3.0` |

The core rule source and all four extension registries **MUST** migrate their 121 retained rules to
canonical qualified relation names and the profile's standard spellings. Expressions that can
overflow a stored integer **MUST** use the wider exact type from §3.5, and every fractional
division **MUST** use the required explicit double operand. The median rule **MUST** use the
profile's ordered-set expression; the one day literal **MUST** use its standard form; and the eight
duplicate result projections **MUST** be repaired under §3.7.

The reference validator **MUST** create schema-qualified packet-local relations, statically check
every Tier 2 rule, lock the deterministic settings in §§3.4–3.5, disable external state and side
effects defensively, and execute only checked queries. The directly maintained profile and schema
**MUST** be vendored with the validator by the registry build and mechanically compared with their
sources.

Development packets and embedded registries **MUST** be regenerated together. No migration
guarantee applies to the earlier unreleased shape. P10 **MAY** assign later final release
identifiers only through its own reviewed decision; it **MUST NOT** mutate this profile's contract
while retaining `escapewheel-rule-sql-v0.1`.

## 4. What this does not change

- Tier 1 invariant meaning remains derived from registry structure and independent of SQL emitted
  by the reference generator.
- Scientific concepts, table columns, stored Parquet values, array and media encodings, and packet
  catalog shape do not change.
- A reader remains able to open ordinary packet resources without embedding a SQL engine. A
  reader's public ad hoc query interface may expose a broader engine dialect; it does not define
  registry-rule conformance.
- P4 still owns uniform non-JSON registry-document invariants and invocation at every registry
  boundary. P6 still owns general packet-to-registry binding and requiredness. P7 still owns final
  report serialization, sampling, coverage, and validity composition.
- The rule language defines how a present predicate treats NaN. It does not decide whether each
  scientific domain predicate should admit NaN; P9 retains that separate audit.
- Adapter protocols and source-specific extraction do not change.

## 5. Consequence

This is an intentionally incompatible change to unreleased registry documents and development
packets. Registry and meta-schema identities change, every registry selects the language, 121 SQL
rules are rewritten, one check moves to the shim, and packet copies are regenerated. Stored table
shapes and scientific data do not change.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged because no scientific concept changes meaning. | No authored Part 01 change; semantic review against the Decision. |
| logical prose and registry | Expand Part 02, incorporate the profile and schema, add `rule_language`, update identities, rewrite 121 rules, remove one SQL rule, and repair eight results. | Meta-schema validation; profile-schema validation; static check of core and all extensions; exact rule inventory and predicate-equivalence review. |
| physical profiles | Replace Part 03 §9.4's flattened text search with parsed base-relation dependencies; stored encodings remain unchanged. | Focused incremental-revalidation tests and no physical-format diff. |
| packet catalog and JSON Schemas | Catalog shape is unchanged; its session inventory is read by a Part 05 shim rather than an SQL relation. | Manifest schema remains byte-identical; orphan-session corpus finding retains its ID and outcome. |
| validation and import | Check profile conformance before execution, distinguish four outcome classes, move the session check, and forbid a conformance claim on incomplete evaluation. | Positive, rejection, runtime-failure, timeout, and unsupported-language tests; corpus expectations. |
| extensions | Add the language declaration and versions, qualify relation names, and enforce core-plus-own visibility and separate incomplete state. | All four extension documents validate; cross-extension and forbidden-language negative cases fail before execution. |
| reader, writer, validator, adapters | Validator gains the checker, relation environment, deterministic settings, and failure state; writer embeds regenerated registries. Reader ordinary access and adapters remain behaviorally unchanged. | Focused validator and writer suites; reader packet-open regression; implementation citation check. |
| conformance fixtures and tests | Add typed semantic vectors, syntax rejection cases, security probes, dependency cases, and preserved packet findings. | Named vector runner and package tests pass; all 28 packet variants retain expected outcomes except intentionally richer incomplete-state assertions. |
| revision process and tooling | No lifecycle semantics change. Add structural anchors, ledger destinations, registry pointers, and clause evidence. | Anchor-bootstrap check, headings, ledger, evidence, stages, citations, and repoint checks pass. |
| generated publications and developer documentation | Regenerate registry JSON, tables, READMEs, vendored artifacts, combined specification, examples, and current counts. | Generators preserve the final candidate state and examples name qualified relations. |

## 6. Conformance and implementation evidence

The incorporation must supply machine-readable vectors under `conformance/rule-language/` and a
runner used by the repository verifier. Each vector names the profile, input registry types and
rows, query or rejected text, expected typed result bag or failure class, and whether row order is
ignored. The evidence is not a second language definition; it exercises the incorporated profile.

The vector set and focused package tests must establish at least:

1. all 121 retained core and extension rules pass static profile checking, bind only authorized
   qualified resources, and execute against typed empty relations;
2. DDL, DML, multiple statements, system catalogs, configuration, external table functions,
   filesystem access, unknown routines, undeclared relations, cross-extension relations,
   unbounded recursion, duplicate output names, and non-profile types are rejected before the
   execution function is called;
3. nulls, infinities, NaNs, signed zero, approximate zero division, integer extrema, decimal
   overflow, explicit fractional division, odd and even medians, timestamp values across a host
   daylight-saving transition, Unicode scalar ordering, window ties, and duplicate result rows
   produce the specified typed results under more than one host time-zone setting;
4. `a.b_c` and `a_b.c` remain distinct qualified resources while their former flattened aliases
   are unavailable;
5. an absent resource binds as a typed empty relation, while an unreadable declared dependency
   produces incomplete evaluation rather than an empty pass;
6. unsupported language, invalid query, engine exception, resource limit, timeout, empty result,
   and non-empty result remain distinct outcomes, and no incomplete required evaluation produces a
   conforming-packet claim;
7. the four recursive rules pass the bounded-form checker, while mutations of each of the five
   required structural elements fail before execution;
8. the six interval-template results and two preferred-run results have unique expected names and
   retain their prior violating source-row bags and pass/fail outcomes;
9. `core.sessions.manifest_sessions_match` is absent from every registry rule list, is produced by
   the shim for each existing positive and negative corpus case, and has no `manifest_sessions`
   relation in the SQL environment;
10. amendment dependency selection uses parsed base resources and is unaffected by resource-like
    text in an alias, common table expression, literal, or comment; and
11. the focused validator, writer, reader, extension, registry, conformance-corpus, and complete
    repository suites pass after generation.

### 6.1 Completed anchor bootstrap

Commit `b78fd3fc246469e2c8d1fb78a277c4ec9fe16595` added one canonical anchor immediately before each
affected existing heading that lacked one:

| current heading | canonical anchor |
|---|---|
| Part 02 §10.2 | `ew-tier-2-rules` |
| Part 03 §9.4 | `ew-incremental-revalidation` |
| Part 05 §5.2 | `ew-tier-2-validation` |
| Part 05 §5.3 | `ew-validation-shim` |
| Part 09 §5.4 | `ew-extension-verdicts` |

Part 00 §10, Part 02 §§1, 9.1, and 9.2, and Part 05 §10 already have canonical anchors. The new
Part 02 child headings and the new subsection under Part 05 §9 receive anchors when created. The
metadata-only comparator found no change between the bootstrap and its parent other than the five
canonical-anchor insertions; no heading, numbering, order, prose, normativity marker, or alias
changed.

## 7. Open

P4 will define and apply the remaining whole-registry invariants uniformly. P6 will define general
packet-to-registry binding and required-resource declarations. P7 will define the report's exact
machine shape, finding sampling, coverage, and validity composition. P9 will audit domain-specific
NaN acceptance. P10 will settle final release identifiers, and P11 will freeze publication bytes.
Those later decisions may build on or supersede this contract through their own revisions; none is
needed to interpret the Decision above.
