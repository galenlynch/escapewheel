# R68 — A Presentation Timestamp Is an Integer

| | |
|---|---|
| **Status** | **Accepted** 2026-09-04 |
| **Amends** | `02` (`core.media_frames.pts`) |
| **Depends on** | R45 (a coordinate is copied verbatim), R14 §2.3 (media is referenced) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

`02` gives `core.media_frames.pts` the type `float64` and the description *"Media presentation
timestamp if relevant."* Neither says which quantity it holds.

### 1.1 One clause, two quantities

A container offers its frame timestamps two ways, and both answer to the name. Measured on one
behaviour video:

```
$ ffprobe -select_streams v:0 -show_entries packet=pts       -of csv=p=0 bottom_camera.mp4
32
64
96

$ ffprobe -select_streams v:0 -show_entries packet=pts_time  -of csv=p=0 bottom_camera.mp4
0.002000
0.004000
0.006000
```

The first is the container's own integer timestamp, in a time base the file declares — here
1/16000 s. The second is that value in seconds. PyAV presents the same split as `packet.pts` and
`frame.time`.

The declared type argues for the second: an integer domain does not need a float to hold it. So a
writer following `02` reasonably stores seconds, and a writer following the container reasonably
stores 32 — under one column name, with nothing in either packet saying which. A consumer holding
two packets cannot tell a count from a duration, and the two differ by a factor the packet does
not carry.

### 1.2 The recorded value is an integer, and the derived one is the float

Every container format that has this concept defines it as an integer: ISOBMFF stores media times
as unsigned integers against a declared timescale, Matroska stores integer ticks scaled by
`TimestampScale`, and libav exposes `AVPacket.pts` as `int64_t`. Seconds are computed from that
integer and the time base; nothing stores them.

R45 settles the analogous case for a clock, and the reasoning transfers without change:

> A writer MUST NOT re-base a source's sample index, and a reader MUST NOT assume any base beyond
> what `origin` declares.

What that prohibition buys, R45 says, is exactness. A presentation timestamp is the same kind of
value — a coordinate on the container's own axis, in the container's own units — so converting it
on the way in is the loss R45 refuses. At the 1/16000 base measured here the seconds happen to be
exact; at MPEG-TS's 1/90000 they are not, so two consumers computing them agree only to
floating-point rounding, on a value the file states exactly.

The 53-bit mantissa is not the argument. A `float64` holds every integer below 2^53, which at a
nanosecond time base is 104 days of video, so nothing measurable is lost today. What is wrong is
the kind: the type says *real number* where every source says *integer*, and that is the only
statement in the packet about which of §1.1's two quantities the column holds.

### 1.3 What it costs, measured

Three cameras of one session, 7,570,450 rows, zstd level 3 throughout, each variant written over
the same row groups:

| `pts` as | encoding | `pts` | whole table |
|---|---|---:|---:|
| `float64` | `RLE_DICTIONARY` | 11.371 MB | 11.73 MB |
| `float64` | `BYTE_STREAM_SPLIT` | 0.273 MB | 0.66 MB |
| `int64` | `DELTA_BINARY_PACKED` | 0.043 MB | 0.43 MB |

The first row is what a packet is written with today, where `pts` is **96.9%** of the table:
dictionary encoding is what a column that declares nothing else receives, and 7.5 M distinct
monotonic values are its worst case. Most of that gap belongs to the writer and closes without a
revision, which is why this is the confirming measurement rather than the argument.

What the type decides is the floor. `DELTA_BINARY_PACKED` is defined for `INT32` and `INT64` only,
and a frame timeline advancing by a constant step is what it exists for; the best a `float64` can
reach is `BYTE_STREAM_SPLIT`, at **6.3x** the size. The type forecloses the encoding.

## 2. Decision

### 2.1 The type

`core.media_frames.pts` becomes **`int64`**. It stays nullable, and stays R48 role `data`.

### 2.2 What it holds

`pts` holds the container's own presentation timestamp for this frame, in the container's own time
base, **verbatim**. A writer **MUST NOT** rescale it — not to seconds, not to a clock's ticks, not
to a frame number — and **MUST** leave it null where it did not read the container's timestamps.

### 2.3 It is not a coordinate, and the reason is structural

`pts` looks like R48's `coordinate` role and **MUST NOT** be declared one. R56 §2.2 resolves a
coordinate's clock, absent `clock_from`, to the table's own `clock_id` — which on
`core.media_frames` is the clock `t_tick` is on, and `pts` is not on it. Declaring the role would
make a conforming reader convert `pts` on the rig's clock and get a number that is wrong without
being detectably wrong.

Nor is a container's timeline a `core.clocks` row. A clock in this format joins a graph that must
be well-founded (R27 §3), declares its parent, and carries observation intervals belonging to it
(R38); a file's internal addressing has none of that, and its relation to the rig clock is what
`t_tick` records per frame rather than anything a transform could express — the frame drops R14's
external media are subject to are exactly what a linear map cannot carry.

### 2.4 The time base is not carried in core

R3 §3.0 admits duplication only where it buys otherwise-unavailable access, and the container
declares its own time base to every library that opens it. A consumer holding a `pts` holds the
file the value indexes into.

A writer **MAY** record the base in `core.media_assets.metadata`, where `09` §3 puts what is not
queried. What is worth recording beside it is which container the value came from, since a media
asset may reference more than one rendering of one capture.

### 2.5 What a consumer may then do

A consumer **MAY** pass `pts` verbatim to a container library to seek the frame a row describes.

A consumer **MUST NOT** compare `pts` between two media assets: two files declare two time bases
and two origins, and neither is a time on any clock this packet declares.

A consumer **MUST NOT** use `pts` to measure elapsed time or to align a frame to anything else in
the packet. `t_tick` is the frame's time, on a declared clock, and it is the column that relates a
frame to a spike.

## 3. What this does not change

- **No new column, no new table, no reference.** One type changes.
- **No writer gains an obligation.** The column stays nullable, so a writer with nothing to put
  there still writes nothing.
- **No change to `frame_index`, `t_tick` or `dropped`.**
- **No new rule.** Nothing checkable in SQL follows: a container's `pts` may be negative (an edit
  list or encoder delay puts it there), so there is no bound to test.

## 4. Migration is regeneration

A packet carrying a `float64` `pts` does not conform, and is rebuilt rather than converted, for
R53 §5's reason.

Converting in place would be unsound here in a way R53's identifiers were not. A stored float is
either container units or seconds, §1.1's whole point is that the packet does not say which, and
the two round to integers that differ by the time base. A migrating writer that cannot re-read the
container **MUST** write null rather than convert what it finds.

## 5. Open

- **What order `frame_index` is in.** `pts` locates a row's frame in the file; nothing says which
  frame is index 0, or whether the numbering follows presentation order or decode order. Both
  columns come from the same read and a writer that has one has the other, so this is a gap rather
  than a conflict — but a rule that `pts` is non-decreasing in `frame_index` cannot be written
  until it is settled, and a container with B-frames is exactly where the two orders diverge.
- **Whether an unreachable asset needs its time base after all.** §2.4 rests on the consumer being
  able to open the file. A packet whose media has moved cannot convert `pts` to seconds of video
  from anything it holds, and whether that is worth two columns depends on a consumer wanting
  seconds of video at all, which `t_tick` has so far always answered better.
