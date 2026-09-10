# Part 00 — Architecture

Normative.

## 1. Scope

This part defines the architecture of an Escapewheel packet: the vocabulary levels, the layers a packet is divided into, and the storage stance. It defines no schema and no file format; those are Parts 02 and 03.

The design objectives are that a packet be fast to query, straightforward to produce from existing acquisition and sorting outputs, readable from more than one language, independent of HDMF as a runtime data model, and precise enough to drive validation.

## 2. Terms and definitions

### 2.1 Semantic standard

The **semantic standard** defines what concepts mean. A Trial is a bounded interval of experimental time; a Unit is a sorted or curated spiking entity; an ElectricalSeries is sampled extracellular voltage over time and channels.

The semantic standard is independent of storage format, and independent of whether a concept is represented as a table or an array. It is specified in Part 01.

### 2.2 Logical standard

The **logical standard** defines how semantic concepts are represented as computable resources: tables, dense array assets, media assets, document assets, views, materialized tables, materialized arrays, and references between them.

The logical standard is storage-agnostic but not shape-agnostic: trials are logically table-shaped. It is specified in Part 02.

### 2.3 Physical profile

A **physical profile** defines how logical resources are stored. Two are contemplated:

| profile | tables | arrays | catalog |
|---|---|---|---|
| portable | Parquet | Zarr | JSON manifest |
| lakehouse | Iceberg over Parquet | Zarr | JSON manifest plus Iceberg catalog references |

Only the portable profile, `escapewheel-portable-v0.1`, is specified. It is Part 03, which is
normative for a packet whose manifest declares its `profile_id` and binds no other packet, and is
the only part whose rules may depend on a storage technology (R93 §3.2).

### 2.4 Packet

A **packet** is one concrete dataset bundle under a declared profile. It may be a local directory, an object-store prefix, or a manifest pointing at distributed assets.

A packet contains a packet catalog, core tables, and any of: dense arrays, media, documents and sidecars, analysis materializations, and validation and provenance records.

A packet is primarily single-session. Multi-session packets are a permitted extension, and a packet declares its sessions in the catalog (R1 §2).

A packet is the unit of storage and a session is the unit of analysis, so a consumer holding several packets — or one packet holding several sessions — has to know which rows belong to which session. That is derivable rather than declared: a table is **session-scoped** where it reaches `core.sessions` through its declared references, directly or transitively (R86 §2.1). 33 of 35 tables are, the exceptions being `core.subjects` and `core.source_files`, which `core.sessions` references rather than the reverse. `registry/check.py` computes it, and every table carrying a `session_id` reaches the table while eight reach it without carrying the column, so the reference graph is the stricter test.

A reader presenting one or more packets MUST carry a session discriminator on every session-scoped table, and MUST NOT carry one on a table that is not (R86 §2.2). The discriminator is **the packet a row came from together with the row's `session_id`**: the reader opened the file and the identifier is unique within it, so the pair is unique by construction and nothing has to be assumed about the world. A reader MUST NOT derive it from a `*_name` — a name is a label, and 6 of 13 name columns hold a value appearing in both of two packets that share no session, no animal and no probe. It SHOULD carry `session_name` beside the discriminator, which promises nothing: whether two packets' matching labels denote one thing is a fact about the world, and an analyst asserting it does so knowingly.

Session identity MUST NOT become part of a join key where the assigned identifier is already unique (R86 §2.3). Within one packet `unit_id` identifies a unit by itself, and widening the join to `(session_id, unit_id)` costs 2.93x over 286,896,563 spikes; across packets that identifier is genuinely ambiguous and the second column buys correctness.

### 2.5 Packet catalog

The **packet catalog** is the dataset-level map. In the portable profile it is `packet.json`, specified in Part 04.

It records what resources exist, where they live, what semantic type each represents, what logical schema and physical profile each uses, which are canonical and which derived, and what validation and provenance records apply.

### 2.6 Iceberg catalog

An **Iceberg catalog** is distinct from the packet catalog. It is relevant only to the lakehouse profile and manages only tabular resources. It does not catalog dense arrays, media, documents, or semantic relationships across a packet, and therefore does not replace the packet catalog.

### 2.7 Resource identity

Resources and rows reference each other by stable identifier. An implementation MUST NOT use HDF5 object references, Zarr hierarchy paths, host object identity, or file layout as the primary identity system.

### 2.8 Actors

Four actors appear throughout this specification, and every requirement binds one of them or states
a property of an artifact (R111 §3.1, §3.3).

A **writer** produces a packet from sources. It stages, validates and commits, and it is the actor
Part 05 binds throughout.

A **reader** opens a committed packet and returns its resources — rows, arrays, resolved
references. It is bound by what it returns.

A **validator** decides whether a packet conforms, and reports findings.

A **consumer** interprets values a reader returned and acts on them. It is bound by what it
concludes, and it is the only actor that may be a person rather than a program.

An actor is a part someone plays, not a distribution: one program is commonly all four. Naming them
separately is what lets a clause say who owes an obligation.

Three further terms resolve to those four (R111 §3.2). A **build** is one execution of a writer
against one recipe, so a requirement on a build binds the writer performing it — which is what makes
Part 05 §10 decidable, an obligation on a build or a writer being a writer obligation and one on a
packet not. An **adapter** is the part of a writer that reads one source, and an obligation on an
adapter binds the writer that ships it. An **implementation** is software performing one or more of
the four, and is the right subject only where a requirement binds every actor alike, as §2.7's ban
on HDF5 object references does.

`importer` is another name for a writer, `client` and `binding` for a reader, and `caller` for a
consumer (R111 §3.4). An accepted revision using one binds the actor it names.

## 3. Layer model

A packet is divided into layers by namespace prefix.

| layer | contents | required |
|---|---|---|
| `core` | canonical normalized facts, domain-general | yes |
| extensions | canonical facts a domain owns, typed (Part 09) | no |
| `analysis` | derived products, reproducible from the canonical resources | no |
| `nwb` | deferred compatibility projection | no |

A layer MAY reference a layer beneath it and MUST NOT reference one above (R20 §5.1). Core does not reference analysis, and neither references an extension — a discriminator names without referencing, which is why core is allowed that one (R90 §3.9).

A packet's **canonical** resources are its canonical core resources together with its canonical
extension resources (R71 §2.1). Core is not the whole of what is canonical: R54 sends a task's own
facts — which side the animal licked, whether it was rewarded — to a typed extension, and no
computation over core recovers them. Core is what every packet has and what every consumer can
read without an extension registry.

A consumer MAY read core alone, and what it reads is complete for every core resource. It MUST NOT
conclude it has read every canonical fact the packet holds (R71 §2.4); a discriminator resolving
`required` is the case where the omission is guaranteed.

Extension namespaces are additional to these and are specified in Part 09.

## 4. Core layer

### 4.1 Requirements

The core layer MUST contain canonical facts in the logical schemas of Part 02. A writer MUST validate core resources before it commits them.

A fact belongs in core when common interpretation, validation, joining or analysis would break
without it (Part 09 §3). A fact a single domain owns belongs in that domain's extension, typed,
with its own vocabularies and rules — not in core, and not in a free-form column.

Core resources are normalized enough to avoid drift and no further. One row per trial in `core.intervals`; one row per unit in a sorting and curation context in `core.units`; one row per spike in `core.spike_events`.

### 4.2 Spike representation

`core.spike_events`, one row per spike with primitive columns only, is the sole canonical spike representation (R5 §2). The ragged chunked representation of v0.1 is withdrawn, as is the catalog's `canonical_representations` block.

`core.units` carries `n_spikes`, `first_spike_tick` and `last_spike_tick` as a denormalization that a validator checks against `core.spike_events` (R5 §4).

### 4.3 Unit identity

A unit's identity is the tuple `(session_id, unit_id, sorting_run_id, curation_id)`, never `unit_id` alone. A packet carrying sorted units MUST carry `core.sorting_runs` and `core.curation_versions`.

## 5. Analysis layer

### 5.1 Requirements

The analysis layer MAY contain denormalized, prejoined, binned, aligned, or otherwise transformed products. An analysis resource MUST declare lineage to the core resources it derives from.

Analysis resources are disposable. A writer MAY delete and recompute any of them. An analysis resource becomes canonical only through an explicit revision of this specification.

### 5.2 Materialization is justified by layout, not by arithmetic

A derived product is materialized only where a query cannot answer the same question at acceptable cost. Measurement rather than expectation decides this, and four of v0.1's five proposed analysis resources are withdrawn on that basis (R43 §2).

`analysis.spike_events` is retained: it is core's spikes on the reference clock, bucketed by time and sorted by unit within each bucket, so that a time filter and a unit filter both prune (R30 §2).

## 6. Deferred NWB projection

A packet SHOULD preserve enough semantic metadata to support an NWB-like projection later. This specification does not require PyNWB-compatible object reconstruction, NWB/HDF5 or NWB-Zarr export, or a complete mapping onto the `NWBFile` hierarchy.

Reserved NWB names are not honoured. A projection is therefore a mapping exercise and not a renaming.

## 7. Storage stance

### 7.1 Portable profile first

The portable profile is a JSON manifest, Parquet tables, Zarr arrays, ordinary media files, and text sidecars. It MUST be readable without a server.

### 7.2 Referencing

A packet need not own every byte it describes. Referencing is expected for large resources: a resource the packet does not own sets `external: true` with an absolute URI and declares its own codecs (R14 §2.3, R15 §2).

Externalizing a table costs more than externalizing an array, because a table's validation rules cannot run at all while it is unreachable.

### 7.3 Iceberg later

Iceberg is a later table-management profile, useful for table snapshots, schema and partition evolution, concurrent writers, catalog integration, and reproducible release tags. An implementation of this specification MUST NOT require it.

A physical profile — Iceberg's or any other — MUST declare a `profile_id` that a packet's manifest names, MUST bind only the packets declaring it, and MUST say how each logical resource of Part 02 is stored. It MUST NOT require an amendment to Part 01 or Part 02; where one would be needed, the defect is in those parts rather than in the profile (R93 §3.2). No clause of Part 01 or Part 02 may depend on a clause of Part 03.

`packet_version` versions the bundle; an Iceberg snapshot would version a table's rows. A writer MUST NOT increment `packet_version` for a rewrite of rows (R61 §4).

## 8. Implementation thesis

The first implementation is not a generic NWB backend. It is:

1. a specification of core logical resources;
2. a validator generated from that specification;
3. an importer that turns source data into validated resources;
4. a packet catalog recording the committed resources;
5. a small access library querying tables and arrays with standard engines.

An import succeeds only when validation succeeds (Part 05 §1).

## 9. The parts, and what each one binds

A reader learns what binds them here rather than by opening ten files and reading the third line of
each. Each part continues to state its own status at its head, and where the two disagree the
part's statement governs (R93 §3.6).

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
| 09 | metadata minimalism and extensions | normative |
| 10 | performance notes | informative |

Position is not the signal and is not made into one: Part 09 is normative and follows two
informative parts, and no arrangement could fix that in general, since Part 06 is normative in two
sections and informative in the rest. The table is appended rather than inserted for the same
reason the sequence is not renumbered — 119 citations across the accepted revisions and the parts
depend on part and section identifiers both.
