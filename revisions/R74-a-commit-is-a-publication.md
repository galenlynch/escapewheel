# R74 — A Commit Is a Publication, Not a Rename

| | |
|---|---|
| **Status** | **Accepted** 2026-09-04 |
| **Amends** | Part 05 §? (the commit sequence), R32 §2 (how a new version becomes visible) |
| **Depends on** | R14 §2.3 (packet-owned bytes are immutable), R32 (amending a committed packet) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

Part 05's commit sequence ends *"rename the candidate to `packet.json` **last**"*. The rename is
what makes a commit atomic: a reader sees the previous catalog or the new one, never a catalog
naming resources still being moved.

The invariant is right. Naming the mechanism as the requirement is not.

### 1.1 The profile permits a store that has no rename

Part 03 allows a packet to live under an object-store prefix, and Part 04 binds resources by URI rather
than by path. An object store has no atomic directory rename: S3's "rename" is a copy followed by
a delete, which is neither atomic nor cheap, and a packet whose catalog is renamed that way has a
window in which no catalog exists at all.

What such a store does have is an atomic single-object write. `packet.json` is a single
object, so the invariant is reachable — by a different primitive than the one Part 05 mandates.

### 1.2 The requirement is stated one level too low

A writer targeting S3 cannot comply with Part 05 as written and can satisfy everything Part 05 wanted.
That is the signature of a specification naming an implementation where it meant to name a
guarantee.

## 2. Decision

### 2.1 The guarantee

> A commit becomes visible when the packet catalog is **atomically published** at the packet's
> catalog location.
>
> Every packet-owned resource the catalog names **MUST** already be at its final location and
> **MUST** have passed validation before the catalog is published.
>
> A reader **MUST** observe either the previously committed catalog or the newly published one,
> and **MUST NOT** observe a catalog naming a resource that is not yet in place.

### 2.2 The mechanism is the profile's

The publication primitive is profile-specific and this standard does not name one. A filesystem
profile **MAY** publish by atomic rename within one directory; an object-store profile **MAY**
publish by a single-object write. A writer **MUST NOT** be required to perform an atomic
**directory** rename, which is the operation Part 05 assumed and which no object store offers.

### 2.3 Concurrent publication

Where the store offers a conditional write — a compare-and-set on the catalog object, or a
rename that fails when the destination exists — a writer publishing a new version **SHOULD** use
it, so that two writers cannot silently overwrite one another's head.

Where the store offers none, a writer **MUST NOT** claim it detected a conflict it could not
detect. R32 §4's retained manifests are what let the loss be found afterwards; they are not a
substitute for the conditional write.

### 2.4 Staging is unchanged

Part 05's staging discipline stands in full: validation is importation, staged resources MUST NOT
appear as committed canonical resources, and nothing is published until validation has passed.
This revision changes the last step of the sequence and no other.

## 3. What this does not change

- **No change to the local implementation.** An atomic rename within one directory satisfies §2.1,
  which is what `PacketWriter.commit` already does.
- **No change to immutability.** R14 §2.3 covers the bytes; this covers when they become visible.
- **No new field.** The catalog's location and name are unchanged.
- **No requirement to support object stores.** A profile that publishes only to a filesystem is
  conforming; §2.2 stops the standard from foreclosing the other case.

## 4. Open

- **What a reader should do with a catalog it cannot read atomically.** A store with read-after-
  write consistency makes §2.1 observable; one with eventual consistency can serve a stale catalog
  naming resources that do exist, which is harmless, or a new one whose resources it cannot yet
  list, which is not. No profile in this specification targets such a store, and naming the
  behaviour for a store nobody uses would be guessing.
