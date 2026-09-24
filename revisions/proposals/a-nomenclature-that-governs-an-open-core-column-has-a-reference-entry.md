# A nomenclature that governs an open core column has a reference entry

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-24 |
| **Based on** | `f5f33647eb9c3e29ff8c850afa480468fea0c582` |
| **Decision domain** | specification |
| **Affects** | Part 00 §10; Part 02 §§9.3 and 13; the specification framework check of reference allocation |

## 1. Problem

Part 02 §9.3 lets a string column declare `authority`, an array naming the
nomenclatures its values are drawn from, and requires a writer to spell a value
as the named nomenclature does. A writer obligation resting on an outside
nomenclature is what Part 00 §10 calls a direct invocation. A directly invoked
authority needs one bibliographic entry, and a release needs its exact edition.

The core registry names five nomenclatures, and Part 02 §13 has an entry only
for UCUM, the Unified Code for Units of Measure. NCBI Taxonomy, the Mouse Genome
Informatics (MGI) and Rat Genome Database (RGD) strain registries, and HL7
FHIR's administrative gender value set have none.

Writing those entries exposes two further defects:

- `core.subjects.sex` is closed, and its `enum` includes `hermaphrodite`, which FHIR's value set
  does not define. Read literally, Part 02 §9.3 requires a writer recording a hermaphrodite subject
  to spell the value as FHIR does, which it cannot.
- NCBI Taxonomy, MGI and RGD are databases whose entries change continually. Part 00 §10's release
  rule would pin each to a dated state, after which a newly registered species or strain has no
  conforming spelling.

## 2. Evidence

### 2.1 The core registry names five authorities, and Part 02 §13 lists one

A walk of every column's `authority` array in `registry/logical_schemas.json` and the four
extension registries under `registry/extensions/`, at the baseline, found:

| authority | URI | core columns | vocabulary | Part 02 §13 entry |
|---|---|---:|---|---|
| UCUM | `https://ucum.org/ucum` | 9 | open | version 2.2, revision date 2024-06-17 |
| NCBI Taxonomy | `https://www.ncbi.nlm.nih.gov/taxonomy` | 1 (`species`) | open | none |
| MGI | `https://www.informatics.jax.org/` | 1 (`strain`) | open | none |
| RGD | `https://rgd.mcw.edu/` | 1 (`strain`) | open | none |
| HL7 FHIR administrative gender | `https://hl7.org/fhir/valueset-administrative-gender.html` | 1 (`sex`) | closed | none |

No extension registry declares an authority, and no numbered part names NCBI Taxonomy, MGI, RGD or
HL7 in its prose. They reach the specification only through Part 02's incorporation of the core
registry, so Part 00 §10 places any entry for them in Part 02.

`core.subjects.genotype` is open, declares no authority, and describes its values as "the genotype
as the source states it, in MGI allele nomenclature where it uses one". The description defers to
the source, and Part 02 §9.3's spelling rule binds a writer only to a nomenclature named in
`authority`, so the column adds no invocation.

### 2.2 `core.subjects.sex` admits a value its authority lacks

`core.subjects.sex` declares `enum` `male`, `female`, `hermaphrodite`, `other`. The page its
authority names belongs to FHIR R5 (5.0.0), whose value set holds exactly `male`, `female`,
`other` and `unknown`. R101 §3.6 put FHIR on the column as the source of three values' spelling and
states that "drawn from is not equal to": the `enum` is the set a validator enforces. Part 02 §9.3
does not carry that distinction, so its spelling sentence applies to `sex` as it does to
`species`.

### 2.3 NCBI Taxonomy, MGI and RGD publish dated states, not editions

- **NCBI Taxonomy.** `ftp.ncbi.nlm.nih.gov/pub/taxonomy/` published a new `taxdump` on 2026-09-24,
  and no file there carries a version or edition label. `pub/taxonomy/taxdump_archive/` holds dated
  monthly snapshots from `taxdmp_2014-08-01.zip` to `new_taxdump_2026-09-01.zip`.
- **MGI and RGD.** Both register strain symbols as they are assigned. The rules for forming a
  symbol are published separately as *Guidelines for Nomenclature of Mouse and Rat Strains*,
  revised September 2024 and reviewed annually by the international mouse and rat nomenclature
  committees; the guidelines fix a symbol's form, and the registry records which symbol a strain
  has. On 2026-09-24 MGI's home page read "last database update 09/08/2026, MGI 6.24", a software
  version and the date of a weekly database update, and RGD's read "RGD Data Snapshot 2026-09-17",
  with no version number.

Part 00 §10 recognizes two entry kinds. An exact entry names an edition. An unversioned entry
follows the linked specification during candidate development, and a release must replace it with
an exact edition. Each of the three registries has a nameable dated state, so a release could name
one, but a strain or species registered after that date would then have no conforming spelling;
a living registry is followed as it stands, which neither kind admits.

### 2.4 The framework check covers four parts

`escapewheel_poc_docs_v0.2/framework.py` checks the reference rows of Parts 00, 03, 04 and 11
against an approved allocation (`REFERENCE_ANCHORS`, `REFERENCE_ROWS`). Part 02 §13 is a bulleted
list without the `reference | candidate edition | application` table the other parts use, and
neither UCUM nor Part 05's TOML entry is in the allocation.

## 3. Desired outcome and constraints

Each nomenclature the specification binds a writer to has exactly one bibliographic entry, whose
edition status a release can satisfy, and a closed column's `enum` stays the whole of its value set.
The outcome preserves:

- every value in every existing packet;
- R101's use of `authority` on a closed column as provenance;
- Part 02 §9.3's prohibition on dereferencing an authority URI; and
- an extension registry's freedom to name nomenclatures of its own.

## 4. Options and tradeoffs

### 4.1 Nomenclatures the spelling rule invokes

**The spelling rule governs an open column** (preferred direction). Part 02 §9.3 would require a
writer to spell a value of an open column as the column's authority does. A closed column's `enum`
already spells every value it admits, and its `authority` records where that spelling came from.
HL7 FHIR then stays on `sex` as provenance, is not directly invoked, and takes no normative entry.
The validator already enforces the `enum`, so behavior and existing packets are unchanged.

Rejected: **an entry for every named nomenclature, HL7 included**, because it would make FHIR the
basis of a requirement `hermaphrodite` cannot satisfy.

Rejected: **bar `authority` from a closed column**, because R101 §3.6 kept it there so that a closed
set's provenance is a declaration rather than prose.

### 4.2 Edition of a living registry

**Part 00 §10 admits a living-registry entry** (preferred direction). The entry would identify the
registry by name and URI, with "living registry" as its candidate edition, and a requirement to
spell a value as the registry does would refer to the registry's entry when the value was written.
A release would identify the registry rather than an edition, and the rest of the release rule would
stand. No verdict depends on the edition, because Part 02 §9.3 already forbids a validator to
dereference an authority or to reject a value it lacks.

Rejected: **pin a dated snapshot**, such as a monthly NCBI archive, because a species or strain
registered after the snapshot would have no conforming spelling and every release would move the pin.

Rejected: **cite the strain guidelines in place of MGI and RGD**, because they fix a symbol's form
and not which symbol a strain was registered under, and NCBI Taxonomy has no counterpart document.

Rejected: **demote the spelling rule to guidance**, because values are compared exactly, and R101
§3.5 made the rule a requirement since `mouse` and `Mus musculus` fail to name one animal.

### 4.3 Placement and form

Part 02 §13 would take entries for NCBI Taxonomy, MGI and RGD, each marked as a living registry and
applied to Part 02 §9.3's spelling rule for the columns that name it, in the three-column table the
other parts use, with UCUM as an exact row. Part 02 §9.3 would cite Part 02 §13 where it states the
spelling rule, as Part 00 §10 requires of invoking prose.

The framework allocation would gain Part 02's rows, so a registry authority dropped from Part 02 §13
or copied into another part is found. A companion check that every authority named on an open core
column has a Part 02 §13 row would catch a registry change that outruns the part; the draft would
place it in `framework.py` or `registry/check.py`.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged: a nomenclature governs how a value is spelled, not what a concept means. |
| logical prose | Affected: Part 02 §9.3 scopes the spelling rule to open columns and cites Part 02 §13; Part 02 §13 gains three entries and the table form. |
| registry meta-schema and declarations | Unchanged: no `authority` entry or vocabulary changes. |
| declarative rules | Unchanged: no rule reads `authority`. |
| framework prose | Affected: Part 00 §10 gains the living-registry entry kind and its release treatment. |
| physical profiles | Unchanged: `authority` has no physical representation. |
| packet manifest and schemas | Unchanged: a manifest binds registries, not their references. |
| validation and import | Unchanged: Part 02 §9.3 already forbids dereferencing an authority. |
| extension registries | Unchanged: none names an authority, and one that does invokes it on its own terms. |
| reader, writer, validator | Unchanged: the writer's `sex` mapping already targets the `enum`. |
| existing packets | Unchanged: no value or binding changes, so each still conforms. |
| conformance fixtures and tests | Affected: a framework probe for a missing or misplaced Part 02 row. |
| revision tooling | Unchanged: the change needs only the ordinary ledger and evidence records. |
| generated publications | Affected: the combined specification picks up Part 00 §10 and Part 02 §§9.3 and 13. |

## 6. Open questions

1. **HL7 FHIR.** Preferred: no normative entry, because the spelling rule governs open columns and
   `sex` is closed (§4.1). An entry for FHIR R5 would require spelling a value its value set lacks.
2. **Living-registry kind.** Preferred: Part 00 §10 names it (§4.2), since that part owns reference
   policy and its edition rule would otherwise pin a living registry to a dated state that excludes
   later registrations.

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
