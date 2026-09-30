# A packet names the packet it replaces

| | |
|---|---|
| **Status** | **Accepted** 2026-09-30 |
| **Based on** | `886ad3a91063a2e3d5a3ececeea8a1baa966fe1a` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 03 §8.1; Part 04 §§1, 3 and 10; Part 05 §§3.1, 3.5, 9.3, 15.1, 15.2, 15.3 and 15.6; the manifest schema; the recipe schema |
| **Depends on** | R150 §§3.3, 3.4 and 3.5 (the amendment, its comparison and the amending build this constrains); R150 §3.10 (the recipe schema version this advances from) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6; §3.7 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

A packet follows another in one of two ways. An amendment (Part 05 §15) publishes a new version of
the packet at its root: it keeps `packet_id`, sets a `packet_version` sorting after the superseded
one, and retains the superseded manifest. A rebuild runs a recipe and publishes a packet at a new
root, and records nothing of the packet it follows. A correction can only be a rebuild, since no
amendment changes a canonical row, and so can any addition Part 05 §15.2 forbids an amendment.

Nothing gives a rebuild an identity of its own. A recipe names the packet it builds and a writer
sets the version, so a rebuild from the same recipe publishes a second packet under its
predecessor's `packet_id` and `packet_version`. A reference held outside a packet names it by those
two values, and after a rebuild they name two packets whose rows and identifiers need not agree.
Neither packet says how it relates to the other, and Part 05 §9.3 asks an import that "replaces an
existing packet" to report the resources it dropped without saying which packet an import replaces.
The parts also disagree about what a correction is: Part 05 §15.2 says a packet whose canonical data
was wrong "is a new packet, not a new version of an old one", and Part 03 §8.1 says "A correction is
a new packet version, not an edit."

This revision lets a manifest name each packet it replaces, by `packet_id`, `packet_version` and
the SHA-256 of the manifest that packet published, and names none by location. A replacement that
keeps its predecessor's `packet_id` takes a greater major version, so `packet_version` orders every
packet sharing a `packet_id` and its major version changes wherever identifiers may. A recipe names
the packets its build replaces, and the build compares against them. An amendment keeps its major
version and its link, and a correction is a replacement. The manifest schema advances to 0.6.0 and
the recipe schema to 0.3.0.

The change is structural because it revises rules inside Part 03 §8.1 and Part 05 §§9.3, 15.1,
15.2, 15.3 and 15.6. Appended sections would leave those sections stating that a correction is a
new version, that any amendment may set any later version, and that every superseded manifest a
packet has is retained, each contradicted by a later section.

### 1.1 Structural crosswalk

The `Based on` commit is a metadata-only bootstrap adding `ew-packet-owned-bytes` before Part 03
§8.1's heading and `ew-prior-packet-comparison` before Part 05 §9.3's, and changes nothing else.
Every other affected section already carried an anchor. No section moves, splits, merges or
retires.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 03 §8.1, what a correction is | revise in place | same section | a correction is a replacement | §3.6 |
| Part 04 §1, the incorporated manifest schema | revise in place | same section | the schema is 0.6.0 | §3.7 |
| Part 04 §3, the top-level members and their meaning | extend in place | same section | a manifest may name the packets it replaces; a replacement keeping a named packet's `packet_id` takes a greater major version; a held named packet is confirmed | §3.1; §3.2; §3.3 |
| Part 04 §10, the `entries` checks | extend in place | same section | `packet.replaces.major_version` | §3.2 |
| Part 05 §3.1, the recipe's members and the recipe schema's identifier | revise and extend in place | same section | a recipe may name the packets its build replaces; the schema is 0.3.0 | §3.4; §3.7 |
| Part 05 §3.5, the refusals of a recipe | extend in place | same section | a replacing recipe's refusals | §3.4 |
| Part 05 §9.3, comparison against a prior packet | replace in place | same section | a build compares against the packets its recipe names | §3.4 |
| Part 05 §15.1, the version an amendment sets | revise in place | same section | an amendment keeps its major version and its link | §3.5 |
| Part 05 §15.2, the scope table and the statement of a correction | revise in place | same section | an amendment changes neither; a correction is a replacement | §3.5; §3.6 |
| Part 05 §15.3, superseded manifests | revise in place | same section | a packet retains the manifests its amendments superseded, byte for byte, and none a replacement names | §3.5 |
| Part 05 §15.6, `amendment.identity_changed` | extend in place | same section | the check covers the major version and `replaces` | §3.5 |

## 2. Background

Section 2 is informative. The measurements read the manifests of every development build of the
two session packets that has one, under this baseline: eight builds of
`ecephys_786867_2025-09-25` and seven of `ecephys_776259_2025-04-09`.

### 2.1 Successive builds share one identity

Every build carries its session's name as `packet_id` and `0.1.0` as `packet_version`, which the
reference writer sets for every build. The first session's eight builds bind seven core registry
versions, 0.1.0 and 0.7.0 through 0.12.0, and the second session's seven bind six, 0.7.0 through
0.12.0. In each session `packet-wf` and `packet-r146` share `packet_id`, `packet_version` and core
registry version. Every build's manifest has its own SHA-256.

Successive builds hold different content. The table compares, by `resource_id`, the SHA-256 each
consecutive pair of manifests records for a packet-owned resource; an external entry records none
and is not counted. The earliest first-session build, `packet-pre-s3video`, precedes the manifest's
`registries` member and is left out.

| builds | first session: changed, dropped, added | second session: changed, dropped, added |
|---|---|---|
| `packet-p9` to `packet-wf` | 3, 0, 0 of 58 | 4, 0, 0 of 56 |
| `packet-wf` to `packet-r146` | 2, 0, 0 | 3, 0, 0 |
| `packet-r146` to `packet-r147` | 8, 1, 1 | 6, 0, 1 |
| `packet-r147` to `packet-r148` | 4, 0, 0 | 4, 0, 0 |
| `packet-r148` to `packet-r149` | 1, 0, 0 | 1, 0, 0 |
| `packet-r149` to `packet-r150` | 1, 0, 0 | 1, 0, 0 |

`core.units` records one digest across all seven builds of each session. `core.intervals` changes
digest at `packet-r148`, where R148 renamed a column; matched by `start_tick`, `stop_tick` and
`clock_id`, every one of its 450 and 708 intervals keeps its identifier. So these rebuilds kept
every unit and interval identifier, and nothing in either packet says so. A rebuild can also
renumber. A single build differs from an amended packet wherever an added group sorts before a held
one (R150 §5), and numbered with a kind of interval sorting before the trials, none of the first
session's 450 trials keeps its identifier (R150 §2.2). Such a rebuild still carries the same
`packet_id` and `packet_version`.

The first session's amended build, `packet-r150-amended`, is `0.1.1` and retains the `packet-r150`
manifest it superseded. The retained copy's SHA-256 equals that of `packet-r150`'s `packet.json`.

### 2.2 Nothing records the packet a build replaces

The manifest's members are closed (Part 04 §3), and none names another packet. The recipe's
`packet.id` is "The packet this recipe builds", and no recipe member names a packet the build
follows. The reference writer compares its result with a packet its caller names and warns of each
resource the result lacks, as Part 05 §9.3 asks; the packet it compared against appears nowhere in
the result.

### 2.3 Provenance

R32 §3 made a corrected packet a new packet rather than a new version, because a result derived from
the old core would be invalidated where nothing detects it. Part 03 §8.1's sentence descends from
the frozen v0.1 text, which sent a correction to "a new packet release or new resource version".
R32 §7 left release semantics open, and R32 §8 left open whether `packet_version` means anything
beyond ordering.

### 2.4 Alternatives

Keeping the current rules leaves a rebuild repeating its predecessor's identity, a reference by
`packet_id` and `packet_version` naming several packets, and §9.3's replaced packet undefined.
Naming a replaced packet by `packet_id` and `packet_version` alone names every build of §2.1
ambiguously. Naming it by location breaks the link when a packet moves or is mirrored, since a
location is not an identity (Part 04 §5.5). Giving each replacement a new `packet_id` makes the two
values name one publication, but a dataset's packets then share no name, a recipe changes its
`packet.id` at every rebuild, which none of §2.1's recipes did, and finding the current packet means
following links forward from the old one, which the old one cannot record.

## 3. Decision

The subsections state the manifest member and its meaning, the version a replacement takes, how a
link is confirmed, the recipe and build, the amendment, a correction, and the schema identifiers.

### 3.1 A manifest names the packets it replaces

A manifest MAY carry `replaces`, naming each packet it **replaces**; the packet is then a
**replacement** of each packet named. An item names one published packet version by its
`packet_id`, its `packet_version`, and `sha256`, the SHA-256 of the exact bytes of the manifest that
version published. The item names no location, and a manifest names no replaced packet by location.
A manifest MAY name several packets, as a multi-session packet may replace the single-session
packets it merges, and MAY name packets whose `packet_id` differs from its own.

An item names the version it records and not a later one. After that packet is amended, its
published manifest is the amended one, and the named manifest is the one Part 05 §15.3 has the
packet retain.

The manifest schema declares, as a member of its top-level `properties`:

```json
"replaces": {
  "description": "Every packet this packet replaces, each named by the manifest it published (Part 04 §3).",
  "type": "array",
  "minItems": 1,
  "uniqueItems": true,
  "items": {
    "$ref": "#/$defs/replaced_packet"
  }
}
```

and, as a member of `$defs`:

```json
"replaced_packet": {
  "description": "One published packet version. sha256 is the SHA-256 of the exact bytes of its manifest.",
  "type": "object",
  "required": [
    "packet_id",
    "packet_version",
    "sha256"
  ],
  "properties": {
    "packet_id": {
      "type": "string",
      "minLength": 1
    },
    "packet_version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$"
    },
    "sha256": {
      "$ref": "#/$defs/sha256"
    }
  },
  "additionalProperties": false
}
```

`replaces` is not required.

### 3.2 A replacement keeping a packet's identifier takes a greater major version

A version's **major version** is the first of its three numbers, read as a non-negative integer.

A manifest MUST NOT carry a `replaces` item whose `packet_id` equals the manifest's own and whose
major version is equal to or greater than the manifest's own. `packet_version` therefore orders, as
a semantic version, every packet sharing a `packet_id` and linked by replacement, and its major
version changes wherever one replaces another.

A checker reports a manifest breaking this rule under `packet.replaces.major_version`, in the
`entries` phase of Part 04 §10, at `error`, naming the item.

### 3.3 A link is confirmed where the named packet is held

A reader or validator that reads a manifest as that of a packet a `replaces` item names MUST report,
against the item, each of the manifest's SHA-256, `packet_id` and `packet_version` that differs from
the item's, and MUST NOT prefer the item or the manifest. A validator reports it at `warning` under
`packet.replaces.mismatch`: it cannot tell whether the item or the packet it was given is wrong.

A reader or validator MUST NOT require a packet an item names, and a validator MUST NOT report a
finding because it holds none: which packets it can reach is a property of the reader or validator.

### 3.4 A recipe names the packets a build replaces

`[packet].replaces` lists the packets a build replaces, each entry saying where the build reads one.
This specification does not fix how a build resolves an entry to a packet, as it does not for an
`extensions` entry. The recipe schema declares, as a member of the `packet` object's `properties`:

```json
"replaces": {
  "type": "array",
  "minItems": 1,
  "uniqueItems": true,
  "items": {
    "type": "string",
    "minLength": 1
  },
  "description": "Where the build reads each packet it replaces (Part 05 §3.1)."
}
```

A build MUST refuse, before it opens any source:

- an entry at which it can read no published manifest, or one whose `packet_id` or `packet_version`
  is absent or does not satisfy the manifest schema, naming the entry;
- a recipe giving both `replaces` and `amends`; and
- two entries at which it reads manifests of equal SHA-256, naming both.

A build whose recipe gives `replaces` MUST record in its manifest's `replaces` one item for each
entry, carrying the `packet_id` and `packet_version` of the manifest it read there and the SHA-256
of the exact bytes it read, and no other item. No checker verifies this. It MUST set a
`packet_version` whose major version exceeds that of every named packet whose `packet_id` equals
`[packet].id`.

A build whose recipe gives `replaces` SHOULD report, as a warning, every resource a named packet's manifest declares that its
own manifest does not. This is a warning: narrowing is legitimate, and no other check sees a
resource that is simply absent.

### 3.5 An amendment keeps its major version and its link

A writer performing an amendment MUST set a `packet_version` that sorts strictly after the
superseded one, compared as a semantic version, and has the superseded one's major version. The
amended manifest MUST carry `replaces` exactly as the superseded manifest does, or omit it where
that manifest omits it. An amendment therefore changes neither the major version nor `replaces`, as
it changes none of `packet_id`, `profile_id` and the standard versions.

`amendment.identity_changed` (Part 05 §15.6) also reports two manifests whose `packet_version`
major versions differ, or whose `replaces` differ, where an absent member differs from any present
one and two arrays differ unless they hold equal items in the same order.

A packet retains every manifest its amendments superseded, and retains no manifest of a packet its
manifest's `replaces` names. A writer retaining a superseded manifest MUST retain its exact bytes, so
that an item naming that version is confirmed from the retained copy. No checker verifies this.

### 3.6 A correction is a replacement

A correction is a replacement, not an edit and not an amendment. A packet whose canonical data was
wrong is corrected by a replacement naming it, which MAY keep its `packet_id` at a greater major
version (§3.2).

### 3.7 The schema identifiers advance

The manifest schema's `$id` is `https://escapewheel.org/schemas/manifest/0.6.0`, and Part 04 §1
incorporates it. The recipe schema's `$id` is `https://escapewheel.org/schemas/recipe/0.3.0`, and
Part 05 §3.1 incorporates it. Part 05 §3.1's recipe table lists `replaces` among the members the
`packet` table admits, and its list of what a recipe declares gains each packet the build replaces.

## 4. What this does not change

A link runs backward only. A replaced packet is immutable and cannot record what replaced it, so a
reader holding only the old packet cannot learn it was replaced; a catalog holding both can. Nothing
requires a rebuild to name what it replaces or to take a new version: a build whose recipe gives no
`replaces` is bound as before, and nothing but the recipe keeps two independent rebuilds of one
packet from publishing the same version, as nothing keeps two amendments from doing so. A
replacement publishes at a root of its own; Part 05 §6 already refuses a promotion over any path its
record lists that exists.

## 5. Consequence

Every existing packet conforms unchanged, since `replaces` is optional and an absent member draws
no check. A packet a build writes names the packets its recipe lists, and `packet_version` gains a
meaning: the major version changes where a replacement is published and the minor and patch where
an amendment is. A packet's versions no longer share a root. The manifests a root retains hold one
major version's history, and R150 §5's statement that every identifier is stable across a packet's
amendments holds across the versions sharing a major version.

R32 §3 is already superseded by R150. R32 §2, applied at Part 05 §15.1, gains a ledger note that
§3.5 has an amendment keep its major version and its link. R150 §3.4's and R150 §3.5's entries gain
notes that §3.5 extends `amendment.identity_changed` and that §3.4 forbids `replaces` beside
`amends`. R32 §7 and R32 §8 are rationale and an open list, and this revision answers R32 §8's
first question.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. Part 01 states no packet identity. | None required. |
| logical prose and registry | Unchanged. The link is a manifest fact, read before any table (Part 04 §2), and no table records it. | None required. |
| physical profiles | Part 03 §8.1 takes §3.6. Part 03 §9 is unchanged: it retains superseded manifests under `manifests/` as Part 05 §15.3 has them. | `evidence/R<N>.json` names the anchor. |
| packet manifest and JSON Schemas | `registry/manifest.schema.json` declares `replaces` and `replaced_packet` and advances to 0.6.0; `registry/recipe.schema.json` declares `[packet].replaces` and advances to 0.3.0. `registry/build.py` labels the new definition for Part 04 §3's generated table and writes both vendored copies. | `registry/check.py` over the schemas and their copies; `registry/recipe.example.toml` validates with a `replaces` entry. |
| validation and import | Part 04 §§1, 3 and 10 take §§3.1–3.3 and §3.7; Part 05 §§3.1, 3.5 and 9.3 take §§3.4 and 3.7, and §§15.1, 15.2, 15.3 and 15.6 take §§3.5 and 3.6. | `evidence/R<N>.json` names each anchor. |
| extensions | Unchanged. No extension registry declares a manifest member. | None required. |
| reader, writer, validator, adapters | The writer reads each manifest the recipe names, refuses as §3.4 requires, records each item, sets a major version above every named packet sharing `[packet].id`, and takes §9.3's comparison from the recipe; an amending build carries `replaces` and keeps the major version. The validator adds `packet.replaces.major_version`, reports `packet.replaces.mismatch` for a named packet its caller supplies, and extends `amendment.identity_changed`. The reader loads a manifest carrying the member and may expose it. Adapters are unchanged: no adapter reads a manifest. | The writer and validator suites; a session packet rebuilt naming its predecessor and validated with no error. |
| conformance fixtures and tests | The negative and positive variants of §6. | `fixtures/corpus.py` and the package suites. |
| revision process and tooling | The ordinary ledger and evidence records, and the notes on R32 §2, R150 §3.4 and R150 §3.5. | `ledger.py`, `evidence.py` and `verify.py`. |
| generated publications and developer documentation | Part 04 §3's generated field table gains `replaces`; the writer's guide documents `[packet].replaces` and the version a replacing build sets; `registry/README.md`, the combined specification and the heading index follow. | `verify.py`. |

## 6. Conformance and implementation evidence

§3.1 is `applied` at Part 04 §3 and §3.2 at Part 04 §§3 and 10. §3.3 is `applied` at Part 04 §3.
§3.4 is `applied` at Part 05 §§3.1, 3.5 and 9.3, and §3.5 at Part 05 §§15.1, 15.2, 15.3 and 15.6.
§3.6 is `applied` at Part 03 §8.1 and Part 05 §15.2, and §3.7 at Part 04 §1 and Part 05 §3.1. Each is
placed by canonical anchor.

These cases distinguish the new rules from the current ones:

- a manifest at `1.0.0` naming a packet of its own `packet_id` at `0.1.0` conforms, where the
  current schema refuses the member;
- a manifest naming a packet of its own `packet_id` at an equal or greater major version, itself
  included, draws `packet.replaces.major_version`;
- a manifest naming a packet of another `packet_id` at any version conforms;
- an item carrying a location, or lacking `sha256`, draws `packet.manifest.schema`;
- a validator given a named packet whose manifest's SHA-256 differs from the item's reports
  `packet.replaces.mismatch` at `warning`, and the packet passes;
- a validator given no named packet reports nothing about the link;
- an amendment of a replacement that changes its major version, or drops or alters `replaces`,
  draws `amendment.identity_changed`, and one keeping both passes;
- an item naming a version later amended is confirmed from the retained manifest;
- a build refuses a recipe giving `replaces` and `amends`, an entry with no readable manifest, and
  two entries reading one manifest, each before any source opens; and
- a build replacing a packet of its own `packet_id` at `0.1.0` records the item and sets a major
  version of at least 1, and warns of each resource the named packet declares that it lacks.

The positive cases are a session packet rebuilt naming its predecessor and the valid corpus packet.
§2.1's retained `packet-r150` manifest, byte-identical to the manifest it superseded, establishes
that a link to an amended version can be confirmed.
