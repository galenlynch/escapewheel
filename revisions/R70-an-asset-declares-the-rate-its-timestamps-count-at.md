# R70 — An Asset Declares the Rate Its Timestamps Count At

| | |
|---|---|
| **Status** | **Accepted** 2026-09-04 |
| **Amends** | `02` (`core.media_assets`), R68 §2.4 (which it reverses) |
| **Depends on** | R68 (a presentation timestamp is an integer), R33 (a rational is two integers) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R68 made `core.media_frames.pts` an integer of the container's own time base and declined, in
§2.4, to carry that base: R3 §3.0 admits duplication only where it buys otherwise-unavailable
access, and the container declares its base to every library that opens it.

The premise is that a consumer holding a `pts` holds the file. R68 §5 recorded that as open, and
it does not hold.

### 1.1 The file is the part a packet is least likely to have

R14 §2.3 makes referencing the **expected** arrangement for large resources, and media is the
case it was written for. The measured session's three cameras are 10.6 GB as MP4 and 80 GB as
the AVI they came from, so the packet references them and owns 0.40 MB of frame timing.

A referenced resource is exactly the one a packet may not be able to reach. R36 §2.4 already
says so about digests — a writer that cannot reach a URI records nothing — and R51 builds a whole
verification level around the store answering when the bytes will not. Resting a column's
interpretation on the reachability of an external file inverts that: every other external fact a
packet needs, it copies.

### 1.2 `pts` is the only core column whose unit is neither declared nor derivable

Twenty-six columns declare a `unit`, a `unit_from` or a `clock_from` (R56). `pts` declares none,
and cannot: its unit varies per asset, so `unit` is wrong, and `unit_from` names a column, which
the packet does not have.

The value is therefore a bare integer whose scale is stated nowhere in the packet — the state
R56 §1 describes for `core.clock_anchors.parent_tick` before it was fixed, arrived at again by a
different route.

### 1.3 A rule cannot see into a JSON string

The writer records the base in `core.media_assets.metadata` today, which is where `09` §3 puts
what is not queried. R66 §1.4 gives the reason that is not enough here, and it applies unchanged:
a value inside a JSON string is unavailable to a Tier 2 rule, so nothing can check that an asset
whose frames carry `pts` said what those timestamps count.

Measured across the packet, all three timed assets carry the base and the fourth carries none,
which is correct — and no check would have noticed had one been missing.

## 2. Decision

### 2.1 Two columns

`core.media_assets` gains:

| column | type | presence | role |
|---|---|---|---|
| `pts_rate_num` | `int64` | nullable | `data` |
| `pts_rate_den` | `int64` | nullable | `data` |

Together they give the **exact rational rate** the container counts presentation timestamps at,
in timestamps per second: a container time base of 1/16000 s is `16000` over `1`.

Rational rather than a float, for R33's reason and in the shape `core.clocks.tick_rate_num` and
`tick_rate_den` already use — a base of 1/90000 has no exact decimal, and a rounded one
accumulates over the millions of frames a session holds. A rate rather than a period, so that a
consumer who has read `core.clocks` needs no second convention; a writer reading `1/16000` from a
container inverts it once, at the boundary.

No third column restates the rate as a float. `core.clocks.tick_rate_hz` exists because `02`
declared it before R4 made the rational conditional; a new declaration would only be duplicating
what R3 §3.0 refuses.

### 2.2 Present when the frames are

A writer that writes `pts` for an asset's frames **MUST** declare both columns for that asset,
and **MUST** declare neither where it did not.

Declaring one alone is an error, checked as Tier 2 — the same shape as
`core.clocks.transform_pair_complete`, and for the same reason: half a rational is not a smaller
statement, it is an unusable one.

### 2.3 What a consumer may then do

A consumer **MAY** convert a frame's presentation timestamp to seconds of the asset's own
timeline as `pts * pts_rate_den / pts_rate_num`, without opening the media.

That is seconds **within the asset**, not a time on any clock the packet declares. R68 §2.5
stands unchanged: `t_tick` is the frame's time, and `pts` MUST NOT be compared between assets or
used to measure elapsed experimental time.

### 2.4 R68 §2.4 is reversed

The base is carried in core. R68 §2.4's argument from R3 §3.0 fails on its own terms — the access
it called available is available only while the referenced file is reachable, which is the one
thing a reference does not promise.

`core.media_assets.metadata` keeps whatever else a writer records about the container. What moves
out of it is the one field something now needs to check.

## 3. What this does not change

- **No new table, no new reference, no vocabulary.** Two nullable columns.
- **No packet becomes invalid.** Both are nullable; a packet gains them on its next rebuild.
- **No change to `core.media_frames`.** `pts` stays `int64`, nullable, role `data`.
- **No change to what `pts` holds.** R68 §2.2's verbatim rule is untouched; this says what the
  units are, not what the number is.

## 4. Open

- **R56 has no rational form.** `pts` still declares no `unit_from`, because R56 §2.1 names a
  single column holding a unit and this unit is two integers. Naming one half would be worse than
  naming neither. This is the first core column to want a rational unit, which is one case: the
  fix is a revision to R56 when a second appears, not a mechanism built for one.
- **Whether a container's timeline should be nameable at all.** R68 §2.3 rules out a
  `core.clocks` row, and these columns give the rate without giving the thing an identity. A
  consumer wanting to say *which* timeline two assets share has no way to; nothing has asked.
