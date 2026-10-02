# A frame's pts and dropped flag each have one meaning

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-10-02 |
| **Based on** | `c0f9214b88a2b134bf130a37abde0c396fb0b932` |
| **Decision domain** | specification |
| **Affects** | Part 01 §3.18, which states what a frame's index, time and presentation timestamp are; the core declarations of `core.media_frames.frame_index`, `pts` and `dropped`; the `core.media_frames` rules |

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

## 2. Evidence

Observed at the baseline commit, where the quick verifier passed all 37 of its stages. The
measurements below use the three behaviour videos of session `ecephys_786867` (h264 High,
`has_b_frames=2`, time base 1/16000) and that session's packet built on 2026-09-28 under core
`0.8.0`, read with ffprobe 8.1.3 and DuckDB.

### 2.1 Each video's edit list shifts every timestamp by 64

Each file's `elst` box holds one entry, with media time 64 in the track's 16000 Hz timescale. The
first three packets of `bottom_camera.mp4`, as ffprobe reports them by default and with
`-ignore_editlist 1`:

| | 1st | 2nd | 3rd |
|---|---:|---:|---:|
| `pts`, edit list applied | 0 | 128 | 64 |
| `pts`, edit list ignored | 64 | 192 | 128 |

The two side cameras give the same first value, 0 applied and 64 ignored. The shift is two frame
steps of 32. The packet's `pts` starts at 0 for all three assets, so the writer stored the value
with the edit list applied. R69 §1.1 measured an earlier transcode of the bottom camera whose first
displayed `pts` was 32, a third value for the first frame of one camera.

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
false; the commonest flagged steps are 125, 188 and 187, one or two periods longer. The flag
therefore carries no count, and the step in `t_tick` does.

The adapter places a video that holds fewer frames than its timing file by assuming the video's
first frame is the timing file's first exposure. Where a transcode lost the leading frames, it
cannot tell, and it still writes false at frame 0.

### 2.3 A check on `t_tick` order passes the packet and fails a reordered copy

The candidate check below orders each asset's frames by `frame_index` and compares each frame's
`t_tick` with the frame before it on the same clock.

```sql
SELECT media_asset_id, frame_index, t_tick, prev AS previous_t_tick
FROM (
  SELECT media_asset_id, frame_index, t_tick, clock_id,
    LAG(t_tick) OVER (PARTITION BY media_asset_id ORDER BY frame_index) AS prev,
    LAG(clock_id) OVER (PARTITION BY media_asset_id ORDER BY frame_index) AS prev_clock
  FROM core.media_frames
) AS derived_1
WHERE prev IS NOT NULL
  AND clock_id = prev_clock
  AND t_tick < prev
```

Over the packet's 7,570,468 frames it returns 0 rows in 0.39 s. No step is zero, and each asset's
frames lie on one clock. With each adjacent pair of frame indices swapped over the first 5,000
frames of every asset, it returns 7,500 rows, one per swapped pair.

### 2.4 No fixture covers the table

No packet in the conformance corpus holds `core.media_frames`, so neither existing rule has an
invalid case. The adapter's tests give presentation timestamps already in order and assert nothing
of `dropped`.

## 3. Desired outcome and constraints

- One stored `pts` per frame for a given file, whichever library a writer uses.
- A `dropped` value whose true, false and null each state something a consumer can act on.
- A check that catches frames timed in an order other than the one they are numbered in.
- The existing packets stay conforming, and R69's order and R68's integer type stay as they are.

## 4. Options and tradeoffs

### 4.1 `pts`

**Preferred direction: the timestamp after the edit list is applied.** `pts` is the frame's
presentation timestamp on the container's presentation timeline, which is the timeline after its
edit list is applied, in the container's own time base. A frame the edit list excludes is not
presented, so it is not a frame the asset presents and gets no row. This is libav's default and the
value the existing packets store.

**Keep the current text.** Two conforming writers of one file can store values a constant apart,
and a consumer seeking through a library that makes the other choice lands on the wrong frame.

**The timestamp before the edit list.** It is the value stored in the sample tables, but a player
does not present it, a frame the edit list excludes would need a row, and libav reports it only
when told to ignore the list.

### 4.2 `dropped`

**Preferred direction: three stated claims.** The **capture** is the sequence of frames the source
records the camera producing, such as the exposures a frame counter numbers.

- True states that the writer knows the capture produced at least one frame, after the asset's
  previous frame and before this one, that the asset lacks. At frame 0 it states the same of the
  frames before it.
- False states that the writer determined that no such frame exists.
- Null states that the writer could not determine it.

The flag carries no count. A consumer estimating how many frames went missing reads it from the
step in `t_tick`. A loss from either cause counts, whether the host dropped an exposure or a
transcode lost a picture, which is the reading R69 §3 gave.

**Keep the flag undefined.** A consumer cannot use false, and every writer chooses its own meaning.

**Two values, with null forbidden.** A writer whose source has no frame counter would have to claim
false or true without knowing either.

**A per-frame capture counter beside the flag.** The reviewer declined it for v0.2. `t_tick` and
`dropped` suffice to align a frame and to find a loss, and a counter is per frame, so it cannot sit
in the asset's metadata and would be a new column whose values only some sources can supply.

### 4.3 The `t_tick` check

**Preferred direction: an error-level rule that `t_tick` does not decrease in `frame_index`
order**, comparing each frame with the frame before it on the same clock. Two frames of one asset
can share a tick where the clock is coarser than the frame period, so equal ticks pass. The check
compares only frames on one clock because ticks on different clocks are not comparable.

**No check.** A writer that pairs times with frames in decode order passes every rule, and the error
is monotonic within each group of pictures, so nothing else shows it.

### 4.4 One proposal or two

The `pts` and `dropped` decisions are independent, and the revision guide's section on length and
focus splits independent decisions. They are kept together because both rewrite Part 01 §3.18's account of a frame and the
same registry declaration, and share one core version.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Affected: Part 01 §3.18 gains the edit-list reading of `pts`, the meaning of `dropped`, and that an excluded frame gets no row. |
| logical prose | Unchanged: Part 02 carries no column text for `core.media_frames`. |
| registry meta-schema | Unchanged: no new field. |
| registry declarations | Affected: descriptions of `frame_index`, `pts` and `dropped`; no type, presence or role changes. |
| declarative rules | Affected: one new error-level rule on `core.media_frames`; the Tier 2 count rises by one. |
| physical profiles | Unchanged: no storage change. |
| packet manifest and other schemas | Unchanged. |
| validation and import | Affected: the validator runs the new rule; the meaning of `pts` and `dropped` cannot be checked, because a validator does not open the media and an asset may be referenced. |
| extension registries | Unchanged: no extension declares frames. |
| reader, writer, validator, adapters | Affected: the AIND adapter writes null at frame 0 where it cannot tell, and gets tests with timestamps in decode order and with `dropped` values; it would skip a frame its container marks excluded, which no measured file has. |
| existing packets | The 786867 packet passes the new rule and stores `pts` with the edit list applied. Its false at frame 0 is supported where the video's first frame is the timing file's first exposure, which holds for all three of its videos. A rebuild gains the descriptions and the new core version. |
| conformance fixtures and tests | Affected: a corpus packet holding `core.media_frames`, with invalid cases for `frame_index_contiguous`, `pts_increases_with_frame_index` and the new rule. |
| revision lifecycle and tooling | Unchanged. |
| publications and developer documentation | Affected: the regenerated parts and registry. |

## 6. Open questions

1. **Frames on more than one clock.** Each measured asset's frames lie on one clock, and `clock_id`
   is a per-frame column. The preferred check compares only consecutive frames on one clock;
   requiring an asset's frames to share one clock would let it compare every pair, and would be a
   new restriction.
2. **An edit list that presents one stored frame twice.** Under the preferred reading each
   presentation is a frame the asset presents, so it gets its own row. No measured file has such a
   list.
3. **One proposal or two** (§4.4). The preferred direction keeps them together.

No other proposal or draft changes Part 01 §3.18 or `core.media_frames`. A proposal giving a null
in a nullable reference column a default reading is being written at the same time; `pts` and
`dropped` are not references, so it does not reach them.

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
