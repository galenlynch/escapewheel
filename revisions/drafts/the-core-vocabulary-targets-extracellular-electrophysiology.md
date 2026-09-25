# The Core Vocabulary Targets Extracellular Electrophysiology

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `3d124a9630793af9916e91a6bbd07e739fb36553` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 00 §§1 and 3.2; Part 02 §2.2 |
| **Depends on** | R128 §3.2 |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4 |

Section 3 is normative. Sections 1, 2, 5, and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

Part 00 §1 says the specification defines "a portable representation of extracellular
electrophysiology data". The packet mechanism confines no packet to that modality: every
extracellular table is optional, and a packet carrying none of them conforms. What targets
extracellular electrophysiology is the core vocabulary, the concepts of Part 01 and the
declarations of the core registry. The text states neither fact. Part 00 §3.2 and Part 02 §2.2 then
define the `core` content class as "domain-general normalized facts", which on its most natural
reading contradicts Part 00 §1.

This revision has Part 00 §1 state both facts and say where another modality's vocabulary is
declared, and it gives `core` a meaning that claims no generality across modalities, in the same
words in both tables. No declaration, packet, or verdict changes. Moving the adapter interface out
of Part 03 is a separate decision and outside this one.

The change is structural because it replaces text inside existing sections: Part 00 §1's statement
of what the specification defines, and the `core` row of two tables. Appended sections would leave
the one-modality scope and "domain-general" standing beside their replacements.

### 1.1 Structural crosswalk

Part 00 §§1 and 3.2 and Part 02 §2.2 already carry the canonical anchors `ew-architecture-scope`,
`ew-packet-content-classes`, and `ew-resource-content-class`, so no anchor bootstrap is needed. No
section is added, moved, split, merged, or retired. The specification README's orientation is
informational and follows Part 00 §1; its ownership does not change.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 00 §1, "This specification defines a portable representation of extracellular electrophysiology data" | replace in place | same section | the specification defines a packet mechanism independent of recording modality | §3.1 |
| none; no text says what the core vocabulary targets | add | Part 00 §1 | the core vocabulary targets extracellular electrophysiology and the session it was recorded in, and requires nothing of a packet | §3.2 |
| none; no text says where another modality's vocabulary is declared | add | Part 00 §1 | an extension under Part 09, reaching core only by a revision under Part 09 §7 | §3.3 |
| Part 00 §3.2, the `core` row, "domain-general normalized facts" | replace in place | same section | normalized facts of the core vocabulary | §3.4 |
| Part 02 §2.2, the `core` row, "domain-general normalized facts" | replace in place | same section | the same words as Part 00 §3.2 | §3.4 |

## 2. Background

Section 2 is informative. Registry counts were taken at the recorded baseline from
`registry/logical_schemas.json` and `registry/extensions/*.json`, concept counts from the
subsections of Part 01 §3, and the packets of §2.3 were built and validated at the same baseline.

### 2.1 The specification states three scopes

| location | what it says | scope it implies |
|---|---|---|
| Part 00 §1 | "a portable representation of extracellular electrophysiology data" | extracellular electrophysiology |
| Part 00 §3.2 and Part 02 §2.2 | `core` holds "domain-general normalized facts" | every domain |
| Part 09 §3 | a field belongs in core when needed to interpret "units, clocks, channels, arrays, or spike times" | a recording, with spikes |
| specification README §1 | "extracellular electrophysiology data", then "whether neurophysiology data can be represented" | two scopes in consecutive paragraphs |
| root README | "An extracellular-electrophysiology data-lake format" | the format itself, not its vocabulary |

"Domain" carries two senses. R71 §2.2 introduced "domain-general" to put identity, time,
instruments, arrays, units, spikes, intervals, and provenance in core and a task's own facts in an
extension. There "domain" means the task or lab an extension serves, as in Part 00 §4.1 ("a fact a
single domain owns belongs in that domain's extension") and Part 09 §2 ("domain-rich, lab-specific
facts"). A reader of Part 00 meets the other sense first, the recording modality of §1, and under
it "domain-general" claims what 15 declared tables contradict (§2.2).

The project sanity check of 2026-09-17 recommended distinguishing the packet architecture from "the
current ecephys/core profile". Part 00 §3.1.3 defines a physical profile and `profile_id` names
one, so this revision calls the core registry and Part 01's concepts a vocabulary.

### 2.2 Fifteen of 43 declared tables are extracellular

The core registry declares 46 resources. Its 42 `core` declarations are 40 tables, the dense-array
family `core.array_asset_instances`, and the opaque family `core.media_asset_instances`; its 4
`analysis` declarations are 3 tables and one dense-array family.

Fifteen of the 43 tables are specific to extracellular electrophysiology: `core.probes`,
`core.electrodes`, `core.electrode_coordinates`, `core.electrode_coordinate_values`,
`core.sorting_runs`, `core.sorting_run_channels`, `core.curation_versions`, `core.units`,
`core.spike_events`, `core.unit_quality_labels`, `core.unit_electrodes`, `core.unit_coordinates`,
`core.unit_coordinate_values`, `core.unit_observation_intervals`, and `analysis.spike_events`.
They hold 112 of the 348 table columns and 17 of the 77 Tier 2 rules.

None is required. `core.sessions` is the one required singleton (Part 02 §2.5), and its required
`subject_id` brings `core.subjects`; neither is extracellular. No declaration names an extracellular
table in `requires`, and the other 28 tables reach the fifteen at one point: none of their 60 rules
reads an extracellular table, and one column, the nullable `core.array_channels.electrode_id`,
references one.

The prose has the same shape. Eight of the 24 concepts of Part 01 §3 are extracellular: Probe,
Electrode, Unit, Spike event, Quality label, ElectricalSeries, Sorting run, and Curation version.
Part 00 §4.2, Part 02 §12.1, Part 02 §12.2, Part 03 §5.4, Part 05 §13.2, and Part 06 §4 state rules
for extracellular tables, and each binds only where its tables are present. Part 01 §3.17 already
lets an array asset hold any sampled quantity, so an instrument the vocabulary does not name needs
no extension to store its samples.

### 2.3 A packet without extracellular data conforms

The four extension registries show what another kind of data needs from core:

| extension | core declarations it references |
|---|---|
| `dynamic_foraging` | `core.sessions`, `core.clocks`, `core.intervals` (also read by a rule) |
| `vr_foraging` | `core.sessions`, `core.intervals` |
| `aind_opto` | `core.sessions`, `core.devices` |
| `aind_unit_qc` | `core.sessions`, `core.units` |

`aind_unit_qc` is the one extension that depends on the extracellular vocabulary, and none of the
four declares a required singleton.

None of the 46 packets of the conformance corpus lacks extracellular tables, so a probe built two.
It took the corpus's valid packet from `fixtures/build.py`'s `content()`, deleted tables, wrote the
result with that module's `write_packet()`, and validated it with `escapewheel_validator.validate`:

- with the 14 extracellular core tables deleted, leaving 15 core tables and
  `dynamic_foraging.trials`, the packet passed with no error or warning;
- with only `core.sessions` and `core.subjects` kept and the session's nullable
  `reference_clock_id` set to null, it passed as well.

Their only findings were `info` findings, about unfilled `metadata` columns, extension tables the
packet did not carry, and data-page types left unassessed. Kept with the corpus's
`reference_clock_id`, the two-table packet fails `packet.resource.reference_target_missing`,
because a populated reference requires `core.clocks`, which is not extracellular.

### 2.4 Alternatives

Keeping the current text leaves a behavior packet conforming while outside the stated scope, beside
a `core` class called "domain-general". Calling the whole specification domain-general sends a
reader looking for another modality's vocabulary to core, where 15 tables and 8 concepts are
extracellular and nothing else modality-specific is. Keeping "domain-general" and defining "domain"
as an extension's task or lab preserves R71's sense but keeps a word most readers take as a
modality. Moving the extracellular declarations into a registry of their own would rename 15
declarations in every packet carrying them and leave `core.array_channels.electrode_id` referencing
an extension, which Part 00 §3.2's direction of reference forbids. Calling the vocabulary a profile
gives that word a second meaning beside Part 00 §3.1.3's physical profile.

### 2.5 Feasibility and overlap

The two other open items, on delivering a packet-owned opaque resource and on a build-supplied
source cache, amend sections of Parts 03 and 05, Part 07 §4, and Part 09 §5.7, none of which this
revision touches. Relocating Part 03 §11 would amend Part 00 §3.1.3, Part 00 §9, and Part 00 §10
and the specification README's part table and reference paragraph, and shares no text with this
revision. §3.1's list of the parts forming the packet mechanism gains the new part when that
relocation lands.

## 3. Decision

Four subsections state what the packet mechanism and the core vocabulary each cover, where another
modality's vocabulary is declared, and what the `core` content class holds. The crosswalk in §1.1
places each at its owner.

### 3.1 The packet mechanism is independent of recording modality

This specification defines a portable data packet as a small semantic and logical standard over
commodity storage formats. Its packet mechanism comprises the packet manifest (Part 04), the
logical declaration and registry model (Part 02 §§2–10), the physical profile (Part 03), validation
and import (Part 05), extensions (Part 09), and the Tier 2 rule language (Part 11), and it confines
no packet to a recording modality. Which resources a packet carries is decided by the registries it
binds and their presence policies (Part 02 §2.5).

### 3.2 Part 01 and the core registry form the core vocabulary

The **core vocabulary** comprises the concepts Part 01 defines and the declarations of the core
registry that Part 02 incorporates. It targets extracellular electrophysiology and the session it
was recorded in. The target states what the vocabulary was designed to represent and requires no
resource of any packet.

### 3.3 Another modality declares its vocabulary in an extension

Another recording modality declares the concepts and resources it needs beyond the core vocabulary
in an extension registry under Part 09 (Part 01 §2.7). They enter the core vocabulary only through a
revision of this specification under Part 09 §7. Data of another modality that a core declaration
already represents, such as a sampled quantity held as an array asset (Part 01 §3.17), needs no
extension.

### 3.4 The `core` content class holds the core vocabulary's facts

The `core` value of `content_class` means normalized facts of the core vocabulary. Part 00 §3.2 and
Part 02 §2.2 each state that meaning in those words; the canonical and required-by-class columns of
both rows are unchanged.

## 5. Consequence

Registry declarations, packet bytes, and every packet's conformance are unchanged, and no packet is
rebuilt. No packet-recorded identifier changes, since no registry or schema byte changes.
Part 00 §4.1 and Part 09 §2 keep "domain" in its sense of a task or lab, and the `extension` rows
of both tables are unchanged.

No accepted clause is superseded. R128 §3.2's table gave `core` the meaning "domain-general
normalized facts", and §3.4 replaces that one cell; its ledger entry, applied at
`ew-packet-content-classes` and `ew-resource-content-class`, gains a note. R71 §2.2, whose
destination is Part 05's error policy, is unaffected, and no ledger entry names Part 00 §1.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Part 00 §1 takes §§3.1–3.3, and Part 00 §3.2 takes §3.4. Part 01's concepts keep their meanings. | `evidence/R<N>.json` names `ew-architecture-scope` and `ew-packet-content-classes`. |
| logical prose and registry | Part 02 §2.2's `core` row takes §3.4. No declaration and no `content_class` value changes, and no registry description states the class's meaning. | `evidence/R<N>.json` names `ew-resource-content-class`. |
| physical profiles | Unchanged. Part 03 and `profile_id` name no modality. | None required. |
| packet manifest and JSON Schemas | Unchanged. `registry/registry.schema.json` enumerates the `content_class` values without stating their meanings, and a manifest does not repeat a resource's content class. | None required. |
| validation and import | Unchanged. No check reads the scope or a content class's meaning. | None required. |
| extensions | Unchanged. The four registries keep their declarations; §3.3 says where a future modality's vocabulary is declared. | None required. |
| reader, writer, validator, adapters | Unchanged. No source or test reads or quotes the scope or "domain-general". | None required. |
| conformance fixtures and tests | The corpus gains the two packets of §2.3 as clean variants, so a future rule tying core to extracellular tables would fail them. Neither distinguishes the new text from the current, since both pass today; the corpus counts regenerate. | `fixtures/corpus.py`. |
| revision process and tooling | The R128 §3.2 ledger note, and ordinary ledger and evidence records. No heading changes. | `ledger.py` and `evidence.py`. |
| generated publications and developer documentation | The combined specification regenerates. The specification README's §1 follows Part 00 §1 in both paragraphs, and the root README's opening line describes a data-lake format whose core vocabulary targets extracellular electrophysiology. | `verify.py`. |

## 6. Conformance and implementation evidence

Each clause is `applied` by canonical anchor: §§3.1–3.3 at `ew-architecture-scope`, and §3.4 at
`ew-packet-content-classes` and `ew-resource-content-class`.

No clause changes a verdict, so no packet can distinguish the new text from the current one, and
there is no negative case. The positive cases are the two packets of §2.3, which pass the validator
today and which the corpus would carry as clean variants: the valid packet without its 14
extracellular core tables, and the packet of `core.sessions` and `core.subjects` alone whose session
names no reference clock.

§3.4's two rows are compared by review, since no tool reads either table's meaning column.
§§3.1–3.3 bind no actor, so their evidence is review of Part 00 §1 against them and of the
specification README against Part 00 §1.
