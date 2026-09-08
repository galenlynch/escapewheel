# Separation of the Logical Standard from the Physical Profile

| | |
|---|---|
| **Status** | Draft |
| **Amends** | `00` §2 (the three-level vocabulary), `02` §5.3 and §13, `03` §1 and §5, `07` §7 (its boundary with Part 10), R2 §6 and `registry.schema.json` (the `sort` field); adds a contents table to `00` and adds Part 10 |
| **Depends on** | R92 (which states the ordering rule this part relocates) |
| **Profile** | all |

Normative, except §2 and §6, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

`00` §2 defines three levels — a semantic standard independent of storage, a logical standard that
is storage-agnostic but not shape-agnostic, and a physical profile saying how logical resources are
stored. Part 02 breaks the second of those in four places, and Part 03 mixes rules a packet is
judged against with advice no validator can check.

This part states where a clause belongs, moves the clauses that are in the wrong document, and
adds a Part 10 for the measurements that justify the profile's choices.

## 2. Where the boundary is crossed

Informative.

Part 02 names a storage technology twice in 344 lines, so the leak is narrow rather than pervasive,
and Part 01 states its own independence and keeps it. Four clauses are nevertheless in the wrong
place, and two of them have already drifted apart from their copies.

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

`02` §13 is struck whole — ordering and partitioning are its only two subsections;
R92 §2.2 carries the ordering rule and
`03` §5.2 already carries the partitioning rules. `02` §5.3's sentence forbidding `INT96` is
struck; `03` §5.5 already states it.

`02` §5.3's remaining requirements stay, because a tick being `int64` and a wall clock being a
microsecond UTC timestamp are statements about the value rather than about its storage.

### 3.2 The physical profile

Part 03 is normative for a packet whose manifest declares its `profile_id`, and binds no other
packet. It is the only part that names a storage technology.

No clause of Part 01 or Part 02 **MAY** depend on a clause of Part 03. A logical rule discharged
by a physical property is the defect R92 §2.1
repairs, and this states the general form of it so a later revision does not reintroduce one.

### 3.3 The registry declares no stored order

The `sort` field is removed from `registry.schema.json` and from every table of
`logical_schemas.json`. A table's stored order is its primary key's, unless `03` §5.4 names another
for it, and a named override **MUST** satisfy
R92 §2.2.

Every registry document drops the field, an extension's (R17 §2) as much as core's, since the
amended meta-schema admits no property it does not declare; all eleven extension tables carrying a
`sort` already sort by their own primary key, so none changes but its declaration.

`determined_by` stays in the registry. That `analysis.spike_events.time_bucket_tick` is a function
of `t_tick` is a statement about values, true under any profile, and it is what lets `03` §5.4's
one remaining override coexist with a minimal key.

The validator holds the override list, since a physical rule is the shim's rather than SQL's
(R12 §4), and **MUST** refuse an override that does not satisfy
R92 §2.2 — a check made with no
packet in hand, as R56 §2.4's is. That is what `aind_unit_qc` needed when it went on sorting by two
columns R81 had removed, which no packet could satisfy and no rule could see.

The thirteen tables carrying `sort: null` stop being a category rather than getting filled in: with
no field there is no null, and a table with no override is in key order by rule rather than by a
value someone remembered to write.

### 3.4 Part 10, performance notes

Part 10 is added, wholly **informative**. It carries what a packet's bytes make true under this
profile: the encoding and compression comparisons, row-group sizing, the object-store request rate
R42 and R86 measured, and the storage measurements of R53 and R81.

A clause **MUST NOT** appear in Part 10 and in a normative part both. Where a measurement supports
a rule, the rule stays where it binds and Part 10 carries the reading.

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

R86 §2.4 is the case that splits. Its **~120 requests per second** is the store's and belongs to
Part 10; its **1.02x** projection against a **2.22x** join is one planner's and stays where Part
07 §7 already records it. R43's query timings split the same way and stay in `06`, since what they
justify is a materialization rule rather than a storage choice.

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
because `00` has no contents list at all. R3 §3.0 forbids restating what a document already
declares unless the duplication buys otherwise-unavailable access, and this buys exactly that:
one place that answers which parts bind, which no part can answer about the others.

**Position is not the signal, and is not made into one.** Part 09 is normative and follows two
informative parts, and no arrangement could fix that in general, since Part 06 is normative in two
sections and informative in the rest. Renumbering to tidy the sequence would move identifiers that
**52** citations depend on, many inside accepted revisions and one inside the ledger's own
`where`, so the order stays as it is and the table carries what the order cannot.

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

## 5. What this makes possible

`00` §7.3 says Iceberg is a later profile that MUST NOT be required by an implementation, and `00`
§2 says a physical profile says how the logical resources of Part 02 are stored. Neither is
satisfiable today: an Iceberg profile would inherit `02` §13.1's ordering rules, which its compaction
does not preserve, and `02` §5.3's prohibition on an encoding it does not have.

This part does not add that profile and makes no claim that it is close. What it establishes is
that adding one requires no amendment to Part 01 or Part 02, which is what `00` §2 already
promises.

## 6. What this does not change

Informative.

- **No table, column, reference or rule.** Every change is to which document holds a sentence.
- **No part is renumbered.** §3.5 records why: the sequence cannot express Part 06, and the
  identifiers 52 citations depend on are worth more than a tidy order.
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

Three sentences move out of `02`, one is corrected in `03`, and Part 10 is written from material
that currently sits in accepted revisions and in `conformance/`.

§3.3 removes one field from the registry's meta-schema and from every document written against it:
25 declarations across core and 11 across the four extensions, none of which changes a stored
order. `registry/build.py` loses its `OVERRIDE` table and its fill pass, `registry/render.py` loses
the `**Sort**` line that would otherwise print the same sentence 38 times, and
`escapewheel_validator` gains the profile's override list and the check over it. No packet's rows
move, and no packet is invalidated: the field was never written into one.

`00` gains §3.6's table, eleven rows restating a line each part already carries.
`escapewheel_poc_docs_v0.2/combine.py` gains Part 10 in its concatenation, and the ledger gains
its clauses. The generated `Escapewheel_POC_v0.2_Implementation_Spec.md` grows by Part 10's length
and by nothing else. Part 07 §7 keeps every line it has, one of which — R86 §2.4's projection
measurement — §3.5 confirms belongs to it rather than to Part 10.

## 8. Open

- **Whether Part 10 should carry a version.** The measurements go stale as libraries move, and
  `conformance/`'s probes are re-runnable where a prose reading is not. Dating each measurement is
  the cheaper answer and needs no clause; versioning the part is a decision this revision does not
  take.
- **Whether `01` §2.5's units belong to the semantic standard.** A unit of measure is a semantic
  fact and R56 puts `unit` in the registry, which is Part 02's machine form, so the two parts
  describe one thing at different levels. Nothing is wrong today; the question is whether the
  registry is the logical standard's form or the semantic standard's as well.
- **Whether a second profile should be attempted before v1.** The separation is only tested by
  writing one, and `00` §7.3 defers Iceberg indefinitely. A profile over a single Parquet file
  with no catalog would test it more cheaply.
