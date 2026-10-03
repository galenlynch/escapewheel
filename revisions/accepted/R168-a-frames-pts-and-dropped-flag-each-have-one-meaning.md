# A frame's pts and dropped flag each have one meaning

| | |
|---|---|
| **Status** | **Accepted** 2026-10-02 |
| **Opened** | 2026-10-02 |
| **Based on** | `04da4ef50a6e4066520778be78eaeedce41e7804` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 01 §3.18; Part 02 §9.2; Part 08 §2; Part 08 §3; the core registry |
| **Depends on** | R69 §2.1 (the presentation order this keeps); R69 §2.2 (the frames an index counts, which this replaces in part); R68 §2.2 (what a presentation timestamp holds, which this replaces in part); R69 §2.3 (the rule on `pts` order, beside which this adds one on `t_tick`); R164 §3.5 (the core registry version at the baseline) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6; §3.7 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Problem

A row of `core.media_frames` describes one frame of a media asset. Part 01 §3.18 states what its
`frame_index`, `t_tick` and `pts` mean, and R69 settled the order its index counts in. Two of the
row's values still admit more than one reading, and one property every frame's time has goes
unchecked.

### 1.1 A container's presentation timestamp depends on its edit list

Part 01 §3.18 makes `pts` the container's own timestamp, "an integer in the container's own time
base, verbatim". An MP4 file can carry an edit list, which maps the timeline its samples are stored
on to the timeline it presents. A library that applies the edit list and one that ignores it report
different integers for the same frame, both read verbatim from the same file, so "verbatim" names no
single value. A consumer that seeks with a stored `pts` through a library making the other choice
lands on the wrong frame.

The same list decides which frames an asset has. Part 01 §3.18 has the index count the frames the
asset "holds", and R69 §2.1 makes index *n* the frame the asset presents nth. A stored frame that
the edit list excludes is held and never presented, so the two sentences disagree about whether it
gets a row.

### 1.2 Nothing states what `dropped` means

The registry describes `dropped` as "Dropped-frame flag." and gives it three values: true, false and
null. Part 01 §3.18 says what went missing "is recorded in the frames' timing", and does not name
the column. Only R69 §3, outside its Decision, says the flag "marks a row with something missing
before it from either cause". No text says what false claims, what null claims, or whether a loss
before the first frame counts. A consumer reading false cannot tell a writer that checked from one
that wrote a default.

### 1.3 A frame's time may run backwards without a finding

R69 added a check that `pts` increases in `frame_index` order. Nothing checks the same of `t_tick`,
so a writer that numbers frames in presentation order but times them from a list in another order
produces rows that pass every check. The `frame_index` description is "Frame index.", which states
nothing Part 01 §3.18 gives it.

### 1.4 Why the change is structural

The Decision revises sentences of Part 01 §3.18 in place: the index counts presented frames rather
than held ones, and the presentation timestamp is read on the presentation timeline rather than
"verbatim". An appended subsection would leave §3.18 stating both readings. Part 02 §9.2 restates
the core registry version.

### 1.5 Structural crosswalk

Every amended section already carries a canonical anchor, so no bootstrap is needed. No section
moves, splits, merges or retires.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 01 §3.18, the index counts the frames the asset holds | replace in place | same section | the asset's frames are those it presents; an excluded stored frame has no row, and a repeated one has a row per presentation | §3.1 |
| Part 01 §3.18, the presentation timestamp is the container's, verbatim | replace in place | same section | the timestamp is the frame's time on the container's presentation timeline | §3.2 |
| Part 01 §3.18, what went missing is recorded in the frames' timing | extend in place | same section | the capture is defined, and the flag's three values state what the writer knows of a loss | §3.3 |
| Part 01 §3.18, a frame's time is a tick on a declared clock | extend in place | same section | a frame's tick does not decrease in presentation order on one clock | §3.5 |
| Part 02 §9.2, the core registry version | revise in place | same section | the version advances | §3.7 |
| Part 08 §2 and Part 08 §3, the example packet's core registry version | revise the informative example in place | same sections | none | none |

## 2. Evidence

Observed at the baseline commit, where the quick verifier passed all 38 of its stages. The
measurements below use the three behaviour videos of session `ecephys_786867` (h264 High,
`has_b_frames=2`, time base 1/16000) and that session's packet built on 2026-10-02 under core
`0.18.0`, the version at the baseline, read with ffprobe 8.1.3 and DuckDB.

### 2.1 Each video's edit list shifts every timestamp by 64

Each file's `elst` box holds one entry, with media time 64 in the track's 16000 Hz timescale. The
first three packets of each video, as ffprobe reports them by default and with
`-ignore_editlist 1`, are the same for all three cameras:

| | 1st | 2nd | 3rd |
|---|---:|---:|---:|
| `pts`, edit list applied | 0 | 128 | 64 |
| `pts`, edit list ignored | 64 | 192 | 128 |

The shift is two frame steps of 32. The packet's `pts` starts at 0 for all three assets, so the
writer stored the value with the edit list applied. R69 §1.1 measured an earlier transcode of the
bottom camera whose first displayed `pts` was 32, a third value for the first frame of one camera.

The edit list here only shifts the timeline: each video holds as many frames as the packet has rows
for it and as its timing file has lines (2,520,209, 2,523,521 and 2,526,738).

### 2.2 The writer's `dropped` values

| asset | frames | true | false | null | true at frame 0 |
|---|---:|---:|---:|---:|---:|
| bottom camera | 2,520,209 | 32,237 | 2,487,972 | 0 | 0 |
| left camera | 2,523,521 | 30,503 | 2,493,018 | 0 | 0 |
| right camera | 2,526,738 | 28,900 | 2,497,838 | 0 | 0 |

The AIND adapter sets the flag where the camera's own frame counter skips more than one between a
frame and the frame before it, and writes false at frame 0 without a test. On the bottom camera the
two commonest steps in `t_tick` are 62 and 63 ticks of the 31,250 Hz rig clock, all with the flag
false; the commonest flagged steps are 125 and 188, one or two periods longer. The flag therefore
carries no count, and the step in `t_tick` does.

The adapter places a video that holds fewer frames than its timing file by assuming the video's
first frame is the timing file's first exposure. Where a transcode lost the leading frames, it
cannot tell, and it still writes false at frame 0.

### 2.3 A check on `t_tick` order passes the packet and fails a reordered copy

The rule of §3.6 orders each asset's frames on one clock by `frame_index` and compares each frame's
`t_tick` with the previous one. The validator's static check of the rule language accepts it and
finds it reads `media_asset_id`, `clock_id`, `frame_index` and `t_tick`, all four declared
`required`, so it names only data guaranteed present. Its window function is the form the existing
`pts` rule already uses.

Over the packet's 7,570,468 frames it returns 0 rows in 0.23 s. No step is zero, and each asset's
frames lie on one clock. With the ticks of each adjacent pair of frame indices swapped over the
first 5,000 frames of every asset, it returns 7,500 rows, one per swapped pair.

### 2.4 No fixture covers the table

No packet in the conformance corpus holds `core.media_frames`, so neither existing rule has an
invalid case. The adapter's tests give presentation timestamps already in order and assert nothing
of `dropped`.

### 2.5 Other open work advances the same version

The other change document open at the baseline, on what a null identifier says, rewrites core
descriptions of nullable naming columns, which `pts` and `dropped` are not, and advances the
core registry version. The two share only that version and its restatements in Part 02 §9.2 and
Part 08, so §3.7 names no target and fixes no order between them.

### 2.6 Alternatives

For `pts`:

**Keep the current text.** Two conforming writers of one file can store values a constant apart,
and a consumer seeking through a library that makes the other choice lands on the wrong frame.

**The timestamp before the edit list.** It is the value stored in the sample tables, but a player
does not present it, a frame the edit list excludes would need a row, and libav reports it only
when told to ignore the list.

For a stored frame presented twice, **one row** would make the index count stored frames rather
than presented ones, against R69 §2.1, and leave the row two presentation timestamps.

For `dropped`:

**Keep the flag undefined.** A consumer cannot use false, and every writer chooses its own meaning.

**Two values, with null forbidden.** A writer whose source has no frame counter would have to claim
false or true without knowing either.

**A per-frame capture counter beside the flag.** The reviewer declined it for v0.2. `t_tick` and
`dropped` suffice to align a frame and to find a loss, and a counter is per frame, so it cannot sit
in the asset's metadata and would be a new column whose values only some sources can supply.

For the `t_tick` check:

**No check.** A writer that pairs times with frames in decode order passes every rule, and the error
is monotonic within each group of pictures, so nothing else shows it.

**Compare adjacent frames only where both share a clock.** A frame on another clock between two
frames of one clock would hide a decrease between them. Comparing each frame with the previous
frame on its own clock catches it and costs the same query.

## 3. Decision

The subsections state which frames an asset has, what a presentation timestamp is, what the dropped
flag says, the order of a frame's time, the descriptions and the rule that carry these in the core
registry, and the registry version.

### 3.1 A media asset's frames are the frames it presents

A media asset's frames are the frames it presents, in the order it presents them, and its frame
index counts these. A frame stored in the container that the container's presentation timeline
excludes is not one of the asset's frames and has no row. A stored frame the presentation timeline
presents more than once is that many frames, each with its own row and index.

### 3.2 A presentation timestamp is a time on the container's presentation timeline

A frame's presentation timestamp is its time on the container's presentation timeline, in the
container's own time base. The presentation timeline is the one the container presents after
applying any mapping it declares from the timeline its frames are stored on, such as an MP4 edit
list; where it declares none, the two coincide.

A writer that records a frame's presentation timestamp MUST record that value, and MUST NOT record
the frame's timestamp on the stored timeline where the two differ. No checker verifies this.

### 3.3 The dropped flag states what the writer knows of a loss

The **capture** of a media asset is the sequence of frames its recording device produced, as the
writer's source records it, such as the exposures a camera's frame counter numbers.

A writer MUST record a frame's dropped flag as:

- true only where it knows that the capture produced at least one frame after the asset's previous
  frame and before this one that the asset does not present;
- false only where it has determined that the capture produced no such frame; and
- null otherwise.

For the asset's first frame, these concern the frames the capture produced before it. The flag is
true whatever lost the frame, whether the recording host or a later transcode, and carries no count
of the frames lost. A consumer MUST NOT read a null flag as true or as false. No checker verifies
either.

### 3.4 Three descriptions state the frame's index, timestamp and flag

The core registry declares these three columns of `core.media_frames` with the descriptions below.
Every other field of each column stands.

| column | type | presence | role | description |
|---|---|---|---|---|
| `frame_index` | `int64` | `required` | `structural_index` | The frame's index in the order the asset presents its frames, counting from 0; not a count of exposures (Part 01 §3.18). |
| `pts` | `int64` | `nullable` | `data` | The frame's presentation timestamp on the container's presentation timeline, after any edit list, in the container's own time base and not rescaled; not a time on any clock the packet declares (Part 01 §3.18). |
| `dropped` | `bool` | `nullable` | `data` | True where the writer knows the capture produced a frame between the asset's previous frame and this one, or before the first, that the asset lacks; false where it determined none is missing; null where it could not tell. Carries no count (Part 01 §3.18). |

### 3.5 A frame's time does not decrease in presentation order

Within a media asset, a writer MUST NOT give a frame a tick earlier than the tick of a frame the
asset presents before it on the same clock. Frames may share a tick, and ticks on different clocks
are not compared.

### 3.6 A rule checks the order of a frame's time

The core registry declares this rule on `core.media_frames`:

| field | value |
|---|---|
| `id` | `core.media_frames.t_tick_nondecreasing_with_frame_index` |
| `level` | `error` |
| `message` | t_tick decreases in frame_index order among an asset's frames on one clock, so the frames are not timed in the order they are numbered |

```sql
SELECT media_asset_id, clock_id, frame_index, t_tick, prev AS previous_t_tick
FROM (
  SELECT media_asset_id, clock_id, frame_index, t_tick,
    LAG(t_tick) OVER (PARTITION BY media_asset_id, clock_id ORDER BY frame_index) AS prev
  FROM core.media_frames
) AS derived_1
WHERE prev IS NOT NULL
  AND t_tick < prev
```

### 3.7 The core registry version advances

The core registry's `registry_version` MUST advance by one minor version from the version the
incorporated registry carries when this change is incorporated. This change alters neither the
registry meta-schema, the registry-contract descriptor nor the rule language.

## 4. Questions

1. **Frames on more than one clock.** **Answered 2026-10-02: the check compares only consecutive
   frames on the same clock,** and an asset's frames are not required to share one clock. Each
   measured asset's frames lie on one clock, and `clock_id` is a per-frame column.
2. **An edit list that presents one stored frame twice.** **Answered 2026-10-02: each presentation
   gets its own row,** since each is a frame the asset presents. No measured file has such a list.
3. **One document or two.** **Answered 2026-10-02: one.** The `pts` and `dropped` decisions are
   independent, but both rewrite Part 01 §3.18's account of a frame and the same registry
   declaration, and share one core version.

## 5. Consequence

Every existing packet conforms as it did. The 786867 packet passes the new rule and stores `pts`
with the edit list applied. Its false at frame 0 is supported where the video's first frame is the
timing file's first exposure, which holds for all three of its videos. A packet binds the registry
it was built with, so an earlier packet keeps the earlier descriptions; a rebuild gains the new
descriptions, rule and core version. The specification README says that development packets are
regenerated.

An edit list that presents an earlier stretch of the capture again after later frames gives that
stretch's second presentation ticks earlier than the frames before it, so §3.5 forbids those ticks
and the rule of §3.6 reports them. Part 01 §3.18 makes a frame's timing a
recommendation, so a writer may leave such an asset's frames out. An edit list that repeats a frame
immediately gives equal ticks, which pass. No measured file has either list.

No accepted clause is superseded whole. §3.1 replaces part of R69 §2.2 and §3.2 part of R68 §2.2;
both entries keep their disposition and destination at Part 01 §3.18. §3.7 replaces the core
version that R164 §3.5 assigns beside two other identifiers, so its entry keeps its disposition.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Part 01 §3.18 takes §3.1 in place of the sentence on held frames, §3.2 in place of "verbatim", §3.3 beside the sentence on what went missing, and §3.5 beside a frame's time; §3.2's and §3.3's obligations are labelled as unchecked. | `evidence/R<N>.json` names `ew-media-asset-concept`. |
| logical prose and registry | The three descriptions of §3.4 and the rule of §3.6 change in the registry source, and the registry source and Part 02 §9.2 state the new version, as do the specification README and the two specification tools that state the version they expect. No type, presence, role, key or reference changes, and the meta-schema and registry-contract descriptor are unchanged. | The registry build and check pass, a guarded registry target names each of the three columns and the rule, and the Tier 2 rule count rises by one. |
| physical profiles | Unchanged. No storage property is involved. | None required. |
| packet manifest and JSON Schemas | Unchanged. A manifest built afterwards records a new version, path and digest in members the schema already has. | None required. |
| validation and import | The validator runs the new rule as it runs every declared rule. §§3.1 to 3.3 are not checkable, because a validator does not open the media and an asset may be referenced. | The corpus findings of §6. |
| extensions | Unchanged. No extension registry declares frames, and an extension's version advances independently (Part 09 §5.5). | None required. |
| reader, writer, validator, adapters | The AIND adapter writes null at frame 0 where its video holds fewer frames than its timing file, skips a stored frame its container excludes from presentation, and gains tests with timestamps in decode order and with asserted `dropped` values. Its design guide states the flag's meaning. Two writer tests that assert the bound core registry's version take the new value. The reader and validator read neither column. | The AIND and writer suites. |
| conformance fixtures and tests | A corpus packet holding `core.media_frames` with a valid case, and invalid cases for `frame_index_contiguous`, `pts_increases_with_frame_index` and the new rule. The corpus regenerates under the new version. | The corpus build and its expected findings. |
| revision process and tooling | The ordinary ledger and evidence records, and four guarded registry targets. No process rule changes. | `ledger.py`, `evidence.py` and `verify.py` pass. |
| generated publications and developer documentation | The rendered table listing and the combined specification regenerate. The specification README's identifier table and the sentence naming the development version are edited by hand, and Part 08 §2 and Part 08 §3 carry the new registry path as the informative example. | The framework check compares the README's table with Part 02 §9.2, and the example-packet check compares Part 08 with the packet the writer builds. |

## 6. Conformance and implementation evidence

§§3.1, 3.2, 3.3 and 3.5 are `applied` at Part 01 §3.18 by its canonical anchor. §3.4 is `registry`,
with a target on each of the three columns guarded by the column's name, and §3.6 is `registry`,
with a target on the rule guarded by its ID. §3.7 is `applied` at Part 02 §9.2 by its canonical
anchor. Part 08 §2 and Part 08 §3 follow §3.7 as the informative example and are no ledger
destination.

The new corpus packet distinguishes the rule from the baseline:

- a valid asset whose frames are numbered in presentation order, with ticks that repeat once and
  never decrease, passes every rule;
- an asset whose ticks follow decode order while `pts` follows presentation order fails the new
  rule alone, which the baseline passes;
- an asset whose frames lie on two clocks, with a decrease only between frames on different clocks,
  passes, and one with a decrease between two frames of one clock separated by a frame of the other
  fails;
- an asset whose `pts` does not increase fails `pts_increases_with_frame_index`; and
- an asset whose indices skip one fails `frame_index_contiguous`.

The meaning of `pts` and `dropped` has no negative packet, since a validator does not open the
media. It is evidenced by Part 01 and by the AIND adapter's tests: one with a video holding fewer
frames than its timing file, which writes null at frame 0; one with a complete video, which writes
false at frame 0 and true after a skip in the frame counter; and one with timestamps given in decode
order, which numbers frames in presentation order.

The measurements of §2.1 to §2.3 establish that the reference adapter's stored `pts` is the value
§3.2 names and that the new rule passes the measured packet and fails a reordered copy.
