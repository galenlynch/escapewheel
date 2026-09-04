# R69 — A Frame Index Is Presentation Order

| | |
|---|---|
| **Status** | **Proposed** 2026-09-04 |
| **Amends** | `02` (`core.media_frames.frame_index`), answering R68 §5's first open question |
| **Depends on** | R3 §6 (a structural index is a 0-based offset), R48 (a column declares a role) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

`02` describes `core.media_frames.frame_index` as *"Frame index."* R48 gives it the role
`structural_index`, and R3 §6 pins what that means:

> **Structural indices** address positions in a stored resource. These MUST be 0-based offsets.
> Clients converting to 1-based languages MUST convert at the boundary.

The base is settled. The sequence is not, and a media asset is the one stored resource in this
format that has more than one.

### 1.1 A container stores its frames in an order it does not display them in

Measured on a behaviour video from `ecephys_786867` — h264, `has_b_frames=2`:

| demuxed packet | 1st | 2nd | 3rd | 4th | 5th | 6th | 7th | 8th |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `pts` | 32 | 160 | 96 | 64 | 128 | 288 | 224 | 192 |
| position when displayed | 0 | 4 | 2 | 1 | 3 | 8 | 6 | 5 |

Each mini-GOP's predicted frame is stored before the three bidirectional frames that display ahead
of it, so a packet sits up to **three positions** from where it is shown. Over the first 2,000
packets the displacement takes four values and never exceeds three.

At the 500 Hz this session recorded, three frames is **6 ms**. A consumer that numbered rows in
storage order would attach each frame's time to a picture up to 6 ms away, and every row would
still carry a plausible, monotonic time — the error does not announce itself.

### 1.2 Which order a consumer gets follows from the library, not from the packet

PyAV's `container.decode()` yields frames in presentation order, because a decoder reorders
internally before handing anything back. `container.demux()` yields packets in storage order.
Both are the obvious loop to write, they disagree, and nothing in a packet says which one the
writer used.

### 1.3 Presentation order is what the question means

Someone who asks for the nth frame is asking for the nth picture displayed — the frame a player
lands on when scrubbed there. Storage order records how a codec arranged its dependencies, and
answers no question anyone asks of a recording.

The packet's own columns already assume it. `t_tick` is when the exposure happened, which orders
by display; `pts` is the container's presentation timestamp, which is monotonic in presentation
order and in no other.

## 2. Decision

### 2.1 The order

Row `frame_index = n` describes the frame the asset presents **nth**, counting from 0.

A writer **MUST** number frames in presentation order — for a container carrying presentation
timestamps, ascending `pts` — and **MUST NOT** number them in storage order, demux order, or any
other order the container's bytes happen to be in.

### 2.2 What is indexed is the asset, not the capture

`frame_index` counts the frames the referenced media **holds**. A frame the capture produced and
the asset does not — dropped by the host before writing, lost in a transcode — gets no row, and no
index is reserved for it.

Measured: `bottom_camera.mp4` holds 2,520,203 frames and the packet carries 2,520,203 rows for it.
What went missing stays visible in the columns that record it rather than in gaps in the index —
`pts` steps by 224 instead of 32 where a transcode lost six frames, `t_tick` steps by 26,812 ticks
(0.858 s) where the host lost about 429 exposures, and `dropped` marks the row after each.

A consumer **MUST NOT** read `frame_index` as a count of exposures, a camera's own frame counter,
or an offset into anything but this asset.

### 2.3 The rule this makes writable

`core.media_frames` gains one Tier 2 rule at level `error`: within an asset, `pts` **MUST** be
strictly increasing in `frame_index` order.

```sql
SELECT media_asset_id, frame_index, pts, prev AS previous_pts
FROM (
  SELECT media_asset_id, frame_index, pts,
         LAG(pts) OVER (PARTITION BY media_asset_id ORDER BY frame_index) AS prev
  FROM core_media_frames
  WHERE pts IS NOT NULL
)
WHERE prev IS NOT NULL AND pts <= prev
```

Nulls are excluded rather than ordered, since `pts` is nullable and an asset whose container had no
timestamps says nothing about order either way.

The rule is unwritable without §2.1: it is satisfied by presentation order and violated by storage
order, so before this revision it would have been testing a requirement nothing had made.

Run against the measured packet it returns **0 rows in 0.21 s** over 7,570,450 frames. Run against
the same rows renumbered out of `pts` order it returns 2,347 of 5,000, which is the check earning
its place — a rule nothing can fail is a rule that has not been shown to test anything.

### 2.4 What a consumer may then do

A consumer **MAY** treat `frame_index` as the ordinal a player counts, converting to 1-based at
the boundary as R3 §6 requires of every structural index.

A consumer **MAY** seek to a row's frame by passing its `pts` to a container library verbatim,
which is the exact route and needs no assumption about ordering at all.

## 3. What this does not change

- **No column, no type, no reference.** One statement of meaning and one rule.
- **No packet on hand becomes invalid.** Every asset in every packet built satisfies §2.3.
- **`dropped` is unchanged**, and still marks a row with something missing before it from either
  cause.
- **Independent of R68.** The rule holds whichever type `pts` has; the two revisions may be
  accepted in either order or one without the other.

## 4. Open

- **An asset with reordering and no timestamps.** A stream without bidirectional frames has one
  order, so the question does not arise; a stream that has them and carries no `pts` cannot be
  numbered by §2.1's operational test, and §2.3 excludes it from the check. No such asset has been
  met, and inventing a rule for one would be guessing at what a writer could see.
