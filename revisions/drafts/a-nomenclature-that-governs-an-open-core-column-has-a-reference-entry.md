# A Nomenclature That Governs an Open Core Column Has a Reference Entry

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `0526ab09528afca6dbea7e79fe10cdea51846c29` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 00 §10; Part 02 §§9.3 and 13 |
| **Depends on** | R101 §§3.5, 3.6, and 3.9; R124 §§3.2 and 3.3; R131 §3.1 |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4 |

Section 3 is normative. Sections 1, 2, 5, and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

Part 02 §9.3 lets a string column declare `authority`, an array naming the nomenclatures its values
are drawn from, and requires a writer to spell a value as the named nomenclature does. Part 00 §10
calls prose that bases a requirement on an external authority a direct invocation, and requires one
bibliographic entry for each directly invoked authority and an exact edition of it in a release.

The core registry names five nomenclatures, and Part 02 §13 has an entry only for UCUM, the Unified
Code for Units of Measure. NCBI Taxonomy, the Mouse Genome Informatics (MGI) and Rat Genome Database
(RGD) strain registries, and HL7 FHIR's administrative-gender value set have none. Writing those
entries exposes two further defects. `core.subjects.sex` is closed and admits `hermaphrodite`, which
FHIR's value set lacks, so a writer recording a hermaphrodite subject cannot satisfy Part 02 §9.3 as
written. NCBI Taxonomy, MGI and RGD change continually, so Part 00 §10's release rule would pin each
to a dated state, after which a newly registered species or strain has no conforming spelling.
Part 02 §9.3's spelling rule also has no answer for a value its nomenclature does not register, such
as a strain not yet registered, and no validator can check the rule.

This revision confines the spelling rule to open columns, so that a closed column's `authority`
records provenance and invokes nothing, and to values whose registered name a writer can identify,
so that a writer writes any other value as the source states it. It states that no validator checks
the rule. It adds a living-registry entry kind to Part 00 §10, which a release identifies by name
and URI rather than edition. It gives Part 02 §13 the three-column table the other parts use, with
entries for NCBI Taxonomy, MGI and RGD as living registries beside UCUM's exact edition, and makes
every authority on an open column of the core registry need an entry there.

The change is structural because it replaces rules inside existing sections: Part 00 §10's edition
paragraph, Part 02 §9.3's spelling sentence, and Part 02 §13's one-item list. Appended sections
would leave each stating a broader or narrower rule beside its replacement.

### 1.1 Structural crosswalk

Part 00 §10 and Part 02 §§9.3 and 13 already carry the canonical anchors `ew-normative-references`,
`ew-registry-vocabularies`, and `ew-logical-schema-normative-references`, so no anchor bootstrap is
needed. No section is added, moved, split, or retired.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 02 §9.3, "A writer MUST spell a value as the named nomenclature does" | replace in place | same section | the rule binds values of open columns whose registered name a writer can identify and cites Part 02 §13; any other value is written as the source states it; no validator checks either, except a unit column's value under Part 02 §8.4; a closed column's `authority` is provenance | §3.1 |
| Part 00 §10, the paragraph defining the exact and unversioned entry kinds and stating the release rule | replace in place | same section | adds the living-registry kind; a release identifies a living registry by name and URI | §3.2 |
| Part 02 §13, a one-item list naming UCUM 2.2 | replace in place | same section | a three-column table of UCUM, NCBI Taxonomy, MGI, and RGD; the closing paragraph on offline validation stays | §3.3 |
| none; nothing ties an authority in the core registry to a reference entry | add | Part 02 §13 | every authority on an open column of the core registry has an entry there | §3.4 |

## 2. Background

Section 2 is informative. Registry observations were read at the recorded baseline; the external
registries' pages were read on 2026-09-24.

### 2.1 The core registry names five authorities, and Part 02 §13 lists one

A walk of every column's `authority` array in `registry/logical_schemas.json` and in the four
extension registries under `registry/extensions/` found twelve columns declaring one, all in the
core registry:

| authority | URI | columns | vocabulary | Part 02 §13 entry |
|---|---|---:|---|---|
| UCUM | `https://ucum.org/ucum` | 9 | open | version 2.2, revision date 2024-06-17 |
| NCBI Taxonomy | `https://www.ncbi.nlm.nih.gov/taxonomy` | 1, `core.subjects.species` | open | none |
| MGI | `https://www.informatics.jax.org/` | 1, `core.subjects.strain` | open | none |
| RGD | `https://rgd.mcw.edu/` | 1, `core.subjects.strain` | open | none |
| HL7 FHIR administrative gender | `https://hl7.org/fhir/valueset-administrative-gender.html` | 1, `core.subjects.sex` | closed | none |

Two of UCUM's nine columns, `analysis.array_assets.unit` and
`analysis.array_dimensions.coordinate_unit`, are in the core registry's `analysis` namespace. No
extension registry declares an authority. NCBI Taxonomy, MGI, RGD and HL7 reach the specification
only through Part 02's incorporation of the core registry, so Part 00 §10 places any entry for them
in Part 02.

`core.subjects.genotype` is open and declares no authority; its description asks for "the genotype
as the source states it, in MGI allele nomenclature where it uses one". The description defers to
the source, and Part 02 §9.3's spelling rule binds only a nomenclature named in `authority`, so the
column invokes nothing.

### 2.2 `core.subjects.sex` admits a value its authority lacks

`core.subjects.sex` declares the `enum` `male`, `female`, `hermaphrodite`, `other`. Its authority's
page is FHIR 5.0.0, whose value set holds `male`, `female`, `other` and `unknown`. R101 §3.6 put
FHIR on the column as the source of three values' spelling, stating that "drawn from is not equal
to" and that the `enum` is the set a validator enforces. Part 02 §9.3 does not carry that
distinction, so its spelling sentence reaches `sex` as it reaches `species`. The reference writer's
`sex` mapping, which the AIND adapter shares, targets the four `enum` values, so no packet depends
on the literal reading.

### 2.3 NCBI Taxonomy, MGI and RGD publish dated states, not editions

On 2026-09-24:

- NCBI's `pub/taxonomy/` directory held a `taxdump.tar.gz` modified that day, and no file there
  carries a version or edition label; `pub/taxonomy/taxdump_archive/` holds monthly snapshots from
  `taxdmp_2014-08-01.zip` to `taxdmp_2026-09-01.zip`.
- MGI's home page read "last database update 09/08/2026, MGI 6.24", a weekly update date and a
  software version.
- RGD's home page read "RGD Data Snapshot 2026-09-17", with no version number.

MGI and RGD register strain symbols as they are assigned. *Guidelines for Nomenclature of Mouse and
Rat Strains*, revised September 2024 and reviewed annually by the international mouse and rat
nomenclature committees, fix a symbol's form; the registries record which symbol a strain has.

Part 00 §10 recognizes an exact entry, naming an edition, and an unversioned entry, which a release
must replace with an exact edition. Each registry has a nameable dated state, but a species or
strain registered after that date would have no conforming spelling. No validator verdict depends
on the state, because Part 02 §9.3 forbids a validator to dereference an authority URI or to reject
a value for being absent from its column's authority.

### 2.4 The spelling rule has no answer for an unregistered value

Part 02 §9.3's sentence "A writer MUST spell a value as the named nomenclature does" assumes the
nomenclature registers what the value names. Where it does not, as for a strain not yet registered
with MGI or a species a source states in a form the writer cannot map to a scientific name, a writer
has no conforming spelling short of inventing a registered name the source never stated. No
validator can tell compliance from noncompliance, because Part 02 §9.3 forbids it to dereference an
authority or to reject a value absent from one. Unit columns differ: Part 02 §8.4 makes each value a
unit code, and Part 05 §5.3 has a validator parse it.

The reference writer's NWB source and the AIND adapter write `species` and `strain` as the source
states them and map neither. No writer or adapter test checks a `species` or `strain` spelling.

### 2.5 The framework check allocates no Part 02 rows

`escapewheel_poc_docs_v0.2/framework.py` compares the reference rows of Parts 00, 03, 04, and 11
with an approved allocation and finds an allocated authority copied into another part's reference
section. Part 02 §13 has no table and no allocation, and UCUM is not among the checked authorities,
so an entry dropped from Part 02 §13 or copied elsewhere goes unreported. Part 05 §15's TOML entry
is outside the allocation too; this revision does not need it there.

### 2.6 Alternatives

Giving HL7 FHIR an entry would make it the basis of a requirement `hermaphrodite` cannot satisfy.
Barring `authority` from a closed column would move `sex`'s provenance back into prose, which
R101 §3.6 kept it out of. Pinning each living registry to a dated snapshot would leave later
registrations without a conforming spelling and move the pin at every release. Citing the strain
guidelines in place of MGI and RGD fails because they fix a symbol's form and not which symbol a
strain was registered under, and NCBI Taxonomy has no counterpart document. Demoting the spelling
rule to a recommendation fails because values are compared exactly, and R101 §3.5 made it a
requirement since `mouse` and `Mus musculus` fail to name one animal. Keeping the rule unscoped
leaves a writer holding an unregistered value no conforming spelling, and having a validator check
spellings against a registry needs the dereference Part 02 §9.3 forbids. Stating §3.4's condition
as a registry-document invariant would bind every extension registry to Part 02's bibliography,
although an extension names nomenclatures on its own terms.

### 2.7 Feasibility and overlap

Every entry identifies its authority by the URI the core registry already declares, so §3.4 is
decidable by comparing strings from two artifacts the repository holds, and no registry declaration
changes.

R136 moved RFC 1952's entry from Part 03 §12 into Part 00 §10's table, moved its row in
`framework.py`'s allocation from Part 03 to Part 00, added Part 04 rows for the CRC64NVME and CRC32C
authorities, and revised the Part 00 and Part 04 sentences of the specification README's paragraph
naming each part's references. It left Part 00 §10's edition paragraph and the README's Part 02
sentence as they were, so this draft's replacements apply to the current text, and RFC 1952's exact
entry is unaffected. R137 amended Part 03 §§5.5 and 6.4 and Part 05 §5.3; the Blosc and
sharding-indexed codecs it admitted to the Zarr v3 floor have unversioned entries in Part 03 §12,
whose release treatment this draft leaves unchanged. R138 amended Part 05 §3.1. R137 and R138 share
no text with this draft.

One other draft is open. `a-float-column-declares-whether-it-admits-non-finite-values.md` edits
Part 02 §§3, 5, 9.2, 9.4, and 10.1 and the specification README's identifier table, and cites
Part 02 §9.3's rule that an absent `vocabulary` is a defect, which this draft keeps. The two share
no text and neither depends on the other; the drafts' application order puts the float draft first.

## 3. Decision

Four subsections scope the spelling rule, add the living-registry entry kind, fix Part 02's
reference entries, and tie the core registry's authorities to them. The crosswalk in §1.1 places
each at its owner.

### 3.1 The spelling rule governs open columns

Where a writer can identify the name that a nomenclature in an open column's `authority` registers
for the thing a value names, it MUST write that name as the nomenclature spells it. Otherwise, as
for a strain not yet registered or a source value matching no registered name, a writer MUST write
the value as the source states it. A validator verifies neither obligation, since it neither
dereferences an authority nor rejects a value for being absent from one. A unit column's value is
the exception: Part 02 §8.4 requires it to be a UCUM code whatever the source states, and a
validator checks it by UCUM's grammar. Part 02 §13 identifies each nomenclature the core registry
names in this way, and the edition that applies.

A closed column's `enum` is its whole value set and spells every value it admits. On a closed
column, `authority` records where the `enum`'s spelling came from and invokes no nomenclature.

### 3.2 A living registry is an entry kind

A **living-registry** entry identifies a registry that assigns names or identifiers as they are
registered, by the registry's name and URI, and gives `living registry` as its candidate edition. A
numbered part MAY give an authority a living-registry entry only where the authority is such a
registry and no validator verdict depends on its content. A requirement invoking a living registry
refers to the registry as it stood when the bound actor acted; for a spelling requirement, when the
writer wrote the value, so a later registration or renaming leaves the value conforming.

A specification release MUST identify the exact external edition on which every conformance
requirement depends, and MUST identify each living registry by its entry's name and URI in place of
an edition. The exact and unversioned entry kinds are unchanged.

### 3.3 Part 02's normative references

Part 02 §13 lists its external authorities in the reference, candidate edition, and application
table the other normative-reference sections use, introduced by the sentence that states the
application column's role, and holds exactly these entries:

| reference | candidate edition | application |
|---|---|---|
| [The Unified Code for Units of Measure](https://ucum.org/ucum) | version 2.2, revision date 2024-06-17 | unit codes (§8.4) and the spelling of values in open columns naming it (§9.3) |
| [NCBI Taxonomy](https://www.ncbi.nlm.nih.gov/taxonomy) | living registry | the spelling of the names it registers, in open columns naming it (§9.3) |
| [Mouse Genome Informatics (MGI)](https://www.informatics.jax.org/) | living registry | the spelling of the names it registers, in open columns naming it (§9.3) |
| [Rat Genome Database (RGD)](https://rgd.mcw.edu/) | living registry | the spelling of the names it registers, in open columns naming it (§9.3) |

HL7 FHIR has no entry.

### 3.4 Every authority on an open core column has an entry

Part 02 §13 MUST carry an entry whose link is the `uri` of each `authority` entry declared on an
open column of the incorporated core registry, in either of its namespaces. A core registry naming
such an authority without a matching entry makes the candidate internally inconsistent under
Part 00 §2.3.

The comparison is exact on the URI string and dereferences nothing, so a check decides it from the
core registry and Part 02 §13 alone. It catches an authority URI on an open core column that no
Part 02 §13 entry links, and names the column and the URI. An extension registry's authorities are
outside the condition.

## 5. Consequence

Packet bytes, registry declarations, and every existing packet's conformance are unchanged, and no
packet is rebuilt. A writer recording a hermaphrodite subject now conforms on the column's own
terms, and one holding a value for which it can identify no registered name conforms by writing it
as the source states it. A release gains three living-registry identifications and no pinned
registry state.

No accepted clause is superseded. R101 §3.5's spelling sentence is narrowed to open columns and to
values whose registered name a writer can identify, and R101 §§3.6 and 3.9 keep FHIR on `sex` as
provenance; the three ledger entries gain notes recording this. R101 §3.5 keeps the `registry`
disposition that records its description requirement. R124 §3.2 gains the third entry kind and R124
§3.3's allocation gains Part 02's section, each with a note. R131 §3.1's UCUM edition stands in the
new table. Eleven ledger destinations naming Part 02 §9.3 by number, from R8 §§3 and 4, R9 §6, R22
§3, R101 §§3.1, 3.3, 3.6, 3.9, and 3.11, and R107 §§3.3 and 3.4, move to `ew-registry-vocabularies`.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. A nomenclature governs how a value is spelled, not what a concept means. | None required. |
| logical prose and registry | Part 02 §9.3 takes §3.1; Part 02 §13 takes §§3.3 and 3.4. No `authority`, vocabulary, or `enum` changes, and no declared rule reads `authority`. | `evidence/R<N>.json` names both anchors. |
| physical profiles | Unchanged. `authority` has no physical representation. | None required. |
| packet manifest and JSON Schemas | Unchanged. A manifest binds registries, not their references, and the registry schema's `authority` shape stands. | None required. |
| validation and import | Unchanged. Part 02 §9.3 already forbids a validator to dereference an authority or reject a value it lacks, so §3.1 adds no check; the `enum` check on `sex` and Part 05 §5.3's unit-code check stand. | None required. |
| extensions | Unchanged. No extension registry declares an authority, and §3.4 excludes one that does. | None required. |
| reader, writer, validator, adapters | Unchanged. The writer's `sex` mapping, which the AIND adapter shares, already targets the `enum`; the writer and the AIND adapter write `species` and `strain` as the source states them; and no reader or validator reads an authority's content. | `test_a_subjects_sex_lands_inside_the_closed_vocabulary` in the writer suite. No test covers `species` or `strain`. |
| conformance fixtures and tests | `framework.py` gains probes: an entry removed from Part 02 §13, a Part 02 entry copied into another part's reference section, and an open core column naming an authority URI no Part 02 §13 entry links. Packet fixtures are unchanged, because no packet-level rule changes. | `framework.py`'s probes. |
| revision process and tooling | `framework.py`'s allocation gains Part 02 §13's section, its four rows, and an owner for each authority, and it gains §3.4's check, which reads the core registry because the condition is a consistency condition of the candidate rather than of a registry document. The ledger changes as stated above. | `framework.py`, `ledger.py`, and `evidence.py`. |
| generated publications and developer documentation | The combined specification regenerates. The last sentence of the specification README's reference paragraph, which places the UCUM and URI authorities in Part 02 §13, names UCUM and the three registries there, since RFC 3986's entry is in Part 00 §10. | `verify.py`. |

## 6. Conformance and implementation evidence

Each clause is `applied` by canonical anchor: §3.1 at `ew-registry-vocabularies`, §3.2 at
`ew-normative-references`, and §§3.3 and 3.4 at `ew-logical-schema-normative-references`.

The negative cases distinguish the new rules from the current ones:

- a candidate whose core registry declares an authority on an open column that Part 02 §13 does not
  link is reported, where nothing reports it now;
- a Part 02 §13 entry dropped, or copied into another part's reference section, is reported, where
  Part 02 is outside the allocation now; and
- a Part 02 §13 row whose edition or application differs from §3.3's is reported.

The positive cases are the candidate after incorporation, which passes `framework.py`, and a
`core.subjects.sex` value of `hermaphrodite`, which conforms under §3.1 and already passes the
validator.

§3.1's open-column rule has no negative case a tool can run, because deciding what name a
nomenclature registers for what a value names needs the dereference Part 02 §9.3 forbids. Its
evidence would be a writer's own mapping tests, and none exists: the reference writer and the AIND
adapter map no `species` or `strain` value, and no test checks either spelling.

§3.2 binds numbered parts and a release rather than an actor a probe can run, so its evidence is
review of Part 00 §10 and of each living-registry entry against its condition.
