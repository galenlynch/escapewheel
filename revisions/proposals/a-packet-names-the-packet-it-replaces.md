# A packet names the packet it replaces

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-29 |
| **Based on** | `7687b1caa6a1a71cab66aa3ae4e176afb45c1adf` |
| **Decision domain** | specification |
| **Affects** | Part 04 §3's manifest fields and the incorporated manifest schema; Part 05 §9.3's comparison against a prior packet, §15.1's `packet_version` and §15.2's statement of a correction; Part 03 §8.1's statement of a correction; the recipe schema Part 05 §3.1 incorporates |

## 1. Problem

A packet follows another in one of two ways. An amendment (Part 05 §15) publishes a new version of
the same packet at the same root: it keeps `packet_id`, sets a `packet_version` sorting after the
superseded one, and retains every superseded manifest, so the packet records its own history. A
rebuild runs a recipe and publishes a packet at a new root, and records nothing of the packet it
follows. A correction can only be a rebuild, since no amendment changes a canonical row, and so can
an addition no amendment may make.

Nothing gives a rebuild an identity of its own. A recipe names the packet it builds and a writer
sets the version, so a rebuild from the same recipe publishes a second packet under its
predecessor's `packet_id` and `packet_version`. A reference held outside a packet names it by those
two values, and after a rebuild they name two packets whose rows and identifiers need not agree.
Neither packet says how it relates to the other. Part 05 §9.3 asks an import that "replaces an
existing packet" to report the resources it dropped, and nothing states which packet an import
replaces.

The parts also disagree about what a correction is. Part 05 §15.2 says a packet whose core data was
wrong "is a new packet, not a new version of an old one"; Part 03 §8.1 says "A correction is a new
packet version, not an edit."

## 2. Evidence

### 2.1 Successive builds share one identity

The development builds of the two session packets were read from their manifests: six builds of
`ecephys_786867_2025-09-25` and five of `ecephys_776259_2025-04-09`. Every build carries its
session's name as `packet_id` and `0.1.0` as `packet_version`, which the reference writer sets for
every build. The first session's six builds bind four core registry versions, 0.1.0, 0.7.0, 0.8.0
and 0.9.0, and each build's manifest has its own SHA-256 digest.

Successive builds hold different content. Comparing the resource digests recorded in consecutive
builds' manifests:

| builds | first session: changed, dropped, added | second session: changed, dropped, added |
|---|---|---|
| `packet-p9` to `packet-wf` | 3, 0, 0 of 58 | 4, 0, 0 of 56 |
| `packet-wf` to `packet-r146` | 2, 0, 0 | 3, 0, 0 |
| `packet-r146` to `packet-r147` | 8, 1, 1 | 6, 0, 1 |

`core.units` and `core.intervals` keep one digest across these four builds of each session, so
these rebuilds kept every unit and interval identifier, and nothing in either packet says so. A
rebuild can also renumber. Under R148, a rebuild adding
a kind of interval that sorts before the trials moves every trial's identifier, as §2.2 of the
proposal `an-amendment-adds-groups-of-rows-a-packet-lacks` measured, and the rebuild still carries
the same `packet_id` and `packet_version`.

### 2.2 Nothing records the packet a build replaces

The manifest's members are closed (Part 04 §3), and none names another packet. The recipe's
`packet.id` is "The packet this recipe builds", and no recipe member names a packet the build
follows. The reference writer's `import` compares its result with a packet its caller names and
warns of each resource the result lacks, as Part 05 §9.3 asks. The packet it compared against
appears nowhere in the result.

### 2.3 Provenance

R32 §3 made a corrected packet a new packet rather than a new version, because a result derived from
the old core would be invalidated where nothing detects it. Part 03 §8.1's sentence descends from the
frozen v0.1 text, which sent a correction to "a new packet release or new resource version". R32 §7
left release semantics open, and R32 §8 left open whether `packet_version` means anything beyond
ordering. The reference writer's amendment increments the patch level, and its documentation says
nothing rests on the choice.

## 3. Desired outcome and constraints

A resolution lets a packet name each packet it replaces, and lets a reader tell from a packet
whether identifiers held against an earlier one still hold. It meets these constraints:

- the name identifies one publication, even where two share a `packet_id` and `packet_version`, as
  the builds of §2.1 do;
- a packet conforms whether or not a packet it replaces can be reached, and names it without
  locating it, as Part 04 §5.5 keeps a source's name apart from its location;
- a reader holding both packets can confirm the link;
- the parts state one meaning of a correction; and
- an amendment is unchanged apart from carrying the link.

## 4. Options and tradeoffs

For the link:

| option | effect |
|---|---|
| keep today's rules | a rebuild repeats its predecessor's identity, a reference by `packet_id` and `packet_version` names several packets, and §9.3's replaced packet stays undefined |
| name it by `packet_id` and `packet_version` | every build of §2.1 is named ambiguously, since all share both values |
| name it by location | a location is not an identity (Part 04 §5.5), so a moved or mirrored packet breaks the link |
| name it by `packet_id`, `packet_version` and the SHA-256 digest of its manifest (preferred direction) | the digest distinguishes packets sharing both names, and lets a reader holding the replaced packet confirm it; nothing needs the replaced packet to be reachable |

For a replacement's own identity:

| option | effect |
|---|---|
| a replacement takes a new `packet_id` | `packet_id` and `packet_version` name one publication, and a packet's versions are exactly its amendments; a dataset's packets share no name, so a recipe changes its `packet.id` at every rebuild, which none of §2.1's recipes did, and finding the current packet means following links forward from the old one, which the old one cannot record |
| a replacement keeps `packet_id` and takes a greater major version (preferred direction) | `packet_id` names the dataset across rebuilds and `packet_version` orders every publication of it; the major version changes exactly where identifiers may change, so a reference held against one major version holds for its amendments; the greatest version is current; a packet's versions span roots |

Dataset repositories draw the same line. A Zenodo record has a concept DOI naming every version, and
the DataCite metadata schema relates versions by `IsNewVersionOf` and `IsPreviousVersionOf`.

Under the preferred direction a packet names each packet it replaces, by `packet_id`,
`packet_version` and the SHA-256 digest of its manifest, and names none by location. It may name
several: Part 00 §3.3 permits a packet to hold several sessions, and such a packet can replace the
single-session packets it merges. Where a packet keeps the `packet_id` of a packet it names, its
major version exceeds that packet's. An amendment keeps its packet's major version and carries the
link unchanged. A correction is a replacement, which reconciles Part 05 §15.2's "new packet" with
Part 03 §8.1's "new packet version".

The work falls to a recipe and three actors:

- a recipe names each packet its build replaces, by where the writer can read it;
- a writer reads each named packet's manifest, records the three values, sets the version, and makes
  Part 05 §9.3's comparison against the packets named;
- a validator checks from the manifest alone that a named packet sharing the `packet_id` has a
  smaller major version; and
- a reader or validator holding a named packet may confirm its digest, and reports a mismatch
  against the link without preferring either, as Part 04 §5.5 has a reader do for a source.

A link runs backward only. A replaced packet is immutable and cannot record what replaced it, so a
reader holding only the old packet cannot learn that it was replaced. A catalog holding both can,
and under the preferred direction the current packet is the greatest version of its `packet_id`.

The cost is that `packet_version` gains a meaning, and a packet's versions no longer share a root:
the manifests a root retains (Part 05 §15.3) hold one major version's history rather than the
packet's. Nothing but the recipe keeps two independent rebuilds of one packet from publishing the
same version, just as nothing keeps two amendments from doing so (R32 §7).

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. Part 01 states no packet identity. |
| logical prose and registry | Unchanged. The link is a manifest fact, read before any table (Part 04 §2), and no table records it. |
| physical profiles | Part 03 §8.1's sentence on corrections cites the replacement rule. Part 03 §9 is unchanged. |
| packet manifest and JSON Schemas | Part 04 §3 gains an optional member naming the replaced packets and states its meaning, and the manifest schema declares it. The recipe schema Part 05 §3.1 incorporates gains a member naming the packets a build replaces. |
| validation and import | Part 05 states what a replacement is and its major-version rule. §9.3 compares against the packets a recipe names, §15.1 has an amendment keep its major version and the link, and §15.2's correction becomes a replacement. The proposal `an-amendment-adds-groups-of-rows-a-packet-lacks` states that identifiers are stable across a packet's amendments, which are then the versions sharing a major version. |
| extensions | Unchanged. |
| reader, writer, validator, adapters | The writer reads each named manifest, records the link, sets the version, and compares against the named packets; today it compares against a packet its caller names, records nothing, and sets 0.1.0 for every build. The validator checks the major-version rule and, holding a named packet, its digest. A reader may expose the link. Adapters are unchanged. |
| existing packets | They conform unchanged, since the member is optional. The field test's builds would name the builds they replace. |
| conformance fixtures and tests | A manifest naming a packet of its own `packet_id` at a smaller major version conforms, and one at an equal or greater major version draws a finding. A named packet whose manifest digest differs draws the mismatch report where the validator holds it. A writer test compares against the packet its recipe names. |
| revision process and tooling | Unchanged. |
| generated publications and developer documentation | Part 04 §3's generated field table gains the member, and the writer's guide documents the recipe member. |

## 6. Open questions

1. **Does a replacement keep `packet_id`, or take a new one?** Resolved 2026-09-29: it keeps
   `packet_id` and takes a greater major version (§4). `packet_id` then names the dataset as every
   recipe in §2.1 already uses it, and the version says both which publication is current and where
   identifiers may have changed.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [x] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.
