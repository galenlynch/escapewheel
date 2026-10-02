# Core declares a clock's transform in typed columns alone

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-10-02 |
| **Based on** | `e60b54e064d98c4479cf58dc18ba831fdfa75ea4` |
| **Decision domain** | specification |
| **Affects** | the core registry's `core.clocks` declaration and its `registry_version`; Part 02 §9.2's statement of that version; Part 02 §5.2's sentence on the `json_string` columns core declares; the ledger entries of R3 §3.4 and R152 §3.4 |

## 1. Problem

`core.clocks` is the core table holding one row for each clock of a session. It states a clock's
linear alignment to its parent clock in two typed columns, `transform_slope` and
`transform_offset`. It also declares a third column on the same subject: `transform_to_parent`, an
optional `json_string` described as "Clock alignment transform."

R3 §3.4 replaced `transform_to_parent` with the two typed columns. The registry gained the typed
columns and kept the column they replaced. No part says what that column holds, no rule reads it,
and no declared rule could read it. A writer can therefore state an alignment in JSON beside the
typed columns, and nothing compares the two.

## 2. Evidence

Each observation below was made on the tracked files at the baseline commit, where
`verify.py --quick` passes all 37 of its stages and reports 45 tables, 360 columns, 116 references
and 91 rules for the core registry.

### 2.1 R3 replaced the column and no later revision kept it

R3 §3.4 is headed with the column's name and opens "Replaced by typed columns on `core.clocks`".
R3 §2.2's table of affected columns gives it the disposition "typed columns", where the rows for
`core.events.payload`, the two `parameters` columns and `metadata` each become `json_string`.

A search of `revisions/accepted/` for the column's name finds five lines in four records. Two are
the R3 lines above. R13 §1 and R99 §2.2 each say that R3 §3.4 replaced the column; R99 §2.2 is
informative background and decides nothing about it. R94 §2, also informative, counts it among the
25 optional columns the registry declared when that revision was accepted. No record keeps the
column or gives it a meaning.

### 2.2 The registry has declared the column since its first version

`spec/source/core/core.clocks.toml` declares 15 columns and 12 rules. `transform_to_parent` is the
twelfth column: type `json_string`, presence `optional`, role `data`. The tenth and eleventh are
`transform_slope` and `transform_offset`, each a nullable finite `float64`. The generated registry
and the generated listing carry the same declaration.

The registry document as first committed, in `8db71976` on 2026-08-26, the day R3 was accepted,
already declares the column. The replacement therefore never reached the registry, and no later
change is needed to explain the declaration.

### 2.3 No rule reads the column and no declared rule could

Five of the twelve rules of `core.clocks` read `transform_slope`, and none of the registry's 91
rules names `transform_to_parent`, counted by searching each rule's SQL. Part 02 §10.2 forbids a
rule to reference a column whose presence is `optional`, and Part 02 §6 makes every `json_string`
column optional. A rule on this column is therefore not expressible.

Part 01 §3.9 has a clock declare "either a linear transform or anchor points, never both".
`core.clocks.one_alignment_model` checks that for `transform_slope` against `core.clock_anchors`.
Nothing checks a JSON transform against either.

### 2.4 No part says what the column holds

A search of the 13 files of `spec/parts/` for the column's name finds no line. Part 02 §5.2 says
that what goes in "the two `json_string` columns core declares" is stated by Part 02 §8.6 for
`metadata` and by Part 02 §12.6 for `core.processing_runs.parameters`.

That count disagrees with the registry. Reading every column of the generated registry finds 22
`json_string` columns, all optional and the only optional columns core declares, under four names:
`metadata` in 18 tables, `parameters` in `core.processing_runs` and `core.sorting_runs`,
`core.events.payload`, and `core.clocks.transform_to_parent`. Three of them have no stated
content: `payload`, the sorting run's `parameters`, and `transform_to_parent`.

Of those three, only `transform_to_parent` covers a subject that typed declarations already
state. Part 02 §12.6 puts three alignment facts in columns because a consumer needs them to place
a tick, and Part 02 §8.6 says that "A fact required to interpret the data belongs in a column,
never in a key." Every alignment fact a part names has a typed home: the two transform columns,
`core.clock_anchors`, `core.clock_phase_steps`, `core.sessions.alignment_bound`, and
`withheld_first_anchor` and `withheld_last_anchor` on `core.clocks`.

### 2.5 Nothing in the tree reads or writes the column

`git grep -c` over the 850 tracked files finds the name in 17.

| where | tracked files | lines naming the column |
|---|---:|---:|
| `spec/parts/` | 13 | 0 |
| the four packages, source and tests, with AIND's two extension registries | 356 | 0 |
| `extensions/`, the other two extension registries | 13 | 0 |
| `fixtures/` and `integration/` | 32 | 0 |
| `conformance/` | 59 | 1 |
| the registry source, the generated registry and the generated listing | 3 | 3 |

The one line under `conformance/` lists the columns R3 §2.2 names, in a sweep of the frozen v0.1
tables. The remaining lines are in accepted records, the frozen v0.1 documents, the ledger's note
on R3 §3.4 and working notes outside the specification.

The built conformance corpus holds 120 packets and 3,629 Parquet files. Reading each file's schema
finds 119 `core.clocks` files and the column in none of them, nor in any other table. Part 08 does
not mention a transform; it shows the core registry's version in its layout and in its manifest
excerpt.

No package source names the column, so no adapter in the tree delivers it. That is an inference
from the search and not a test. The session packets that R99 §2 measured are outside the tree and
were not inspected.

### 2.6 A column that no bound registry declares draws no finding

A probe built the corpus's valid session twice, each time adding a `transform_to_parent` string
column to the `core.clocks` file. One packet bound the baseline registry. The other bound a copy
with the declaration removed and `registry_version` set to `0.15.0`. The reference validator
passed both with no error and no warning, and reported the same 18 `info` findings for each, none
naming the column.

No part states a check for a file column that no bound registry declares; a search of Parts 02,
03, 05, 11 and 12 found none. Part 11 §3 exposes to a rule a table's registry-declared columns
"and no others", and Part 05 §15.6 compares an amendment's rows over declared columns. The
reference build refuses a record or a batch carrying a column that no loaded registry declares,
naming the column, and three tests of the writer's suite assert that refusal.

### 2.7 Each recent registry change advanced the version

Part 02 §9.2 states the core `registry_version` as `0.14.0` and forbids reusing a development
identifier "for an incompatible contract". R149 §3.4, R150 §3.10, R151 §3.2 and R152 §3.4 each
advanced the version by one minor step, from `0.10.0` to `0.14.0`. R151 added one rule to one table
and changed nothing else in the registry, which is the nearest case to removing one column.

Outside accepted records, the version is stated in these tracked places: the registry source's
`registry.toml`; the generated registry and listing; Part 02 §9.2; the specification README's
identifier table and the sentence after it; Part 08's layout and manifest excerpt; five lines of
the combined rendering; two constants in the tree's tools, one the structural check's expected
version and one the README projection's; and two lines of one writer test. No package source
states it. No package carries a copy of the core registry: the three packages that copy from the
tree copy schemas, descriptors and checkers.

The column count of 360 appears in five generated lines: the listing, the source guide, two root
status documents and the validator's README.

### 2.8 The tree regenerates without the column

A second probe copied `spec/`, deleted the column's entry, and set the version to `0.15.0` in the
registry source, Part 02 §9.2, the README and the two tool constants. The tree's build regenerated
the registry, the listing and the source guide, and the tree's check passed at 45 tables, 359
columns, 116 references and 91 rules. The generated registry lost the seven lines of the column's
object and changed its version line.

### 2.9 No ledger pointer moves

The ledger records R3 §3.4 as `registry`, with the note "core.clocks gains transform_slope and
transform_offset; the replaced transform_to_parent is still declared". Its four targets are the
names of the tenth and eleventh columns of `core.clocks` and the identifiers of its fourth and
fifth rules, `core.clocks.transform_pair_complete` and `core.clocks.transform_requires_parent`.
A target stores a zero-based JSON Pointer index, so those columns appear there as 9 and 10.

The registry-target map and the evidence manifests hold 11 pointers into the columns of
`core.clocks`. Each names the fourth, tenth or eleventh column. Removing the twelfth shifts the
three columns after it, which no pointer names, and removes no rule.

The ledger records R152 §3.4 as `applied` at Part 02 §9.2 with the note "meta-schema 0.11.0 and
core 0.14.0", and records R151 §3.2, whose whole clause was the version, as `superseded` by R152.

### 2.10 One open draft also changes the core registry

Five drafts are open and no other proposal is. Four of them name neither `core.clocks`, the
registry source nor `registry_version`. `core-declares-a-catalog-of-sidecars.md` amends the core
registry: it adds two declarations, taking 48 to 50, one of them a table with a `metadata` column.
A search of that draft for `registry_version` and for a version identifier finds neither, so it
states no advance of the version.

`the-ledger-resolves-a-superseded-entrys-successor-and-keeps-no-ratchet.md` states how the ledger
records a clause that a later revision replaced in part, which is the case of R152 §3.4 here.

## 3. Desired outcome and constraints

The core registry states a clock's linear alignment once, in typed columns, and declares no column
whose content no part states and no rule can read. The resolution preserves:

- R3 §3.4's two typed columns and the two rules on them;
- Part 01 §3.9's two alignment models and the rules that check them;
- the validity of a packet against the registry it binds (Part 04 §8); and
- the rule that one registry identifier names one contract (Part 02 §9.2).

## 4. Options and tradeoffs

| option | effect |
|---|---|
| keep the declaration | the registry keeps a column R3 §3.4 replaced, and a JSON alignment stays admissible beside the typed columns with no rule reading it (§2.3) |
| keep the column and give it a meaning | reverses R3 §3.4. If the meaning is an alignment, a consumer needs a JSON parser to place a tick, against Part 02 §8.6 and Part 02 §12.6, and Part 01 §3.9 needs a third model that no declared rule can check (§2.3). If the meaning is the source's own description, `core.clocks.metadata` already holds it |
| keep the column and forbid a writer to fill it | a declaration whose only rule is that it stays empty, which no declared rule can check, and which every listing still shows |
| remove the column and keep `0.14.0` | two documents with different declarations share one identifier, against Part 02 §9.2 and the four advances of §2.7 |
| remove the column as a correction with no revision | the change alters the incorporated registry's contract: a writer that fills the column writes a declared column before it and an undeclared one after |
| remove the column and advance the version (preferred direction) | `core.clocks` declares 14 columns, the version advances one minor step, and no part gains a sentence |

Under the preferred direction the core registry declares no `transform_to_parent` on `core.clocks`.
The other 14 columns keep their order and declarations, and the 12 rules are unchanged.

**The version advances one minor step.** It goes from `0.14.0` to `0.15.0`. The registry
meta-schema, the registry-contract descriptor and the rule language stay as they are, as under
R151 §3.2.

**No part gains a sentence for the removal.** Part 01 §3.9 states the two alignment models, and
the registry's descriptions and rules state the typed columns. The removal is a property of the
incorporated registry.

**No fact loses its home.** Part 01 §3.9 admits a linear transform and anchor points, and each has
typed declarations (§2.4). What a source states about a clock that the standard does not model
goes in `core.clocks.metadata` under Part 02 §8.6.

**A packet bound to `0.14.0` is unaffected.** It embeds the registry it binds, and a declaration
resolves only there (Part 04 §8), so such a packet validates as before whether or not it holds the
column. A packet built afterwards binds `0.15.0`. The reference build refuses an adapter that
still delivers the column. A packet that another writer builds with the column passes with the
column unreported, as a packet holding any undeclared column does today (§2.6).

**R3 §3.4 stays `registry` in the ledger.** It keeps its four targets, and its note says that the
replaced column is no longer declared and names the removing clause. The removing clause is itself
`registry`, placed by a pointer to the `core.clocks` table, since a removal leaves no child to
point at. The version clause is `applied` at Part 02 §9.2. R152 §3.4 keeps `applied`, since its
meta-schema and descriptor rows remain, and its note names the clause that advances the version.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. Part 01 §3.9 already admits two alignment models and neither is JSON. |
| logical prose, registry meta-schema, declarations and rules | The registry source drops one column and advances its version. Part 02 §9.2 states the new version. Part 02 §5.2 changes only under question 1. The meta-schema, the descriptor and every rule are unchanged. |
| physical profiles | Unchanged. A table's stored order and encodings do not depend on the column. |
| packet manifest and other JSON Schemas | Unchanged. A registry descriptor's `version` is a pattern and carries no fixed value. |
| validation and import | Unchanged in rule. No check names the column, and Tier 1 generates nothing for an optional `json_string`. Question 2 asks about a check on undeclared columns. |
| extension registries | Unchanged. None of the four declares, references or reads the column, and each advances its own version independently. |
| reader, writer, validator, adapters, code generation | No package source changes (§2.5). One writer test pinning the core version follows it. An adapter outside the tree that delivers the column is refused by the reference build until it stops. |
| existing packets | A packet bound to `0.14.0` stays valid against that registry. A rebuild binds `0.15.0`. Whether either session packet holds the column is unknown and does not change its validity. |
| conformance fixtures and implementation tests | No corpus packet changes verdict; each binds the new version once rebuilt. No new fixture, since no check distinguishes a file with the column from one without. The registry checks at 359 columns are the evidence. |
| revision lifecycle, ledger, evidence and tooling | Two new ledger entries and one registry target, and the notes on R3 §3.4 and R152 §3.4. No existing pointer moves (§2.9). The tree's two expected-version constants follow. |
| generated publications and developer documentation | The generated registry, listing, source guide and combined rendering regenerate. Part 08's layout and manifest excerpt show the new version. The five generated count lines read 359. |

## 6. Open questions

1. Whether the revision also corrects Part 02 §5.2's count of `json_string` columns. After the
   removal the registry declares such columns under three names where the sentence says two.
   - Leave the sentence. The revision then amends only the registry and Part 02 §9.2, and the
     sentence still says two where the registry declares three names.
   - Restate it without a count, naming the two columns whose content a part states (preferred
     answer). The revision then amends Part 02 §5.2 in place, and that section needs a canonical
     anchor first.
   - Also state what `core.events.payload` and `core.sorting_runs.parameters` hold. That decides
     what an event carries and what a sorting run records, and neither answer changes the removal,
     so it belongs in a proposal of its own.
2. Whether a validator reports a file column that no bound registry declares.
   - No new check here (preferred answer). The property predates the removal and covers every
     table of every registry (§2.6). A packet built under `0.15.0` by a writer that still fills the
     column then passes with the column unreported.
   - The revision adds a check in Part 05 §5.3. Such a packet then draws a finding, and so does
     every packet of any registry holding a column its writer added, which changes the validator,
     the corpus and each extension's packets.
3. Which value the version takes where another revision changes the core registry first.
   - The draft names `0.14.0` and `0.15.0` and remeasures its counts and its version if
     `core-declares-a-catalog-of-sidecars.md` or another registry change is incorporated first
     (preferred answer). The two touch different declarations, so neither blocks the other.
   - The draft waits until that draft says whether it advances the version.

Questions 1 and 3 each fix a Decision clause, so both are needed before a draft is appraised.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [ ] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.
