# Declare portable-profile encodings and capabilities

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-23 |
| **Based on** | `6fc02db5628440cc632f7608b2164985d4ec0f92` |
| **Decision domain** | specification |
| **Affects** | portable physical-profile authority and identity; resource encoding selection and capability requirements; Parts 02, 03, 04, 05, and 06; a new physical-profile descriptor and schema |

## 1. Problem

Part 03 owns the portable physical profile, but its exact encoding and capability assignments exist
only as prose and duplicated implementation constants. The logical registry now declares every
resource as `table`, `dense_array`, or `opaque`, and every packet resource binds one declaration.
There is no equivalent machine-readable physical authority that answers which encoding may realize
each kind, which ownership states an encoding admits, or which features every conforming reader
supports.

The packet catalog compounds the omission. Its top-level `profile_id` identifies the whole physical
profile, while each generically readable resource's `physical_profile` field actually names an
encoding such as `parquet` or `zarr_v3`. The same field is also used to enumerate formats such as
`mp4` for opaque resources even though Escapewheel defines no generic access contract for those
formats. Its `codecs` and `required_codecs` fields contain unqualified names,
although Part 03 says readability depends on the pair of Zarr version and codec and, for Blosc, on
configuration. The fields therefore cannot represent the contract precisely enough for a reader or
validator to distinguish the portable floor, recognized optional support, and an unsupported
requirement.

The result is a data-driven logical layer followed by a hand-coded physical layer. A new reader,
writer, validator, extension, or adapter must reconstruct the physical policy from prose and can
silently choose a different set. The current reference implementations already do.

This proposal concerns the physical model and the selectors a packet will use. Complete manifest
shape, registry identity and digest binding, packet verdict composition, exact codec-floor choices,
and portability-report wording remain separate decisions.

## 2. Evidence

All observations below were reproduced at the recorded baseline. The quick repository verifier
passed all 31 stages before the proposal was opened.

### 2.1 The current selector conflates a profile with an encoding

Part 03 identifies the whole profile as `escapewheel-portable-v0.1`. Part 04 records that identifier
once as top-level `profile_id`, but calls the per-resource selector `physical_profile`. The manifest
schema permits nine values in that latter field: `parquet`, `parquet_dataset`, `zarr_v2`, `zarr_v3`,
`markdown`, `json`, `text`, `pdf`, and `mp4`. The table and dense-array values select physical
interfaces, while the remaining values merely label representations that the generic reader does
not interpret. None is the packet's physical profile.

The distinction affects behavior. The reader treats `parquet_dataset` as a table layout, maps
`zarr_v2` and `zarr_v3` to metadata formats, and does not consult one shared profile declaration.
The writer emits the strings directly. The validator compares strings against local sets. A field
named for the enclosing profile is therefore serving as an unversioned encoding vocabulary.

### 2.2 Kind-to-encoding compatibility has no machine owner

Part 03 §2 maps tables to Parquet and dense arrays to Zarr, then lists ordinary media and document
formats. Part 02 now has only the logical kinds `table`, `dense_array`, and `opaque`; the specific
declaration `core.media_asset_instances` is an opaque catalog family associated with
`core.media_assets`, not a fourth generic kind.

No incorporated artifact expresses these consequences:

- `parquet` and `parquet_dataset` realize `table`;
- `zarr_v2` and `zarr_v3` realize `dense_array`;
- `zarr_v2` is allowed only for an external resource;
- a table or dense array must select a profile-defined encoding that provides its generic access
  contract; and
- an opaque resource does not select an encoding because Escapewheel does not define a generic
  interface to its internal representation.

The manifest JSON Schema enumerates encoding strings but cannot compare one with the logical kind
resolved from a separate checked registry. The validator performs dense-array checks after logical
declaration resolution, but has no general descriptor-driven compatibility phase. An extension
resource consequently depends on the reference implementation having anticipated its physical
case even though its logical declaration is code-free.

### 2.3 Capability sets disagree and lose necessary context

Part 03 §6.4 says that a conforming Zarr v3 reader supports `none`, `gzip`, and `zstd`, while
`blosc` with selected parameters and `sharding_indexed` are optional. It gives a different row for
Zarr v2. The validator constant named `FLOOR` includes Blosc and sharding in the v3 floor, so its
`codec.outside_the_floor` finding cannot distinguish the normative floor from implementations it
happens to recognize. The reader's `DECODABLE` set includes a different combination, and the writer
maintains another `FLOOR` set that it documents as a reader obligation.

The catalog stores bare codec names. `required_codecs: ["gzip"]` does not say whether the resource
is Zarr v2 or v3 even though the current profile deliberately classifies that pair differently.
`codecs: ["blosc"]` omits `cname` and `shuffle`, although Part 03 restricts the recognized optional
form using those values and the upstream Zarr codec metadata records them. Nested
`sharding_indexed` pipelines are flattened to names, losing where a codec acts.

The upstream formats support a descriptor rather than a copied metadata schema. Zarr gives codecs
stable registered names and carries each codec's complete configuration in array metadata; for
example, its Blosc specification makes `cname`, `shuffle`, `typesize`, and related parameters part
of that metadata. Parquet likewise records compression and value encodings in its own footer. A
packet need not duplicate either format's complete metadata to name the additional reader
capability it requires.

### 2.4 The manifest projection is incomplete even on its own terms

Part 04 §4.1 requires every resource to carry a physical selector and requires codecs for arrays.
The manifest schema requires only `resource_id`, `declaration_id`, and `uri`; `physical_profile` is
optional in its generic resource branch. It has no semantic check connecting encoding, logical
kind, ownership, partitioning, or capability requirements. Complete repair belongs with the packet
manifest reconciliation, but that repair cannot be designed until the physical profile provides
one exact vocabulary and lookup model.

### 2.5 Stored resources and views are not separated cleanly

Parts 00, 02, and 06 correctly say that a materialization or a view is a realization rather
than a logical kind. Every current packet resource nevertheless names bytes through `uri`; the
portable profile defines no view language, view definition, or view resource entry. Reader-created
SQL views are operations over packet resources rather than independently declared packet
resources.

A physical model should be able to identify the realization selected by an encoding without
inventing `view` as a logical kind. It should not claim that the current profile supports a
serialized view until the profile defines how such a view is represented and evaluated.

### 2.6 Baseline, overlap, and feasibility

There were no other open proposals or drafts. R122 assigns physical encodings to Part 03 and exact
incorporated assignments to machine-readable artifacts. R128 establishes the logical declaration
and packet-binding inputs this change consumes and explicitly leaves formats and capabilities to a
later physical descriptor.

The section-impact scan found 135 current citations to the affected Part 02, Part 03, and Part 04
sections. Live implementation consumers include the reader resource models and Zarr dispatcher,
writer array and manifest construction, validator physical shims and codec reporting, adapter
resource delivery, fixtures, and conformance probes. Historical accepted revisions remain
historical and are not rewritten.

A standalone JSON descriptor is feasible with the same source-and-vendoring pattern already used
for the registry contract and Tier 2 rule-language profile. The descriptor can enumerate encoding
and capability IDs, their classification, their applicable modeled kinds, and their owning prose
anchors. Format metadata remains in Parquet or Zarr rather than being copied wholesale into the
descriptor or packet. Opaque representations remain outside the descriptor's closed encoding
vocabulary.

## 3. Desired outcome and constraints

A successful resolution should establish one physical-profile authority while preserving these
constraints:

- Part 03 owns the meaning of physical encodings and portability. It expressly incorporates a
  closed descriptor schema and one descriptor for the current portable profile.
- The physical descriptor is separate from the logical registry. It consumes the logical kind and
  resource ownership state without adding formats, codecs, or implementation capabilities to Part
  02 declarations.
- The packet's `profile_id` selects the whole profile; a differently named per-resource field on
  each table or dense array selects one encoding declared by that profile. An opaque resource has
  no such selector.
- Every declared encoding states its applicable modeled kinds, materialized realization, and
  permitted packet-owned or external states. Logical declaration ID and namespace do not become
  encoding selectors.
- The same descriptor distinguishes capabilities guaranteed by a conforming profile reader from
  recognized optional capabilities. An implementation's larger support set does not enlarge the
  normative portable floor.
- Capability identity preserves encoding/version context and can distinguish configurations where
  configuration affects interoperability.
- Format-owned metadata remains the source for shape, dtype, compression configuration, and other
  payload facts. The packet records only the profile selection and any additional capability
  requirements needed before access.
- A reader checks capabilities only when asked to use the affected resource. It does not reject a
  whole packet because another resource requires unsupported optional functionality.
- Ordinary catalog access to an `opaque` resource does not require a known representation or
  generic payload decoding. A format-aware implementation may offer additional operations without
  changing the logical kind or packet validity.
- Extension declarations use the same kind-to-encoding mapping without modifying the core logical
  registry or requiring extension code.
- The model separates materialized and view realizations, but does not enable a serialized view
  before a view-definition contract exists.
- Existing development packets and APIs may be regenerated or changed incompatibly; the migration
  still needs to be explicit and verified.

## 4. Options and tradeoffs

### 4.1 Keep Part 03 prose and implementation constants

The project could retain the current fields and add tests comparing the reader, writer, and
validator sets. This is a small change, but it leaves prose as an unstructured capability registry,
keeps extension physical handling hand-coded, and cannot generate schema branches or conformance
vectors. It does not complete the data-driven architecture.

### 4.2 Add physical fields to the logical registry

Each logical declaration could list its allowed encodings and capabilities. This makes exact
declaration-specific restrictions easy, but it violates the storage-agnostic logical boundary and
duplicates the same table and array mappings across core and extension declarations. Supporting a
second physical profile would require changing logical registries whose meanings did not change.

### 4.3 Incorporate a standalone physical-profile descriptor

This proposal prefers a hand-authored descriptor and a closed JSON Schema under `registry/`, with
Part 03 expressly incorporating both. The descriptor identifies the profile, the logical standard
it consumes, its generic encodings, and their capabilities. Reader, writer, and validator
distributions vendor the exact artifact through the existing generator rather than maintain local
policy sets.

This follows the established local pattern: prose defines the semantics and actor obligations;
the incorporated descriptor owns exact identifiers, assignments, and classification; external
format specifications continue to own their metadata. A disagreement is an inconsistent candidate,
not an invitation to choose prose or JSON silently.

### 4.4 Name the resource selector for what it selects

One option retains `physical_profile` and documents that it means an encoding within the top-level
profile. Another renames it to `encoding_id`. This proposal prefers `encoding_id`: it prevents two
different scopes from sharing the word “profile,” makes descriptor lookup literal, and avoids
carrying the confusion into the final release. No released packet requires compatibility.

An `encoding_id` is a profile-local stable token that selects an Escapewheel-defined physical
interface for generic logical access. Current examples are `parquet`, `parquet-dataset`, `zarr-v2`,
and `zarr-v3`. It is required for `table` and `dense_array` resources and absent for `opaque`
resources. Consequently, an unknown encoding ID on a table or dense array cannot satisfy the
selected profile, while an opaque resource remains valid regardless of whether Escapewheel
recognizes its representation.

An optional media type or format hint could help specialized consumers discover opaque resources,
but it would be an open, informative catalog value rather than an encoding selector. Its exact
field belongs to the complete packet-catalog decision. Absence or an unrecognized value must not
invalidate an opaque resource or create a generic reader obligation.

### 4.5 Describe capability requirements without copying format metadata

Three representations were considered:

1. keep bare codec names;
2. copy complete Zarr codec objects and Parquet footer features into the manifest; or
3. use stable capability IDs whose exact applicability is defined by the descriptor and its Part
   03 anchor, while the payload remains the complete source for format metadata.

This proposal prefers the third, hybrid representation. A capability ID includes its encoding
context and, where necessary, the configuration distinction that changes support. Illustrative
tokens are `zarr-v3.codec.gzip`, `zarr-v3.codec.sharding-indexed`, and a distinct token for the
recognized Blosc configuration. They are not proposed final spellings.

The descriptor entry states whether the capability is part of the mandatory portable floor or is
recognized optional, which encodings it applies to, and which normative anchor defines the mapping
from format metadata to the token. It does not introduce a general JSON-path or predicate language.
A validator reads the format's own metadata and applies those small, specified mappings. This is
less mechanically ambitious than serializing arbitrary selectors, but keeps the normative
vocabulary and classification data-driven without creating another executable language.

### 4.6 Record only requirements beyond the portable floor

One design lists every codec or feature a resource uses, including features every conforming
reader already supports. Another records only capabilities beyond the mandatory floor. This
proposal prefers the latter.

A materialized table or dense array selects `encoding_id`. If its metadata uses only the encoding's
mandatory portable features, it needs no additional capability declaration. If it uses a
recognized optional or otherwise unsupported feature, the resource declares a version-qualified
capability requirement. A packet-level union can then answer whether one implementation can read
every generically readable resource without confusing mandatory features with optional
dependencies. The exact manifest field and union invariant are incorporated by the later complete
packet-catalog change. Opaque resources declare neither an encoding ID nor generic decoding
capabilities.

For packet-owned bytes, a validator derives the requirement from the payload and checks the
declaration. For an unreachable external resource, the declaration is an adapter-supplied claim,
as its current codec and size fields are. A reader still checks only the resource it opens.

### 4.7 Classify unknown features without enlarging the floor

A fully closed feature vocabulary would reject every newly registered upstream codec until this
profile changed. A fully open vocabulary would make a typo indistinguishable from an intentional
extension and could not provide a stable portability answer.

For a recognized table or dense-array encoding, this proposal prefers a closed set of mandatory
and recognized-optional entries plus an explicit unsupported fallback for well-formed upstream
feature identifiers. Unsupported does not mean that the bytes violate their upstream format; it
means this profile promises no portable reader support. The resource remains independently
addressable, and an implementation may advertise support, but a validator reports that the
resource is outside the profile's recognized portability set. Exact codec-floor membership and
report severity remain for the dedicated codec-portability decision. Opaque representations do not
enter this classification: being unknown is expected and has no validity or portability effect.

### 4.8 Bind capabilities to generic logical access

“Support” needs an operation and an actor. This proposal prefers to define a portable read
capability as the ability of a conforming reader to expose a `table` or `dense_array` resource's
logical values through the applicable generic access model. A profile reader also resolves,
locates, and integrity-checks an `opaque` resource, but need not decode or render its payload.

The descriptor contains only encodings that provide this generic logical access. Validator support
is a separate implementation capability: a validator may inspect metadata and establish physical
conformance without offering an application-level decoder. Opaque resources remain resolvable,
listable, integrity-checkable, and byte-accessible without an encoding entry. This prevents an
installed video player, PDF renderer, or domain library from silently becoming part of baseline
Escapewheel reader conformance. A specialized consumer may advertise such support independently.

### 4.9 Represent realization without inventing a current view format

The descriptor schema can make realization an encoding property rather than a logical kind. Every
current encoding is `materialized`; packet ownership and external reference are a separate
dimension. A packet-owned Parquet file and an externally referenced Zarr store are both
materialized resources. The current descriptor should not include a view encoding because Part 03
defines no query or view serialization. Reader-created views therefore remain operations, not
packet resources.

A later profile can add a view realization only together with an encoding or definition contract
that makes its inputs, language, and evaluation behavior decidable. That addition would not change
the logical declaration's kind.

### 4.10 Illustrative descriptor shape

This is a feasibility sketch rather than proposed normative JSON:

```json
{
  "$schema": "https://escapewheel.org/schemas/physical-profile/0.1.0",
  "id": "escapewheel-portable-v0.1",
  "logical_standard": "escapewheel-logical-v0.1",
  "encodings": {
    "parquet": {
      "kinds": ["table"],
      "realization": "materialized",
      "access": "logical_values",
      "ownership": ["packet", "external"]
    },
    "zarr-v3": {
      "kinds": ["dense_array"],
      "realization": "materialized",
      "access": "logical_values",
      "ownership": ["packet", "external"]
    },
    "zarr-v2": {
      "kinds": ["dense_array"],
      "realization": "materialized",
      "access": "logical_values",
      "ownership": ["external"]
    }
  },
  "capabilities": {
    "zarr-v3.codec.gzip": {
      "class": "mandatory_portable",
      "encodings": ["zarr-v3"],
      "anchors": ["ew-array-codecs"]
    },
    "zarr-v3.codec.sharding-indexed": {
      "class": "recognized_optional",
      "encodings": ["zarr-v3"],
      "anchors": ["ew-array-codecs"]
    }
  }
}
```

The final shape needs a closed schema, stable identifier grammar, unique references, complete
coverage of the current generic-access encoding vocabulary, and an exact rule for unsupported
identifiers. It does not need to restate Zarr's codec configuration schema or Parquet's footer or
enumerate opaque representations.

## 5. Impact sketch

| surface | impact |
|---|---|
| semantic prose | unchanged; Part 01's meanings do not depend on encoding or reader capability |
| logical prose and registry | semantics unchanged; Part 02 remains storage-agnostic and supplies only the resolved kind consumed by the descriptor |
| physical profile | affected; Part 03 incorporates the descriptor and schema, defines lookup and capability classes, and replaces duplicated encoding tables where the descriptor owns exact assignments |
| physical descriptor and schema | new authoritative artifacts; exact profile, generic encoding, modeled kind, realization, ownership, capability-class, and anchor assignments become data; opaque representations remain open and unenumerated |
| packet catalog | conditional selector and capability concepts affected; complete field shape, any informative opaque-format hint, and cross-field reconciliation remain with the packet-catalog change |
| manifest and resource-delivery schemas | later affected by `encoding_id` and capability requirements; current proposal must settle their semantics first |
| validation and import | affected; build and validation plans consume the descriptor after declaration resolution and distinguish validity from portability support |
| extension registries | unchanged in shape; extension resources use their resolved generic kind against the same physical descriptor without declaring formats in the logical registry |
| reader | affected; resolve table and dense-array encoding metadata from one vendored descriptor and check optional capability requirements only for the accessed resource; list and resolve opaque resources without recognizing their representation |
| writer | affected; choose only descriptor-declared encodings for tables and dense arrays, derive optional requirements from bytes it writes, carry claims for external modeled resources, and omit the selector for opaque resources |
| validator | affected; replace `FLOOR` with descriptor lookup, check modeled kind/encoding/ownership compatibility, report capability class separately from payload validity, and never reject an opaque resource because its representation is unknown |
| adapters | external-resource delivery is affected only in the physical claims it carries; static adapter production capability remains a separate adapter-contract decision |
| existing packets | incompatible development field and identifier migration; generated packets and fixtures are regenerated rather than dual-read indefinitely |
| conformance fixtures | affected; add every encoding/kind/ownership row, missing and unknown modeled encoding, opaque resources with arbitrary representations, baseline capability, recognized optional capability, unsupported capability, parameter-sensitive capability, and per-resource degradation cases |
| implementation tests | affected across reader, writer, validator, adapter delivery, schema vendoring, and cross-package integration |
| revision lifecycle and tooling | unchanged; ordinary specification-domain lifecycle applies |
| generated publications | affected; render descriptor facts or tables from the authoritative JSON and regenerate the combined specification |
| developer documentation | affected after incorporation; explain authoring source, generated copies, lookup, and capability-report interpretation |

## 6. Resolved direction

1. Part 03 incorporates a standalone physical-profile descriptor and closed schema; the logical
   registry remains entirely storage-agnostic.
2. A table or dense array uses `encoding_id` instead of `physical_profile`. An opaque resource has
   no encoding selector, and an unknown opaque representation does not affect packet validity.
3. Packet capability requirements use stable, encoding-qualified tokens whose parameter mappings
   are owned by descriptor-linked Part 03 clauses, rather than copied codec objects or a generic
   selector language.
4. The packet records only requirements beyond the mandatory portable floor. Format-owned metadata
   remains the complete record of mandatory codecs and encodings.
5. Within a recognized table or dense-array encoding, well-formed but unrecognized upstream
   features remain resource-valid but unsupported and non-portable. Exact codec membership and
   finding severity remain for the dedicated codec-portability change.
6. The current descriptor declares only materialized encodings and leaves reader-created views
   outside the packet resource set until a view-definition contract exists.
7. Mandatory reader capability means generic logical-value access for tables and dense arrays.
   Opaque resources require resolution and byte access but no representation-specific interface;
   specialized consumers may support such interfaces independently.

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
