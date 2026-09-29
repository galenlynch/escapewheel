# Part 00 lists a packet's contents by logical kind

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-29 |
| **Based on** | `59f98973df38c6938ce64390c69989ebef532c8d` |
| **Decision domain** | specification |
| **Affects** | Part 00 §3.3's list of what a packet contains, §3.5's list of what an Iceberg catalog leaves out, and §7.1's statement of what the portable profile is; the root README's summary of the logical level |

## 1. Problem

Part 00 §3.1.2 names three logical kinds, tables, dense arrays and opaque payloads, and calls a
view or materialization a realization of one of them. Part 02 §2.3 owns the vocabulary and
forbids `media_asset` and `document_asset` as kinds. Three sentences elsewhere in Part 00 still
describe a packet's contents in categories that predate the three kinds:

- §3.3: "A packet contains a packet manifest, core tables, and any of: dense arrays, media,
  documents and sidecars, analysis materializations, and validation and provenance records."
- §3.5: an Iceberg catalog "does not catalog dense arrays, media, documents, or semantic
  relationships across a packet".
- §7.1: "The portable profile is a JSON manifest, Parquet tables, Zarr arrays, ordinary media
  files, and text sidecars."

Each leaves a packet-owned opaque payload that is neither media nor a document, such as a figure
or a report, in no category it names.

## 2. Evidence

### 2.1 The three lists descend from v0.1's categories

The frozen v0.1 Part 00 represented semantic concepts as tables, dense array assets, media assets,
document assets, views, materialized tables and arrays, and references between resources. Its
packet held a manifest, core tables, dense arrays, optional media, optional docs and sidecars,
optional analysis materializations, and validation and provenance records. Its Iceberg catalog did not catalog "Zarr arrays, MP4 files, free-form
documents", and its portable profile stored "media: MP4 or ordinary files" and "docs:
Markdown/JSON/text/PDF sidecars". R128 §3.3 replaced these with three kinds, and its crosswalk
revised Part 00 §§3.1.2 and 3.2 but not §§3.3, 3.5 or 7.1. R143 replaced Part 03 §3.1's `media/`
directory with `opaque/<resource_id>/<name>` for every packet-owned opaque resource.

### 2.2 The owners already state the model

Part 03 §2 maps `table` to Parquet, `dense_array` to Zarr and `opaque` to no generic interface,
and Part 03 §11 stores a packet-owned opaque resource as one regular file or one directory,
whatever its format. At the baseline the core registry declares 45 tables, 2 dense-array families
and 1 opaque family, `core.media_asset_instances`; the four extension registries declare 11
tables; no declaration has content class `documentation`. No incorporated JSON Schema names media
or documents as a category.

Each list mixes levels. §3.3's names a kind (dense arrays), a Part 01 concept (media), a content
class (documents and sidecars, Part 02 §2.2's `documentation`) and a realization (analysis
materializations), and omits the registries a packet binds (Part 04 §8). What an Iceberg catalog
leaves out is every resource not of kind `table`, whatever its concept.

Part 01 §3.18's media asset is consistent with the model and is not among the stale sentences.
R128 §3.3 requires Part 01 to define a media asset, as an image or video with its timing facts
represented logically, and forbids it URI, container format and registry binding. A media asset is
represented as an instance of the opaque family `core.media_asset_instances` plus rows of
`core.media_assets` and `core.media_frames`.

### 2.3 Nothing reads the sentences as rules

None of the three uses a BCP 14 keyword or binds an actor. `revisions/impact.py` finds three live
citers of Part 00 §3.3, Part 03 §4 and two reference-reader docstrings, and all three cite its first
paragraph, on the forms a packet root takes, which this change leaves alone. Part 00 §3.5 is cited
by nothing, and §7.1 only by the placement-defect inventory. Part 00 §7.1 has no canonical anchor.

The root README's summary of the logical level lists "tables, arrays, views", naming a realization
and omitting opaque payloads.

## 3. Desired outcome and constraints

A resolution describes a packet's contents by the classifications Part 00 §§3.1.2 and 3.2 define,
and meets these constraints:

- no rule changes, and every current owner keeps its text;
- Part 01 §3.18's media asset stays, as R128 §3.3 requires;
- Part 03 §3.1's recommended layout stays, `docs/` beside `opaque/`, since a reader resolves every
  resource through the manifest; and
- Part 00 §3.3's first paragraph, which three citers rely on, stays.

## 4. Options and tradeoffs

For the text, the preferred direction states each list by kind:

- §3.3: a packet contains a packet manifest, the registries it binds, and resources of the three
  logical kinds (§3.1.2), each in one content class (§3.2);
- §3.5: an Iceberg catalog does not catalog dense arrays, opaque payloads, or semantic
  relationships across a packet; and
- §7.1: the portable profile stores tables as Parquet, dense arrays as Zarr and each opaque payload
  as its own file or directory, under a JSON manifest.

Deleting the lists and citing the owners would also remove the contradiction, and would leave
Part 00's architecture overview without the one sentence saying what a packet holds.

For the route:

| option | effect |
|---|---|
| keep today's text | Part 00 contradicts its own §3.1.2 and Part 03 §§2 and 11 |
| a revision | a structural draft, since text inside existing sections is replaced, as in R143 §1; an anchor bootstrap for Part 00 §7.1; ledger and evidence records for clauses that bind no actor |
| maintenance, recorded in the placement-defect inventory (preferred direction) | one reviewed commit, as `5236850` replaced Part 00 §7.1's restated rule with a citation and resolved PD-020 without a revision |

The revisions guide sends meaning-preserving editorial fixes to the ordinary workflow, and asks
whether two implementations could behave differently after the change while both conformed before
it. No implementation can: the current owners already state every fact the corrected sentences
would, so the proposal's disposition would be abandonment in favour of that maintenance commit.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. Part 01 §3.18 defines the concept R128 §3.3 requires and names no kind, URI or format. |
| logical prose and registry | Unchanged. Part 02 §2.3 already states the three kinds and forbids `media_asset` and `document_asset`. |
| physical profiles | Unchanged. Part 03 §§2 and 11 already state opaque storage, and §3.1 keeps `docs/` beside `opaque/`. |
| packet manifest and JSON Schemas | Unchanged. No schema names media or documents as a category. |
| validation and import | Unchanged. No check reads Part 00's lists. |
| extensions | Unchanged. The four extension registries declare tables only. |
| reader, writer, validator, adapters | Unchanged. The reader's two citations of Part 00 §3.3 name its first paragraph. |
| existing packets | Unchanged. Every packet conforms as before. |
| conformance fixtures and tests | Unchanged. The sentences bind no actor, so no fixture distinguishes the two texts. |
| revision process and tooling | The placement-defect inventory gains an entry for the three sentences. The maintenance route needs no ledger or evidence record. |
| generated publications and developer documentation | The combined rendering regenerates. The root README's logical-level line names the three kinds. The specification README's "standard media containers for media" stays: it names the container a video keeps, not a kind. |

## 6. Open questions

1. **Does the repair need a revision?** Preferred: no. It is maintenance recorded in the
   placement-defect inventory, since the owners already state the model and no implementation
   behaves differently either way (§4).

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
