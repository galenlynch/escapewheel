# Define a Portable Tier 2 Rule Language

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-21 |
| **Based on** | `2378763ec5afc398f25e0b3ab68c9027fc4a86dd` |
| **Decision domain** | specification |
| **Affects** | Part 00 §10, Part 02 §10.2, Part 03 §9.4, Part 05 §5.2 and §9, Part 09 §5.4, registry documents, Tier 2 rules, and validators |

## 1. Problem

Part 02 §10.2 says that a Tier 2 rule is SQL returning offending rows, and that an empty result
passes while a non-empty result fails. It does not identify a SQL edition or dialect, define the
relations visible to the query, map registry types into SQL types, delimit the permitted query
surface, or settle null, NaN, arithmetic, timestamp, collation, result, and execution-error
semantics. A validator therefore cannot tell from a registry document whether it supports a rule,
and two implementations can conform to the written protocol while returning different rows.

The omission is also a safety boundary. A packet embeds registry documents whose SQL the reference
validator currently passes to DuckDB without first restricting it to a read-only relational query.
SQL outside the intended validation subset can inspect external state, alter the execution
environment, or perform work unrelated to the declared packet relations.

This proposal explores a versioned, query-only subset of ISO SQL/Foundation. Escapewheel would
define only the profile and the semantics that ISO SQL leaves open for this data model. DuckDB
would remain the tested reference engine, not the language authority.

## 2. Evidence

### 2.1 Current owners and dependency state

At the baseline commit:

- Part 02 §10.2 owns Tier 2 declaration and the empty/non-empty execution protocol.
- Part 05 §5.2 invokes those rules during validation, and Part 05 §9 says that query result rows are the
  finding.
- Part 03 §9.4 decides incremental revalidation by searching SQL text for flattened resource
  names.
- Part 09 §5.4 owns the separation of core and extension validation.
- Part 00 §10 expressly identifies the missing Tier 2 language as a release-blocking candidate
  defect and forbids observed library behavior from silently becoming authority.
- `registry/registry.schema.json` requires `id`, `level`, `message`, and `sql` for each rule, but
  carries no rule-language identifier.

There were no open proposals or drafts. Relevant accepted history is R2 (registry format and the
original SQL choice), R24 (build-time rule templates), R26 (advisory execution), R35 (incremental
revalidation), R94 (rules do not name optional columns), and R122 (current authority and release
blocking). P4 depends on this work for whole-registry conformance; P6 and P7 later settle packet
registry binding and validity composition.

The impact scan for Part 02 §10.2, Part 05 §5.2, and Part 00 §10 found 17 live citations. In
addition to the numbered parts, they reach the validator generator and registry-document checks,
the corpus, registry checks and rendering, the registry README, and the reconciliation roadmap.

### 2.2 The released rule surface is small enough to profile

The generated core registry contains 77 Tier 2 rules over 27 of its 43 tables. Four extension
registries contain another 45 rules over 10 of their 11 tables. Parsing all 122 queries with the
installed DuckDB 1.5.5 parser found this complete authored function and operator surface:

```text
arithmetic       +  -  *  /
scalar           abs  coalesce  cast
aggregate        count  min  max  median
window           lag  row_number  dense_rank
predicate        comparisons  between  distinct-from  null  in  like  exists
relational       select  join  group/having  distinct  subquery
                 union/union-all  with  with-recursive
```

The rules use ordinary relational constructs rather than DuckDB file functions, macros, nested
types, `QUALIFY`, `GROUP BY ALL`, or other broad dialect extensions. The principal authored
non-portable spelling is `median(gap)`. DuckDB accepts the standard ordered-set spelling
`percentile_cont(0.5) WITHIN GROUP (ORDER BY gap)` with the same results for odd and even input
counts. It also accepts the standard `INTERVAL '1' DAY` spelling used to replace the one
`INTERVAL 1 DAY` literal.

A non-writing feasibility probe created all registry relations under SQL schemas named for their
resource namespaces, changed flattened references such as `core_clocks` to `core.clocks`, and made
those two standard-form substitutions. All 121 rules whose inputs are registry tables parsed,
bound, and executed against empty relations. The one excluded rule reads the validator-created
`manifest_sessions` relation rather than a registry table; §2.5 treats that separately.

This establishes that a standard subset can carry the present rule corpus. It does not establish
the rules' data semantics; empty relations exercise neither predicates nor result rows.

### 2.3 Current results depend on the host and engine

The Python projects require `duckdb>=1.5.5`, not an exact semantic version. DuckDB documents its
language as a PostgreSQL-derived dialect and records differences from PostgreSQL in integer
division, floating division by zero, and implicit conversion. Its documented NaN ordering also
differs from ordinary IEEE comparisons. The project's current queries rely on some of those
choices without declaring them.

Reproducible probes against the installed DuckDB 1.5.5 showed:

```text
1::BIGINT / 2::BIGINT                         -> 0.5
'NaN'::DOUBLE <= 0.0                          -> false
'NaN'::DOUBLE > 1.0                           -> true
9223372036854775807::BIGINT - -1::BIGINT      -> overflow error
```

The validation connection inherits the host time zone. With identical rows around the 2026
spring daylight-saving transition, `core.clocks.tick_zero_plausible` returned zero offending rows
under `UTC` and one under `America/Los_Angeles`. The query's `TIMESTAMP WITH TIME ZONE + INTERVAL
'1' DAY` bound denoted 24 elapsed hours in the first session and 23 in the second. A packet's
verdict can therefore depend on where it is validated.

The current checker executes every query against empty DuckDB tables. That catches syntax and
stale column names, but not null behavior, non-finite values, overflow, division, time zones,
collation, window ties, duplicate results, or runtime failure on legal boundary values.

### 2.4 Unrestricted embedded SQL is not a validation language

DuckDB's own [security guidance](https://duckdb.org/docs/current/operations_manual/securing_duckdb/overview)
states that SQL can read arbitrary files with functions such as `read_csv` and `read_text`, and can
write through `COPY` unless external access is constrained. The current rule meta-schema accepts
any non-empty SQL string. The reference validator then executes core and embedded-extension rules
on the same connection that can reach packet resources. It does not first require one query,
reject table functions or side-effecting statements, restrict relation references, disable
environment-dependent functions, or lock session configuration.

Resource limits bound memory and threads, but do not turn unrestricted SQL into a read-only,
packet-local language. A safe language needs a positive syntax and function profile checked before
execution, plus a locked execution environment.

### 2.5 Relation and result drift is already visible

Registry resource identity is dotted, but current SQL flattens `core.units` to `core_units`. The
mapping is not injective for all names admitted by the meta-schema: `a.b_c` and `a_b.c` both become
`a_b_c`. Standard schema-qualified names can preserve the resource ID directly.

One core rule reads `manifest_sessions`, a relation constructed in validator code from the packet
catalog. It is absent from the registry and contradicts Part 05 §5.3's placement of
catalog-to-table comparisons in the non-SQL shim. Keeping it as a hidden relation would make the
new language environment partly data-driven and partly implementation-defined.

Eight current rules produce duplicate result-column names. Six interval-template results repeat
`start_tick`; two `core.preferred_runs` rules project different values under duplicate
`activity_type` or `session_id` names. The Python report discards all result-column names and keeps
only the first five stringified rows. The empty/non-empty verdict is defined, but the meaning and
comparability of the purported finding relation are not.

### 2.6 Established specifications and test practice

The applicable standard is [ISO/IEC 9075-2:2023, SQL/Foundation](https://www.iso.org/standard/76584.html),
as corrected by [Technical Corrigendum 1:2026](https://www.iso.org/standard/93691.html), under the
framework of [ISO/IEC 9075-1:2023](https://www.iso.org/standard/76583.html). It is a broad,
feature-based language rather than one small validator profile, so citing it does not by itself
select safe statements, optional features, implementation types, or floating-point behavior.

DuckDB's [SQL dialect overview](https://duckdb.org/docs/current/sql/dialect/overview) confirms that
its own dialect is not identical to ISO SQL or PostgreSQL. Its
[SQLLogicTest documentation](https://duckdb.org/docs/lts/dev/sqllogictest/intro) demonstrates the
established pattern of executable query inputs, expected results, expected errors, and explicit
result-order treatment. Escapewheel needs typed packet-domain vectors rather than adopting that
test file format wholesale, but the same separation of language definition from executable
evidence applies.

## 3. Desired outcome and constraints

A successful resolution should:

- give every Tier 2 registry document one exact, machine-readable language identifier;
- define a query-only ISO SQL/Foundation subset sufficient for all released core and extension
  rules, without making the rest of DuckDB SQL available implicitly;
- bind queries only to registry-declared logical relations using their canonical resource IDs;
- define the registry-to-SQL type mapping and all semantics that can change offending rows;
- make query evaluation deterministic across hosts and conforming implementations;
- let a validator distinguish an unsupported language, a non-conforming registry rule, a packet
  finding, and an execution failure;
- keep Tier 1's structural meaning independent of SQL generated by one implementation;
- reject external access, side effects, configuration changes, volatile functions, and undeclared
  relations before a rule is executed;
- provide positive and negative, typed data fixtures that exercise semantics rather than only
  parse empty tables; and
- preserve reading without a SQL engine.

The work should remain compatible with the data-driven architecture. Prose owns meaning and
processing semantics; a directly incorporated machine-readable profile can own exact feature and
function assignments; registry documents select that profile; validators interpret it; and
conformance vectors test the result. The profile must not turn DuckDB's parser AST or the reference
validator into normative authority.

There are no released external consumers or remote compatibility commitments. Development packets
and extension registries can be regenerated together. That permits correcting relation names,
registry shape, and finding projections now rather than preserving accidental prototype forms.

## 4. Options and tradeoffs

### 4.1 Keep unspecified SQL

This preserves every file but leaves P3's release blocker unresolved. A validator cannot advertise
support accurately, the host can change a verdict, and embedded SQL remains broader than the
packet-validation problem. Reject.

### 4.2 Make one DuckDB version the language

Pinning DuckDB 1.5.5 would be easy for the reference implementation and would identify current
behavior more closely than `>=1.5.5`. It would still make an implementation rather than a
language-neutral contract authoritative, expose a much larger and side-effecting SQL surface, and
require every validator to embed that exact engine. DuckDB's
[release calendar](https://duckdb.org/release_calendar) places 1.5.6 and 2.0.0 immediately after
the baseline, illustrating the maintenance cost. Reject as the normative model; retain DuckDB as
the reference implementation.

### 4.3 Define a versioned ISO SQL query profile

This is the preferred direction. `escapewheel-rule-sql-v0.1` would select only the standard query
constructs and routines the released rules need. Part 02 would define relation binding, logical
types, edge semantics, result meaning, and failure boundaries. A directly maintained JSON profile
would enumerate exact permitted features, operators, routines, and settings, while Part 02 would
incorporate it for those assignments. Every core and extension registry would declare the exact
profile ID once, rather than mixing languages rule by rule.

The candidate surface is:

- one query expression, optionally using subqueries, `WITH`, or a mechanically bounded
  `WITH RECURSIVE`;
- projection, filtering, grouping, `HAVING`, `DISTINCT`, standard joins, and `UNION` forms;
- standard scalar expressions, three-valued null logic, `CASE`, `CAST`, and `COALESCE`;
- the current standard aggregate and window-function set, replacing `median` with
  `percentile_cont`;
- no DDL, DML, transaction, catalog, configuration, import/export, attachment, extension, macro,
  table-function, volatile, filesystem, network, or environment surface; and
- no implicit relation or function added merely because the selected engine provides it.

Registry resources would be SQL schema-qualified names such as `core.units` and
`dynamic_foraging.trials`. Each registry table would be visible with its declared columns and type
mapping even when the packet omits the resource, in which case it is an empty relation as today.
Core rules could see core resources; an extension's rules could see core and that extension's own
resources. Common-table-expression names would remain local query names.

The logical type binding would use the corresponding standard scalar domains: `INTEGER`, `BIGINT`,
`REAL`, `DOUBLE PRECISION`, `BOOLEAN`, `DATE`, `TIMESTAMP WITH TIME ZONE`, and `CHARACTER VARYING`.
`json_string` would remain a character value; the rule profile would supply no JSON parser.

The execution environment would use UTC and a specified binary character collation. Integer
division intended to be fractional would use explicit `DOUBLE PRECISION` casts. Integer
arithmetic that can exceed a stored type would use an explicitly wider standard exact numeric
type. Rule expressions would be required to be total over all values admitted by their input
declarations; extrema and zero denominators would be fixture cases. Non-finite floating behavior
would be stated explicitly rather than inherited from an engine.

A rule result would be a typed, unordered bag of rows: row order would carry no meaning, while
duplicate multiplicity would. Every projected column would have one unique lower-snake-case name.
The report-format question of full results versus an explicitly marked sample can remain with P7,
but truncation could not redefine the rule result itself.

The language profile would be checked before query execution. Static validation would establish
that there is one permitted query, every base relation is authorized, every function and construct
is in the profile, and every result column is named uniquely. The execution connection would then
apply locked settings and resource limits. A parser implementation may use DuckDB's AST, but AST
field names would not appear in the normative profile.

The recursive form would be admitted only when the recursive relation carries an integer depth
column, the seed assigns it a non-negative integer literal, the recursive term increases it by a
positive integer literal, and that term filters the prior depth against a finite integer-literal
upper bound. This is the mechanically recognizable form used by all four current recursive rules;
an execution timeout remains a backstop rather than the definition of bounded recursion.

### 4.4 Replace SQL with a custom expression language

A smaller expression language could be easier to sandbox, but the existing rules need joins,
aggregates, windows, recursion, and subqueries. Recreating those facilities would amount to a new
relational language and require every validator to implement it. The standard SQL subset already
provides the needed abstraction and is supported by the chosen reference engine. Reject.

## 5. Impact sketch

| Surface | Expected effect |
|---|---|
| Architecture and normative references | Part 00 §10 adds exact ISO/IEC 9075-1 and 9075-2 references, including the applicable corrigendum, and removes the Tier 2 language from the initial release-blocking omissions once the new contract is incorporated. |
| Semantic prose | Unchanged. No scientific concept or packet fact changes meaning. |
| Logical prose | Part 02 §10.2 gains the language identifier, relation environment, type mapping, permitted query profile, edge semantics, result relation, and rule-validity boundary. Tier 1 remains structural and language-independent. |
| Registry meta-schema | Add a required registry-level `rule_language` string. Do not add a duplicate dependency list to each rule: authorized relation inputs are derived from the parsed query. |
| Registry declarations and rules | Core and all four extension registries declare the profile. Of the 122 current rules, 121 remain queries and change to qualified resource names and standard spellings; the catalog-crossing rule moves to the shim. Arithmetic and duplicate result projections are repaired where required. |
| Machine-readable language profile | Incorporate one new directly maintained, schema-validated profile for exact feature, function, operator, type-binding, and setting assignments. Its semantic interpretation remains in Part 02. |
| Physical profile | Stored table bytes and types do not change. Part 03 §9.4 replaces flattened text matching with parsed base-relation dependencies for incremental revalidation. |
| Packet catalog | Catalog shape is unchanged in P3. The catalog-to-`core.sessions` equality check moves out of Tier 2 to the existing Part 05 shim boundary while retaining its check identity and verdict behavior. P6 later reconciles manifest ownership and binding comprehensively. |
| Validation and reports | Part 05 distinguishes rule findings from unsupported-language, invalid-rule, and execution-failure states. The rule result is typed and unordered; P7 remains responsible for overall validity composition and report coverage. |
| Extensions | Each extension registry declares its rule language and is statically checked on the same language terms as core. Unsupported extension evaluation remains separate from core conformance, consistent with Part 09 §5.4. |
| Reader | Ordinary table and array reading remains SQL-independent. The public ad hoc DuckDB query API need not be restricted to the rule profile and may retain compatibility aliases; it does not define validation semantics. |
| Writer and adapters | No source fact or adapter protocol changes. Writers regenerate embedded registries and packets with the language declaration and rewritten rules. |
| Validator and code generation | Add a static rule-profile checker, schema-qualified validation relations, locked deterministic settings, distinct failure handling, and typed semantic-vector execution. Tier 1 SQL generation remains an implementation strategy. |
| Existing packets | Development packets are regenerated. No migration guarantee is needed; a registry lacking `rule_language` is an earlier development shape rather than a v0.2 release registry. |
| Fixtures and tests | Add typed positive, negative, rejection, and boundary vectors for every semantic class; retain packet corpus findings; add tests that forbidden queries are never executed. Empty-table parsing remains a fast check but no longer the semantic evidence. |
| Revision process and evidence | No lifecycle rule changes. Incorporation evidence will identify Part 02 and Part 05 owners, the exact profile and schema pointers, rewritten registries, validator tests, and conformance vectors. |
| Generated publications and developer documentation | Regenerate registry tables and the combined specification. Update registry, validator, extension, and example documentation to describe the profile and qualified relation names. |

P4 can then validate the language declaration and every rule through the same registry-document
path. P6 can bind packet catalogs to exact registries without inheriting a hidden SQL relation. P7
can compose conformance only after P3 distinguishes a finding from an incomplete evaluation. P10
can assign final release identifiers to the profile and its schema without redesigning the model.

## 6. Resolved direction

The user approved the following five resolutions on 2026-09-21. Together they define one language
contract; none is deferred to an engine default.

### 6.1 Machine-readable profile and registry-level negotiation

Part 02 will define the semantics of `escapewheel-rule-sql-v0.1` and expressly incorporate one
directly maintained, schema-validated JSON profile for its exact feature, operator, routine, type,
and execution-setting assignments. Every core or extension registry document will carry the
required top-level declaration:

```json
"rule_language": "escapewheel-rule-sql-v0.1"
```

The declaration applies atomically to every Tier 2 rule in that document. A document cannot mix
rule languages, and a rule does not repeat or override the registry-level ID. The registry
meta-schema checks the field's shape; P4 will make support and all non-JSON invariants part of the
uniform registry-document conformance path. A change to the language contract gets a new language
ID, while a change to a registry's particular declarations or queries gets a new registry version.

The profile will admit a recursive CTE only in the bounded form described in §4.3. The static
profile check will reject another recursive form before execution. All four released recursive
rules already use the required depth-counter structure and need only the relation-name and numeric
spelling changes required elsewhere in this proposal.

### 6.2 Relation names and the catalog-crossing rule

Tier 2 rules will name a registry resource by its canonical two-part, schema-qualified resource ID,
such as `core.units` or `dynamic_foraging.trials`. A base relation is visible only when declared by
the applicable core registry or by the extension registry whose rule is executing. A query may
give a relation a local alias and may define local common-table expressions, but flattened aliases
such as `core_units` are not part of the rule language.

`core.sessions.manifest_sessions_match` will move to the Part 05 shim because one input is a packet
catalog fact rather than a registry relation. Incorporation will preserve its check ID, level,
message, offending values, and corpus outcome; it will remove the undeclared `manifest_sessions`
SQL relation. P6 may later replace or generalize the shim mechanism when it reconciles manifest
requiredness and registry binding, but P3 will leave no hidden relation in the rule language.

### 6.3 Failure classification

SQL outside the declared profile makes its registry document non-conforming and is rejected before
execution. It is a registry-document defect, not a finding returned by the rule.

A validator that does not support the registry's exact `rule_language`, or that cannot complete a
valid rule because of an engine, resource, timeout, or other execution failure, has not established
the affected registry's Tier 2 result. It will report incomplete validation and will not convert
that inability into an error-level finding against packet data. P7 will define how incomplete core
or extension evaluation composes into the complete packet report and conformance claim. A query
that completes and returns rows remains the only way that query produces its declared finding.

### 6.4 Floating point, arithmetic, and time

The rule language will state a total floating-point order explicitly: negative infinity is below
finite values, positive infinity is above them, and NaN is equal to NaN and above every other
non-null floating value. Positive and negative zero compare equal. The profile will add exactly
two floating classifiers to the standard query subset: `isnan(value)` and `isfinite(value)` over
`REAL` or `DOUBLE PRECISION`. Each returns null for null, `isnan` is true only for NaN, and
`isfinite` is true only for a finite value. An engine's additional numeric routines do not enter
the language implicitly.

Fractional division will require an explicit `DOUBLE PRECISION` operand rather than depend on an
engine's integer-division choice. Integer expressions that can exceed a stored `INTEGER` or
`BIGINT` will cast to an adequate standard exact numeric type before the operation; the profile
will include `DECIMAL(38,0)` for that intermediate purpose. Released queries will be tested at
their admitted extrema and zero denominators. An arithmetic exception is an execution failure
under §6.3, not an offending row.

Timestamp operations will run with the session time zone fixed to UTC, so a day in the current
plausibility rule spans 86,400 elapsed seconds. Character comparison will use one binary collation
over the stored Unicode scalar sequence, without case folding or normalization. A later audit may
ask whether an individual scientific rule should accept or reject NaN; P3 preserves each current
predicate's result under the approved total order and does not infer a new domain requirement from
the language choice.

### 6.5 Finding-relation semantics

A rule result will be a typed, unordered bag of rows. Row order carries no meaning, while duplicate
multiplicity does. Every projected column will have one unique lower-snake-case name; an expression
whose name is not inherited uniquely from a declared column will use an explicit alias.

The six interval-template projections that repeat `start_tick` will report that value once. The two
`core.preferred_runs` projections will distinguish the preferred-row and processing-run values by
name. These repairs change no predicate, violating source-row set, level, or pass/fail outcome.
P7 will decide how a report serializes or explicitly samples the complete result; a report sample
will not redefine the result relation.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [x] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [x] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.

## 8. Promotion appraisal

**Disposition:** ready for promotion after the exact proposal is committed and the user explicitly
authorizes promotion.

The appraisal used baseline `2378763ec5afc398f25e0b3ab68c9027fc4a86dd`. P1 and P2 are complete,
no other proposal or draft overlaps this owner, and P4 remains correctly downstream of this
decision. The proposal changes the rule-language contract and development registry shape; it does
not change stored table types or promise compatibility for development packets. Core and extension
registries and packets will be regenerated together.

The five resolved sections form one usable contract and should not be split. A language identifier
without executable semantics would still be ambiguous; executable semantics without relation and
failure boundaries would still be unsafe; and result semantics without the same profile would not
be independently negotiable. The directly maintained profile will carry exact assignments while
Part 02 owns their meaning, preserving the data-driven architecture without making DuckDB or its
AST authoritative.

The draft can now state testable clauses for the profile identifier, query allowlist, bounded
recursive form, registry-to-SQL binding, deterministic edge behavior, result relation, and failure
classification. It can also name the corresponding meta-schema field, profile/schema artifacts,
rewritten registry sources, Part 05 shim check, conformance vectors, and validator obligations.
No source or destination section needs an anchor bootstrap before drafting; any new section will
receive its canonical anchor when incorporated.

The proposal deliberately leaves four downstream owners unchanged: P4 supplies uniform registry-
document conformance, P6 reconciles general catalog-to-registry binding, P7 composes incomplete
evaluation into the packet report, and P10 confirms final release identifiers. A separate P9
domain-rule audit will decide whether particular scientific predicates should reject NaN; P3 only
removes engine-dependent interpretation of their present predicates.

Checks run on 2026-09-21 produced these results:

- `revisions/stages.py`: one proposal, zero drafts, and all open artifacts structurally complete;
- `revisions/check_citations.py`: zero unresolved citations (historical loose and frozen-v0.1
  notices remain informational);
- `verify.py --quick`: all 28 stages passed after regeneration synchronized the two generated
  open-stage fact regions in the root `STATUS.md` and `TODO.md`; and
- `git diff --check`: passed.

No substantive question remains for promotion. The remaining unchecked criterion is the separate
authorization to replace this committed proposal with a revision draft.
