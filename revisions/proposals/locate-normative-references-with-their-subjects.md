# Locate Normative References with Their Subject Owners

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-21 |
| **Based on** | `eea8883fc55cc173eb4fe9f1f7dac1aeac0a504c` |
| **Decision domain** | specification |
| **Affects** | Part 00 §§2 and 10; Part 03 §1 and a new terminal reference section; Part 04 §1 and a new terminal reference section; specification-framework checks; informational specification and developer documentation; P3 reference placement |

## 1. Problem

Part 00 currently owns both normative-reference policy and the complete normative bibliography.
Part 00 §10 consequently forbids a subject-owning part from maintaining a local normative
bibliography even when no other part uses the external authority. Part 03 identifies all of its
JSON, URI, Parquet, Arrow, Zarr, Zstandard, and SHA-256 dependencies through one link back to that
central table.

That model gives the bibliography one mechanically convenient location, but it separates a
part-specific dependency from the rules whose interpretation depends on it. A reader of the
portable profile must leave Part 03 to discover which Parquet, Arrow, Zarr, and compression
specifications it invokes. It also makes Part 00 grow with details that do not describe the
specification framework or apply across numbered parts.

The open P3 draft makes the cost concrete. Its current crosswalk would add ISO SQL and IEEE 754 to
Part 00 solely because the accepted central-bibliography policy requires that placement, while the
detailed rule-language contract is now intended for a dedicated Part 11. The reference identity,
edition, and scope are part of understanding that language contract, not the architecture in Part
00.

This is not an editorial correction that can bypass the revision lifecycle. R122 §3.9 expressly
assigned the complete bibliography to Part 00, Part 00 §2 repeats that ownership, and the framework
checker enforces it. Changing that rule changes normative ownership even though it need not change
any packet behavior.

## 2. Evidence

### 2.1 Baseline and current rule

The baseline is commit `eea8883fc55cc173eb4fe9f1f7dac1aeac0a504c`. The quick repository
verifier passed all 28 stages there, including the 28-packet conformance corpus. The only other
open lifecycle artifact is the P3 rule-language draft, whose acceptance appraisal is paused on
this precursor and on its agreed move to Part 11. An untracked HTML rendering of that draft is
unrelated working state and was not used as evidence.

Part 00 §2 says that Part 00 owns “the normative-reference policy and bibliography.” Part 00 §10
then says that it carries the complete bibliography, that a subject part cites the corresponding
central entry, and that a subject part does not maintain a second normative bibliography. R122
§§3.4 and 3.9 are the accepted decisions behind those statements. The roadmap recorded a central
bibliography as P1 exit evidence, so a later change must supersede that decision explicitly rather
than reinterpret it.

The current framework checker contains 23 markers and searches for all of them only in Part 00
§10. Its mutation probe treats a missing central entry as a framework defect. The root contribution
guide and the specification README likewise describe Part 00 as the complete or central
bibliography.

### 2.2 Actual dependency distribution

The current bibliography contains four groups with different scopes:

| external authority | normative use in the current candidate | narrowest reference home indicated by that use |
|---|---|---|
| BCP 14 | normative language throughout the numbered parts | Part 00, cross-cutting |
| RFC 8259 | JSON documents and protocols governed through several parts | Part 00, cross-cutting |
| RFC 3986 | logical URI values plus physical and catalog resolution | Part 00, cross-cutting |
| JSON Schema Draft 2020-12 Core and Validation | incorporated schemas governed through Parts 02–04 | Part 00, cross-cutting |
| Apache Parquet format and logical types | table encoding under the portable profile | Part 03 |
| Apache Arrow columnar format, IPC, and Flight | portable adapter-transfer protocols | Part 03 |
| Zarr v3 core, data types, grids, keys, and codecs; Zarr v2 | array encoding under the portable profile | Part 03 |
| RFC 8878 | Zstandard framing used by the portable profile | Part 03 |
| NIST FIPS 180-4 | the SHA-256 digest recorded and defined by the packet catalog | Part 04 |

The table classifies normative reliance, not every informative mention of a technology. Part 10,
for example, may discuss measured Zarr behavior without becoming the owner of the Zarr format
dependency. Part 03 verifies resource checksums but delegates their catalog meaning and prefix
composition to Part 04; that makes Part 04 the narrowest subject owner for FIPS 180-4.

The existing external identities and candidate edition states can move without changing: BCP 14,
RFC 8259, RFC 3986, JSON Schema Draft 2020-12, Zarr v3 core 3.0, Zarr v2 2.0, RFC 8878, and FIPS
180-4 remain pinned as they are now; the currently unversioned Parquet, Arrow, and specified Zarr
components remain visibly unversioned during candidate development. Part 00's existing release
rule still requires exact editions before publication.

### 2.3 Established publication patterns

There is no single external convention that requires either placement. The
[RFC Style Guide](https://www.rfc-editor.org/rfc/rfc7322.html#section-4.8.6) puts normative and
informative reference lists in each RFC. W3C technical reports, such as
[RDF 1.1 N-Triples](https://www.w3.org/TR/n-triples/#references), likewise carry their own
normative-reference sections. Unicode instead maintains
[common references](https://www.unicode.org/reports/tr41/) for its annexes in Unicode Standard
Annex #41. These patterns support a distinction between a reference local to one independently
readable module and a dependency genuinely shared by a document family; none makes a central list
an authority for the subject matter it cites.

Escapewheel's numbered parts are separately readable normative documents, while the combined
specification is a generated convenience rendering. Local placement for single-part dependencies
therefore improves lookup without requiring the same bibliographic entry to be copied into every
part.

### 2.4 Overlap, citations, and anchors

The open P3 draft currently amends Part 00 §10 to add ISO/IEC 9075-1, ISO/IEC 9075-2, their 2026
corrigenda, and IEEE 754-2019. After this precursor, P3 can instead put those entries in the new
Part 11 that invokes them. P3 remains responsible for their exact editions, the scope of
incorporation, and the machine-readable profile's matching basis fields; this proposal does not
define the rule language.

The impact query for Part 00 §§2 and 10, Part 03 §1, and Part 04 §1 reported 16 live citations.
They comprise root and specification orientation, the Part 03 blanket citation, framework and
heading checks, R122 ledger and evidence records, and the open P3 draft. Historical R122 remains
immutable. Its §3.9 ledger disposition can become superseded by the later accepted clause while
the new decision maps to the resulting current owners.

Every affected existing numbered heading already has a canonical anchor:
`ew-specification-authority`, `ew-normative-references`, `ew-portable-profile-scope`, and
`ew-packet-catalog-scope`. The new terminal sections in Parts 03 and 04 would receive anchors when
created. No metadata-only anchor bootstrap is needed.

## 3. Desired outcome and constraints

A successful resolution would establish this ownership model:

- Part 00 owns the policy that determines when and how an external reference becomes normative,
  distinguishes exact from development-time unversioned editions, and requires publication to pin
  every normative dependency.
- A normative bibliographic entry used by exactly one numbered part is carried in that part. Its
  invoking clauses state the extent to which the external authority applies.
- Part 00 carries references used by the framework or by more than one subject-owning part. A
  shared entry stays singular rather than being copied into local lists.
- Bibliographic placement owns the external document's identity and edition, not the Escapewheel
  behavior that invokes it. The subject-owning clause remains the sole owner of that behavior.
- Informative technology mentions do not create a normative dependency, and an implementation or
  library is not promoted into a normative authority when language-neutral behavior remains
  unspecified.
- The current references retain their identities, edition states, and scope. Part 03 receives the
  portable-storage and transport references; Part 04 receives FIPS 180-4; Part 00 retains BCP 14,
  JSON, URI, and JSON Schema references.
- The informational README can navigate to the policy and local reference sections without
  maintaining a normative or independently authoritative aggregate bibliography.
- The framework check verifies the approved owner of every bibliographic entry and rejects a
  missing, misplaced, or duplicate normative entry. Human review remains responsible for deciding
  whether a dependency is truly shared or subject-specific.
- P3 can add the ISO SQL and IEEE 754 references directly to Part 11 without creating an exception
  to the general rule.

The resolution would not introduce a machine-readable reference catalog. At this size, such a
catalog would add another incorporated artifact and authority boundary without removing the need
for local prose to state applicability. P11 may later decide whether a release manifest records
external dependency identities as publication metadata; it need not reopen where the normative
invocation is stated.

## 4. Options and tradeoffs

### 4.1 Retain one complete bibliography in Part 00

This preserves R122 and the smallest implementation diff. It resembles the single reference list
used by an RFC and keeps edition strings in one place. Its cost is that a separately read part does
not contain its own single-part dependencies, Part 00 accumulates lower-level technology details,
and Part 11's language authorities would be remote from the language contract. This option was
considered and rejected for the approved direction.

### 4.2 Give every part a complete local list

This maximizes local readability and resembles independently published W3C modules. Shared JSON,
URI, JSON Schema, and normative-language entries would then be duplicated across parts, making
edition drift possible and violating the project's one-owner rule unless the copies were generated
from another source. A new generated source would be disproportionate for the present inventory.

### 4.3 Selected direction: local single-part references and central shared references

This hybrid keeps each single-part dependency beside its subject while retaining exactly one entry
for genuinely cross-cutting authorities. It changes the policy and checker once, relocates existing
entries without changing their meaning, and gives P3 a stable rule for Part 11.

The tradeoff is that a reader seeking every external dependency follows more than one reference
section. The generated combined specification already includes all numbered parts, and an
informative aggregate index can be derived later if discovery proves difficult. Such an index
would be a projection, not another normative owner.

### 4.4 Add a machine-readable reference catalog now

A JSON catalog could centralize identifiers, editions, links, and part assignments and generate
local sections. It would also require a schema, incorporation semantics, generation and drift
checks, and a decision about whether the JSON or rendered part owns each field. No current
reference is allocated dynamically, and the subject clauses would still need to state what each
external document contributes. This option is deferred unless the inventory or publication model
later demonstrates that the additional artifact pays for itself.

## 5. Impact sketch

- **Semantic prose — unchanged.** No scientific concept or identity changes.
- **Logical prose, registry, and rules — unchanged.** The cross-cutting JSON, URI, and JSON Schema
  entries remain in Part 00; no registry declaration, meta-schema, rule, or version changes.
- **Physical profile — affected structurally.** Part 03 §1 distinguishes its local references from
  cross-cutting ones, and a terminal reference section receives the Parquet, Arrow, Zarr, and
  Zstandard entries without changing their editions or application.
- **Packet catalog — affected structurally.** Part 04 identifies FIPS 180-4 in a terminal reference
  section because it owns the recorded SHA-256 digest and prefix composition. No catalog field or
  schema changes.
- **Validation and import — unchanged behavior.** Validators, writers, and readers apply the same
  current formats and algorithms. Requirement citations need review only where they point at the
  moved bibliography.
- **Extensions — unchanged.** Extension registries and packets inherit the same logical and
  physical contracts; no extension declaration changes.
- **Reader, writer, validator, adapters, and code generation — unchanged behavior.** The
  specification-framework checker and its mutation probe change from a Part-00-only inventory to
  an expected-owner inventory. Other implementation code is unaffected.
- **Existing packets and migration — unchanged.** No packet bytes, interpretation, regeneration,
  or compatibility policy changes.
- **Conformance fixtures and implementation tests — affected only for framework evidence.** Packet
  fixtures remain byte-identical. Framework mutations cover a missing, misplaced, duplicated, or
  implementation-valued reference under the distributed model.
- **Revision lifecycle, ledger, and evidence — affected.** This is a structural
  specification-domain revision. The accepted record would supersede R122 §3.9's central-only
  rule, map its own clauses to Parts 00, 03, and 04, and record the checked structural relocation.
  Existing accepted history remains unchanged.
- **Generated publications and human documentation — affected.** The combined specification is
  regenerated; the specification README, root contribution guide, style guide, roadmap, placement
  inventory, and any other statement claiming a complete central bibliography are updated to
  describe the new model.
- **Open P3 draft — affected after this precursor lands.** Its baseline, crosswalk, Part 00
  amendment, Part 11 outline, descriptor-clause destinations, and evidence plan are revised before
  a new acceptance appraisal. Its already approved rule-language semantics do not change.

### 5.1 Distinguishing evidence

The incorporated change would be demonstrated by:

1. Part 00 retaining the general policy and the four cross-cutting reference groups;
2. Part 03 containing the unchanged Parquet, Arrow, Zarr, and Zstandard entries in its own
   normative-reference section;
3. Part 04 containing the unchanged FIPS 180-4 entry in its own normative-reference section;
4. the framework checker rejecting removal, placement in the wrong part, duplication across
   normative-reference sections, and an implementation substituted for an external authority;
5. the README remaining informational and carrying no normative-reference section;
6. every changed citation resolving to the current policy or the subject-local entry it uses;
7. ledger, evidence, heading, citation, projection, and combined-rendering checks passing; and
8. the complete repository verifier preserving all current packet and corpus outcomes.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [x] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [x] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.
