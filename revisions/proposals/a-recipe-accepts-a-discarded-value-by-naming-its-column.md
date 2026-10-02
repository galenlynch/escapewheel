# A recipe accepts a discarded value by naming its column

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-10-02 |
| **Based on** | `e60b54e064d98c4479cf58dc18ba831fdfa75ea4` |
| **Decision domain** | specification |
| **Affects** | Part 05 §3.4's sentence on resolving a discarded value; Part 05 §3.1's `overrides` row and the recipe schema it incorporates; Part 05 §3.5's refusals and reports; Part 05 §3.6's report of an idle override |

## 1. Problem

A recipe that lists two sources able to supply one resource declares a preference between them,
and a build takes the preferred source's rows and discards the other's (Part 05 §3.3). Part 05 §3.4
has the build refuse where that discards a value: where the passed-over source states a value in a
column the preferred source leaves null. The same section names three ways a recipe resolves the
refusal, and the first is naming the fact in `[overrides]` with its reason.

No recipe can write that first resolution. `[overrides]` is the table in which a recipe declares
that its own value for a session or subject field supersedes a source's (Part 05 §3.6). Its keys
are `block.field` names, so the recipe schema refuses a key that spells the refused column, and no
sentence requires a build to honour an entry. The reference build refuses with an entry in place,
in a message that recommends adding one.

Where each of two sources holds a column the other lacks, the second resolution fails as well,
since either preference discards a value. The third, correcting a source, is not always in the
hands of the recipe's author, and then no recipe builds.

## 2. Evidence

Observed in the tracked files at the baseline commit, where `verify.py --quick` passes all 37 of
its stages. Two probes ran the incorporated recipe schema and the reference build's refusal over
hand-written recipes and rows, and changed no tracked file.

### 2.1 Part 05 §3.4 states the override resolution and binds no build to it

Part 05 §3.4 requires a build to refuse "where a preference discards a value another source
stated", and forbids it to compose a row from more than one source. The next sentence reads: "A
recipe resolves the refusal by naming the fact in `[overrides]` with its reason, by preferring the
other source, or by correcting the source that states less." Its subject is a recipe, and it gives
a build nothing to do, where the refusal and the prohibition before it each bind a build with a
keyword.

A search of `spec/parts/` for `overrides` finds five lines: the table row of Part 05 §3.1, the
sentence above, the refusal of the member in an amending recipe in Part 05 §3.5, the definition in
Part 05 §3.6, and a rationale in Part 05 §3.8. The definition gives the table one purpose, a recipe
declaring "that its own value supersedes the source's". No part says what an entry does for a
preference.

### 2.2 R108 §3.3 states the rule with force and a `block.field` key

R108 §3.3 requires an `[overrides]` entry naming a fact to silence the refusal for that fact. It
calls the table R87 §2.5's, "keyed the same `block.field` way and carrying the reason it requires",
and it fixes the unit: "an entry silences that column and no other". The ledger records R108 §3.3
as `applied` at Part 05 §3.4.

A search of `revisions/accepted/` for `[overrides]` finds four revisions: R87, R108, R133 and R150.
Neither of the two after R108 restates the rule or withdraws it.

### 2.3 The recipe schema refuses the key that spells the refused column

The incorporated recipe schema constrains each `[overrides]` key to
`^[a-z][a-z0-9_]*\.[a-z0-9_]+$`, which is two segments. A recipe carries facts in two blocks,
`[session]` and `[subject]`, for `core.sessions` and `core.subjects`, and R87 §2.8 keeps
`core.sessions` with the recipe. A preference can name any resource more than one listed source
produces (Part 05 §3.3). A `block.field` key therefore reaches the columns of one table a
preference can arbitrate, `core.subjects`, out of the 45 tables the core registry declares.

Six keys were validated against the schema. It admits `subject.strain`,
`session.session_start_time` and `core.probes`. It refuses `core.probes.probe_type`,
`core.subjects.strain` and `aind_unit_qc.metrics.num_spikes_used`. `core.probes` passes because it
has two segments, although it names no block and no column.

### 2.4 A column of a resource already has a three-segment spelling

Part 05 §3.8 keys a recipe's `[encoding]` table `resource.column`, and the schema puts no pattern
on those keys. The registry meta-schema spells a resource identifier as two segments and a column
name as one, and spells a column of a resource as three segments in `discriminates_via` and
`specialises`. Each of the core registry's 48 resource identifiers has exactly one dot, and each of
its 360 column names is one segment. A three-segment key therefore names one column of one resource
and cannot be read as a `block.field` key.

### 2.5 The refusal has three shapes, and one of them names a column

Part 05 §3.4 refuses "where a passed-over source's row holds a non-null value in a column the
preferred source's row leaves null, or does not produce at all", and calls a preferred source that
produces no rows the limiting case. The comparison leaves out `metadata`. The sentence does not say
which row of the preferred source a passed-over row is compared with.

The reference build pairs rows by the table's declared primary key, on the values the adapters
delivered. It reports three shapes of loss:

| shape | what the reference build reports |
|---|---|
| a null column in a row both sources produce | `core.probes.probe_type: sorter stated 'NP2000' and nwb left it null` |
| a row the preferred source does not produce | `core.probes: sorter stated a row nwb did not` |
| a preferred source producing no rows | `core.probes: sorter stated 1 row(s) and nwb staged none` |

The first names a column in the spelling of §2.4. The other two name a resource and no column.

Part 05 §3 uses "fact" for two units. In Part 05 §3.6 a fact is a field a recipe declares, one
value for the session or the subject. In Part 05 §3.4 the fact a recipe is to name is a value in a
column of a row some source produced.

### 2.6 The reference build refuses with an entry in place and recommends one

The probe recipe prefers the NWB source for `core.probes`, and the two sources produce one probe
row each: the NWB source leaves `probe_type` null and the sorter source states `NP2000`.

- With no `[overrides]` entry the build refuses, and its message says to declare the fact "in
  [overrides] with a reason, prefer the other source, or fix the one that states less". The code
  that refuses reads no `[overrides]` entry.
- With `"core.probes.probe_type"` as the key, the recipe fails the schema before any comparison.
- With `"probes.probe_type"`, the nearest key the schema admits, the build refuses as before, and
  the recipe check warns that the entry "overrides nothing; no source in this recipe states it".

The writer's suite has four cases for the refusal, and none carries an override.

### 2.7 Where each source holds a column the other lacks, neither preference builds

In a second probe the NWB source states `manufacturer` and leaves `probe_type` null, and the sorter
source states `probe_type` and leaves `manufacturer` null. Preferring the NWB source refuses over
`core.probes.probe_type`, and preferring the sorter source refuses over `core.probes.manufacturer`.
R108 §6 anticipated the case as "a refusal that no choice of source resolves".

Two other routes are closed. Part 05 §3.3 forbids `owns` for a resource two sources produce unless
a preference is declared, and Part 05 §3.4 forbids composing the row. Correcting a source is the
one resolution left, and R87 §2.5 describes the case an override exists for as an upstream defect
that will not be fixed in the file the build reads.

### 2.8 The idle-override report is defined on a field

Part 05 §3.6 requires a build to report an override "for a field the source agrees with, or that no
source states", and forbids it to refuse on either. Both conditions concern what a source states
for a recipe field. No adapter states a column of a preferred resource as a recipe field, so an
entry naming such a column meets the second condition on every build. The warning in §2.6 is that
report.

Part 05 §3.5 has two reports of the same kind: a declared field "some listed source states and no
override covers" is a warning, and one an override covers is information.

### 2.9 An amending recipe can declare a preference and cannot declare an override

Part 05 §3.5 has an amending build refuse "a `[subject]` member, or an `[overrides]` member".
Part 05 §3.3 says of an amending build that its "preferences arbitrate among the recipe's sources
only". An amending build can therefore meet the refusal of Part 05 §3.4, and the reference build
runs the comparison in an amending build as in any other.

### 2.10 The recipe schema's identifier has advanced with each change of its shape

Part 05 §3.1 incorporates the schema under the `$id`
`https://escapewheel.org/schemas/recipe/0.3.0`. R150 §3.10 advanced it from 0.1.0 to 0.2.0 and
R153 §3.7 set 0.3.0, each in a revision that added members to the schema. R138 §5 kept the `$id`
because it left the shape unchanged. No part states when the identifier advances. The writer's
packaged copy of the schema equals the incorporated artifact.

## 3. Desired outcome and constraints

Every resolution Part 05 §3.4 names is one a recipe can write and a build honours. The recipe of
§2.7 builds once it says which value it gives up and why. The resolution preserves:

- the refusal for every discarded value the recipe has not named;
- the prohibition in Part 05 §3.4 on composing a row from more than one source;
- one meaning for each `[overrides]` entry, so that a build can tell a stale entry from a used one;
- the conformance of every recipe the current schema admits; and
- every existing packet.

## 4. Options and tradeoffs

| option | effect |
|---|---|
| keep the current text | Part 05 §3.4 names a resolution no recipe can write, the ledger records R108 §3.3 as applied at a sentence that binds no build, and the recipe of §2.7 does not build |
| withdraw the override resolution | Part 05 §3.4 names two resolutions and the reference build's message is corrected; the recipe of §2.7 still does not build |
| give the sentence force and keep the `block.field` key | reaches `core.subjects` alone (§2.3); `subject.strain` then says either that the recipe's value stands or that the preferred source's null stands, and the report of §2.8 cannot tell which |
| an entry names a whole resource | releases a dropped row and an empty preferred source along with a null column, which leaves the preference unchecked for that resource, the state R108 §3.1 closed |
| a `[preference]` entry lists the columns it may discard | the acceptance sits beside the preference it qualifies and needs no second key form; Part 05 §3.3's entry gains a member, and the table that Part 05 §3.4 and R108 §3.3 name is not the one a recipe uses |
| `[overrides]` admits a `resource.column` key (preferred direction) | the key spells what the refusal names (§2.5), and one table lists every statement of a source the recipe sets aside; Part 05 §3.5 and Part 05 §3.6 then tell the two kinds of entry apart |

The preferred direction is described below. It calls an entry keyed `block.field` a field override
and an entry keyed `resource.column` a column override.

### 4.1 A column override names one column of a resource the recipe declares a preference for

The key is a resource identifier followed by a column name, three segments in all, as §2.4 finds
the registry meta-schema and `[encoding]` already spell a column.

```toml
[preference."core.probes"]
source = "nwb"
reason = "the NWB states a probe's manufacturer and serial number"

[overrides]
"core.probes.probe_type" = "the sorter infers the type from the stream name"
```

Part 05 §3.4 then names the unit as a column, and "fact" keeps the one meaning Part 05 §3.6 gives
it (§2.5).

### 4.2 A column override releases a null column in a row both sources produce

A build does not refuse over a value a passed-over source states in the named column where the
preferred source's corresponding row leaves that column null. The release covers every such row and
every passed-over source. It covers no other column.

A row the preferred source does not produce and a preferred source that produces no rows stay
refused. Neither loss names a column (§2.5), and a recipe that drops a whole row says that its two
sources disagree about what exists, which a statement about one column does not answer.

Two finer units were weighed. An entry for one row's column needs the recipe to name the row. A
recipe names an assigned row by its `*_name`, as a `preferred_run` entry's `scope` does, since the
identifier does not exist until the build assigns it, and twelve probes would then take twelve
entries carrying one reason. An entry for one passed-over source changes the value from a string to
a table, and differs from an entry for the column only in a recipe that lists three or more sources
producing the resource.

### 4.3 The packet holds the preferred source's row unchanged

A column override accepts a loss. The build stages the preferred source's row with its null and
discards the passed-over value, so the prohibition on composing a row stands. The recipe of §2.7
builds with one of the two values and a recorded reason for giving up the other. An author who
wants both values still has to correct a source.

### 4.4 The value stays a reason, and the recorded recipe carries it

The value is a non-empty string, as Part 05 §3.6 requires of a field override, and it says why the
passed-over value is given up. Part 05 §3.2 has the writer record the recipe in the import run's
parameters, so the entry and its reason reach the packet with no new member.

A build reports each release as information, naming the column, the passed-over source and the
reason, as Part 05 §3.5 has it report a field an override covers.

### 4.5 Each kind of entry has its own idle condition

A field override keeps the meaning Part 05 §3.6 gives it and releases nothing under Part 05 §3.4.
The idle report of Part 05 §3.6 and the two reports of Part 05 §3.5 apply to field overrides only
(§2.8).

A column override is idle where it released no value in the build. A build reports it and does not
refuse, for the reason R87 §2.5 gives: an entry that stopped applying leaves the packet correct. An
entry that can release nothing in any build of the recipe is refused before a source is opened, by
the discipline of Part 05 §3.3, which forbids a preference that arbitrates nothing. Two cases are
of that kind: the resource carries no preference in the recipe, and the column is `metadata` or one
the resource does not declare.

### 4.6 The recipe schema's identifier advances

The schema's `overrides` member admits a three-segment key beside the two-segment one, and the
value's constraint is unchanged. A JSON Schema pattern expresses both forms, as the registry
meta-schema's patterns show (§2.4). The shape changes, so the `$id` advances as it did at each
earlier change of shape (§2.10), and Part 05 §3.1 names the new identifier and both key forms.

Every recipe the 0.3.0 schema admits stays admitted. A build written to the 0.3.0 schema refuses a
recipe carrying a column override and names the key.

A build already holds each passed-over source's rows for a preferred resource in order to compare
them (Part 05 §3.4), so honouring an entry needs no input the build lacks.

### 4.7 The ledger records R108 §3.3 as superseded

The revision restates the rule of R108 §3.3 whole, with a different key and a stated scope, so the
entry of R108 §3.3 changes from `applied` at Part 05 §3.4 to `superseded`, naming that revision in
`by`. The ledger records R20 §2.4 the same way, as restated by R147 with a different key. The
revision's own clauses are `applied` at the four sections of Part 05 they amend.

Four entries stay `applied` and gain a note naming the later clause: R87 §2.5, whose table gains a
second key form; R133 §3.4, whose schema changes; R153 §3.7, whose recipe `$id` is replaced; and
R150 §3.5, if an amending recipe admits a column override.

Under the withdrawal option the entry of R108 §3.3 is `superseded` by the revision that withdraws
it. Under the current text it stays `applied` at a sentence that does not state its rule.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. An override is a fact about a build and no concept of Part 01. |
| logical prose, registry meta-schema, declarations and rules | Unchanged. No resource, column or rule changes, and the meta-schema's three-segment spelling is reused and not altered. |
| physical profiles | Unchanged. Part 12 §7's `states` names recipe fields, which a field override still answers, and no delivery changes. |
| packet manifest and other JSON Schemas | The recipe schema's `overrides` key pattern, its description and its `$id` change. The manifest, adapter and resource-document schemas are unchanged. |
| validation and import | Part 05 §3.1's row and `$id`; Part 05 §3.4's resolution sentence, which gains the release and names a column; Part 05 §3.5's two static refusals, the amending refusal and the wording of its two reports; Part 05 §3.6's idle report. No validator check is added: a packet does not show whether a build refused. |
| extension registries | Unchanged. A column override names an extension table's column as it names a core one, where a recipe prefers a source for that table. |
| reader, writer, validator, adapters, code generation | The reference build honours a column override, refuses the two static cases, reports a release and an idle entry, and keeps its message. Its packaged copy of the schema regenerates. Adapters, the reader and the validator are unchanged. |
| existing packets | Unchanged. No packet is rebuilt, and no tracked recipe changes meaning: the one tracked recipe file, the example under `spec/informative/`, carries one field override. |
| conformance fixtures and implementation tests | No packet fixture, since a packet does not show whether a build refused. Build tests: the recipe of §2.6 builds with a column override and stages a null; an entry for another column, a field override, a dropped row and an empty preferred source each still refuse; the recipe of §2.7 builds under either preference with one entry; the two static cases refuse before a source opens; an idle entry is reported. Schema tests: a three-segment key is admitted and a four-segment key refused. The example recipe gains a column override. |
| revision lifecycle, ledger, evidence and tooling | The ledger changes of §4.7 and the ordinary evidence record. No tool changes. |
| generated publications and developer documentation | The combined specification regenerates. The writer's guide documents both kinds of entry; a search of the tracked Markdown outside `spec/` and `revisions/` finds `overrides` in no package document. |

Of the five open drafts, one amends a section this proposal touches. The draft on recording a
recipe without its credentials extends the refusals of Part 05 §3.5, as §4.5 does, so whichever is
incorporated second rereads that list. It keeps the recipe schema unchanged and changes only values
a build recognizes as credentials in the recorded recipe, so a recorded `[overrides]` entry is
unaffected. The draft on the ledger's superseded entries requires the `by` field that §4.7 uses.
The other three touch no section named here. No other proposal is open.

## 6. Open questions

1. Which table carries the entry. `[overrides]` is the table Part 05 §3.4, R108 §3.3 and the
   reference build's message already name, and it then lists in one place every source statement a
   recipe sets aside; it costs a second key form and changes to Part 05 §3.5 and Part 05 §3.6. A
   member of the `[preference]` entry cannot name a resource without a preference, is already
   admitted in an amending recipe, and leaves Part 05 §3.6 untouched; it changes Part 05 §3.3's
   entry and renames the published resolution. Preferred: `[overrides]`.
2. Whether a field override also releases a `core.subjects` column, as R108 §3.3 literally has it.
   If it does, `subject.strain` carries two meanings (§4). If it does not, a recipe writes
   `core.subjects.strain` for the preference and `subject.strain` for its own value. Preferred: it
   does not.
3. Whether a column override reaches a row the preferred source does not produce. Reaching it lets
   a recipe drop a row by naming each of its non-null columns. Not reaching it leaves that loss with
   two resolutions. Either answer needs Part 05 §3.4 to say which rows correspond, which it does not
   say today (§2.5). Preferred: it does not reach the row, and rows correspond by the table's
   primary key as delivered.
4. What a packet records beyond the recipe. With nothing more, a packet shows that a column's
   discard was accepted and not whether the build discarded anything. A list in the import run's
   parameters of each column released, with the passed-over source and the number of rows, would
   show it, under a key no checker verifies. Preferred: nothing more.
5. Whether an amending recipe admits a column override. Admitting it narrows the refusal of
   Part 05 §3.5 to field overrides. Refusing it leaves an amending build with two resolutions
   (§2.9).
   Preferred: admit it.
6. Whether an entry that can release nothing in any build is refused or reported (§4.5). Refusing
   adds two refusals to Part 05 §3.5 and stops a misspelled key before a source is read. Reporting
   adds none, and a misspelled key then fails at the refusal it was written to release. Preferred:
   refuse.

Each answer fixes a Decision clause. The first selects between two forms of the same direction, and
none reopens the choice between completing the rule and withdrawing it.

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
