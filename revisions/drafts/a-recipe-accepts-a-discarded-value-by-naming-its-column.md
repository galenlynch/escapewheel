# A recipe accepts a discarded value by naming its column

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `cf9e816a13575a419d6917d8285992d7cb09f2f3` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 05 §§3.1, 3.4, 3.5 and 3.6; the recipe schema |
| **Depends on** | R108 §3.1 (the refusal a column override releases); R108 §3.3 (the rule this restates); R87 §2.5 (the table and its field overrides); R133 §3.4 (the recipe document's `overrides` row); R150 §3.5 (the amending build's refusal this narrows); R153 §3.7 (the recipe schema identifier this advances from) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

A recipe that lists two sources able to supply one resource declares a preference between them,
and a build takes the preferred source's rows and discards the other's (Part 05 §3.3). Part 05 §3.4
has the build refuse where that discards a value: where the passed-over source states a value in a
column the preferred source leaves null. The same section names three ways a recipe resolves the
refusal, and the first is naming the fact in `[overrides]` with its reason.

No recipe can write that first resolution. `[overrides]` is the table in which a recipe declares
that its own value for a session or subject field supersedes a source's (Part 05 §3.6). Its keys
are `block.field` names, so the recipe schema refuses a key that spells the refused column, and no
sentence requires a build to honour an entry. Where each of two sources holds a column the other
lacks, preferring the other source fails as well, and a recipe whose author cannot correct a source
does not build.

This revision gives `[overrides]` a second kind of entry, keyed by a resource and a column, and
binds a build to release the refusal for that column. It says which rows of two sources correspond,
which entries a build refuses before it opens a source, what a build reports, and that an amending
recipe may carry such an entry. It advances the recipe schema's identifier.

The change is structural because it revises rules inside existing sections: the `overrides` row
and the schema identifier of Part 05 §3.1, the resolution sentence of Part 05 §3.4, the refusals
and reports of Part 05 §3.5, and the definition and idle report of Part 05 §3.6. Appended sections
would leave Part 05 §3.4 naming a resolution no recipe can write beside the section that makes it
writable.

### 1.1 Structural crosswalk

No anchor bootstrap is needed: at the `Based on` commit Part 05 §§3.1, 3.4, 3.5 and 3.6 carry
`ew-recipe-purpose`, `ew-source-declarations`, `ew-recipe-check` and `ew-declared-fact-authority`
in that order. No section moves, splits, merges or retires.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 05 §3.1, the `overrides` row and the recipe schema's identifier | revise in place | same section | the table holds two kinds of entry; the schema admits both keys under an advanced identifier | §3.1; §3.6 |
| Part 05 §3.4, the refusal of a discarded value and the sentence on resolving it | revise and extend in place | same section | rows are compared once a build fills the columns it fills, and correspond by primary key; a row with a null key column corresponds to none; a column override releases a null column of a corresponding row and nothing else | §3.2 |
| Part 05 §3.5, the refusals made before a source is opened | extend in place | same section | a column override that can release nothing is refused | §3.3 |
| Part 05 §3.5, the amending build's refusal of an `[overrides]` member | revise in place | same section | the item refusing an `[overrides]` member refuses a field override instead, and no item is added; an amending build admits a column override | §3.5 |
| Part 05 §3.5, the two reports of a declared field | revise in place | same section | each concerns a field override | §3.4 |
| Part 05 §3.6, the definition of an override and the report of an idle one | revise and extend in place | same section | the definition is a field override's, whose block is `session` or `subject`; a build reports a release as information and an idle column override as a warning | §3.1; §3.4 |

## 2. Background

The facts below were observed in the tracked files at the `Based on` commit, where
`verify.py --quick` passes all 37 of its stages. Three probes ran the incorporated recipe schema
and the reference build's refusal over hand-written recipes and rows at `9c180d6`, the draft's
first baseline; since then the recipe schema and the code that refuses are unchanged, and Part 05
§§3.2, 3.5 and 7 have gained only R159's text. A fourth probe ran a JSON Schema engine over the
revised key pattern of §3.6. None changed a tracked file.

### 2.1 Part 05 §3.4 names the override resolution and binds no build to it

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

### 2.2 R108 §3.3 states the rule with force and a key no column fits

R108 §3.3 requires an `[overrides]` entry naming a fact to silence the refusal for that fact. It
calls the table R87 §2.5's, "keyed the same `block.field` way and carrying the reason it requires",
and it fixes the unit: "an entry silences that column and no other". The ledger records R108 §3.3
as `applied` at Part 05 §3.4. A search of `revisions/accepted/` for `[overrides]` finds four
revisions, R87, R108, R133 and R150. Of the two after R108, R133 §3.4 lists the member with
`block.field` keys and R150 §3.5 refuses it in an amending recipe, and neither restates the rule or
withdraws it.

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

### 2.3 A column of a resource already has a three-segment spelling

Part 05 §3.8 keys a recipe's `[encoding]` table `resource.column`, and the schema puts no pattern
on those keys. The registry meta-schema spells a resource identifier as two segments and a column
name as one, and spells a column of a resource as three segments in `discriminates_via` and
`specialises`. Each of the core registry's 48 resource identifiers has exactly one dot, and each of
its 360 column names is one segment. A three-segment key therefore names one column of one resource
and cannot be read as a `block.field` key.

### 2.4 The refusal has three shapes, and one of them names a column

Part 05 §3.4 refuses "where a passed-over source's row holds a non-null value in a column the
preferred source's row leaves null, or does not produce at all", and calls a preferred source that
produces no rows the limiting case. The comparison leaves out `metadata`. The sentence does not say
which row of the preferred source a passed-over row is compared with.

The reference build pairs rows by the table's declared primary key, on the values the adapters
delivered. Each of the 45 tables declares a primary key, and every key column is `required`.
Part 12 §5 has an adapter hand over an identifier as the name its source used, so an identifier in
a delivered key is a name, and two rows pair only where both sources use the same name. Two edges
are settled by the code and by no sentence: rows whose key columns are both null pair with each
other, and where the preferred source delivers two rows with one key, a passed-over row is compared
with the last of them. The build compares the rows before it fills any column. The build reports
three shapes of loss:

| shape | what the reference build reports |
|---|---|
| a null column in a row both sources produce | `core.probes.probe_type: sorter stated 'NP2000' and nwb left it null` |
| a row the preferred source does not produce | `core.probes: sorter stated a row nwb did not` |
| a preferred source producing no rows | `core.probes: sorter stated 1 row(s) and nwb staged none` |

The first names a column in the spelling of §2.3. The other two name a resource and no column.

Part 05 §3 uses "fact" for two units. In Part 05 §3.6 a fact is a field a recipe declares, one
value for the session or the subject. In Part 05 §3.4 the fact a recipe is to name is a value in a
column of a row some source produced.

### 2.5 The reference build refuses with an entry in place and recommends one

A probe recipe prefers the NWB source for `core.probes`, and the two sources produce one probe row
each: the NWB source leaves `probe_type` null and the sorter source states `NP2000`.

- With no `[overrides]` entry the build refuses, and its message says to declare the fact "in
  [overrides] with a reason, prefer the other source, or fix the one that states less". The code
  that refuses reads no `[overrides]` entry.
- With `"core.probes.probe_type"` as the key, the recipe fails the schema before any comparison.
- With `"probes.probe_type"`, the nearest key the schema admits, the build refuses as before, and
  the recipe check warns that the entry "overrides nothing; no source in this recipe states it".

The writer's suite has four cases for the refusal, and none carries an override.

### 2.6 Where each source holds a column the other lacks, neither preference builds

In a second probe the NWB source states `manufacturer` and leaves `probe_type` null, and the sorter
source states `probe_type` and leaves `manufacturer` null. Preferring the NWB source refuses over
`core.probes.probe_type`, and preferring the sorter source refuses over `core.probes.manufacturer`.
R108 §6 anticipated the case as "a refusal that no choice of source resolves".

Two other routes are closed. Part 05 §3.3 forbids `owns` for a resource two sources produce unless
a preference is declared, and Part 05 §3.4 forbids composing the row. Correcting a source is the
one resolution left, and R87 §2.5 describes the case an override exists for as an upstream defect
that will not be fixed in the file the build reads.

### 2.7 The idle-override report is defined on a field

Part 05 §3.6 requires a build to report an override "for a field the source agrees with, or that no
source states", and forbids it to refuse on either. Both conditions concern what a source states
for a recipe field. No adapter states a column of a preferred resource as a recipe field, so an
entry naming such a column meets the second condition on every build. The warning in §2.5 is that
report.

Part 05 §3.5 has two reports of the same kind: a declared field "some listed source states and no
override covers" is a warning, and one an override covers is information.

### 2.8 An amending recipe can declare a preference and cannot declare an override

Part 05 §3.5 has an amending build refuse "a `[subject]` member, or an `[overrides]` member".
Part 05 §3.3 says of an amending build that its "preferences arbitrate among the recipe's sources
only". An amending build can therefore meet the refusal of Part 05 §3.4, and the reference build
runs the comparison in an amending build as in any other.

The same list refuses every `[subject]` member and every `[session]` member but `session_id`, so an
amending recipe declares no field that a field override could supersede a source with. A column
override names no recipe field.

### 2.9 A source may omit a column that a writer fills

Of the 245 columns the core registry declares outside a primary key and `metadata`, 78 are
`required`. Two kinds of them are columns a build fills:

- 27 are a table's `session_id`. Part 02 §7.1 has a writer fill that column "from the parent row it
  already read, or from the session it was constructed with", so a source's row may leave it null
  and the packet still holds a value. `session_id` is also in the primary key of 16 tables.
- 8 are the name of an owned assigned identifier (Part 02 §8.2), and the names of the other 9 of
  the 17 owning tables are `nullable`. Part 12 §5 has an adapter hand over an identifier as the name
  its source used, and the reference writer fills the name from that text where the adapter
  delivers no name of its own. No part has a writer fill a name.

At least 35 of the 78 are therefore columns a build fills. The open draft
`a-unit-is-identified-outside-its-packet-by-its-name.md` makes the nine `nullable` names
`required`, which makes 87 of 245 `required` and 44 of those columns a build fills.

The comparison of Part 05 §3.4 is over the rows as the sources state them. In a third probe the
preferred source delivers a `core.probes` row without `session_id` and the passed-over source
delivers the same probe with it, and the reference build refuses over `core.probes.session_id`.
A probe made while this draft was appraised found the same for `core.probes.probe_name`, where the
passed-over source states the name the writer would fill. Each refusal is over a value nothing
loses. Where `session_id` is in the key and one source omits it, the two rows do not pair, and the
build refuses as over a row the preferred source does not produce, which no override of any kind
releases.

Where a preferred source's row leaves null a `required` column that no writer fills, the packet
fails the generated non-null check (Part 05 §5.1), and Part 05 §2 forbids the build to promote it.

### 2.10 The recipe schema's identifier has advanced with each change of its shape

Part 05 §3.1 incorporates the schema under the `$id`
`https://escapewheel.org/schemas/recipe/0.3.0`. R150 §3.10 advanced it from 0.1.0 to 0.2.0 and
R153 §3.7 set 0.3.0, each in a revision that added members to the schema. R138 §5 kept the `$id`
because it left the shape unchanged. No part states when the identifier advances. The writer's
packaged copy of the schema equals the incorporated artifact.

Part 05 §3.2 has a writer record the recipe in the import run's parameters. No part has a validator
check that record against the recipe schema, and the reference validator and reader read no recipe.

### 2.11 Alternatives

| alternative | why it is not taken |
|---|---|
| keep the current text | Part 05 §3.4 names a resolution no recipe can write, and the recipe of §2.6 does not build |
| withdraw the override resolution | the recipe of §2.6 still does not build |
| give the sentence force and keep the `block.field` key | reaches `core.subjects` alone (§2.2); `subject.strain` then says either that the recipe's value stands or that the preferred source's null stands, and the report of §2.7 cannot tell which |
| an entry names a whole resource | releases a dropped row and an empty preferred source along with a null column, which leaves the preference unchecked for that resource, the state R108 §3.1 closed |
| a `[preference]` entry lists the columns it may discard | Part 05 §3.3's entry gains a member, and the table that Part 05 §3.4 and R108 §3.3 name is not the one a recipe uses |
| a new top-level table keyed `resource.column` | the recipe gains a table, and the resolution Part 05 §3.4 and R108 §3.3 name is renamed |
| an entry for one row's column | the recipe has to name the row, and twelve probes take twelve entries carrying one reason |
| an entry for one passed-over source | the value becomes a table, and differs from an entry for the column only in a recipe listing three or more sources that produce the resource |
| a column override also releases a row the preferred source does not produce | a recipe then drops a row by naming each of its columns, and a recipe that drops a whole row says its two sources disagree about what exists, which a statement about one column does not answer |
| a list of released columns in the import run's parameters | the recorded recipe already carries the entry and its reason, and the list would sit under a key no checker verifies |

### 2.12 Other open work

R159, accepted and incorporated at the baseline, amended Part 05 §3.2, Part 05 §3.5 and
Part 05 §7. Part 05 §3.5 now holds its paragraph permitting a build to refuse a recipe carrying a
value it recognizes as a credential. This revision changes other items of that section and no
sentence R159 added. R159 left the recipe schema unchanged, and its recorded recipe differs from
the recipe only where a build recognizes a credential, so a column override and its reason are
recorded as stated.

R160 amends Part 05 §4.3 by R160 §3.7, sections of four other parts and the core registry, and
changes no recipe rule. It has two sources that each deliver sidecars name
`core.sidecars` and `core.sidecar_scopes` under `contributes`. Part 05 §3.5 refuses a preference
for a resource an entry declares under `contributes`, and a column override needs a preference
(§3.3), so no column override names either table in such a recipe.

Other open work concerns a clock's transform, a null producing run on an array, and a unit's name.
None amends Part 05 §3.1, Part 05 §3.4, Part 05 §3.5 or Part 05 §3.6, and none changes the recipe
schema. The unit-name draft changes the count of §2.9, as that section says, and makes every owned
name a column a source may omit and a build fills under the reference writer's practice.

`revisions/impact.py` lists 288 citations of the four amended sections outside this document. Those
that concern an override lie in the reference build and its tests, which §5 has change, and in the
records under `revisions/audit/`, which describe the parts as an audit found them and list
R108 §3.3 as a rule Part 05 §3.4 weakened.

## 3. Decision

The subsections state the two kinds of entry, what a column override releases, which column
overrides a build refuses, what a build reports, the amending recipe, and the recipe schema.

### 3.1 An `[overrides]` entry is a field override or a column override

A recipe's `[overrides]` table holds two kinds of entry, and an entry's key says which it is. A
**field override** has a key of two segments, `block.field`, whose block is `session` or
`subject`, and declares that the recipe's own value for that field supersedes a source's, as
Part 05 §3.6 defines an override. A **column
override** has a key of three segments, a resource's dotted identifier followed by one of its
column names, and §3.2 says what it declares.

A recipe MUST give a column override a non-empty string as its value, saying why the recipe gives
up the value a passed-over source states, as Part 05 §3.6 requires a reason of a field override.

A field override releases no refusal of Part 05 §3.4, a field of `[subject]` included. A recipe
that prefers a source for `core.subjects` names a column of that table in a column override, and
names a `[subject]` field in a field override where it declares its own value for the field.

### 3.2 A column override releases a null column of a corresponding row

For the refusal of Part 05 §3.4, a build MUST compare each source's row with the columns it fills
when it stages a row already filled: the `session_id` Part 02 §7.1 has a writer fill, and any name
of an owned assigned identifier (Part 02 §8.2) the build fills from the name its source delivered
as the identifier (Part 12 §5). Every other value is compared as its source delivered it.

A row of a passed-over source **corresponds** to a row of the preferred source where, so filled,
the two hold equal non-null values in every column of the table's primary key. A row holding a null
in a key column corresponds to no row. Where the preferred source delivers several rows with one
key, each of them corresponds. A passed-over source's row to which no row of the preferred source
corresponds is a row the preferred source does not produce.

A column override names one column of a resource the recipe declares a preference for. Where a
recipe carries one, a build MUST NOT refuse under Part 05 §3.4 over a value that a passed-over
source's row holds in the named column and that every corresponding row of the preferred source
leaves null, whether a row states a null or omits the column. The release reaches every such row
and every passed-over source, and it reaches no other column. Where some corresponding rows state a
value in the column and others leave it null, the build MUST refuse as Part 05 §3.4 has it, and the
column override releases nothing.

A build MUST still refuse over a row the preferred source does not produce, and over a preferred
source that produces no rows while another source produces some. No column override releases
either refusal.

A build that releases a value stages the preferred source's row as that source delivered it and
discards the passed-over value, so the prohibition of Part 05 §3.4 on composing a row from more
than one source stands.

A recipe resolves a refusal over a null column by a column override, by preferring the other
source, or by correcting the source that states less. It resolves each of the other two refusals
by preferring the other source or by correcting a source.

### 3.3 A build refuses a column override that can release nothing

A build MUST refuse, before it opens any source and naming the entry's key, a column override:

- whose resource the recipe declares no preference for;
- whose column the resource does not declare, which includes every column named for a resource
  that is not a table;
- whose column is `metadata`; or
- whose column belongs to the resource's primary key.

A build admits a column override naming any other declared column of a preferred table, a
`required` column included.

### 3.4 A build reports a release and an idle column override

A build MUST report as information each column override that released a value, naming the column,
each passed-over source whose value it released, and the entry's reason.

A column override is **idle** in a build where it released no value. A build MUST report an idle
column override as a warning and MUST NOT refuse on it.

No checker verifies either report.

The two reports Part 05 §3.5 makes of a declared field, and the report Part 05 §3.6 makes of an
override for a field the source agrees with or that no source states, concern field overrides
alone. A column override covers no declared field and draws none of the three.

### 3.5 An amending recipe admits a column override

An amending build (Part 05 §15.1) MUST refuse a field override before it opens any source, as it
refuses a `[subject]` member, and MUST NOT refuse a column override on the ground that the build
amends. A column override in an amending recipe releases as §3.2 has it, among the recipe's sources
only (Part 05 §3.3).

### 3.6 The recipe schema admits both keys and its identifier advances

The recipe schema's `overrides` member admits a key of either form and no other: `session` or
`subject`, a dot and a field spelled as the baseline schema spells one; or a resource identifier and
a column name joined by a dot, each spelled as the registry meta-schema spells it. The constraint
on an entry's value is unchanged.

The schema's `$id` advances one minor version from the identifier Part 05 §3.1 incorporates when
this revision is incorporated. At the baseline that identifier is
`https://escapewheel.org/schemas/recipe/0.3.0`. Part 05 §3.1 names the new identifier, and its
informative table lists both key forms.

## 4. What this does not change

A column override accepts a loss and merges nothing. The packet holds the preferred source's row
with its null, and a recipe whose author wants both values still has to correct a source.

A build records nothing beyond the recipe. Part 05 §3.2 has the writer record the recipe in the
import run's parameters, so a column override and its reason reach the packet there, and the packet
does not say whether the build released a value.

A `required` column is not among the refusals of §3.3, and an entry naming one gives up no
protection the column had. Without the entry, a passed-over value in the column makes the build
refuse under Part 05 §3.4 before it stages anything. With the entry, where the preferred source's
row leaves the column null and no writer fills it, the packet fails the non-null check of
Part 05 §5.1 and Part 05 §2 forbids the build to promote it (§2.9). Where a writer fills the
column, §3.2 compares the filled value and the entry is idle.

## 5. Consequence

The revised schema refuses one kind of key the baseline schema admits: two segments whose first is
neither `session` nor `subject`, such as `core.probes` or `probes.probe_type`. Such a key names no
block a recipe declares, so it superseded nothing and drew the idle report of Part 05 §3.6 on every
build. The tracked recipes, the informative example and the writer's tests carry `subject.` keys
alone. Every other recipe the baseline schema admits stays admitted and none changes meaning: a key
of `session` or `subject` and a field is a field override as before. A build written to the
baseline schema refuses a recipe carrying a column override and names the key. No packet changes
and none is rebuilt. A packet built from a
recipe carrying a column override records that recipe in the import run's parameters, which no
validator check reads (§2.10), so it conforms as any other packet does.

A build already holds each passed-over source's rows for a preferred resource in order to compare
them (Part 05 §3.4), so releasing a value needs no input the build lacks. The four refusals of §3.3
are decided from the recipe and the registries it binds, which Part 05 §3.5 already has a build
check the recipe against before it opens any source.

Comparing filled rows removes two refusals of the baseline. A refusal over a `session_id` or a name
that a passed-over source states and the writer fills is gone, since the filled value is compared
and nothing is lost. So is the refusal over a row whose key holds `session_id` where one source
omits it, which no entry could release. A build already holds the session and each delivered
identifier when it compares, so filling needs no new input; the reference build fills these
columns only after it compares, and moves the fill before the comparison.

Rows correspond only where two sources deliver equal key values once filled. Two sources that name
one probe differently deliver rows that do not correspond. Each such loss is a row the preferred
source does not produce, which no column override releases.

A row holding a null in a key column corresponds to no row, so a passed-over row with a null key is
refused as a row the preferred source does not produce, and a preferred row with one releases
nothing. Either would fail the non-null check of a key column (Part 05 §5.1). A repeated key in the
preferred source fails the primary-key check of Part 05 §5.1 as well; until then a column override
releases a value only where every row of that key leaves it null, so the build never chooses among
them.

A refusal of §3.3 also stops a recipe whose preference was removed while its column override
stayed, where a stale field override is only reported.

R108 §3.3 is restated whole by §§3.1 and 3.2, with a different key and a stated reach, so its
ledger entry becomes `superseded`, naming this revision in `by` and carrying no `where`, as
R158 §3.1 requires. Five entries keep `applied` and gain a note naming the later clause, as
R158 §3.2 requires: R108 §3.1, whose refusal §3.2 gives a correspondence; R87 §2.5, whose table
gains a second kind of entry and whose idle report §3.4 confines to a field override; R133 §3.4,
whose `overrides` row §3.1 restates; R150 §3.5, whose refusal of an `[overrides]` member §3.5
narrows; and R153 §3.7, whose recipe identifier §3.6 replaces.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. An override is a fact about a build and no concept of Part 01. | None required. |
| logical prose and registry | Unchanged. No resource, column or rule changes, and the meta-schema's spelling of a column of a resource is reused and not altered. | None required. |
| physical profiles | Unchanged. No storage property and no delivery changes. | None required. |
| packet manifest and JSON Schemas | The recipe schema's `overrides` key pattern, its descriptions and its `$id` change (§3.6). No other incorporated schema changes. | The schema artifact; schema tests admitting a three-segment key and refusing a four-segment one and a two-segment key whose block is neither `session` nor `subject`. |
| validation and import | Part 05 §3.1 takes §§3.1 and 3.6; Part 05 §3.4 takes §3.2; Part 05 §3.5 takes §§3.3, 3.4 and 3.5; Part 05 §3.6 takes §§3.1 and 3.4. No validator check is added, since a packet does not show whether a build refused. | `evidence/R<N>.json` names the four anchors. |
| extensions | Unchanged. A column override names an extension table's column as it names a core one, where a recipe prefers a source for that table. | None required. |
| reader, writer, validator, adapters | The reference build compares rows after filling each `session_id` and owned name it fills, which moves that fill before the comparison of Part 05 §3.4; pairs no row holding a null key column and compares a passed-over row with every preferred row of its key; honours a column override; refuses the four cases of §3.3; admits a column override in an amending recipe; reports a release as information and an idle entry as a warning; and names the column override in its refusal message. Its packaged copy of the schema regenerates. An adapter is unchanged: its `states` (Part 12 §7) names recipe fields, which a field override still answers. The reader and the validator are unchanged, since neither reads a recipe. | The writer suite's cases of §6; the copies check of `verify.py`. |
| conformance fixtures and tests | No packet fixture, since a packet does not show whether a build refused. Build and schema tests cover §6's cases. The informative example recipe, which declares a preference for `core.probes`, gains a column override. | The writer suite; the example recipe validated against the schema. |
| revision process and tooling | The ledger changes above and the ordinary evidence record. No tool changes. | `ledger.py`, `evidence.py` and `verify.py`. |
| generated publications and developer documentation | The combined specification regenerates. The writer's guide documents both kinds of entry; no package document mentions `overrides` at the baseline. | `verify.py`. |

## 6. Conformance and implementation evidence

§3.1 is `applied` at Part 05 §3.1 and Part 05 §3.6, §3.2 at Part 05 §3.4, §3.3 and §3.5 at
Part 05 §3.5, §3.4 at Part 05 §3.5 and Part 05 §3.6, and §3.6 at Part 05 §3.1, each by canonical
anchor.

No validator finding distinguishes the rule. These build cases do:

- the recipe of §2.5 builds with `"core.probes.probe_type"` in `[overrides]`, stages the preferred
  source's row with `probe_type` null, and reports the release with its reason;
- the same recipe still refuses with an entry for another column, and with the field override
  `"probes.probe_type"`;
- a row the preferred source does not produce, and a preferred source that produces no rows, each
  still refuse with a column override in place;
- the recipe of §2.6 builds under either preference with one column override;
- a column override for a resource with no preference, for an undeclared column, for `metadata`
  and for a primary-key column is each refused before any source opens, naming the key;
- with no entry, a preferred source omitting `core.probes.session_id` or `core.probes.probe_name`
  where the passed-over source states the value the writer fills builds without a refusal, and a
  column override naming that column is idle;
- a table whose key holds `session_id`, where one source omits it, builds without a refusal over
  a row the preferred source does not produce;
- a passed-over row holding a null in a key column is refused as a row the preferred source does
  not produce, with or without a column override;
- where the preferred source delivers two rows with one key and both leave the column null, a
  column override releases the passed-over value; where one of them states it, the build refuses;
- a column override that released nothing is reported as a warning and the build proceeds; and
- an amending recipe carrying a column override is not refused for it, and one carrying a field
  override is.

These schema cases distinguish §3.6: the schema admits `subject.strain`,
`session.session_start_time`, `core.probes.probe_type` and `aind_unit_qc.metrics.num_spikes_used`,
and refuses `core.probes`, `probes.probe_type`, a key of four segments and a key with an empty
segment.

The probes of §2 establish feasibility: the comparison already names the column in the spelling a
column override uses, a JSON Schema pattern expresses both key forms and the restricted block (the
fourth probe admits and refuses exactly the keys above), and the build holds every row the release
reads and the session and identifiers it fills from.
