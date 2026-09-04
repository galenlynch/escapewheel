# R49 — A Scope Names What Kind of Thing It Is

| | |
|---|---|
| **Status** | **Accepted** 2026-09-02 |
| **Amends** | R41 §2.3 (`core.preferred_runs`), R44 §2.1 (`core.processing_runs.scope`), R44 §3 (no validation of the referent) |
| **Depends on** | R8 (open vocabularies), R41 (currency), R44 (a run declares its scope) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

`scope` says what a run or a preference is *about*: R41 §2.3 defines it as *"a `probe_id`, an
`array_asset_id`, a camera name — or the `session_id` itself where the preference is
session-wide."* One row names a probe, the next an array asset, the next a session.

**The value is an identifier whose table the packet does not say.** Both revisions saw the
consequence and accepted it:

> No validation of the scope's referent. `scope` names a probe, an asset or a camera, so no single
> foreign key covers it — the same reason R41 §2.3 left it a plain string. — R44 §3

That leaves three things undone. A consumer resolving a scope has to **guess** which table to look
in, and guessing by value is unsound the moment a probe and a device share a name. A validator
cannot check the referent at all, so a preference naming a probe that does not exist is
conforming. And the primary key `(session_id, activity_type, scope)` collides if two different
kinds of thing carry the same identifier.

The database answer to this shape is a **discriminator**: a second column saying which kind, so
the pair is resolvable and each kind is checkable on its own. That is what R41 declined by
choosing a plain string, and it costs nothing to adopt now — **no packet carries a `scope`**, and
`core.preferred_runs` has never been written.

## 2. Decision

### 2.1 `scope` becomes a pair

`core.processing_runs` and `core.preferred_runs` each gain `scope_kind`, beside the existing
`scope`. `since: R49`.

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `scope_kind` | string | see §2.4 | The resource whose primary key `scope` holds, as a dotted resource ID — `core.probes`, `core.array_assets`, `core.sessions`. Open (R8 §4). |

`scope` is unchanged in type and meaning: the primary-key value of the thing named.

### 2.2 The kind is a resource ID, not a short name

`scope_kind` holds `core.probes` rather than `probe`. This is what makes a scope resolvable
**generically**: the registry gives the named resource's primary key, so a consumer reads the
kind, looks up the key column, and resolves — with no mapping table and no knowledge of what
kinds exist.

That is the property R41 §1 wanted and could not have. An R17 extension scoping a run to one of
its own tables writes that table's resource ID, and a consumer resolves it by the same rule
without the core registry knowing the extension.

`scope_kind` is **open**, like `activity_type`. A value naming no declared resource means the
scope is something the packet does not carry — R41's camera, where no device row exists — and a
consumer MUST treat it as opaque rather than as an error.

### 2.3 The primary key gains the kind

`core.preferred_runs`'s primary key becomes `(session_id, activity_type, scope_kind, scope)`.

Without it, a probe and a device sharing an identifier would collide on one preference row. The
pair is the address; half of it is not.

R44 §2.2's ambiguity rule reads on the pair correspondingly: a session has more than one run for
the same `(activity_type, scope_kind, scope)`.

### 2.4 Presence, and the third state

On `core.preferred_runs`, `scope_kind` is **required**: R41 §2.3 required `scope`, and half an
address is no better than none.

On `core.processing_runs` it is **nullable**, matching `scope` under R44 §2.1, and the two MUST
agree — a run declares both or neither. A run declaring neither is *undeterminable* under
R44 §2.3, unchanged. A run declaring one but not the other is an error, since the pair is what
carries the meaning.

### 2.5 The referent becomes checkable

**Strike** R44 §3's *"No validation of the scope's referent."* A Tier 2 rule per named kind is now
possible and SHOULD be provided: for each `scope_kind` that names a declared resource, `scope`
MUST be a value of that resource's primary key. A `scope_kind` naming no declared resource is
skipped rather than failed, per §2.2.

This is Tier 2 rather than a `references` entry because the target varies by row and `references`
names exactly one resource — which is the same reason the pair was needed, arriving at the place
R2 §7 reserves for what structure cannot imply.

## 3. Cost

| | |
|---|---|
| packets carrying `core.processing_runs.scope` | **0** |
| packets carrying `core.preferred_runs` | **0** |
| rows to migrate | **0** |

`scope` was added by R44 on 2026-09-02 and the writer emits it, but nothing has been rebuilt since.
The window in which this is free closes the next time a packet is written.

## 4. What this does not do

- **No change to what a scope means.** It is still what a run or preference is about; §2.1 only
  makes the packet say which kind of thing that is.
- **No change to R41's currency mechanism.** The preference is still keyed on the producing run,
  still separate from the run log, and still what a consumer must not resolve silently without.
- **No new reference.** §2.5 explains why this is Tier 2.
- **No closed vocabulary.** An open `scope_kind` is what lets an extension scope to its own
  tables (§2.2), which was R41 §1's requirement for the whole mechanism.

## 5. Open

- **Whether a resource ID is the right spelling.** A short name (`probe`) is more readable and
  needs a mapping; a resource ID is resolvable with none. The latter is chosen because the
  extension case is what the mechanism exists for, and a mapping table is exactly what an
  extension cannot add to. A packet is not read by eye often enough for the readability to win.
- **Whether the same pair should replace other polymorphic columns.** There are no others today.
  If one appears, the choice is this shape or a role saying "identifier you cannot resolve", and
  this shape is better because it resolves.
