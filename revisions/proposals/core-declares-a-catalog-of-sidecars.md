# Core declares a catalog of sidecars

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-10-01 |
| **Based on** | `2928aa8a895ae7971aceb21364c2744998532471` |
| **Decision domain** | specification |
| **Affects** | Part 02 §2.2's meaning of the `documentation` class; Part 02 §2.6's list of catalog tables; Part 02 §11's resource index and the incorporated registry; Part 03 §3.1's layout and Part 03 §7's placement table; Part 09 §2's tier table |

## 1. Problem

A packet often has to carry a file that Escapewheel does not interpret: a protocol as a PDF, a
README, a viewer's saved state, or an image in a format no logical kind models. Part 02 §2.2 calls
such a file a sidecar and gives it a content class, `documentation`. Part 03 and Part 09 say that a
sidecar belongs in a directory `docs/` under the packet root.

No registry declares a resource of that class, so no manifest can list a sidecar. A file placed in
`docs/` is therefore outside the packet's contract: nothing records its digest, no reader lists it,
and a copy that follows the manifest leaves it behind. The route that does list such a file is an
extension registry with an opaque declaration, and an adapter to deliver the payload. That is a
registry document and a program for a file the packet only indexes.

## 2. Evidence

Observed in the tracked files at the baseline commit.

### 2.1 The parts name a place for a sidecar and declare none

Part 02 §2.2 defines the class `documentation` as human-readable sidecars that assert no semantic or
conformance fact. Part 03 §3.1's recommended layout has a `docs/` directory for human-readable
sidecars, and Part 03 §7 and Part 09 §2 both place human-readable context in `docs/`. A search of
`spec/parts/` for `docs/` and for `sidecar` finds no other statement about them.

The core registry holds 48 declarations, 43 of class `core` and 5 of class `analysis`. The extension
registries in the repository hold 11, all of class `extension`. No declaration has the class
`documentation`.

### 2.2 A file in `docs/` is a stray

Part 03 §9 defines a stray as a file under the packet root that no manifest ever named, and
Part 05 §15.5 lets a packet carry files the specification does not govern. Part 03 §3.1 has a reader
resolve resources through the manifest and never from a path. A file in `docs/` that no manifest
names is a stray under those rules. Part 04 §4.3 records a digest for a manifest entry only, so no
digest covers the file, and no validator verifies it.

### 2.3 The one opaque declaration in core describes frames on a clock

The core registry has one opaque declaration, `core.media_asset_instances`, catalogued by
`core.media_assets`. Part 01 §3.18 defines a media asset as an image or video and the timing of its
frames. Its catalog row requires a session and carries a presentation-timestamp rate and a clock. A
document has none of these, so a row for one would state nothing true about it.

### 2.4 A manifest entry describes no payload

Part 04 §4.1 gives a resource entry eleven members. They identify the resource, locate it, and
record its integrity and lineage; none states a media type, a title, or a description. Part 12 §5
has a build record no format for a payload. A catalog row is therefore the only place an opaque
resource can be described, and a singleton or family instance is known by its resource ID and its
file name alone.

### 2.5 Listing one file takes a registry and an adapter

Part 05 §10 requires every resource a manifest lists to resolve a logical declaration, and names an
extension registry as the route for a resource core does not define. Part 09 §5.6 has a writer build
an extension's tables from its registry document and its rows with no code of the extension, and
excludes an opaque payload from that promise. Under Part 12 §5 a packet-owned payload crosses only
from an adapter that declares `opaque_location`.

An author who wants a PDF listed therefore writes an extension registry declaring an opaque
resource, a catalog table too where the file is to be described, and an adapter that delivers the
payload. None of the adapters the reference implementation ships delivers a payload; its video
adapter delivers each video as a referenced resource.

### 2.6 The delivery rules already serve an opaque catalog

Part 12 §5 binds a payload to the catalog row of an opaque catalog family whose `resource_id` equals
the payload's resource directory, and delivers a referenced resource as an entry of a resource
document. Part 03 §2 lets an opaque resource be packet-owned or external. An opaque catalog declared
by core is delivered by those rules as they stand, and each of its instances can be either.

### 2.7 A table has a session or has none

Part 02 §7.1 requires a session-scoped table to carry a required `session_id` and forbids the column
to any other table, so no table has an optional session. Two core tables carry no `session_id`:
`core.subjects` and `core.source_files`.

### 2.8 An amendment may replace a documentation resource and no canonical one

Part 05 §15.2 lets an amendment add a resource other than a canonical table, and remove or replace
an analysis, compatibility-projection or documentation resource. It forbids an amendment to change a
canonical resource that is not a table or to remove a canonical resource, and makes a correction of
canonical data a replacement of the packet.

## 3. Desired outcome and constraints

A packet's author lists a file by naming it and describing it, with no registry and no adapter of
their own. A consumer finds a packet's sidecars with one query, learns from each row what the file
is, and resolves its bytes through the manifest, which records a digest for it. A sidecar is
packet-owned or external, as any opaque resource is. The resolution preserves:

- Part 05 §10's rule that every resource a manifest lists resolves a logical declaration;
- Part 02 §2.2's rule that a canonical resource depends on no non-canonical one;
- Part 02 §2.3's meaning of opaque, under which no generic code parses, decodes or renders a payload;
- Part 09 §8.1's rule that core holds no table of arbitrary name-value pairs;
- the conformance of every existing packet, including one that holds a stray in `docs/`; and
- the extension route, for a payload whose meaning another table states.

## 4. Options and tradeoffs

| option | effect |
|---|---|
| keep the current rules | a sidecar is a stray with no digest, or its author writes a registry and an adapter; `docs/` stays a named place with no contract |
| let a manifest list a resource with no declaration | removes the effort and contradicts Part 05 §10; the entry would have no content class, lineage policy or instance rule for a validator to apply |
| core declares an opaque family with no catalog | the lightest declaration; an instance has no description or media type (§2.4); Part 12 §5 binds a payload to a catalog row or a singleton only, so a family payload would need a delivery rule |
| core declares an opaque catalog of class `core` | a sidecar is canonical, so an extension's table could reference its row and state facts about it; an amendment could add one and could never replace or remove one, so correcting a README would take a replacement packet |
| core declares an opaque catalog of class `documentation` (preferred direction) | uses the class Part 02 §2.2 defines for a sidecar; an amendment adds, replaces or removes one; no canonical table references one, so a payload whose meaning tables state keeps the extension route |

Under the preferred direction the core registry gains two declarations of class `documentation`: a
catalog table with one row for each sidecar, and an opaque catalog declaration whose instances that
table's `resource_id` column names. A manifest then lists each sidecar as an instance of the opaque
declaration, bound one-to-one to its row under Part 02 §2.6.

**The row describes the file and is read by no rule.** It carries the assigned identifier and the
name Part 02 §8.2 pairs with it, the `resource_id` Part 02 §2.6 requires, a media type, and a
description. The media type and the description are nullable. A media type is absent where none is
registered for the format, which is ordinary for a scientific file format. Part 02 §2.6 keeps
`format` out of the three existing catalog tables because physical encoding belongs to Part 03; a
sidecar has no encoding the specification defines, and its media type tells a consumer which program
opens it.

**The table carries no session.** Part 02 §7.1 admits no optional session column (§2.7), and a
sidecar may describe the packet, a subject, a session, or one resource. The table is therefore
scoped to the packet, as `core.source_files` is, and a sidecar's description says what it is about.

**The class covers a sidecar a program reads.** Part 02 §2.2's meaning of `documentation` loses
"human-readable": a sidecar asserts no semantic or conformance fact, whether a person or a program
reads it. A viewer's saved state and an image in a format no kind models are then sidecars. Part 02
§2.2's sentence about a machine-interpreted control artifact stays, since it excludes a document that
Escapewheel itself interprets, such as a recipe or a registry.

**A payload that tables describe is not a sidecar.** Part 02 §2.2 forbids a canonical table to
reference a documentation resource. An image that a coordinate frame is registered to, or a volume
whose axes a table states, therefore takes a dense-array declaration or an extension's own
declaration, as it does now.

**Storage and delivery follow the existing opaque rules.** A packet-owned sidecar is a payload under
Part 03 §11, at `opaque/<resource_id>/<name>` in the recommended layout, and a referenced one is
external under Part 04 §5. Part 03 §3.1's layout drops `docs/`, and Part 03 §7 and Part 09 §2 name
the sidecar catalog as the place for human-readable context. A file already in `docs/` remains a
stray that Part 05 §15.5 protects. Part 12 §5 is unchanged (§2.6), and so is the recipe: an adapter
that delivers the files its options name is an adapter like any other, and a build may ship one.

Family mode keeps its definition in Part 02 §2.4. No declaration uses it and Part 12 §5 gives a
family payload no binding rule, which is a separate question.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. A sidecar asserts no semantic fact, so Part 01 gains no concept. |
| logical prose, registry meta-schema, declarations and rules | Part 02 §2.2 restates the meaning of `documentation`. Part 02 §2.6 names a fourth catalog table whose `resource_id` is a string. Part 02 §11 gains the two resources. The registry gains the table and the opaque catalog declaration; the table declares `[]` as its amendment groups, as every non-canonical table does. The meta-schema and the registry contract are unchanged: a core registry may already declare the class. Whether a declared rule checks a media type's form is unknown, and either answer leaves the direction unchanged. |
| physical profiles | Part 03 §3.1's layout drops `docs/` and Part 03 §7 names the catalog. Part 03 §11 and the descriptor are unchanged. |
| packet manifest and other JSON Schemas | Unchanged. A sidecar's entry uses the existing members, and the recipe schema already admits an adapter's options. |
| validation and import | Unchanged in rule. Part 04 §10's catalog-binding checks and Part 05 §15.2's amendment table already cover a documentation catalog. Part 09 §2's tier table names the catalog in place of `docs/`. |
| extension registries | Unchanged. An extension keeps the right to declare its own opaque or documentation resource. |
| reader, writer, validator, adapters, code generation | Each package's registry copy regenerates. The reader lists the table and resolves an instance as it does any catalogued resource. The writer ships an adapter that delivers the files a recipe names, each packet-owned or referenced. The validator applies its existing checks. Other adapters are unchanged. |
| existing packets | Unchanged in conformance. No existing packet carries either resource, and a stray in `docs/` stays a stray. A packet built afterwards binds the changed core registry. |
| conformance fixtures and implementation tests | The corpus gains a packet with a packet-owned sidecar and a referenced one, a catalog row no entry binds, and an entry no row binds. Build tests cover the adapter. An amendment test replaces and removes a sidecar. |
| revision lifecycle, ledger, evidence and tooling | The ledger records that the accepted clause defining the class meanings is superseded in that one row. No process rule changes. |
| generated publications and developer documentation | The generated table listing and the combined rendering regenerate. The writer's guide documents the adapter, and Part 08's example is unchanged unless the draft adds a sidecar to it. |

## 6. Open questions

1. Whether a sidecar is of class `documentation` or `core`. Section 4 prefers `documentation`. The
   answer decides whether an amendment can correct a sidecar and whether an extension's table can
   reference one.
2. Whether the catalog table is scoped to the packet or to a session. Section 4 prefers the packet.
   A session-scoped table would let a query join a sidecar to its session, and would oblige a
   document about the whole packet to name one.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [ ] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [ ] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.
