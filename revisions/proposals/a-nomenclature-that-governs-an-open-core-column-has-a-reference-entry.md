# A nomenclature that governs an open core column has a reference entry

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-24 |
| **Based on** | `f5f33647eb9c3e29ff8c850afa480468fea0c582` |
| **Decision domain** | specification |
| **Affects** | Part 00 §10; Part 02 §9.3 and Part 02 §13; the specification framework check of reference allocation |

## 1. Problem

[Part 02 §9.3](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#93-vocabularies) lets a
string column declare `authority`, an array naming the nomenclatures its values are drawn from, and
requires a writer to spell a value as the named nomenclature does. That requirement makes each
nomenclature the core registry names the basis of a writer obligation, which
[Part 00 §10](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-normative-references) calls a
direct invocation. A directly invoked authority needs one bibliographic entry, and a release needs
its exact edition.

The core registry names five nomenclatures, and
[Part 02 §13](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-logical-schema-normative-references)
has an entry for one of them, UCUM. The other four have none: NCBI Taxonomy, MGI, RGD, and HL7
FHIR administrative gender.

Two further defects surface once entries are written:

- `core.subjects.sex` is closed, and its `enum` includes `hermaphrodite`, which FHIR's value set
  does not define. Read literally, Part 02 §9.3 requires a writer recording a hermaphrodite
  subject to spell the value as FHIR does, which it cannot do.
- NCBI Taxonomy, MGI and RGD are databases whose entries change without editions, so Part 00 §10's
  release rule has no edition to name for them.

## 2. Evidence

### 2.1 Authorities the registries name

A walk of every column's `authority` array in `registry/logical_schemas.json` and the four
extension registries under `registry/extensions/` at the baseline found:

| authority | URI | core columns | vocabulary | Part 02 §13 entry |
|---|---|---:|---|---|
| UCUM | `https://ucum.org/ucum` | 9 | open | version 2.2, revision date 2024-06-17 |
| NCBI Taxonomy | `https://www.ncbi.nlm.nih.gov/taxonomy` | 1 (`species`) | open | none |
| MGI | `https://www.informatics.jax.org/` | 1 (`strain`) | open | none |
| RGD | `https://rgd.mcw.edu/` | 1 (`strain`) | open | none |
| HL7 FHIR administrative gender | `https://hl7.org/fhir/valueset-administrative-gender.html` | 1 (`sex`) | closed | none |

No extension registry declares an authority. No numbered part names NCBI Taxonomy, MGI, RGD or HL7
in its prose. They reach the specification only through Part 02's incorporation of the core
registry, so Part 00 §10 places any entry for them in Part 02.

`core.subjects.genotype` is open, declares no authority, and describes its values as "the genotype
as the source states it, in MGI allele nomenclature where it uses one". That description defers to
the source, and Part 02 §9.3's spelling rule binds a writer only to a nomenclature a column names in
`authority`, so it adds no invocation.

### 2.2 The closed column and its authority

`core.subjects.sex` declares `enum` `male`, `female`, `hermaphrodite`, `other`. The page its
authority names belongs to FHIR R5 (5.0.0), and its value set holds exactly `male`, `female`,
`other` and `unknown`. R101 §3.6 put FHIR on the column as the source of the spelling of three
values, and states that "drawn from is not equal to": the `enum` is the set a validator enforces.
Part 02 §9.3 does not carry that distinction, so its spelling sentence applies to `sex` as it does
to `species`.

### 2.3 The living registries

- **NCBI Taxonomy.** `ftp.ncbi.nlm.nih.gov/pub/taxonomy/` published a new `taxdump` on
  2026-09-24, and no file there carries a version or edition label.
  `pub/taxonomy/taxdump_archive/` holds dated monthly snapshots from `taxdmp_2014-08-01.zip` to
  `new_taxdump_2026-09-01.zip`.
- **MGI and RGD.** Both register strain symbols as they are assigned. The rules for forming a
  symbol are published separately as *Guidelines for Nomenclature of Mouse and Rat Strains*,
  revised September 2024, which the international mouse and rat nomenclature committees review
  annually. The guidelines fix a symbol's form. Which symbol a strain has is recorded in the
  registry.

Part 00 §10 recognizes two entry kinds. An **exact** entry names an edition. An **unversioned**
entry follows the linked specification during candidate development, and a release has to replace
it with an exact edition. A living registry fits neither kind, because it has no edition for a
release to name.

### 2.4 The framework check covers four parts

`escapewheel_poc_docs_v0.2/framework.py` checks the reference rows of Parts 00, 03, 04 and 11
against an approved allocation (`REFERENCE_ANCHORS`, `REFERENCE_ROWS`). Part 02 §13 is a bulleted
list without the `reference | candidate edition | application` table the other parts use, and
neither UCUM nor Part 05's TOML entry is in the allocation.

## 3. Desired outcome and constraints

Each nomenclature that the specification binds a writer to has exactly one bibliographic entry,
whose edition status a release can satisfy. A closed column's `enum` stays the whole of its value
set. The outcome also has to preserve four things:

- every value in every existing packet;
- R101's use of `authority` on a closed column as provenance;
- Part 02 §9.3's prohibition on dereferencing an authority URI;
- an extension registry's freedom to name nomenclatures of its own.

## 4. Options and tradeoffs

### 4.1 Nomenclatures the spelling rule invokes

**The spelling rule governs an open column** (preferred direction). Part 02 §9.3's sentence would
require a writer to spell a value of an **open** column as the column's authority does. A closed column's
`enum` already spells every value it admits, and its `authority` records where that spelling came
from. HL7 FHIR then remains on `sex` as provenance and is not directly invoked, so it takes no
normative entry. Behavior and existing packets are unchanged, since the validator already enforces
the `enum`.

Rejected: **an entry for every named nomenclature, HL7 included.** The entry would make FHIR the
basis of a requirement that `hermaphrodite` cannot satisfy, which is the contradiction in §1.

Rejected: **bar `authority` from a closed column.** R101 §3.6 kept it there on purpose, so that a
closed set's provenance is a declaration and not prose.

### 4.2 Edition of a living registry

**Part 00 §10 admits a living-registry entry** (preferred direction). The entry would identify the
registry by name and URI, and its candidate edition would read "living registry". A requirement to
spell a value as a living registry does would refer to the registry's entry when the value was
written. A release would identify the registry and not an edition, and nothing else in the
release rule would change. No verdict depends on the edition, because Part 02 §9.3 already forbids a
validator to dereference an authority or to reject a value it lacks.

Rejected: **pin a dated snapshot**, such as a monthly NCBI archive. A species or strain registered
after the snapshot would have no conforming spelling, and every release would have to move the pin.

Rejected: **cite the strain guidelines in place of MGI and RGD.** They fix a symbol's form but not
which symbol a strain was registered under, so the spelling requirement would still read the
registries. NCBI Taxonomy has no counterpart document. Under Part 00 §10 the guidelines already
apply through the registries that follow them.

Rejected: **demote the spelling rule to guidance.** Values are compared exactly, and R101 §3.5 made
the rule a requirement because `mouse` and `Mus musculus` fail to name one animal.

### 4.3 Placement and form

Part 02 §13 would take entries for NCBI Taxonomy, MGI and RGD, each marked as a living registry
and applied to Part 02 §9.3's spelling rule for the columns that name it. It would also take the
same three-column table the other parts use, with UCUM as an exact row. Part 02 §9.3 would cite
Part 02 §13 where it establishes the spelling rule, as Part 00 §10 requires of the invoking prose.

The framework allocation would gain Part 02's rows, so a registry authority dropped from
Part 02 §13 or copied into another part is found. A companion check that every authority named on an open core
column has a row in Part 02 §13 would catch a registry change that outruns the part. Whether that
check belongs in `framework.py` or `registry/check.py` is left to the draft.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. |
| logical prose | Affected: Part 02 §9.3 scopes the spelling rule to open columns and cites Part 02 §13; Part 02 §13 gains three entries and the table form. |
| registry meta-schema and declarations | Unchanged; no `authority` entry or vocabulary changes. |
| declarative rules | Unchanged. |
| framework prose | Affected: Part 00 §10 gains the living-registry entry kind and its release treatment. |
| physical profiles | Unchanged. |
| packet manifest and schemas | Unchanged. |
| validation and import | Unchanged; Part 02 §9.3 already forbids dereferencing an authority. |
| extension registries | Unchanged; none names an authority, and one that does invokes it on its own terms. |
| reader, writer, validator | Unchanged; the writer's `sex` mapping already targets the `enum`. |
| existing packets | Unchanged and still conforming. |
| conformance fixtures and tests | Affected: a framework probe for a missing or misplaced Part 02 row. |
| revision tooling | Unchanged. |
| generated publications | Affected: the rendered specification picks up Part 02 §9.3 and Part 02 §13 and Part 00 §10. |

## 6. Open questions

1. **HL7 FHIR.** Preferred: no normative entry, because the spelling rule governs open columns
   and `sex` is closed (§4.1). An entry for FHIR R5 would instead require spelling a value that the
   value set lacks.
2. **Living-registry kind.** Preferred: Part 00 §10 names it (§4.2), since that part owns
   reference policy and a living registry otherwise blocks release under its edition rule.

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
