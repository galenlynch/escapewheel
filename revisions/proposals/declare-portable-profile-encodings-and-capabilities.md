# Declare portable-profile encodings and capabilities

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-23 |
| **Based on** | `6fc02db5628440cc632f7608b2164985d4ec0f92` |
| **Decision domain** | specification |
| **Affects** | portable physical-profile authority and identity; kind-to-interface binding, table resource form, and observed capability classification; Parts 00, 03, 04, and 05; packet schemas and implementations; a new physical-profile descriptor and schema |

## 1. Problem

Part 03 owns the portable physical profile, but its exact encoding and capability assignments exist
only as prose and duplicated implementation constants. The logical registry now declares every
resource as `table`, `dense_array`, or `opaque`, and every packet resource binds one declaration.
There is no equivalent machine-readable physical authority that answers which encoding may realize
each kind, which ownership states an encoding admits, or which features every conforming reader
supports.

The packet catalog compounds the omission. Its top-level `profile_id` identifies the whole physical
profile, while each resource's `physical_profile` field repeats a physical fact as a mixture of
interface, layout, version, and opaque format names. Its `codecs` and `required_codecs` fields repeat
selected facts from resource metadata as unqualified names, although Part 03 says readability
depends on the pair of Zarr version and codec and, for Blosc, on configuration. The duplicated
fields are lossy, can become stale, and cannot establish the properties of an unavailable external
resource.

The result is a data-driven logical layer followed by a hand-coded physical layer. A new reader,
writer, validator, extension, or adapter must reconstruct the physical policy from prose and can
silently choose a different set. The current reference implementations already do.

This proposal concerns the physical model and how implementations determine its interfaces,
variants, and capabilities without copying self-describing format metadata into the packet.
Complete manifest shape, registry identity and digest binding, packet verdict composition, exact
codec-floor choices, and portability-report wording remain separate decisions.

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

- the selected profile maps `table` to the Parquet interface and `dense_array` to the Zarr
  interface;
- the current Parquet interface realizes each table as one file, while Zarr v2 versus v3 is a
  variant discoverable from array metadata rather than a packet-selected interface;
- the Zarr v2 variant is allowed only for an external resource; and
- an opaque resource does not select an encoding because Escapewheel does not define a generic
  interface to its internal representation.

The manifest JSON Schema enumerates the duplicated strings but cannot compare one with the logical
kind resolved from a separate checked registry or prove that it agrees with the resource. The
validator performs dense-array checks after logical declaration resolution, but has no general
descriptor-driven compatibility phase. An extension resource consequently depends on the
reference implementation having anticipated its physical case even though its logical declaration
is code-free.

Part 00 §3.4 also says the catalog records each resource's physical encoding. That architecture
summary must instead distinguish the packet's profile selection from interfaces and variants
derived under that profile; otherwise the high-level abstraction would continue to require the
per-resource duplication removed below. Part 00 §7.2 likewise says an external resource declares
its own codecs; externality changes ownership and verification reach, not the authority for
self-describing format metadata.

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

The upstream formats support classification from their own metadata rather than a copied metadata
schema. Zarr gives codecs stable registered names and carries each codec's complete configuration
in array metadata; for
example, its Blosc specification makes `cname`, `shuffle`, `typesize`, and related parameters part
of that metadata. Parquet likewise records compression and value encodings in its own footer. A
physical-profile descriptor can classify those observed facts without a packet duplicating either
format's metadata or declaring the reader capability they imply.

Part 03 §6.5 currently says metadata required for validation must also appear in tables or the
catalog. Read broadly, that sentence would reimpose every physical metadata duplication this
proposal removes. Its purpose is sound for logical or scientific facts that would otherwise be
hidden in optional Zarr attributes, but it must exclude self-describing physical conformance facts
such as format version, shape, dtype, chunking, and codecs. Those facts are validated from the
resource itself.

### 2.4 The manifest projection is both incomplete and redundant

Part 04 §4.1 requires every resource to carry a physical selector and requires codecs for arrays.
The manifest schema requires only `resource_id`, `declaration_id`, and `uri`; `physical_profile` is
optional in its generic resource branch. It has no semantic check connecting the duplicated facts
to logical kind, ownership, partitioning, or the actual resource metadata. Requiring the fields in
more schema branches would make the duplication more consistent without making it authoritative.
This revision can remove the four fields whose meaning the physical model settles:
`physical_profile`, `partitioning`, per-resource `codecs`, and top-level `required_codecs`.
Complete reconciliation of the manifest's other fields remains a separate decision.

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

The final section-impact scan found 137 citations to 16 affected sections in Parts 00, 03, 04, and
05. Live implementation consumers include the reader resource models and Zarr dispatcher, writer
array and manifest construction, validator physical shims and codec reporting, adapter resource
delivery, fixtures, and conformance probes. Historical accepted revisions remain historical and
are not rewritten.

The repository already tested partitioned tables rather than merely anticipating them. Withdrawn
R42 measured a 650 MB table with 286,896,563 rows as one file, an explicit member list, a globbed
dataset, and Hive layout. DuckDB was faster on the single file for every measured query; PyArrow's
multi-file gains appeared where scan parallelism rather than partition pruning dominated. R42 also
found that prefix listing breaks old-manifest snapshot identity when new members appear and that no
defined cross-file row order supports the profile's adjacency-based ordering and uniqueness checks.
It was withdrawn because no packet demonstrated the write-side case that would justify that
machinery. The current writer and fixture corpus remain single-file.

A standalone JSON descriptor is feasible with the same source-and-vendoring pattern already used
for the registry contract and Tier 2 rule-language profile. The descriptor can enumerate physical
interfaces, their discoverable variants, capability IDs and classes, their applicable logical
kinds, and their owning prose anchors. Format metadata remains in Parquet or Zarr rather than being
copied into the descriptor or packet. Opaque representations remain outside the descriptor's
closed interface vocabulary.

A disposable feasibility probe confirmed that the current PyArrow dependency can open either a
single file or a Hive directory through one dataset entry point. That establishes implementation
feasibility but does not answer R42's snapshot, order, schema, or demonstrated-need objections.

## 3. Desired outcome and constraints

A successful resolution should establish one physical-profile authority while preserving these
constraints:

- Part 03 owns the meaning of physical encodings and portability. It expressly incorporates a
  closed descriptor schema and one descriptor for the current portable profile.
- The physical descriptor is separate from the logical registry. It consumes the logical kind and
  resource ownership state without adding formats, codecs, or implementation capabilities to Part
  02 declarations.
- The packet's `profile_id` selects the whole profile. The resolved logical kind and that profile
  select the one current generic physical interface; the packet does not repeat that result in a
  per-resource selector.
- Every declared interface states its applicable modeled kind and materialized realization. Its
  resource form and discoverable variants state their permitted packet-owned or external states.
  Logical declaration ID and namespace do not become physical selectors.
- The current Parquet interface realizes one table as one file. It does not admit a directory or
  prefix dataset, and the packet carries no layout or partitioning declaration.
- The same descriptor distinguishes capabilities guaranteed by a conforming profile reader from
  recognized optional capabilities. An implementation's larger support set does not enlarge the
  normative portable floor.
- Capability identity preserves interface/version context and can distinguish configurations where
  configuration affects interoperability.
- The resource representation and its format-owned metadata remain the sole source for
  self-describing physical facts such as Zarr version, shape, dtype, compression configuration,
  and capability use. The packet records the profile selection but no physical selector, codec
  declaration, or capability projection.
- A reader checks capabilities only when asked to use the affected resource. It does not reject a
  whole packet because another resource requires unsupported optional functionality.
- A validator derives capability use from an available resource. An unavailable external resource
  remains physically unassessed rather than acquiring verified properties from packet claims.
- Ordinary catalog access to an `opaque` resource does not require a known representation or
  generic payload decoding. A format-aware implementation may offer additional operations without
  changing the logical kind or packet validity.
- Extension declarations use the same kind-to-interface mapping without modifying the core logical
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

Each logical declaration could list its allowed interfaces and capabilities. This makes exact
declaration-specific restrictions easy, but it violates the storage-agnostic logical boundary and
duplicates the same table and array mappings across core and extension declarations. Supporting a
second physical profile would require changing logical registries whose meanings did not change.

### 4.3 Incorporate a standalone physical-profile descriptor

This proposal prefers a hand-authored descriptor and a closed JSON Schema under `registry/`, with
Part 03 expressly incorporating both. The descriptor identifies the profile, the logical standard
it consumes, its generic interfaces, variants, and capabilities. Reader, writer, and validator
distributions vendor the exact artifact through the existing generator rather than maintain local
policy sets.

This follows the established local pattern: prose defines the semantics and actor obligations;
the incorporated descriptor owns exact identifiers, assignments, and classification; external
format specifications continue to own their metadata. A disagreement is an inconsistent candidate,
not an invitation to choose prose or JSON silently.

### 4.4 Derive the physical interface instead of declaring it twice

One option retains `physical_profile`; another renames it to `encoding_id`. Both make the packet
repeat information already determined by the selected profile, resolved logical kind, and resource
metadata. This proposal prefers no per-resource physical selector in the current profile.

The profile descriptor binds `table` to the single-file Parquet interface and `dense_array` to the
Zarr interface. Zarr metadata reveals the applicable format version when an implementation
accesses it. A reader therefore uses `profile_id` and the declaration's logical kind to choose the
generic interface, then verifies the resource while opening it. A validator follows the same
derivation when it assesses physical conformance.

A future profile that permits multiple interfaces for one logical kind can define how they are
selected when that need exists. A later Parquet-dataset realization must first define immutable
membership, cross-file row order, partition-value encoding, and schema validation. The current
profile does not add a selector or partitioning declaration for that unused case. An unavailable
external Zarr resource has no verified variant until its metadata can be inspected.

An optional media type or format hint could help specialized consumers discover opaque resources,
but it would be an open, informative catalog value rather than an encoding selector. Its exact
field belongs to the complete packet-catalog decision. Absence or an unrecognized value must not
invalidate an opaque resource or create a generic reader obligation.

### 4.5 Classify observed capabilities without copying format metadata

Three representations were considered:

1. keep bare codec names in the packet;
2. copy complete Zarr codec objects and Parquet footer features into the packet; or
3. keep capability classifications in the descriptor and derive their use solely from the
   resource's format-owned metadata.

This proposal prefers the third representation. A capability ID includes its interface and variant
context and, where necessary, the configuration distinction that changes support. Illustrative
tokens are `zarr-v3.codec.gzip`, `zarr-v3.codec.sharding-indexed`, and a distinct token for the
recognized Blosc configuration. They are not proposed final spellings.

The descriptor entry states whether the capability is part of the mandatory portable floor or is
recognized optional, which interface variant it applies to, and which normative anchor defines the
mapping from format metadata to the ID. The IDs support implementation capability advertisement,
validation findings, and portability reports; they are not packet fields. The descriptor does not
introduce a general JSON-path or predicate language. An implementation reads the format's own
metadata and applies those small, specified mappings. This keeps normative classification
data-driven without creating another executable language or a stale packet projection.

### 4.6 Do not serialize capability projections in the packet

The strongest reason to copy capabilities into the packet is zero-I/O planning: a scheduler or
catalog could estimate compatibility without dereferencing every resource. Making that projection
reliable would require version- and configuration-qualified per-resource requirements, validation
against the payload, integrity binding, rules for unavailable resources, and a mismatch policy.
The reader would still have to inspect the resource metadata before decoding it.

The current project has no requirement for offline capability negotiation that justifies that
second contract. This proposal therefore removes per-resource `codecs` and any replacement
capability declaration, and removes packet-level `required_codecs` or capability unions. Readers
derive requirements lazily from the resource they open. Validators and reporting tools derive them
from every resource they inspect. Writers choose profile-conforming output but do not restate facts
already recorded by the format.

An unreachable external resource remains unresolved for physical-capability assessment. An adapter
claim would not make its codecs verified. If zero-I/O scheduling becomes a demonstrated use case,
a later specification can define an optional integrity-bound generated index without making it the
source for decoding or physical conformance.

### 4.7 Classify unknown features without enlarging the floor

A fully closed feature vocabulary would reject every newly registered upstream codec until this
profile changed. A fully open vocabulary would make a typo indistinguishable from an intentional
extension and could not provide a stable portability answer.

For a recognized table or dense-array interface variant, this proposal prefers a closed set of
mandatory and recognized-optional entries plus an explicit unsupported fallback for well-formed
upstream feature identifiers. Unsupported does not mean that the bytes violate their upstream
format; it means this profile promises no portable reader support. The resource remains
independently addressable, and an implementation may advertise support, but a validator reports
that the resource is outside the profile's recognized portability set. Exact codec-floor
membership and report severity remain for the dedicated codec-portability decision. Opaque
representations do not enter this classification: being unknown is expected and has no validity or
portability effect.

### 4.8 Bind capabilities to generic logical access

“Support” needs an operation and an actor. This proposal prefers to define a portable read
capability as the ability of a conforming reader to expose a `table` or `dense_array` resource's
logical values through the applicable generic access model. A profile reader also resolves,
locates, and integrity-checks an `opaque` resource, but need not decode or render its payload.

The descriptor contains only interfaces that provide this generic logical access. Validator support
is a separate implementation capability: a validator may inspect metadata and establish physical
conformance without offering an application-level decoder. Opaque resources remain resolvable,
listable, integrity-checkable, and byte-accessible without an interface entry. This prevents an
installed video player, PDF renderer, or domain library from silently becoming part of baseline
Escapewheel reader conformance. A specialized consumer may advertise such support independently.

### 4.9 Represent realization without inventing a current view format

The descriptor schema can make realization an interface property rather than a logical kind. Every
current interface is `materialized`; packet ownership and external reference are a separate
dimension. A packet-owned Parquet file and an externally referenced Zarr store are both
materialized resources. The current descriptor should not include a view interface because Part 03
defines no query or view serialization. Reader-created views therefore remain operations, not
packet resources.

A later profile can add a view realization only together with an interface or definition contract
that makes its inputs, language, and evaluation behavior decidable. That addition would not change
the logical declaration's kind.

### 4.10 Illustrative descriptor shape

This is a feasibility sketch rather than proposed normative JSON:

```json
{
  "$schema": "https://escapewheel.org/schemas/physical-profile/0.1.0",
  "id": "escapewheel-portable-v0.1",
  "logical_standard": "escapewheel-logical-v0.1",
  "kind_interfaces": {
    "table": "parquet",
    "dense_array": "zarr",
    "opaque": null
  },
  "interfaces": {
    "parquet": {
      "realization": "materialized",
      "access": "logical_values",
      "resource_form": "single_object",
      "ownership": ["packet", "external"]
    },
    "zarr": {
      "realization": "materialized",
      "access": "logical_values",
      "resource_form": "prefix",
      "variants": {
        "v3": {"format_version": 3, "ownership": ["packet", "external"]},
        "v2": {"format_version": 2, "ownership": ["external"]}
      }
    }
  },
  "capabilities": {
    "zarr-v3.codec.gzip": {
      "class": "mandatory_portable",
      "interface": "zarr",
      "variant": "v3",
      "anchors": ["ew-array-codecs"]
    },
    "zarr-v3.codec.sharding-indexed": {
      "class": "recognized_optional",
      "interface": "zarr",
      "variant": "v3",
      "anchors": ["ew-array-codecs"]
    }
  }
}
```

The final shape needs a closed schema, stable identifier grammar, unique references, complete
coverage of the current generic-access interface and variant vocabulary, and an exact rule for
classifying unsupported observed features. It does not need to restate Zarr's codec configuration
schema or Parquet's footer, enumerate opaque representations, or define packet capability fields.

## 5. Impact sketch

| surface | impact |
|---|---|
| architecture prose | affected; Part 00 distinguishes the packet's profile selection and resource location from interfaces and variants derived through the profile, and no longer says an external resource declares codecs |
| semantic prose | unchanged; Part 01's meanings do not depend on encoding or reader capability |
| logical prose and registry | semantics unchanged; Part 02 remains storage-agnostic and supplies only the resolved kind consumed by the descriptor |
| physical profile | affected; Part 03 incorporates the descriptor and schema, defines kind-to-interface derivation and observed capability classes, and replaces duplicated tables where the descriptor owns exact assignments |
| physical descriptor and schema | new authoritative artifacts; exact profile, generic interface, resource form, discoverable variant, modeled-kind binding, realization, ownership, capability-class, and anchor assignments become data; opaque representations remain open and unenumerated |
| packet catalog | affected; the current `physical_profile`, `partitioning`, `codecs`, and `required_codecs` declarations are retired rather than renamed; complete treatment of other fields and any informative opaque-format hint remains with packet-catalog reconciliation |
| manifest and resource-delivery schemas | affected now by removal of duplicated physical selectors and capability claims; no replacement codec or capability field is introduced; the later complete schema reconciliation remains broader |
| validation and import | affected; build and validation plans resolve the logical kind, consume the descriptor, inspect available resource metadata, and distinguish validity from portability support and unavailable-resource assessment |
| extension registries | unchanged in shape; extension resources use their resolved generic kind against the same physical descriptor without declaring formats in the logical registry |
| reader | affected; derive the interface from profile plus logical kind, require a table URI to resolve to one Parquet object, discover Zarr variant and capabilities from metadata only when accessing an array, and list or resolve opaque resources without recognizing their representation |
| writer | affected; write each table as one Parquet object, choose only descriptor-declared interfaces and variants for dense arrays, and omit physical selectors, partitioning, codec lists, and capability summaries from packet entries |
| validator | affected; replace `FLOOR` and packet claims with descriptor lookup over inspected resource metadata, check kind/interface/variant/ownership compatibility, report capability class separately from payload validity, and never reject an opaque resource because its representation is unknown |
| adapters | no codec or capability claim is required; external resource delivery still supplies identity and location, while static adapter production capability remains a separate adapter-contract decision |
| existing packets | incompatible removal of development fields; generated packets and fixtures are regenerated rather than dual-read indefinitely |
| conformance fixtures | affected; add every kind/interface/variant/ownership row, rejection of a table prefix, metadata-discovered Zarr variants, opaque resources with arbitrary representations, baseline capability, recognized optional capability, unsupported capability, parameter-sensitive capability, unavailable external assessment, and per-resource degradation cases |
| implementation tests | affected across reader, writer, validator, adapter delivery, schema vendoring, and cross-package integration; writer codec-selection options remain implementation inputs rather than packet declarations |
| revision lifecycle and tooling | unchanged; ordinary specification-domain lifecycle applies |
| generated publications | affected; render descriptor facts or tables from the authoritative JSON and regenerate the combined specification |
| developer documentation | affected after incorporation; explain authoring source, generated copies, lookup, and capability-report interpretation |

## 6. Resolved direction

1. Part 03 incorporates a standalone physical-profile descriptor and closed schema; the logical
   registry remains entirely storage-agnostic.
2. The selected profile and resolved logical kind derive the current generic interface: `table`
   maps to Parquet, `dense_array` maps to Zarr, and `opaque` has no generic physical interface. No
   per-resource physical selector replaces `physical_profile`.
3. The current Parquet interface realizes every table as one file or object. Partitioned or other
   multi-file tables are outside this profile, and the packet contains no layout or partitioning
   declaration. A later profile can add them only with complete membership, order, partition-value,
   and schema semantics.
4. The resource representation and its format-owned metadata are the sole authority for
   self-describing physical facts including Zarr version, codec use, codec configuration, Parquet
   compression, and Parquet value encoding. The packet contract contains no codec declarations,
   per-resource capability requirements, or packet-level capability union.
5. Stable interface- and variant-qualified capability IDs exist only in the descriptor and in
   implementation advertisements or reports. Descriptor-linked Part 03 clauses map observed
   format metadata to those IDs without copying complete upstream schemas or defining a general
   selector language.
6. Within a recognized table or dense-array interface variant, well-formed but unrecognized
   upstream features are classified as unsupported and non-portable without implying that the
   upstream representation is malformed. Exact codec membership, finding severity, and verdict
   composition remain for their dedicated later decisions.
7. The current descriptor declares only materialized interfaces and leaves reader-created views
   outside the packet resource set until a view-definition contract exists.
8. Mandatory reader capability means generic logical-value access for tables and dense arrays.
   Opaque resources require resolution and byte access but no representation-specific interface;
   specialized consumers may support such interfaces independently.
9. Physical variant and capability assessment requires resource metadata. An unavailable external
   resource remains unassessed; packet claims do not substitute for inspection.
10. Part 03's metadata-placement rule continues to require logical and scientific validation facts
   outside optional format attributes, but it does not require self-describing physical
   conformance facts to be duplicated in tables or the catalog.

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
