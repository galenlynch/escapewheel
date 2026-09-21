# Part 01 — Semantic Standard

Normative.

<a id="ew-semantic-standard-scope" data-spec-anchor="canonical"></a>
## 1. Scope

This part defines what the concepts in a packet mean. It does not decide how they are stored.

The semantic standard defined by this part is identified by `escapewheel-semantic-v0.1`.

Every semantic concept MUST be representable in the logical standard (Part 02). The semantic standard itself is independent of Parquet, Zarr, Iceberg, or any other substrate.

## 2. Global semantic rules

### 2.1 Stable identity

Any object referenced by another object MUST have a stable identifier.

An identifier is a signed 32-bit integer. Implementations MUST NOT encode semantic meaning in identifier values, and MUST NOT derive an identifier from a value's position in a file.

Each identifier declares its **identity**:

| identity | definition |
|---|---|
| `carried` | the source's own number, reproduced unchanged |
| `assigned` | chosen by the writer when the packet was built |

An assigned identifier's owning table MUST carry a `*_name` column holding the name it was assigned from, so that a process outside the packet can reference the row without knowing the number.

### 2.2 Time basis

Every event, interval, spike time, dense time axis, and media frame timing record MUST declare a time basis: an integer tick and a `clock_id`.

Floating-point seconds MUST NOT be the canonical representation. Seconds MAY be derived, and are defined from the session's time origin. A consumer lacking that origin MUST refuse to derive seconds rather than assume one.

Where a writer cannot map one of its clocks' observation starts onto the reference, it MUST NOT declare a time origin. An origin it could not compute shifts every second a consumer derives.

A tick is a coordinate, not a label and not a quantity. A writer MUST NOT re-base a source's sample index: for a sample clock, tick 0 is sample 0.

### 2.3 Observation

A session's extent is stated as **wall-clock time**, not as a tick range. A hull over every clock's ticks would need those ticks converted to one clock, and alignment may be anchor-based — outside the first and last anchor the mapping is undefined, which is exactly where a hull reaches. A session therefore declares when it started and MAY declare when it ended, both as instants.

A clock is observing during declared intervals, in that clock's own ticks. Anything timed by a clock inherits that clock's window and MAY refine it, but MUST NOT assert a window derived from its own timestamps.

An interval is **closed**: `start_tick` and `stop_tick` both name observed ticks, so an interval covers `stop - start + 1` ticks and a one-tick interval has `start == stop`.

### 2.4 Provenance

An imported core resource SHOULD be traceable to source data or source activities, and a derived analysis resource MUST declare lineage to the core resources it derives from.

Provenance is a source-file record, a processing-run record, and a link between them. A packet carrying no provenance is conforming; where provenance is present it is validated.

### 2.5 Units of measure

A measured quantity SHOULD declare its unit. A stored integer requiring conversion to physical units MUST declare the conversion.

A unit is declared on the column, not left to the column's name.

### 2.6 Currency

Where several derived results of the same kind and scope coexist, a consumer MUST NOT silently choose between them: it refuses, or reports the ambiguity. A preference is declared, keyed on the producing run, and a consumer selecting derived data for an activity SHOULD use the preferred run where one is declared for the matching scope — a declared preference a consumer ignores is a preference for nobody.

A run declares the scope it is about. A run declaring none is **undeterminable**, which a consumer MUST report separately from ambiguous, and the state is contagious: where more than one run exists for an `activity_type` and **any** of them declares no scope, a consumer MUST NOT conclude the group is unambiguous. The unscoped run may or may not be about the same thing as the others, and nothing in the packet says which.

Where a run supersedes another, the chain MUST be well-founded: a run MUST NOT supersede itself, directly or transitively.

### 2.7 Extension

Lab-specific concepts MAY be added through namespaced extensions (Part 09). An extension MUST NOT alter the meaning of a core concept without a new semantic version.

## 3. Concepts

### 3.1 Dataset

A collection of packets sharing a semantic and logical standard. It is a organizational concept and has no required representation.

### 3.2 Packet

One concrete bundle of resources under a declared physical profile. A packet MUST declare the sessions it contains.

### 3.3 Session

One continuous recording engagement with one subject.

- MUST have an identifier and a subject.
- MUST declare the clock its times are reported on.
- MUST declare its time origin where seconds are to be derived.

### 3.4 Subject

The animal or preparation recorded from.

- MUST have an identifier.
- SHOULD declare species, sex, and date of birth.

### 3.5 Device

A physical instrument used during acquisition.

- MUST have an identifier.
- SHOULD declare manufacturer, model, and serial number where its source states them.
- SHOULD declare the **hardware revision** and **firmware version** it was running.
- SHOULD name the device it was **attached to**, where a source states it.
- SHOULD declare **which port** of that device it occupied, where a source states it.

A serial number identifies the object; its firmware determines what the object does. Two sessions can record the same make, model and serial and need interpreting differently, so a version is not an identifier's decoration but a separate fact.

A consumer MAY walk from a probe to the hardware that acquired it, and MAY group probes by any element of the chain they share — which is the question the chain exists to answer. It MUST NOT infer attachment from a device's name: a name is unconstrained by this standard, and the reference is the statement.

Attachment names a device, and which place on that device a child occupied is a second fact. A device SHOULD declare the port, dock or slot of its parent it attached to, where a source states one. Where it declares none the coordinate is **unrecorded**, and a consumer MUST report it as such rather than parse it out of a name. Two devices sharing a parent and a port are not one device, and nothing declares that they are: the four bases of a quad-base probe occupy a single dock, so a port says where something was plugged in and not what it was.

A device is the **physical object**. Where a source presents several recording entities from one object — the bases of a quad-base probe — each is a Probe and all name the same Device; a writer MUST NOT create a second device row for one instrument. Attachment is stated, never inferred from a name, and the chain MUST terminate: a device MUST NOT be its own ancestor.

A writer records both versions **verbatim** as the source stated them, and MUST NOT normalise, pad, or parse them into components. Neither is ordered: a consumer MAY compare two version strings for equality and MUST NOT compare them for precedence, because different manufacturers' schemes share none.

Where an element of an acquisition chain reports its own versions, it is its own device. A value the source gives as unknown is recorded as the source gave it, which is distinct from a source that said nothing.

This standard names no kinds of device, so a writer MUST record every instrument its source declares — a camera on the same terms as a headstage — and identity is the serial the source states. What a device row does not carry is where an instrument was pointed: a camera's target is a fact about the instrument that `core.devices` has no column for, and it stays in `metadata` until something has to read it.

### 3.6 Probe

A device that carries electrodes.

- MUST belong to a session's device inventory.
- MAY declare manufacturer, part number, and geometry.

### 3.7 Electrode

One recording contact.

- MUST belong to one probe.
- MAY have a position in one or more coordinate frames.

### 3.8 Coordinate

A position of an electrode or unit in a declared frame.

- MUST name a frame the packet declares (§3.24).
- MUST carry one value per axis that frame declares, each on the axis it sits on.
- MUST declare the **basis** of its claim:

| basis | meaning |
|---|---|
| `planned` | where the probe was meant to go; intent, and possibly missed |
| `measured` | where it was, established after the fact by observation |
| `nominal` | where it is by construction; nothing aimed at it and nothing observed it |

The vocabulary is open. A consumer that does not recognise a basis MUST NOT treat the coordinate as `measured`.

A position is as many numbers as its frame has axes, so the values are one row per axis rather than a fixed three. Each value's unit is the axis's, and its meaning is what the axis says it holds.

A coordinate MAY carry an atlas annotation: the structure the position falls in, as an identifier and a label. An electrode is not in a region; a position is, so the annotation belongs to the coordinate rather than to the contact.

Where the identifier is present the label SHOULD be too, so a consumer without the atlas can still read the annotation. A table MUST NOT carry a structure's full name or its ancestry path as columns: both are derivable from the identifier, and an ancestry path is a list, which Part 02 §5.2 forbids in a delimited string.

A validator MUST NOT treat an absent annotation as a finding. Where a position falls outside any declared structure, or no registration covered it, the packet records a fact about the session.

A coordinate SHOULD name the processing run that produced it where the writer knows it. That is provenance — which run produced the row that is there — and not a choice between rows.

### 3.9 Clock

A monotonic counter with a declared rate and origin.

- MUST declare a tick rate, as a rational where the rate is not an integer.
- MAY declare a parent clock, and if so MUST be alignable to it.
- MUST declare either a linear transform or anchor points, never both.
- MAY bind its **tick 0 to a wall-clock instant**, which is the only route from a
  packet's ticks to real time; absent it, ticks relate to each other and to nothing else.
- A counter that resets mid-session is two clocks, one per epoch, each with its own
  identifier, origin and wall-clock binding. A packet MUST NOT represent a reset as a
  discontinuity within one clock: an anchor sequence requires both sides to increase, so there
  is no way to express it and no way to read it.

A clock's tick-zero binding and a session's start time are **independent and MUST NOT be
conflated**. One is a property of a counter, the other a fact about when work began.
Where a wall-clock binding is derived rather than declared, the tick it is anchored on MUST lie
in the same epoch as the instant it is paired with — a binding computed across a reset
describes neither clock.

An importer MUST examine a source in acquisition order and MUST NOT assume monotonicity. A reset is
visible only in the order the samples arrived; sorting first hides it.

A tick's zero is where the clock's declared origin says it is — for a sample clock whose origin is
sample 0 of a recording, tick 0 **is** that sample. A writer MUST NOT re-base a source's sample
index and a consumer MUST NOT assume any base beyond what the origin declares; that
prohibition is what makes a tick exact.

Alignment beyond the terminal anchors is defined only while the estimator's error stays within tolerance, 3 ms at p95 by default. A profile or a recipe MAY state a different tolerance; a writer MUST record the value it used.

A writer reaching past one median anchor interval MUST measure its error and MUST record the median, p95, and maximum, so a consumer can judge the packet by a stricter rule than the writer applied.

A consumer MUST **report** ticks it cannot map rather than omitting them, so a converted table has the same row count as its source with nulls where the mapping is undefined. A row that vanishes in conversion is indistinguishable from one that was never there. It MUST record how many rows it dropped for falling outside the bound **even when that count is zero**: silence is what lets a reader and a writer disagree about which rows exist.

### 3.10 Interval

A bounded span of experimental time within a session.

- MUST belong to one session.
- MUST have start and stop ticks on a declared clock, closed per §2.3.
- MUST declare its **kind**: the resource that specialises it.

A trial is one kind of interval. Blocks, epochs, and stimulation periods are others. What an interval *means* — condition, stimulus, choice, outcome, stimulation parameters — is declared by the specialising resource and MUST NOT be added to the core interval.

### 3.11 Event

An instantaneous or near-instantaneous timestamped observation: a tick, and the stream it was
observed on.

- MUST belong to one session and to one event stream.
- MUST have a tick, on the clock its stream declares.
- MAY carry a structured payload.

An event carries no type and no clock of its own: both are properties of the stream, which emits
one kind of event and declares one clock. An event does not reference an interval. Examples:
stimulus onset, reward delivery, lick, threshold crossing, TTL edge,
synchronization pulse.

### 3.12 Event stream

The context a class of events was observed in: what produced them, on what clock, what kind of
event they are, and where anything further about them lives.

- MUST declare an event type, from an open vocabulary, and the clock its events are timed on.
- MAY name a device, a processing run, and a table specialising its events.

A stream emits **one kind** of event, so a source emitting several on one channel is written as
several streams. What a stream's events carry beyond a tick is that named table's to declare, not
core's: how many marks an event has and of what type is a property of what produced it.

<a id="ew-unit-concept" data-spec-anchor="canonical"></a>
### 3.13 Unit

A sorted or curated spiking entity.

- MUST be identified by session, unit, sorting run, and curation version together.
- MUST belong to one sorting run and one curation version.
- MAY sit on several electrodes, and MAY have a position in one or more frames.

A unit is not a neuron. It is what a sorting produced.

### 3.13.1 A rate needs a denominator

A firing rate is a count over a duration, so the duration MUST be knowable. Where a unit declares observation intervals, the rate is its spike count over the total of those intervals; where it declares none, it is the count over the recording's extent. A packet SHOULD state which denominator it used, because the two differ for any unit that drifted out and back.

### 3.14 Spike event

One detected action potential of one unit, at one tick on one clock. Spike events are the canonical spiking representation.

### 3.15 Quality label

An assessment of a unit by one scorer. A unit has many, not one.

- MUST name the source that assigned it.
- MAY carry the source's own label verbatim, which is open.
- MAY carry a normalized label from a closed vocabulary.

### 3.16 ElectricalSeries

Sampled extracellular voltage over time and channels, represented as a dense array asset with a declared time axis and channel mapping.

### 3.17 Array asset

A dense array stored outside the table layer, with declared axes. An axis declares its coordinates; a regularly sampled axis declares them as an origin, a step, and a length rather than as stored values.

An array asset holds **any** sampled quantity, whatever instrument produced it. This standard names the concepts it defines — §3.16 is the one it defines for extracellular voltage — and it does not enumerate instruments. A packet names its own arrays, and an array names the device that made it (§3.5); a rig fitted with an instrument this standard has never heard of therefore needs no extension, no new concept, and no revision.

`semantic_type` is open. A value this standard does not define is a label and carries no contract, which is the honest state of affairs for a quantity whose meaning lives in the device rather than in the format.

It is also **nullable**, and null is the ordinary case: a writer MUST NOT fill it where the row's declared facts already say what the asset holds. Requiring it is what made it a duplicate — a column carrying no contract that every row must fill is one a writer invents a value for, and `ElectricalSeries` stood on 22 of 25 arrays where the unit, the channel map and the dimensions already said voltage per channel over time. What remains is what the facts cannot express: which statistic of a waveform an array holds, or what a video shows, neither of which any other column carries.

Which **band** of a signal an array holds is a separate question, answered by a column of its own: `wideband`, `ap` and `lfp` are reserved for the corresponding signal bands, the vocabulary is open, and an array not split into bands declares none. A band value is a conventional shorthand for a filter the packet does not record, so a consumer MUST NOT read it as a statement of the filter's corners, and MUST NOT infer a band from an asset's `semantic_type`, its device or its sampling rate — a signal can be decimated without being filtered and filtered without being decimated.

An array asset SHOULD name the device that produced it, where the writer knows which one did. A consumer MAY then resolve any array to its instrument without knowing what kind of array it is, and MUST NOT infer an instrument from an asset's `semantic_type`, its name, or its URI: those are labels, and the device is a reference.

An array a processing run produced MUST name that run; an acquired array names none. The manifest records a run per resource as well, and that entry keeps its meaning for resources that are not rows of a table — but it is not per row and no rule can join it, so currency is unreachable for an array without the column. A produced array without a declared run is an error.

### 3.18 Media asset

An image or video stored in an ordinary container, with frame timing carried in tables.

- MUST have a stable media asset ID, a URI, and a format.
- SHOULD carry a frame table where synchronization matters.

A frame row is indexed by **presentation order**: row *n* describes the frame the asset presents nth, counting from 0. A writer MUST NOT number frames in the order the container stores them, which differs wherever a codec reorders — a stream with bidirectional frames displaces one by several positions, and the resulting misattribution of time is monotonic and therefore invisible.

The index counts the frames the asset **holds**, not the exposures the capture produced. A frame lost before or during writing gets no row and no reserved index; what went missing is recorded in the columns that carry timing, not as a gap in the numbering.

A frame's time is a tick on a declared clock, like every other time in a packet (§2.1). A container's own **presentation timestamp** is a different quantity and is carried separately: an integer in the container's own time base, verbatim. A writer MUST NOT rescale it to seconds, to a clock's ticks, or to a frame number, and MUST leave it absent where it did not read the container. It is not a time on any clock the packet declares, so a consumer MUST NOT compare it between assets or use it to measure elapsed time; what it locates is the frame inside the file.

A consumer MAY pass a presentation timestamp verbatim to a container library to seek the frame a row describes, which is the exact route and assumes nothing about ordering.

The asset declares the **rate** those timestamps count at, as an exact rational — a container time base of 1/16000 s is 16000 over 1, in the shape a clock's tick rate already uses. A writer that carries presentation timestamps MUST declare it and MUST NOT declare half of it. A consumer MAY then convert a timestamp to seconds of the asset's own timeline without opening the media, which is the case a referenced asset makes ordinary: the file is the part a packet is least likely to have.

A media asset SHOULD name the device that recorded it where its source states one, as an array asset does. Nothing else separates two assets of one format: a behaviour video and a movie from a head-mounted microscope are both `mp4` written by a camera, and `semantic_type`, the asset's name and its URI are labels rather than references. Where the source states no device the column is null, and a consumer MUST report the instrument as unrecorded rather than read one out of the asset's name.

### 3.19 Source file

An input the packet was built from.

### 3.20 Processing run

An activity that produced resources, declaring what it was, what it ran on, and the scope it was about.

### 3.21 Sorting run

A processing run that produced units from a recording, declaring the clock its ticks are on.

### 3.22 Curation version

A named state of a sorting's unit set, optionally derived from a parent curation.

### 3.23 Calibration

What someone measured about an instrument so that its numbers can be interpreted: how many microlitres a valve delivers when held open for 30 ms, how much light a fibre emits at a given drive, where a manipulator's own coordinates sit in the rig, where a camera is mounted.

- MUST have an identifier, a name, and a declared type from an open vocabulary.
- MUST name the session it was in force for.
- SHOULD declare when it was measured, where the source states one.
- MAY name the devices it covers, carry the points of its curve, or name the array holding it.

A calibration is a standing property of an instrument rather than an activity of this packet, so a session reports it as **in force** rather than as having happened, and it is not a Processing run. Both packaged sessions cite water calibrations measured 133 and 302 days before the recording, one of them by two sessions six months apart.

One calibration covers many devices — six manipulator modules cite one file and one timestamp between them — so which devices it covers is recorded per device and not as a property of the calibration.

A source states a calibration in at least four ways: as a curve, as an array, as a date and nothing else, and as an assertion that none was made. A calibration with no recorded content is still a calibration, and a consumer MUST read such a row as **unrecorded** rather than as absent. A source stating that no calibration was performed gets no row: the absence of a calibration is not a calibration.

### 3.24 Coordinate frame

The space a coordinate is a position in, together with its axes.

- MUST have a name, which is the session's own name for that space.
- MUST declare one row per axis it has, each carrying the source's own name for what that axis holds.
- MAY name the published atlas the space is, and the version of that atlas.
- MAY declare which way an axis's values increase, and MUST leave that undeclared where the source does not state it.

A frame has as many axes as it has: two for a shank, five for a rendering space. Three was what the column names `x_um`, `y_um` and `z_um` claimed, and of the two packaged sessions' 27,557 coordinate rows, 8,448 are shank positions that leave the third empty.

An axis's name is the source's word for the field its values came from, carried verbatim — `ccf_ml` where the source's electrodes table has a column of that name. It records where the value came from and not what the quantity is conventionally taken to be, so a consumer needing to know which way an axis runs, where no direction is declared, MUST report the coordinate unusable for that purpose rather than assume a convention.

Which published atlas a frame is, is a fact the frame declares rather than a spelling of its name: two packets both naming a frame `ccf` may be registered against CCFv3 and against a successor whose structure ids differ, and comparing names cannot tell them apart. A writer MUST NOT fill the atlas or its version from the name.

A frame belongs to one session, because a name two sessions reuse may name different spaces — the reason `core.devices` is session-scoped.
