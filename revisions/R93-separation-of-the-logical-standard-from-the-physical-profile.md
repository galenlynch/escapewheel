# R93 — Separation of the Logical Standard from the Physical Profile

| | |
|---|---|
| **Status** | **Accepted** 2026-09-08 |
| **Amends** | `00` §2 (the three-level vocabulary), `00` §7.3 (what a second profile must satisfy), `02` §5.3 and §13, `03` §1 and §5, `07` §7 (its boundary with Part 10), R2 §6 and `registry.schema.json` (the `sort` field); adds a contents table to `00` and adds Part 10 |
| **Depends on** | R92 (which states the ordering rule this part relocates) |
| **Profile** | all |

§3 is normative; every other section is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

`00` §2 defines three levels — a semantic standard independent of storage, a logical standard that
is storage-agnostic but not shape-agnostic, and a physical profile saying how logical resources are
stored. The second is crossed in four places: three clauses of Part 02 and one field of the
registry, which is Part 02's machine form. Part 03 crosses the other way, mixing rules a packet is
judged against with advice no validator can check.

This part states where a clause belongs, moves the clauses that are in the wrong document, and
adds a Part 10 for the measurements that justify the profile's choices.

## 2. Where the boundary is crossed

Informative.

Part 01 states its own independence and keeps it. Part 02 names a storage technology three times
and only one is a leak: `02` §10.3 places Parquet and Zarr rules outside SQL's reach, which §3.1's
rule permits in as many words, and `02` §8 cites Zarr in an example of what duplication buys. Four
clauses are nevertheless in the wrong place, and two have already drifted apart from their copies.

**Ordering is stated in both parts.** `02` §13.1 and `03` §5.3 each say a writer SHOULD sort every
table by its primary key, and each names `analysis.spike_events` as the one override. One rule,
written twice, in the part that must hold under any profile and in the part that describes one
profile's storage. Nothing compares them, so `verify.py` passes however far they drift — and they
have: until R91 §3.2 was accepted the two gave `core.events` orders of four columns and three.

**Partitioning is stated in `02` §13.2.** Partitioning is `03` §5.2's subject, and `02`'s copy
carries the same two rules.

**`02` §5.3 forbids `INT96`.** No such encoding exists outside Parquet, so a profile storing
tables another way cannot satisfy or violate the clause.

**A per-table `sort` field sits in the registry**, which is the logical standard's machine form,
while `registry.schema.json` describes the field as "Physical ordering a writer SHOULD apply.
Performance, not correctness." It is declared on 25 of 38 tables and null on the other 13, so a
reader cannot tell a table with no override from one a later block forgot.

Part 03 crosses in the other direction. "A table MUST be a valid Parquet file" and "100,000 to
1,000,000 rows is a starting point to be adjusted by profiling" sit two lines apart, and only the
first is a conformance statement. The rationale for `DELTA_BINARY_PACKED` on tick columns, for
Zstandard, and for preferring a single file to a partitioned one is the same kind of content:
measured, useful, and not something a packet can fail.

## 3. What each part contains

### 3.1 The logical standard

Part 02 **MUST NOT** name a storage technology, a file format, an encoding, or a physical property
of a stored resource, except to place such a rule outside its own scope. Every clause of Part 02
**MUST** hold unchanged under any physical profile.

`02` §13 is struck whole — ordering and partitioning are its only two subsections. R92 §2.2 carries
the ordering rule and `03` §5.3 the override that `02` §13.1 points at, so nothing is lost there.
`03` §5.2 carries the partitioning rules, and its SHOULD is the narrower and better statement: it
recommends partitioning a large **multi-session** table where `02` §13.2 recommends it for any
large table, and partitioning a single-session table by `session_id` yields one partition. Striking
`02` §13.2 therefore corrects the recommendation rather than moving it.

`02` §5.3's prohibition on `INT96` is struck, which is a clause and not a sentence: it reads
"Wall-clock columns MUST be `timestamp` with microsecond precision in UTC, and MUST NOT use
INT96", and only the second half goes. `03` §5.5 already states it.

`02` §5.3's remaining requirements stay, because a tick being `int64` and a wall clock being a
microsecond UTC timestamp are statements about the value rather than about its storage.

### 3.2 The physical profile

Part 03 is normative for a packet whose manifest declares its `profile_id`, and binds no other
packet. It is the only part whose **rules may depend on** a storage technology.

Naming one is not the test, and could not be: `00` names Iceberg across fifteen lines and `01`
names Parquet, Zarr and Iceberg to disclaim dependence on any of them, as §2 counts `02` doing
three times with a rule turning on only one. What Part 03 alone may do is make a rule that holds
because of one.

No clause of Part 01 or Part 02 **MAY** depend on a clause of Part 03. A logical rule discharged by
a physical property is the defect R92 §2.1 repairs, and this states the general form of it so a
later revision does not reintroduce one.

`00` §7.3 gains what a second profile has to satisfy. A physical profile **MUST** declare a
`profile_id` that a packet's manifest names, **MUST** bind only the packets declaring it, and
**MUST** say how each logical resource of Part 02 is stored. It **MUST NOT** require an amendment
to Part 01 or Part 02; where one would be needed, the defect is in those parts rather than in the
profile.

Today `00` §7.3's only binding sentence about a second profile is that no implementation may be required
to support one, which is a portability guarantee and says nothing about how to write one. Keeping
the prohibition and adding the requirements makes a profile something a reader can attempt rather
than only something they may decline.

### 3.3 The registry declares no stored order

The `sort` field is removed from `registry.schema.json` and from every table of
`logical_schemas.json`. A table's stored order is its primary key's, unless `03` §5.4 names another
for it, and a named override **MUST** satisfy R92 §2.2.

Every registry document drops the field, an extension's (R17 §2) as much as core's, since the
amended meta-schema admits no property it does not declare; all eleven extension tables carrying a
`sort` already sort by their own primary key, so none changes but its declaration.

`determined_by` stays in the registry. That `analysis.spike_events.time_bucket_tick` is a function
of `t_tick` is a statement about values, true under any profile, and it is what lets `03` §5.4's
one remaining override coexist with a minimal key.

With the field gone, `03` §5.4's table is the only statement an override has, and it is read by
two actors rather than one: a writer **MUST** emit an overridden table in that order (`03` §5.4)
and a validator **MUST** establish it (R92 §2.2), by scan rather than by query, since a physical
rule is the shim's rather than SQL's (R12 §4). A validator **MUST** refuse an override that does
not satisfy R92 §2.2 — a check made with no packet in hand, as R56 §2.4's is, and what
`aind_unit_qc` needed when it went on sorting by two columns R81 had removed, which no packet could
satisfy and no rule could see.

The thirteen tables carrying `sort: null` stop being a category rather than getting filled in: with
no field there is no null, and a table with no override is in key order by rule rather than by a
value someone remembered to write.

### 3.4 Part 10, performance notes

Part 10 is added, wholly **informative**. It carries what a packet's bytes make true under this
profile: the encoding and compression comparisons, row-group sizing, the object-store request rate
R86 §1.1 measured, R42's comparison of four ways of staging one table to S3, and the storage
measurements of R53 and R81.

A clause **MUST NOT** appear in Part 10 and in a normative part both. Where a measurement supports
a rule, the rule stays where it binds and Part 10 carries the reading.

Part 10 **MUST** carry a version of its own. The three the specification declares — semantic,
logical and portable — version what binds, and a measurement binds nothing, so none of them covers
it. This is the same requirement §3.6 puts on every part's status line and for the same reason: it
binds an editor rather than a packet, and a citation of `10` §3 that names no edition is the
navigability defect §3.6's table exists to fix.

What a measurement records is a recommendation rather than a requirement, since the part is
informative and a reading without a date is still a reading. Each **SHOULD** record the date it was
taken and the versions of the libraries it was taken against, and where those were not kept it
**SHOULD** say so rather than leave the field out.

The alternative is a requirement nothing already measured could meet. Six measurements across every
accepted revision name a library version — `zarr-python 3.3.0` and `pyarrow 25.0.1` — and the rest,
R53's storage figures and R68's encoding comparison among them, record none, most of them
irrecoverably. A number whose toolchain is marked unkept says what a reader needs, which is that
its currency is unknown; one silently missing the field says nothing.

The two answer different questions and neither substitutes for the other: the version says which
edition of the part a citation names, and the date and the toolchain say whether a number is still
true, which a version cannot, since it bumps on any edit. R21's codec finding is the case — Zarr.jl
reads gzip in v3 and not in v2 — and a reading of that kind stops being true the moment the library
moves, with nothing in the prose changing to show it.

Part 10 is not a substitute for `conformance/`, which holds the probes that produced the numbers.
Part 10 says what they mean.

### 3.5 Part 07 keeps the measurements that are its own

Part 07 §7 already holds performance notes and already opens by saying they are *"properties of
the reference implementation, not requirements"*. Part 10 does not absorb it, and **MUST NOT**
repeat it.

The two divide on whose property a number is. Part 10 carries what follows from Parquet, Zarr or
the object store, so any conforming implementation meets it: a column's compressed size, a row
group's span, a store's request rate. Part 07 §7 carries what follows from this implementation's
code and would change if someone wrote another in another language: how a columnar library decodes
a batch, how one query planner treats a projection against a join.

R86 is the case that splits, and it splits across its own sections. The **~120 requests per
second** its §1.1 measures is the store's and belongs to Part 10; the **1.02x** projection against
a **2.22x** join its §2.4 measures is one planner's and stays where Part 07 §7 already records it.
R43's query timings split the same way and stay in `06`, since what they justify is a
materialization rule rather than a storage choice.

### 3.6 `00` lists the parts and what each one binds

`00` **MUST** carry a table of every part, its subject, and its conformance status. Each part
**MUST** continue to state its own status at its head, and where the two disagree the part's
statement governs.

| part | subject | status |
|---|---|---|
| 00 | architecture and the three-level vocabulary | normative |
| 01 | semantic standard | normative |
| 02 | core logical schemas | normative |
| 03 | portable physical profile | normative |
| 04 | packet catalog | normative |
| 05 | validation and import | normative |
| 06 | analysis layer | informative, except §2 and §5 |
| 07 | reference implementation and plan | informative |
| 08 | example packet | informative |
| 09 | metadata and extensions | normative |
| 10 | performance notes | informative |

Today a reader learns what binds them by opening ten files and reading the third line of each,
which is where every part states its status, because `00` has no contents list at all. R3 §3.0
forbids a table restating what the data it describes already declares unless the duplication buys
otherwise-unavailable access; the same test one level up admits this one, since what it buys is a
single place that answers which parts bind, and no part can answer that about the others.

The table is **appended** to `00` rather than inserted. `00` runs to §8 and the identifiers this
section counts are part *and* section both, so a table placed anywhere but the end would renumber
what it exists to make citable.

**Position is not the signal, and is not made into one.** Part 09 is normative and follows two
informative parts, and no arrangement could fix that in general, since Part 06 is normative in two
sections and informative in the rest. Renumbering to tidy the sequence would move identifiers that
**119** citations depend on across the accepted revisions and the parts themselves, **51** distinct
part-and-section pairs, with more in the drafts and one inside the ledger's own `where`. So the
order stays as it is and the table carries what the order cannot.

## 4. Placing a clause

A clause belongs to Part 03 where it would change if the profile changed, to Part 07 where it
would change if the reference implementation changed, to Part 10 where it is a number rather than
a rule and neither of those claims it, and to Part 02 where none of them does.

The test settles the four crossings of §2 without appeal to judgement: an ordering rule changes
under Iceberg, so it is Part 03's; `INT96` names a Parquet encoding, so it is Part 03's; row-group
sizing is a number the format fixes, so it is Part 10's; a tick being `int64` is true under any
profile, so it stays in Part 02.

It settles the boundary §3.4 draws for the same reason. A measurement that would change if this
repository's code were replaced is Part 07's, and one that would survive that replacement is Part
10's, which is why an object store's request rate and a query planner's cost model separate.

The same test places a **registry field**, and the answer it gives is that the registry is not a
level at all. A field belongs to the semantic level where it would survive replacing the tabular
model with another encoding of the same concepts, to the logical level where it would not, and to
the physical level where it changes with the profile.

A column may carry seventeen. Seven are semantic — `unit`, `unit_from`, `clock_from`, `identity`,
`enum`, `vocabulary` and `reserved_values` — since a quantity's unit and a tick's clock are the
same fact in any encoding. Seven are logical: `name`, `type`, `presence`, `determined_by`,
`discriminates`, `discriminates_via` and `resolves`, each of which presupposes columns and tables.
`description` and `since` are documentation and belong to neither. `role` spans the two, which is
what makes it the interesting case rather than an exception: `data`, `identifier` and `coordinate`
survive any encoding, where `structural_index` and `sequence_position` presuppose an indexed
sequence and `discriminator` presupposes resolution to a table. The one physical field a table
carries is `sort`, which is why §3.3 removes it.

So `00` §2's levels classify **statements, not documents**. §3.1's rule binds Part 02 because a
part is made of clauses; the registry is made of fields and carries statements at every level,
which is what makes it the machine form of the specification rather than of one part of it.
Turning §3.1 on it would strike `unit` and `clock_from` and leave a consumer resolving a tick to
join against Part 01's prose, which no consumer can read.

## 5. What this makes possible

`00` §2 says a physical profile says how the logical resources of Part 02 are stored, and today
that is not satisfiable: a second profile would inherit `02` §13.1's ordering rules, which
Iceberg's compaction does not preserve, and `02` §5.3's prohibition on an encoding it does not
have. §3.1 removes both, and §3.2 states what a profile must satisfy in their place.

This part adds no profile and makes no claim that one is close. What it establishes is that adding
one requires no amendment to Part 01 or Part 02, which `00` §2 promised and nothing made
checkable.

## 6. What this does not change

Informative.

- **No table, column, reference or rule.** Every change is to which document holds a sentence.
- **No part is renumbered.** §3.6 records why: the sequence cannot express Part 06, and what
  depends on the identifiers is worth more than a tidy order.
- **No packet is invalidated.** The moved clauses say the same things in their new homes, and
  `03` §5.4 names one override where it once named two, R91 §3.2 having removed `core.events`',
  so there is no disagreement left here to reconcile.
- **Part 07 §7 is unmoved.** Its performance notes are the reference implementation's and stay
  informative where they are; §3.4 divides Part 10 from it rather than merging the two.
- **Part 03 stays normative.** A profile that were merely described could not be validated, and
  `escapewheel-portable-v0.1` is the only profile any packet declares. What stops binding is
  Part 02's dependence on it, not the profile itself.
- **`03` §5.1's SHOULDs stay in Part 03.** A recommendation a writer can follow is a rule;
  only the numbers behind it move to Part 10.
- **`registry/check.py` gains no check.** Whether a document names a storage technology is not
  decidable from the registry, and the ledger already records a disposition per clause.

## 7. Consequence

`02` loses a section and half a sentence — §13 whole, and §5.3's `INT96` clause — and `03` §5.1
loses a number to Part 10, which is written from material that currently sits in accepted revisions
and in `conformance/`.

§3.3 removes one field from the registry's meta-schema and from every document written against it:
25 declarations across core and 11 across the four extensions, none of which changes a stored
order. Six places read the field and each is accounted for. `registry/build.py` loses its `OVERRIDE`
table and its fill pass; `registry/render.py` loses the `**Sort**` line that would otherwise print
the same sentence 38 times; and `escapewheel_writer.scaffold` stops writing `"sort": None` into a
scaffolded registry. The other three read `03` §5.4's list instead, which `escapewheel_reader`
gains: both packages needing it depend on the reader and neither depends on the other, so one copy
serves `escapewheel_writer.arrow`, which emits the order §3.3 binds a writer to;
`fixtures/build.py`, which builds the corpus against it; and `escapewheel_validator`, which
establishes it and refuses an override failing R92 §2.2. No packet's rows move, and no packet is
invalidated: the field was never written into one.

`00` gains §3.6's table, eleven rows restating a line each part already carries.
`escapewheel_poc_docs_v0.2/combine.py` gains Part 10 in its concatenation, and the ledger gains
its clauses. The generated `Escapewheel_POC_v0.2_Implementation_Spec.md` grows by Part 10's length
and by nothing else. Part 07 §7 keeps every line it has, one of which — R86 §2.4's projection
measurement — §3.5 confirms belongs to it rather than to Part 10.

## 8. Open

- **Whether a second profile should be attempted before v1.** §3.2 states what one must satisfy and
  nothing has tested the statement, which only writing one does. Iceberg is the profile `00` §7.3
  names and `07`'s Phase 7 carries, and it is the expensive one; a profile over a single Parquet
  file with no catalog would exercise the same separation for far less.
