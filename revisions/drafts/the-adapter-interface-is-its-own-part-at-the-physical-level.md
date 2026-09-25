# The Adapter Interface Is Its Own Part at the Physical Level

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `be9d1a106c2641ba5d239d8450c38616447adbe6` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 00 §§1, 3.1.3, 9, and 10; Part 03 §§1, 11, and 12; Part 09 §5.8; a new Part 12; the specification README's part table and reference navigation |
| **Depends on** | R93 §3.2; R124 §§3.1 and 3.3; R141 §3.1 |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5 |

Section 3 is normative. Sections 1, 2, 5, and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

Part 03, the portable physical profile, holds in its §11, "Reaching a source", what passes between
a build and its adapters: the routes an adapter delivers by, the protocols rows cross by, the
values a build supplies, what a delivery states, the declaration document, and the source cache.
Part 00 §9 gives Part 03 another subject, the "portable physical mapping of logical resources to
stored bytes", and §11 is now 49% of Part 03's words. An adapter author reads it alongside
Part 09 §5.8, which specifies a run's report for an extension although §11 routes every adapter's report
through it.

This revision moves Part 03 §11 into a new Part 12, "Adapter Interface", and Part 09 §5.8 with it.
Part 12 sits at the physical level beside Part 03 and is bound to the portable profile, so no
relocated rule changes meaning except that Part 09 §5.8's rules take an adapter rather than an
extension as their subject. The Arrow reference entry moves with the text that invokes it, the
Parquet entry becomes shared because two parts then invoke it, and Part 03 §12 becomes section 11. The
core vocabulary's scope, which R141 settled, is outside this revision.

The change is structural because it moves eight sections out of Part 03 and one out of Part 09,
creates a part, and renumbers a section. An appended section could not remove the moved text from
Part 03.

### 1.1 Structural crosswalk

Commit `be9d1a1` gave Part 03 §11.4 the anchor `ew-arrow-ipc-floor`, Part 03 §11.6
`ew-reaching-a-running-adapter`, and Part 09 §5.8 `ew-adapter-run-report`; every other moved
section already had one, and each keeps its anchor. The two new headings are Part 12 section 1, anchored
`ew-adapter-interface-scope`, and Part 12 section 11, anchored `ew-adapter-interface-normative-references`.

Moved text keeps its words. Citations inside it change form only: a citation of another Part 03
section gains "Part 03", one of a moved section takes its Part 12 number, and one of Part 09 §5.8
becomes Part 12 section 9. A section that only cites a moved section, such as Part 05 §3.4 or
Part 09 §5.7, is repointed and has no row.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 03 §1, the incorporation of `registry/resources.schema.json` | move | Part 12 section 1 | none | §3.1 |
| Part 03 §1, "It is the only part whose rules may depend on a storage technology" | replace in place | same section | Parts 03 and 12 are the only such parts | §3.2 |
| Part 03 §1, the authorities its requirements directly invoke | replace in place | same section | Parquet is identified among the shared authorities and the portable-profile entries at §11 | §3.5 |
| Part 03 §11, its list of routes and its definition of an adapter | move | Part 12 section 2 | none | §3.1 |
| Part 03 §11, "This section is what passes between them" and the argument for placing it in the profile | replace | Part 12 section 1 | the interface is a part of the physical level bound to the portable profile | §3.1 |
| Part 03 §11.1 | move | Part 12 section 3 | none | §3.1 |
| Part 03 §11.2 | move | Part 12 section 4 | none | §3.1 |
| Part 03 §11.3 | move | Part 12 section 5 | none | §3.1 |
| Part 03 §11.4 | move | Part 12 section 6 | none | §3.1 |
| Part 03 §11.5, including its incorporation of `registry/adapter.schema.json` | move | Part 12 section 7 | none | §3.1 |
| Part 03 §11.6 | move | Part 12 section 8 | none | §3.1 |
| Part 09 §5.8 | move and widen | Part 12 section 9 | every rule binding an extension's run binds an adapter's | §3.4 |
| Part 03 §11.7 | move | Part 12 section 10 | none | §3.1 |
| Part 03 §12, number and Parquet and Arrow rows | renumber to section 11; rows move | Part 03 section 11; Part 00 §10; Part 12 section 11 | none | §3.5 |
| none | add | Part 12 section 11 | the Arrow entry, invoked only by Part 12 | §3.5 |
| Part 00 §1, the packet mechanism's parts | replace in place | same section | the physical profile is Parts 03 and 12 | §3.2 |
| Part 00 §3.1.3, "Part 03 specifies it" | replace in place | same section | Parts 03 and 12 specify the portable profile | §3.2 |
| Part 00 §9, the part table and dependency direction | add a row and an item | same section | Part 12's subject, status, and dependency direction | §3.3 |
| Part 00 §10, the shared table | add a row | same section | the Parquet entry | §3.5 |
| specification README, part table and reference paragraph | informational projection | same | follows Part 00 §§9 and 10 | none |

## 2. Background

Section 2 is informative. Counts were taken at the recorded baseline. Words and BCP 14 keywords
were counted per section from heading to heading. Citation counts come from a scan of every file
the baseline tracks except the generated rendering and open proposals, counting a linked citation
once. The scan matched `Part 03 §11`, its subsections, `§§` lists containing 11, and the eight
anchors of the moved Part 03 sections.

### 2.1 Part 03 §11 is an interface between parts of a writer

| section | subject | canonical anchor | words | keywords |
|---|---|---|---:|---:|
| §11 | the routes an adapter delivers by | `ew-reaching-a-source` | 276 | 0 |
| §11.1 | protocol groups | `ew-protocol-groups` | 485 | 8 |
| §11.2 | what a build supplies | `ew-build-supplied-values` | 1,099 | 29 |
| §11.3 | what a delivery states | `ew-referenced-resource-delivery` | 1,503 | 35 |
| §11.4 | the Arrow IPC floor | `ew-arrow-ipc-floor` | 412 | 8 |
| §11.5 | the declaration document | `ew-adapter-declaration-document` | 530 | 11 |
| §11.6 | reaching an adapter that must be running | `ew-reaching-a-running-adapter` | 176 | 3 |
| §11.7 | the source cache | `ew-source-cache` | 580 | 13 |

The section holds 5,061 of Part 03's 10,251 words and 107 of its 227 keywords. Its clauses bind
builds and adapters, the two terms Part 00 §2.4 resolves to a writer, and none binds a reader or
validator. The profile descriptor `registry/physical_profiles/escapewheel-portable-v0.1.json` names
no protocol and no §11 anchor.

Three parts of §11 depend on a storage technology: the `files-v0.1`, `stream-v0.1`, and
`flight-v0.1` protocols carry rows as Parquet, Arrow IPC, and Arrow Flight; §11.4 pins an Arrow IPC
member; and a packet-owned array is written as Zarr v3 by citing Part 03 §6.1. Part 00 §3.1.3 makes
a physical profile the only abstraction level whose rules may depend on a storage technology, and
Part 03 §1 makes Part 03 the only such part, so Part 12 needs a place under both sentences.

§11 argues that it is "the profile's rather than the pipeline's because every rule in it would
change if the profile changed". Most would not: the input object on standard input, `needs` and
`accepts`, the declaration document, identifiers as source names, and an empty resource arriving
empty depend on no storage technology. The interface is still the portable profile's, since the
protocol group and the Arrow floor are, so Part 12 is bound to that profile rather than given an
identity of its own.

### 2.2 Part 09 §5.8 already governs every adapter's report

Part 09 §5.8, "What an extension may state about its own run", runs 415 words. Its subject is an
extension, but Part 03 §11 lists a report among every adapter's routes, §11.2 supplies `report_path`
to any adapter reached by `files-v0.1` or `stream-v0.1`, and §11.5 sends every adapter's `stated`
values through the report. The reference writer applies the section to every adapter: the tests
`test_a_stale_report_is_not_read_as_this_runs`, `test_what_the_report_says_is_reported`, and
`test_a_report_is_not_required` in `escapewheel-writer/tests/test_delivery.py` exercise the core
NWB adapter, which delivers no extension.

An extension reaches a build through an adapter (Part 09 §5.7), so widening the subject to an
adapter keeps every rule that bound an extension's report.

### 2.3 Citations into the moved sections

| population | citations | after incorporation |
|---|---:|---|
| Part 03 outside §11, citing §11.3 | 4 in §§1, 2, 4, and 10 | Part 12 section 5 |
| §11 citing another Part 03 section | 12 | each gains "Part 03" |
| §11 citing its own subsections | 19 | renumbered within Part 12 |
| Parts 04 (1), 05 (13), 07 (6), and 09 §5.7 (2) | 22 | repointed |
| §11 citing Part 09 §5.8 | 4 | Part 12 section 9 |
| Part 09 §5.8 citing §11 | 2 | local within Part 12 |
| `revisions/applied.toml` destinations | 46, of 37 clauses in 13 revisions | repointed; below |
| `headings.toml` anchor records, once the bootstrap anchors are recorded | 9 | regenerated |
| Python source and tests | 191 of §11 in 43 files, 12 of Part 09 §5.8 in 7 | repointed |
| `registry/adapter.schema.json` and `registry/recipe.schema.json` descriptions | 6 of §11, 1 of Part 09 §5.8 | repointed; vendored copies regenerate |
| developer documents | 10 of §11 in 5 files, 3 of Part 09 §5.8 in 2 | repointed |
| accepted records | 155 of §11 in 15, 11 of Part 09 §5.8 in 3 | unchanged |
| committed evidence manifests | 25 owner records in 8 | unchanged |

The 46 ledger destinations belong to R109, R111, R115, R116, R117, R119, R129, R130, R133, R134,
R135, R142, and R143. Thirty-eight name a moved anchor and change only their part. Eight are
numeric, Part 03 §11.4 twice, §11.6 once, and Part 09 §5.8 five times, and migrate to the anchors
of `be9d1a1`.

Accepted records are read at their own baselines, and `revisions/evidence.py` resolves a manifest
against the working tree only until its record is committed, so neither population changes.

Part 03 §12 is cited three times outside Part 03 and the accepted records: in Part 00 §10,
Part 03 §1, and the specification README. Its anchor `ew-portable-profile-normative-references` survives
the renumbering.

### 2.4 Alternatives

Keeping the interface in Part 03 leaves half of that part outside the subject Part 00 §9 gives it.
Folding it into Part 05, whose subject is the build's procedure, would put storage-technology rules
in a part outside the physical level. Placing the new part after Part 03 renumbers Parts 04–11,
which 1,078 live citations and ledger destinations in 124 files and 765 accepted-record citations
name; placing it after Part 05 renumbers Parts 06–11, which 162 in 47 files and 250 name. Part 12 renumbers no part, and numbered order was never dependency order, since
Part 00 §9 lists Part 11 third.

Giving the interface an identity and version of its own would let a later profile share it; no
second profile exists, and a new identifier belongs with the final-identifier work. Splitting by
dependence, with the protocol table and the array rule left in Part 03, would divide §11.1 and
§11.3 across two parts that an adapter author must read together. Having the `files-v0.1` row cite
Part 03 §5 in place of Parquet would bind a delivery to Part 03 §5.5's writer floor, which binds no
delivery today.

Part 09 §5.7 stays, since its subject is an extension's registry document and determinism.
Part 05 §§3.4, 3.7, and 4.4 stay, since they are the build's procedure; where one restates a rule
Part 12 owns, the restatement is a separate placement question. Part 03 §9 stays, since amendment
and retention are packet lifecycle.

### 2.5 Feasibility and overlap

No proposal or draft is open besides this one. R142 and R143, which amended Part 03 §§11.2, 11.3,
and 11.7, are incorporated, so the counts above cover the text as it now stands.

Most tooling finds parts by globbing `[0-9][0-9]_*.md`: `combine.py`, `headings.py`, `columns.py`,
`revisions/check_citations.py`, `revisions/impact.py`, and `registry/check.py` need no change for a
new file. `escapewheel_poc_docs_v0.2/framework.py` fixes the part set at 00–11, fixes the reference
allocation, and projects the README part table. `conformance/specification-framework/probe.py`
uses a row for Part 12 as its unknown-part case and expects Parquet's entry in Part 03.

## 3. Decision

Five subsections create Part 12, place it at the physical level, record it in Part 00 §9, widen
the run's report to every adapter, and allocate the reference entries. The crosswalk in §1.1 places
the moved text.

### 3.1 Part 12 specifies the portable profile's adapter interface

Part 12, titled "Adapter Interface", is normative. It specifies what passes between a build and the
adapters it reaches under `escapewheel-portable-v0.1`: the routes an adapter delivers by, the
protocols rows cross by, what a build supplies an adapter, what a delivery states, how an adapter
declares itself and reports its run, and where an adapter may keep what it reads from a source for
later builds. Part 12 is normative for a build writing a packet whose manifest declares
`profile_id: escapewheel-portable-v0.1` and for each adapter such a build reaches, and binds no
other build.

Part 12 incorporates `registry/resources.schema.json`, whose `$id` is
`https://escapewheel.org/schemas/resources/0.5.0`, as the exact shape of the resource document of
its section 5, and `registry/adapter.schema.json`, whose `$id` is
`https://escapewheel.org/schemas/adapter/0.1.0`, as the exact shape of the declaration document of
its section 7.

Part 12's sections carry these numbers, titles, and canonical anchors:

| section | title | canonical anchor |
|---|---|---|
| 1 | Scope | `ew-adapter-interface-scope` |
| 2 | Reaching a source | `ew-reaching-a-source` |
| 3 | Protocol groups | `ew-protocol-groups` |
| 4 | What a build supplies | `ew-build-supplied-values` |
| 5 | What a delivery states | `ew-referenced-resource-delivery` |
| 6 | The Arrow IPC floor | `ew-arrow-ipc-floor` |
| 7 | The declaration document | `ew-adapter-declaration-document` |
| 8 | Reaching an adapter that must be running | `ew-reaching-a-running-adapter` |
| 9 | What an adapter may state about its own run | `ew-adapter-run-report` |
| 10 | The source cache | `ew-source-cache` |
| 11 | Normative references | `ew-adapter-interface-normative-references` |

### 3.2 Parts 03 and 12 specify the portable profile

Part 03 specifies how `escapewheel-portable-v0.1` stores a packet, and Part 12 specifies its
adapter interface. Part 03 is normative for a packet whose manifest declares that `profile_id` and
binds no other packet. A physical profile is the only abstraction level whose rules may depend on a
storage technology, and Parts 03 and 12 are the only parts whose rules may; Part 00 §3.1.3 and Part
03 §1 each say so.

The packet mechanism that Part 00 §1 describes comprises the packet manifest (Part 04), the logical
declaration and registry model (Part 02 §§2–10), the physical profile (Parts 03 and 12), validation
and import (Part 05), extensions (Part 09), and the Tier 2 rule language (Part 11).

### 3.3 Part 00 §9 assigns Part 12

Part 00 §9's table assigns Part 12 the subject "exchange between a build and the adapters it
reaches under a physical profile" and the status normative. Its dependency direction includes,
after the item for Part 03, this item: Part 12 specifies what a build and the adapters it reaches
exchange under a profile without changing Part 02's logical resources and identities or the stored
bytes Part 03 defines.

### 3.4 Every adapter may report its run

Part 12 section 9 states the rules of Part 09 §5.8 with an adapter as their subject:

An adapter MAY validate the tables it delivers before returning them, against the registry that
declares them and on the same terms a validator applies. A build MUST NOT rely on its having done
so; its own validation runs over every staged resource whatever produced it.

An adapter MAY write a report of its run at a path the recipe names, and a build MUST report what
one contains where it is present. A build MUST NOT require one, and MUST NOT fail on a report's
contents alone.

Part 09 §5.8's other rules move to Part 12 section 9 unchanged and govern the report of every adapter.
Part 09 keeps no rule about a report.

### 3.5 Parquet's entry is shared and Arrow's is Part 12's

Part 00 §10 carries this shared entry, since Parts 03 and 12 invoke it directly:

| reference | candidate edition | application |
|---|---|---|
| [Apache Parquet format](https://github.com/apache/parquet-format), including [logical types](https://github.com/apache/parquet-format/blob/master/LogicalTypes.md) | unversioned | Parquet files and logical types |

Part 12 section 11 carries this entry:

| reference | candidate edition | application |
|---|---|---|
| [Apache Arrow columnar format](https://arrow.apache.org/docs/format/Columnar.html), [IPC](https://arrow.apache.org/docs/format/Columnar.html#serialization-and-interprocess-communication-ipc), and [Flight](https://arrow.apache.org/docs/format/Flight.html) | unversioned | Arrow data, IPC, and Flight |

Part 03's normative-reference section is section 11, titled "Normative references" with canonical anchor
`ew-portable-profile-normative-references`, and carries its Zarr, RFC 8878, and RFC 1951 entries.
Part 03 §1 identifies the shared JSON, URI, Parquet, and RFC 1952 authorities of Part 00 §10 and
the entries of Part 03 section 11 as those its requirements directly invoke. Part 12 section 1 identifies the
shared JSON, URI, and Parquet authorities of Part 00 §10 and the entry of Part 12 section 11.

## 5. Consequence

Registry declarations, packet bytes, and every packet's conformance are unchanged, and no packet is
rebuilt. No build or adapter obligation changes, except that §3.4 extends Part 09 §5.8's report
rules from an extension to every adapter, which the reference writer already follows (§2.2). No
schema `$id` changes: the descriptions in `registry/adapter.schema.json` and
`registry/recipe.schema.json` cite Part 12, which changes their bytes as earlier description edits
have.

No accepted clause is superseded. Ledger notes record that R93 §3.2's statement that Part 03
specifies the portable profile now names Parts 03 and 12, that R124 §3.3's allocation moves the
Parquet entry to Part 00 and the Arrow entry to Part 12 and renumbers Part 03 §12 to section 11, and that
R141 §3.1's list of the packet mechanism's parts gains Part 12. Part 00 §7.3's rule that no clause
of Part 01 or Part 02 depends on a clause of Part 03 is unchanged; neither part cites the moved
sections.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. Part 01 cites no moved section. | None required. |
| logical prose and registry | Unchanged. Part 02 cites no moved section, and no declaration changes. | None required. |
| physical profiles | Part 03 loses §11 and its incorporation of the delivery schema; §1's storage-technology and reference sentences take §§3.2 and 3.5; §12 becomes section 11 without the Parquet and Arrow rows; §§2, 4, and 10 repoint. Part 12 is created from the moved text and §3.1's scope. The profile descriptor is unchanged. Part 00 §§1, 3.1.3, 9, and 10 take §§3.2, 3.3, and 3.5. | `evidence/R<N>.json` names `ew-adapter-interface-scope`, `ew-physical-profile`, `ew-portable-profile-scope`, `ew-numbered-part-ownership`, `ew-normative-references`, and `ew-adapter-interface-normative-references`; `framework.py` passes. |
| packet manifest and JSON Schemas | Part 04 §5.4's citation repoints. The two schema descriptions repoint and keep their `$id`; the vendored copies regenerate. | `registry/check.py` and the vendored-copy check in `verify.py`. |
| validation and import | Part 05's 13 citations repoint. No check reads a moved section. | `revisions/check_citations.py`. |
| extensions | Part 09 §5.8 leaves, under §3.4, and §5.7's two citations repoint. No extension registry changes. | `evidence/R<N>.json` names `ew-adapter-run-report`. |
| reader, writer, validator, adapters | Behavior unchanged. 203 source and test citations in 45 files repoint. | The writer tests of §2.2. |
| conformance fixtures and tests | The framework probe's unknown-part case moves to Part 13, and its Parquet placement cases expect Part 00. No packet fixture changes. | `conformance/specification-framework/probe.py`. |
| revision process and tooling | `framework.py` gains Part 12 in its part set and the new allocation; the 46 ledger destinations repoint, eight migrating to anchors; `headings.toml` regenerates; ledger notes on R93 §3.2, R124 §3.3, and R141 §3.1. | `ledger.py`, `headings.py --check`, and `repoint.py`. |
| generated publications and developer documentation | The combined rendering gains Part 12. The specification README's part table gains the row, and its reference paragraph names Part 00 for Parquet, Part 03 section 11, and Part 12 section 11. The specification style guide's placement table gains Part 12, and its first placement test names Parts 03 and 12. Thirteen citations in six developer documents repoint. | `verify.py`. |

## 6. Conformance and implementation evidence

§3.1 is `applied` at `ew-adapter-interface-scope`; §3.2 at `ew-architecture-scope`,
`ew-physical-profile`, and `ew-portable-profile-scope`; §3.3 at `ew-numbered-part-ownership`; §3.4
at `ew-adapter-run-report`; and §3.5 at `ew-normative-references`, `ew-portable-profile-scope`,
`ew-portable-profile-normative-references`, `ew-adapter-interface-scope`, and
`ew-adapter-interface-normative-references`.

No clause changes a verdict, so no packet distinguishes the new text from the current one. The
checks that do are the framework's:

- positive: `framework.py` accepts a candidate whose Part 00 §9 table and README list Parts 00–12,
  whose Parquet entry is in Part 00 §10, and whose Arrow entry is in Part 12 section 11;
- negative: the probe's candidate with a Part 13 row fails as an unknown part, and its candidates
  placing Parquet's entry outside Part 00 fail placement.

§3.4's widening is evidenced by the three writer tests of §2.2, which report, remove, and do without
the report of an adapter that carries no extension. `headings.py --check` confirms every moved
anchor resolves in Part 12, `revisions/check_citations.py` that no live citation names a removed
Part 03 section, and `revisions/repoint.py --quiet` that no ledger destination is stale.
