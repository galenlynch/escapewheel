# The Adapter Interface Is Its Own Part at the Physical Level

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `9bac392d5760d0e800d7707cc37b0002a53d5e88` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 00 §§1, 3.1.3, 7.3, 9, and 10; Part 03 §§1, 11, and 12; Part 09 §5.8; a new Part 12; the specification README's part table and reference navigation |
| **Depends on** | R93 §3.2; R109 §§3.5 and 3.6; R124 §§3.1 and 3.3; R141 §3.1; R143 §§3.2 and 3.3 |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5 |

Section 3 is normative. Sections 1, 2, 5, 6, and 7 are informative.

Normative keywords follow BCP 14.

## 1. Scope

Part 03, the portable physical profile, holds in its §11, "Reaching a source", what passes between
a build and its adapters: the routes an adapter delivers by, the protocols rows cross by, the
values a build supplies, what a delivery states, the declaration document, and the source cache.
Part 00 §9 gives Part 03 another subject, the "portable physical mapping of logical resources to
stored bytes", and Part 03 §11 is half of Part 03's prose. An adapter author reads it alongside
Part 09 §5.8, which specifies a run's report for an extension although Part 03 §11 routes every
adapter's report through it.

This revision moves Part 03 §11 into a new Part 12, "Adapter Interface", and Part 09 §5.8 with it.
Part 12 sits at the physical level beside Part 03 and is bound to the portable profile. The
relocated rules keep their meaning except that Part 09 §5.8's take an adapter rather than an
extension as their subject and, like the rest of Part 12, bind only under the portable profile.
Part 03 §11.3's definition of a payload and its rules for the names a payload keeps describe the
stored packet, so they stay in Part 03 as a new §11, "Opaque storage". Part 00 says that a physical
profile may define an adapter interface and that Parts 03 and 12 form the physical level, and its
rule that Parts 01 and 02 depend on no clause of Part 03 extends to Part 12. The Arrow reference
entry moves with the text that invokes it, and the Parquet entry becomes shared because two parts
then invoke it. The core vocabulary's scope, which R141 settled, is outside this revision.

The change is structural because it moves eight sections out of Part 03 and one out of Part 09,
creates a part, and gives what stays of Part 03 §11.3 a section of its own. An appended section
could not remove the moved text from Part 03.

### 1.1 Structural crosswalk

Commit `be9d1a1` gave Part 03 §11.4 the anchor `ew-arrow-ipc-floor`, Part 03 §11.6
`ew-reaching-a-running-adapter`, and Part 09 §5.8 `ew-adapter-run-report`, and commit `9bac392`
gave Part 00 §7.3 `ew-later-physical-profiles`. Every other affected section already had an
anchor, and each moved section keeps its own. The three new headings are Part 12 section 1,
anchored `ew-adapter-interface-scope`; Part 12 section 11, anchored
`ew-adapter-interface-normative-references`; and Part 03 section 11, anchored `ew-opaque-storage`.

Moved text keeps its words, apart from the citations and the phrases below. Of the citations
inside Part 03 §11:

- the 19 of its own subsections take their Part 12 numbers, and the 4 of Part 09 §5.8 become Part
  12 section 9;
- of the 12 of other Part 03 sections, the 2 of §§3.1 and 4 stay in Part 03 with the text holding
  them, 8 gain "Part 03", one already names Part 03 §8.1, and "the delivery schema §1
  incorporates" names Part 12 section 1, where the incorporation moves;
- Part 12 section 5 cites Part 03 section 11 where it names a payload's shape or a representable
  name.

In the moved text, "This part also incorporates" loses "also", since it opens Part 12's list of
incorporations; §11.5's "which this section forbids requiring", which meant Part 03 §11 as a
whole, becomes "which this part forbids requiring"; and Part 09 §5.8's two citations of Part 03
§§11.2 and 11.5 become local. The four uses of "this profile" keep their words and name the
portable profile, to which Part 12 section 1 binds the part. "A profile adding a term amends this
section" and "An **adapter** here" move unchanged. A section that only cites a moved section, such
as Part 05 §3.4 or Part 09 §5.7, is repointed and has no row.

Splitting Part 03 §11.3 rewords four sentences. Part 03 section 11 opens by saying what a packet
stores for a packet-owned opaque resource, in place of "A packet-owned opaque resource crosses as a
payload: one regular file, …" and "A payload that is a file is a single object, …", and Part 12
section 5 opens its paragraph with "A packet-owned opaque resource crosses as a payload (Part 03
§11)". "Nothing else about a name is refused", which limited the delivery refusals, becomes the
statement that a representable name need not be in any Unicode normalization form and that two
names in one directory may differ only in case. "A build MUST publish each payload under its name"
names the name the payload was delivered under (Part 12 section 5).

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| none | add | Part 12 section 1 | the part's title, status line, scope, and binding | §3.1 |
| Part 03 §1, the incorporation of `registry/resources.schema.json` | move | Part 12 section 1 | none | §3.1 |
| Part 03 §1, "It is the only part whose rules may depend on a storage technology" | replace in place | same section | cites Part 00 §3.1.3 for the parts that may | §3.2 |
| Part 03 §1, the authorities its requirements directly invoke | replace in place | same section | Parquet is among the shared authorities, and JSON Schema, which its incorporations invoke, is named | §3.5 |
| Part 03 §11, its list of routes and its definition of an adapter | move | Part 12 section 2 | none | §3.1 |
| Part 03 §11, "This section is what passes between them" and the argument for placing it in the profile | replace | Part 12 section 1 | the interface is a part of the physical level bound to the portable profile | §3.1 |
| Part 03 §11.1 | move | Part 12 section 3 | none | §3.1 |
| Part 03 §11.2 | move | Part 12 section 4 | none | §3.1 |
| Part 03 §11.3, what a delivery states | move | Part 12 section 5 | none | §3.1 |
| Part 03 §11.3, a payload's shape and "A payload keeps its names" | move | Part 03 section 11 | a stored payload holds no empty directory, which the delivery refusal of one already ensures | §3.2 |
| Part 03 §11.4 | move | Part 12 section 6 | none | §3.1 |
| Part 03 §11.5, with its incorporation of `registry/adapter.schema.json` | move | Part 12 section 7 | none | §3.1 |
| Part 03 §11.6 | move | Part 12 section 8 | none | §3.1 |
| Part 09 §5.8 | move and widen | Part 12 section 9 | every rule binding an extension's run binds an adapter's, under the portable profile | §3.4 |
| Part 03 §11.7 | move | Part 12 section 10 | none | §3.1 |
| Part 03 §12, its Parquet and Arrow rows | move | Part 00 §10; Part 12 section 11 | none | §3.5 |
| none | add | Part 12 section 11 | the Arrow entry, invoked only by Part 12 | §3.5 |
| Part 00 §1, the packet mechanism's parts | replace in place | same section | the physical profile is Parts 03 and 12 | §3.2 |
| Part 00 §3.1.3, the definition of a physical profile and "Part 03 specifies it" | replace in place | same section | a profile may define an adapter interface; Parts 03 and 12 specify the portable profile and form the physical level | §3.2 |
| Part 00 §7.3, "MUST bind only the packets declaring it" and "No clause of Part 01 or Part 02 may depend on a clause of Part 03" | replace in place | same section | an adapter interface binds builds and adapters only under packets declaring its profile, and Part 12 is covered by the dependency rule | §3.2 |
| Part 00 §9, the part table and dependency direction | add a row and an item | same section | Part 12's subject, status, and dependency direction | §3.3 |
| Part 00 §10, the shared table | add a row | same section | the Parquet entry | §3.5 |
| specification README, part table and reference paragraph | informational projection | same | follows Part 00 §§9 and 10 | none |

## 2. Background

Section 2 is informative. Counts were taken at the recorded baseline. Words are whitespace-separated
tokens of prose, excluding headings and anchor lines; BCP 14 keywords are counted from heading to
heading, headings included. Citation counts come from a scan of every file the baseline tracks
except the generated rendering, proposals, and drafts, counting a linked citation once. The scan
matched `Part 03 §11`, its subsections, `§§` lists containing 11, and `Part 09 §5.8`, across line
breaks and comment leaders and with `§` written as `\u00a7`, and the eight anchors of the moved Part
03 sections outside the parts and accepted records.

### 2.1 Part 03 §11 is an interface between parts of a writer

| section | subject | canonical anchor | words | keywords |
|---|---|---|---:|---:|
| Part 03 §11 | the routes an adapter delivers by | `ew-reaching-a-source` | 268 | 0 |
| Part 03 §11.1 | protocol groups | `ew-protocol-groups` | 478 | 8 |
| Part 03 §11.2 | what a build supplies | `ew-build-supplied-values` | 1,090 | 29 |
| Part 03 §11.3 | what a delivery states | `ew-referenced-resource-delivery` | 1,497 | 35 |
| Part 03 §11.4 | the Arrow IPC floor | `ew-arrow-ipc-floor` | 403 | 8 |
| Part 03 §11.5 | the declaration document | `ew-adapter-declaration-document` | 525 | 11 |
| Part 03 §11.6 | reaching an adapter that must be running | `ew-reaching-a-running-adapter` | 164 | 3 |
| Part 03 §11.7 | the source cache | `ew-source-cache` | 572 | 13 |

Part 03 §11 holds 4,997 of Part 03's 9,967 words and 107 of its 227 keywords. Its clauses bind
builds and adapters, the two terms Part 00 §2.4 resolves to a writer, and none binds a reader or
validator. The profile descriptor `registry/physical_profiles/escapewheel-portable-v0.1.json` names
no protocol and no anchor of Part 03 §11.

Three parts of Part 03 §11 depend on a storage technology: the `files-v0.1`, `stream-v0.1`, and
`flight-v0.1` protocols carry rows as Parquet, Arrow IPC, and Arrow Flight; Part 03 §11.4 pins an
Arrow IPC member; and a packet-owned array is written as Zarr v3 by citing Part 03 §6.1. Part 00
§3.1.3 defines a physical profile as how logical resources are stored and makes it the only
abstraction level whose rules may depend on a storage technology, Part 03 §1 makes Part 03 the only
such part, and Part 00 §7.3 keeps Parts 01 and 02 from depending on a clause of Part 03. Part 12
needs a place under all four sentences.

Part 03 §11 argues that it is "the profile's rather than the pipeline's because every rule in it
would change if the profile changed". Most would not: the input object on standard input, `needs`
and `accepts`, the declaration document, identifiers as source names, and an empty resource
arriving empty depend on no storage technology. The interface is still the portable profile's,
since the protocol group and the Arrow floor are, so Part 12 is bound to that profile rather than
given an identity of its own.

Part 03 §11.3 also says what a packet stores for a packet-owned opaque resource. Its payload is one
regular file or one directory of regular files and directories, and the paragraphs beginning "A
payload keeps its names", 210 words holding 3 keywords, define a representable name and require a
build to publish a payload under its names in a directory of its own. Part 03 §4's URI grammar,
which binds readers and validators, uses the representable name; Part 03 §10's digest, Part 04
§5.4's prefix rule, and Part 05 §5.3's name checks use the payload; and the reference reader's
`uri.py` and validator's `opaque.py` cite the section for both. These are facts about the stored
packet, which is Part 03's subject.

### 2.2 Part 09 §5.8 already governs every adapter's report

Part 09 §5.8, "What an extension may state about its own run", runs 399 words and states R109
§§3.5 and 3.6. Its subject is an extension, but Part 03 §11 lists a report among every adapter's
routes, Part 03 §11.2 supplies `report_path` to any adapter reached by `files-v0.1` or
`stream-v0.1`, and Part 03 §11.5 sends every adapter's `stated` values through the report. The
reference writer applies the section to every adapter: the tests
`test_a_stale_report_is_not_read_as_this_runs`, `test_what_the_report_says_is_reported`, and
`test_a_report_is_not_required` in `escapewheel-writer/tests/test_delivery.py` exercise the core
NWB adapter, which delivers no extension.

An extension reaches a build through an adapter (Part 09 §5.7), so widening the subject to an
adapter keeps every rule that bound an extension's report.

### 2.3 Citations into the moved sections

| population | citations | after incorporation |
|---|---:|---|
| Part 03 outside §11, citing Part 03 §11.3 | 4, in §§1, 2, 4, and 10 | §1's moves with the incorporation to Part 12 section 1; §§4 and 10 cite §11; §2's cites §11 and Part 12 section 5 |
| Part 03 §11 citing other Part 03 sections | 12 | as §1.1 says |
| Part 03 §11 citing its own subsections | 19 | renumbered within Part 12 |
| Parts 04 (1), 05 (13), 07 (6), and 09 §5.7 (2) | 22 | Part 04 §5.4's and Part 05 §5.3's name Part 03 section 11; the rest are repointed to Part 12 |
| Part 03 §11 citing Part 09 §5.8 | 4 | Part 12 section 9 |
| Part 09 §5.8 citing Part 03 §11 | 2 | local within Part 12 |
| `revisions/applied.toml` destinations | 46, of 37 clauses in 13 revisions | repointed; below |
| `headings.toml` anchor records, once the bootstrap anchors are recorded | 9 | regenerated |
| Python source and tests | 195 of Part 03 §11 and 12 of Part 09 §5.8, in 45 files | repointed by what each cites |
| descriptions in `registry/adapter.schema.json` (5), `registry/recipe.schema.json` (1), and `registry/resources.schema.json` (1) | 7 of Part 03 §11 and 1 of Part 09 §5.8 | repointed; generated and vendored copies regenerate |
| developer documents | 12 of Part 03 §11 and 3 of Part 09 §5.8, in 7 files | repointed |
| accepted records | 158 of Part 03 §11 in 15, 11 of Part 09 §5.8 in 3 | unchanged |
| committed evidence manifests | 25 owner records in 8 | unchanged |

The 46 ledger destinations belong to R109, R111, R115, R116, R117, R119, R129, R130, R133, R134,
R135, R142, and R143. Thirty-eight name a moved anchor. Of those, R143 §3.3's destination at
`ew-referenced-resource-delivery`, noted "representable names, publication under them in a directory
of its own, and the unchecked-by-validator statement", moves to `ew-opaque-storage` in Part 03, and
the other 37 change only their part. Eight are numeric, Part 03 §11.4 twice, §11.6 once, and Part 09
§5.8 five times, and migrate to the anchors of `be9d1a1`.

Accepted records are read at their own baselines, and `revisions/evidence.py` resolves a manifest
against the working tree only until its record is committed, so neither population changes.

### 2.4 Alternatives

Keeping the interface in Part 03 leaves half of that part outside the subject Part 00 §9 gives it.
Folding it into Part 05, whose subject is the build's procedure, would put storage-technology rules
in a part outside the physical level. Moving Part 03 §11.3 whole would put the representable name,
which Part 03 §4 uses to bind readers and validators, in a part that binds only builds and
adapters, and make Part 03 depend on Part 12 for its own URI grammar.

Placing the new part after Part 03 renumbers Parts 04–11; after Part 05, Parts 06–11. Counting
single-line `Part NN §` citations and ledger `part` values in live files, and the same citations in
accepted records, the first would rewrite 1,078 in 124 files and leave 765 accepted-record
citations naming another part, and the second 162 in 47 files and 250. Part 12 renumbers no part,
and numbered order was never dependency order, since Part 00 §9 lists Part 11 third.

Giving the interface an identity and version of its own would let a later profile share it; no
second profile exists, and a new identifier belongs with the final-identifier work. Splitting by
dependence, with the protocol table and the array rule left in Part 03, would divide Part 03
§§11.1 and 11.3 across two parts that an adapter author must read together. Having the
`files-v0.1` row cite Part 03 §5 in place of Parquet would bind a delivery to Part 03 §5.5's
writer floor, which binds no delivery today.

Part 09 §5.7 stays, since its subject is an extension's registry document and determinism.
Part 05 §§3.4, 3.7, and 4.4 stay, since they are the build's procedure. Part 03 §9 stays, since
amendment and retention are packet lifecycle.

### 2.5 Feasibility and overlap

No proposal or draft is open besides this one. R142 and R143, which amended Part 03 §§11.2, 11.3,
and 11.7, are incorporated, so the counts above cover the text as it now stands.

Part 03 §5.6 mentions Arrow's validity bitmap to explain why one null marker suffices. It bases no
requirement on Arrow, so under Part 00 §10 it is not a direct invocation, and after the move Part
12 is the one part invoking Arrow directly. Parquet is invoked directly by Part 03 §5 and by the
`files-v0.1` row; Parts 05 and 09 cite Part 03's contract rather than Parquet. Part 03 incorporates
`registry/physical_profile.schema.json` and Part 12 will incorporate two schemas, so both invoke
JSON Schema as Part 04, which incorporates the manifest schema, already states it does.

The text moving to Part 12 cites Part 05 sixteen times, six of them its import pipeline in §2, and
Part 05 cites that text twelve times, so Part 12 and Part 05 depend on each other as Part 03 and
Part 05 do now.

Most tooling finds parts by globbing `[0-9][0-9]_*.md`: `combine.py`, `headings.py`, `columns.py`,
`revisions/check_citations.py`, `revisions/impact.py`, and `registry/check.py` need no change for a
new file. `escapewheel_poc_docs_v0.2/framework.py` fixes the part set at 00–11, fixes the reference
allocation and row order, matches each part's invocation sentence against a literal, and projects
the README part table. `conformance/specification-framework/probe.py` uses a row for Part 12 as its
unknown-part case, expects Parquet's entry in Part 03, and matches Part 03's invocation sentence.
`revisions/check_citations.py` reads `Part NN §N` on one line, so it cannot see a citation a line
break or a `\u00a7` escape splits.

## 3. Decision

Five subsections create Part 12, place it and Part 03's opaque storage at the physical level,
record Part 12 in Part 00 §9, widen the run's report to every adapter, and allocate the reference
entries. The crosswalk in §1.1 places the moved text.

### 3.1 Part 12 specifies the portable profile's adapter interface

Part 12, titled "Adapter Interface", is normative. It specifies what passes between a build and the
adapters it reaches under `escapewheel-portable-v0.1`: the routes an adapter delivers by, the
protocols rows cross by, what a build supplies an adapter, what a delivery states, how an adapter
declares itself and reports its run, and where an adapter may keep what it reads from a source for
later builds. Its rules bind a build writing a packet whose manifest declares
`profile_id: escapewheel-portable-v0.1` and each adapter such a build reaches, and bind no other
build.

Part 12's section 1 incorporates `registry/resources.schema.json`, whose `$id` is
`https://escapewheel.org/schemas/resources/0.5.0`, as the exact shape of the resource document of
its section 5. Its section 7 incorporates `registry/adapter.schema.json`, whose `$id` is
`https://escapewheel.org/schemas/adapter/0.1.0`, as the exact shape of the declaration document.

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

### 3.2 Parts 03 and 12 form the physical level

A physical profile defines how logical resources are stored, and can also define the adapter
interface by which a build writing a packet under it receives what adapters read.
`escapewheel-portable-v0.1` defines both. Part 03 specifies how it stores a packet and is normative
for a packet whose manifest declares that `profile_id` and binds no other packet; Part 12 specifies
its adapter interface. A physical profile is the only abstraction level whose rules may depend on a
storage technology, and Parts 03 and 12, which form the physical level, are the only parts whose
rules may. Part 00 §3.1.3 states these facts, and Part 03 §1 cites it for them.

A physical profile's adapter interface binds a build only while the build writes a packet declaring
the profile, and binds an adapter only while such a build reaches it. Part 00 §7.3's other
requirements on a physical profile are unchanged, and no clause of Part 01 or Part 02 may depend on
a clause of Part 03 or Part 12.

Part 03 section 11, titled "Opaque storage" with canonical anchor `ew-opaque-storage`, states what
a packet stores for a packet-owned opaque resource: its payload, one regular file or one directory
whose every member is a regular file or a directory, a single object where it is a file and a
prefix where it is a directory, published under the names it keeps. No directory within a payload,
the payload included, is empty, since a prefix consists of objects. The section carries Part 03
§11.3's definition of a representable name and its rules for publishing a payload, under the names
it was delivered with, in a directory of its own. Part 12 section 5 cites it for a payload's shape
and for a representable name, and a build's refusal of a delivery holding an empty directory stays
there.

The packet mechanism that Part 00 §1 describes comprises the packet manifest (Part 04), the logical
declaration and registry model (Part 02 §§2–10), the physical profile (Parts 03 and 12), validation
and import (Part 05), extensions (Part 09), and the Tier 2 rule language (Part 11).

### 3.3 Part 00 §9 assigns Part 12

Part 00 §9's table assigns Part 12 the subject "exchange between a build and the adapters it
reaches under the portable profile" and the status normative. Its dependency direction includes,
after the item for Part 05, this item: Part 12 specifies what a build and the adapters it reaches
exchange under a profile, within Part 05's import pipeline, without changing Part 02's logical
resources and identities or how Part 03 stores them; Part 05 cites it for what a build supplies an
adapter and what a delivery states.

### 3.4 Every adapter may report its run

Part 12 section 9 states the rules of Part 09 §5.8 with an adapter as their subject:

An adapter MAY validate the tables it delivers before returning them, against the registry that
declares them and on the same terms a validator applies to core. A build MUST NOT rely on its
having done so; its own validation runs over every staged resource whatever produced it.

An adapter MAY write a report of its run at a path the recipe names, and a build MUST report what
one contains where it is present. A build MUST NOT require one, and MUST NOT fail on a report's
contents alone.

Part 09 §5.8's other rules move to Part 12 section 9 unchanged and govern the report of every
adapter. Part 09 keeps no rule about a report. Part 09 §5.8 names no profile; in Part 12 section 9
its rules bind as §3.1 binds Part 12, which changes no build while `escapewheel-portable-v0.1` is
the only physical profile.

### 3.5 Parquet's entry is shared and Arrow's is Part 12's

Part 00 §10 carries this shared entry as the last row of its table, since Parts 03 and 12 invoke it
directly:

| reference | candidate edition | application |
|---|---|---|
| [Apache Parquet format](https://github.com/apache/parquet-format), including [logical types](https://github.com/apache/parquet-format/blob/master/LogicalTypes.md) | unversioned | Parquet files and logical types of stored tables (Part 03 §5) and of `files-v0.1` deliveries (Part 12 section 3) |

Part 12 section 11 carries this entry:

| reference | candidate edition | application |
|---|---|---|
| [Apache Arrow columnar format](https://arrow.apache.org/docs/format/Columnar.html), [IPC](https://arrow.apache.org/docs/format/Columnar.html#serialization-and-interprocess-communication-ipc), and [Flight](https://arrow.apache.org/docs/format/Flight.html) | unversioned | Arrow data, IPC, and Flight |

Part 03 §12 keeps its number, title, and anchor, and its Zarr, RFC 8878, and RFC 1951 entries in
their present order. Part 03 §1 identifies the shared JSON, URI, JSON Schema, Parquet, and RFC 1952
authorities of Part 00 §10 and the entries of Part 03 §12 as those its requirements directly
invoke. Part 12 section 1 identifies the shared JSON, URI, JSON Schema, and Parquet authorities of
Part 00 §10 and the entry of Part 12 section 11.

## 5. Consequence

Registry declarations, packet bytes, and every packet's conformance are unchanged, and no packet is
rebuilt. No build or adapter obligation changes, except that §3.4 extends Part 09 §5.8's report
rules from an extension to every adapter, which the reference writer already follows (§2.2), and
binds them only under the portable profile, the only physical profile there is. No schema `$id`
changes: the descriptions in `registry/adapter.schema.json`, `registry/recipe.schema.json`, and
`registry/resources.schema.json` cite Part 12, which changes their bytes as earlier description
edits have.

No accepted clause is superseded. Ledger notes record that:

- R93 §3.2's statement that Part 03 specifies the portable profile, and its rule at Part 00 §7.3,
  now name Parts 03 and 12;
- R109 §§3.5 and 3.6 bind every adapter under the portable profile, at Part 12 section 9;
- R124 §3.3's allocation moves the Parquet entry to Part 00 and the Arrow entry to Part 12;
- R141 §3.1's list of the packet mechanism's parts gains Part 12; and
- R143 §3.2's definition of a payload's shape is at Part 03 section 11 and the rest of the clause at
  Part 12 section 5, and R143 §3.3's representable names and publication rules are at Part 03
  section 11.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. Part 01 cites no moved section. | None required. |
| logical prose and registry | Unchanged. Part 02 cites no moved section, and no declaration changes; Part 00 §7.3 keeps it from citing Part 12. | None required. |
| physical profiles | Part 03 loses its incorporation of the delivery schema and §11, except a payload's shape and "A payload keeps its names", which become section 11, "Opaque storage"; §1's storage-technology and reference sentences take §§3.2 and 3.5; §12 loses the Parquet and Arrow rows; §§4 and 10 cite section 11, and §2 section 11 and Part 12 section 5. Part 12 is created from the moved text and §3.1's scope. The profile descriptor is unchanged. Part 00 §§1, 3.1.3, 7.3, 9, and 10 take §§3.2, 3.3, and 3.5. | `evidence/R<N>.json` names `ew-adapter-interface-scope`, `ew-adapter-declaration-document`, `ew-architecture-scope`, `ew-physical-profile`, `ew-later-physical-profiles`, `ew-portable-profile-scope`, `ew-opaque-storage`, `ew-numbered-part-ownership`, `ew-normative-references`, `ew-portable-profile-normative-references`, and `ew-adapter-interface-normative-references`; `framework.py` passes. |
| packet manifest and JSON Schemas | Part 04 §5.4's citation names Part 03 section 11. The three schema descriptions repoint and keep their `$id`; `registry/build.py` regenerates the resources schema, and the vendored copies regenerate. | `registry/check.py` and the generation checks in `verify.py`. |
| validation and import | Part 05 §5.3's citation names Part 03 section 11 and Part 05's other 12 name Part 12. No check reads a moved section. | A citation sweep that crosses line breaks and `\u00a7` escapes, and `revisions/check_citations.py`. |
| extensions | Part 09 §5.8 leaves, under §3.4, and §5.7's two citations repoint. No extension registry changes. | `evidence/R<N>.json` names `ew-adapter-run-report`. |
| reader, writer, validator, adapters | Behavior unchanged. Of 207 source and test citations in 45 files, those citing a payload's shape or names, among them the reader's `uri.py` and the validator's `opaque.py`, name Part 03 section 11, and the rest name Part 12. | The writer tests of §2.2, and the citation sweep. |
| conformance fixtures and tests | The framework probe's unknown-part case moves to Part 13; its Parquet placement cases expect Part 00; its Part 03 invocation case follows §3.5's sentence; and it gains cases for a missing Part 12 invocation and for Arrow's entry outside Part 12. No packet fixture changes. | `conformance/specification-framework/probe.py`. |
| revision process and tooling | `framework.py` gains Part 12 in its part set, its reference allocation, row order, and invocation sentences, and the README message. Of the 46 ledger destinations, 37 anchored ones change their part, R143 §3.3's moves to `ew-opaque-storage`, and the eight numeric ones migrate to anchors; R143 §3.2 gains a destination at `ew-opaque-storage`; and the numeric Part 00 §7.3 destinations of R93 §3.2 and R111 §3.5 migrate to `ew-later-physical-profiles`. `headings.toml` regenerates, and the ledger notes above are added. | `ledger.py`, `headings.py --check`, and `repoint.py`. |
| generated publications and developer documentation | The combined rendering gains Part 12. The specification README's part table gains the row, and its reference paragraph names Part 00 for Parquet and Part 12 section 11 for Arrow. Part 07 §4's "the requirements in Part 05 and Part 03" names Part 12. The specification style guide's placement table gains Part 12's subject, which places a statement about what a build and an adapter exchange; its first placement test, which asks whether changing the physical profile would change a statement, names Parts 03 and 12 as the physical level. The root README's physical line names Parts 03 and 12. Fifteen citations in seven developer documents repoint. | `verify.py`. |

## 6. Conformance and implementation evidence

§3.1 is `applied` at `ew-adapter-interface-scope` and `ew-adapter-declaration-document`; §3.2 at
`ew-architecture-scope`, `ew-physical-profile`, `ew-later-physical-profiles`,
`ew-portable-profile-scope`, and `ew-opaque-storage`; §3.3 at `ew-numbered-part-ownership`; §3.4
at `ew-adapter-run-report`; and §3.5 at `ew-normative-references`, `ew-portable-profile-scope`,
`ew-portable-profile-normative-references`, `ew-adapter-interface-scope`, and
`ew-adapter-interface-normative-references`.

No clause changes a verdict, so no packet distinguishes the new text from the current one. The
checks that do are the framework's:

- positive: `framework.py` accepts a candidate whose Part 00 §9 table and README list Parts 00–12,
  whose Parquet entry is the last row of Part 00 §10, whose Arrow entry is in Part 12 section 11,
  and whose Parts 03 and 12 each state §3.5's invocation;
- negative: the probe's candidates with a Part 13 row, with Parquet's entry outside Part 00, with
  Arrow's outside Part 12, or with Part 12's invocation missing each fail.

§3.4's widening is evidenced by the three writer tests of §2.2, which report, remove, and do without
the report of an adapter that carries no extension. `headings.py --check` confirms every moved
anchor resolves in Part 12 and `ew-opaque-storage` in Part 03, and `revisions/repoint.py --quiet`
that no ledger destination is stale. A citation sweep that crosses line breaks and `\u00a7` escapes
confirms that no live citation names a moved section by its Part 03 or Part 09 number, which
`revisions/check_citations.py` alone cannot. Since Part 03 §11 then names opaque storage, the sweep
reads every remaining `Part 03 §11` citation against that section's subject.

## 7. Open

Part 05 §§3.4, 3.7, and 4.4 describe the build's procedure and stay in Part 05. Where one restates
a rule Part 12 will own, whether it becomes a citation is a placement question for a later
revision; either answer leaves this Decision unchanged.
