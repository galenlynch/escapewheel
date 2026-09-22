# Normative References Reside with Their Subject Owners

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `3769082d29514ea9eeabe81c0931f98171faf8ea` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 00 §§2 and 10; Part 03 §1 and a new §12; Part 04 §1 and a new §10; the specification README's reference navigation |
| **Depends on** | R120 §§3.1 and 3.3–3.7; R122 §§3.4 and 3.9 |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3 |

Section 3 is normative. Sections 1–2 and 4–7 are informative.

Normative keywords follow BCP 14.

## 1. Scope

This revision locates each external normative reference at the narrowest numbered-part boundary
that invokes it. It replaces Part 00's complete-central-bibliography rule with a hybrid rule: Part
00 owns reference policy and references used across numbered parts, while a reference used by one
part resides with that part's subject.

The revision relocates existing bibliography entries without changing their external identity,
candidate edition state, invocation scope, or the Escapewheel behavior that relies on them. It
does not add the SQL and IEEE references needed by the Tier 2 rule language; it establishes the
general placement rule under which the later P3 revision will add them to Part 11.

This is a structural revision. Append-only text would leave Part 00 §§2 and 10 requiring a
complete central bibliography while later text required subject-local entries, creating two
incompatible ownership rules. The existing policy must be replaced in place and the current
single-part entries moved to new terminal sections in Parts 03 and 04.

### 1.1 Structural crosswalk

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 00 §2 `ew-specification-authority` — Part 00 owns normative-reference policy and bibliography | replace the complete-bibliography assignment with policy and shared-reference ownership | Part 00 §2, same anchor | permits subject-local reference sections without moving general policy | §3.1 |
| Part 00 §10 `ew-normative-references` — complete central bibliography, applicability rule, edition policy, and release-blocking omissions | retain the anchor; replace the placement rule and retitle the section for policy and shared references; preserve edition, application, dependency, and implementation-authority rules | Part 00 §10 | changes bibliographic placement but no referenced behavior | §§3.1–3.3 |
| Part 00 §10 entries for BCP 14, RFC 8259, RFC 3986, and JSON Schema Draft 2020-12 | retain | Part 00 §10 | classifies references invoked across numbered parts as shared | §3.3 |
| Part 00 §10 entries for Parquet, Arrow, Zarr, and RFC 8878 | move without changing text or edition state | planned Part 03 section 12, `ew-portable-profile-normative-references` | places portable-format and transport references with the physical profile | §3.3 |
| Part 00 §10 entry for NIST FIPS 180-4 | move without changing text or edition state | planned Part 04 section 10, `ew-packet-catalog-normative-references` | places SHA-256 identity with the catalog digest definition | §3.3 |
| Part 00 §10 statement that the missing Tier 2 language prevents release | retain the general missing-authority rule but remove the issue-specific initial list after P3 supplies that authority | Part 00 §10 policy; P3 later owns the concrete resolution | avoids preserving a resolved issue as permanent architecture | §3.2 |
| Part 03 §1 `ew-portable-profile-scope` — one blanket link to the central JSON, URI, Parquet, Arrow, Zarr, Zstandard, and SHA-256 bibliography | replace with links to Part 00 for shared JSON and URI references, the planned Part 03 reference section for profile-local references, and the planned Part 04 reference section for catalog digest identity | Part 03 §1, same anchor | changes lookup location only | §§3.1, 3.3 |
| Part 03, no current terminal reference section | add | planned Part 03 section 12, `ew-portable-profile-normative-references` | creates the local bibliography for one-part profile dependencies | §§3.1, 3.3 |
| Part 04 §1 `ew-packet-catalog-scope` — catalog scope without local reference navigation | retain and extend with reference navigation | Part 04 §1, same anchor | makes the catalog's external dependency locally discoverable | §§3.1, 3.3 |
| Part 04, no current terminal reference section | add | planned Part 04 section 10, `ew-packet-catalog-normative-references` | creates the local bibliography for SHA-256 | §§3.1, 3.3 |
| specification README §5 — says every normative external authority is listed centrally in Part 00 | replace with informative links to Part 00 policy and the local reference sections | informational README | removes a stale projection without creating authority | §§3.1, 3.3 |

Part 00 §§2 and 10, Part 03 §1, and Part 04 §1 already have canonical anchors. The two new
terminal sections receive their anchors when created. No affected existing source or destination
lacks an anchor, so the structural procedure requires no metadata-only bootstrap.

## 2. Background

### 2.1 Current authority and observed distribution

At the baseline, Part 00 §10 contains 23 mechanically checked markers representing eleven
bibliographic rows. Part 03 §1 links to the entire table for JSON, URI, Parquet, Arrow, Zarr,
Zstandard, and SHA-256. No other numbered part has a normative-reference section.

The actual normative uses are not all cross-cutting. BCP 14 governs normative language throughout
the specification. JSON, URI, and JSON Schema govern documents or values across Parts 02–04 and
their incorporated schemas. Parquet, Arrow, Zarr, and Zstandard govern storage and transfer under
the portable physical profile in Part 03. Part 04 defines the recorded SHA-256 digest, including
the deterministic prefix-resource composition, while Part 03 delegates digest meaning to that
catalog contract.

The current central placement is deliberate rather than accidental. R122 §3.4 assigns Part 00 the
complete normative bibliography, and R122 §3.9 prohibits a second bibliography in a subject part.
The current framework checker searches for every marker only after Part 00's
`ew-normative-references` anchor. This revision therefore supersedes R122 §3.9 as a whole and
narrows only the bibliography bullet of R122 §3.4; the rest of R122's framework allocation remains
in force.

### 2.2 Modular specification practice

The [RFC Style Guide](https://www.rfc-editor.org/rfc/rfc7322.html#section-4.8.6) places normative
and informative references in each RFC. W3C technical reports, such as
[RDF 1.1 N-Triples](https://www.w3.org/TR/n-triples/#references), likewise carry their own
reference sections. Unicode instead publishes
[common references](https://www.unicode.org/reports/tr41/) for its annex family. These are
compatible patterns at different publication boundaries: local references support independently
readable modules, while one common entry avoids duplicating a dependency shared by modules.

Escapewheel's numbered parts are the normative documents and the combined specification is a
generated convenience rendering. A hybrid allocation therefore preserves one entry for each
external authority while keeping a single-part dependency in the part a reader is implementing.

### 2.3 Alternatives and compatibility

Retaining a complete bibliography in Part 00 would minimize the edit and resemble a single RFC,
but would keep physical-profile and future rule-language details remote from their subjects.
Giving every part a complete local list would maximize local lookup but duplicate BCP 14, JSON,
URI, and JSON Schema identities across parts. Generating local lists from a new machine-readable
reference catalog would avoid textual duplication but introduce another schema, incorporated
artifact, generation path, and authority boundary for an eleven-row inventory.

The selected hybrid requires no packet migration or regeneration. The reference strings, links,
editions, unversioned candidate states, and invoking requirements remain unchanged. There are no
released packets or external compatibility commitments, but the absence of compatibility cost is
not used to change any external dependency in this revision.

### 2.4 Overlap and citation inventory

The only overlapping open artifact is the P3 Tier 2 rule-language draft. Its current text assumes
the central-only rule and assigns the future ISO/IEC 9075 and IEEE 754 entries to Part 00. P3 is
ordered after this revision, will move the detailed language contract to Part 11, and will place
those entries there under §3.1. Its approved query, type, numeric, outcome, and machine-descriptor
decisions are unaffected.

The baseline impact query for Part 00 §§2 and 10, Part 03 §1, and Part 04 §1 reported 16 live
citations. They cover repository orientation, the specification README, the Part 03 blanket link,
the framework and heading checks, R122 ledger and evidence records, and the open P3 draft. Accepted
R122 remains immutable; the ledger records its changed current disposition instead of editing its
historical text.

## 3. Decision

### 3.1 Reference ownership and invocation

Part 00 **MUST** own the specification-wide policy for external normative references. An external
authority on which normative requirements in exactly one numbered part depend **MUST** have its
bibliographic entry in a normative-reference section of that part. An external authority on which
normative requirements in more than one numbered part depend, or on which the Part 00 framework
itself depends, **MUST** have one shared bibliographic entry in Part 00.

Each direct external normative authority **MUST** have exactly one bibliographic entry in the
numbered parts. A subject-owning part **MUST** cite that entry from the requirement that invokes
the authority and **MUST** state the extent to which it applies. The entry identifies the external
document and edition; it **MUST NOT** become the owner of the Escapewheel meaning, processing
rule, actor obligation, or conformance behavior that invokes it.

An informative mention of a technology **MUST NOT** make its specification normative. Moving a
bibliographic entry **MUST NOT** change the referenced behavior, and a reference used by several
parts **MUST NOT** be copied into several normative-reference sections. The informational
specification README **MUST NOT** contain a normative-reference section or become an independent
bibliographic owner.

### 3.2 Edition and authority discipline

An **exact** bibliographic entry **MUST** identify the edition used by the candidate. An
**unversioned** entry **MUST** be identified as such and follows the linked external specification
during candidate development. A specification release **MUST** identify the exact external
edition on which every conformance requirement depends.

A normative reference's own dependencies **MUST** apply through that reference and need not be
copied into an Escapewheel reference section unless this specification relies on them directly.
Where required behavior has no sufficient language-neutral authority, a numbered part **MUST NOT**
promote an implementation or library's observed behavior into a normative reference. The missing
authority **MUST** remain a candidate defect and **MUST** prevent release until the subject-owning
part defines the behavior or cites an adequate specification.

### 3.3 Current reference allocation

Part 00 **MUST** retain these shared entries:

| reference | candidate edition | application |
|---|---|---|
| [BCP 14](https://www.rfc-editor.org/info/bcp14), comprising RFC 2119 and RFC 8174 | exact RFC editions | normative keywords |
| [RFC 8259](https://www.rfc-editor.org/info/rfc8259) | exact | JSON |
| [RFC 3986](https://www.rfc-editor.org/info/rfc3986) | exact | URI syntax |
| [JSON Schema Core](https://json-schema.org/draft/2020-12/json-schema-core) and [Validation](https://json-schema.org/draft/2020-12/json-schema-validation) | Draft 2020-12 | incorporated JSON Schemas |

Part 03 **MUST** carry these portable-profile entries in its normative-reference section:

| reference | candidate edition | application |
|---|---|---|
| [Apache Parquet format](https://github.com/apache/parquet-format), including [logical types](https://github.com/apache/parquet-format/blob/master/LogicalTypes.md) | unversioned | Parquet files and logical types |
| [Apache Arrow columnar format](https://arrow.apache.org/docs/format/Columnar.html), [IPC](https://arrow.apache.org/docs/format/Columnar.html#serialization-and-interprocess-communication-ipc), and [Flight](https://arrow.apache.org/docs/format/Flight.html) | unversioned | Arrow data, IPC, and Flight |
| [Zarr v3 core](https://zarr-specs.readthedocs.io/en/latest/v3/core/v3.0.html), [data types](https://zarr-specs.readthedocs.io/en/latest/v3/data-types/index.html), [regular chunk grid](https://zarr-specs.readthedocs.io/en/latest/v3/chunk-grids/regular-grid/index.html), and [default chunk-key encoding](https://zarr-specs.readthedocs.io/en/latest/v3/chunk-key-encodings/default/index.html) | core v3.0; other entries unversioned | Zarr v3 arrays |
| Zarr v3 [Bytes](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/bytes/), [Gzip](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/gzip/), [Blosc](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/blosc/), [CRC32C](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/crc32c/), [transpose](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/transpose/), and [sharding-indexed](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/sharding-indexed/) codec specifications | unversioned | permitted Zarr v3 codec pipeline components |
| [Zarr v2 storage specification](https://zarr-specs.readthedocs.io/en/latest/v2/v2.0.html) | 2.0 | permitted external Zarr v2 arrays |
| [RFC 8878](https://www.rfc-editor.org/info/rfc8878) | exact | Zstandard framing |

Part 04 **MUST** carry this packet-catalog entry in its normative-reference section:

| reference | candidate edition | application |
|---|---|---|
| [NIST FIPS 180-4](https://csrc.nist.gov/pubs/fips/180-4/upd1/final) | exact | SHA-256 |

Within Part 03, the new heading **MUST** use section number 12, title “Normative references,” and
canonical anchor `ew-portable-profile-normative-references`. Within Part 04, the new heading
**MUST** use section number 10, title “Normative references,” and canonical anchor
`ew-packet-catalog-normative-references`. Part 00 §10 **MUST** retain canonical anchor
`ew-normative-references` and **MUST** be titled “Normative-reference policy and shared
references.”

## 4. What this does not change

- No external standard, edition, link, candidate pinning state, or normative scope changes.
- No packet field, registry declaration, JSON Schema, stored resource, digest algorithm, physical
  encoding, validator verdict, reader behavior, writer behavior, or adapter contract changes.
- The numbered prose invoking an external authority remains the owner of the corresponding
  Escapewheel behavior.
- The combined specification remains a generated convenience rendering, not a separate owner.
- This revision neither defines the Tier 2 rule language nor adds ISO SQL or IEEE 754 references.
- It does not create a machine-readable reference catalog or decide whether the future release
  manifest records external dependencies.

## 5. Consequence

This is a meaning-preserving but normative ownership change. Part 00 ceases to be the complete
bibliography, Parts 03 and 04 become bibliographic owners for their subject-local dependencies,
and framework checks enforce the distributed allocation. No existing packet requires migration,
regeneration, or reinterpretation.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged because no scientific concept or identity changes. | Part 01 remains byte-identical. |
| logical prose and registry | Unchanged because the JSON, URI, and JSON Schema entries remain shared in Part 00 and no logical declaration changes. | Parts 02 and the registry artifacts remain byte-identical. |
| physical profiles | Part 03 §1 points to shared and local owners; the new terminal reference section receives the six existing profile-reference rows. | Exact row comparison against baseline Part 00 §10; framework owner check. |
| packet catalog and JSON Schemas | Part 04 §1 gains reference navigation and its new terminal reference section receives FIPS 180-4; all JSON Schemas remain unchanged. | Exact FIPS row comparison; schema byte comparison; framework owner check. |
| validation and import | Runtime behavior is unchanged; only bibliography lookup moves. | Existing validator, writer, reader, and corpus results remain unchanged. |
| extensions | Unchanged because extension declarations inherit the same logical and physical contracts. | All extension registries remain byte-identical and pass existing checks. |
| reader, writer, validator, adapters | Runtime code is unchanged. The specification-framework checker changes from a Part-00-only marker set to exact per-part owners. | Positive framework check plus focused mutation probe. |
| conformance fixtures and tests | Packet fixtures are unchanged. Framework mutations cover missing, misplaced, duplicate, and implementation-valued references. | Framework probe and complete corpus pass. |
| revision process and tooling | No lifecycle rule changes. Ledger, evidence, headings, impact, citation, and stage records incorporate the structural move. | Lifecycle and traceability checks pass; R122 §3.9 is superseded. |
| generated publications and developer documentation | Regenerate the combined specification and counts; update README navigation, the contribution and style guides, roadmap, and placement inventory. | Generation preserves the candidate; documentation search finds no current complete-central-bibliography claim. |

P3 becomes dependent on the accepted result. Its draft then rebases, adds Part 11 to the numbered
part model, locates ISO SQL and IEEE 754 there, and updates its machine descriptor's clause anchors
without reopening its approved language semantics.

## 6. Conformance and implementation evidence

The framework checker must represent each current marker together with its approved numbered part
and inspect only normative-reference sections. Its positive case must establish that:

1. every required marker appears in the approved reference section;
2. no marker appears in another numbered part's normative-reference section;
3. each direct external authority has one normative bibliographic entry;
4. Part 00 retains the shared entries and policy;
5. Parts 03 and 04 contain the exact relocated entries and canonical anchors;
6. no implementation or library is substituted for a missing language-neutral authority;
7. the informational README contains no normative-reference section; and
8. the combined specification exactly reproduces the changed parts.

The mutation probe must independently reject:

- removal of a shared Part 00 entry;
- removal of a Part 03 or Part 04 local entry;
- moving an entry to a different part's reference section;
- duplicating an entry across normative-reference sections;
- inserting DuckDB, zarr-python, or Numcodecs as normative authority; and
- a stale combined rendering.

The incorporation must also run the structural lifecycle checks, citation and impact checks,
ledger and evidence checks, heading check, generated-document checks, all package-independent
framework probes, the complete packet corpus, and the full repository verifier. Since this
decision changes no runtime contract, existing package suites are regression evidence rather than
new behavioral evidence; no new packet fixture is warranted.

## 7. Open

P3 will identify and scope the ISO SQL and IEEE 754 references in Part 11. P11 may later decide
whether the immutable release manifest records external dependency identities or whether an
informative aggregate reference index is useful. Neither decision can change the placement and
invocation rules in §3 without a later revision.
