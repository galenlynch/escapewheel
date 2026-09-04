# Part 01 — Semantic Standard

Normative.

## 1. Scope

This part defines what the concepts in a packet mean. It does not decide how they are stored.

Every semantic concept MUST be representable in the logical standard (Part 02). The semantic standard itself is independent of Parquet, Zarr, Iceberg, or any other substrate.

## 2. Global semantic rules

### 2.1 Stable identity

Any object referenced by another object MUST have a stable identifier.

An identifier is a signed 32-bit integer (R53 §2.1). Implementations MUST NOT encode semantic meaning in identifier values, and MUST NOT derive an identifier from a value's position in a file.

Each identifier declares its **identity** (R53 §2.3):

| identity | definition |
|---|---|
| `carried` | the source's own number, reproduced unchanged |
| `assigned` | chosen by the writer when the packet was built |

An assigned identifier's owning table MUST carry a `*_name` column holding the name it was assigned from, so that a process outside the packet can reference the row without knowing the number.

### 2.2 Time basis

Every event, interval, spike time, dense time axis, and media frame timing record MUST declare a time basis: an integer tick and a `clock_id`.

Floating-point seconds MUST NOT be the canonical representation. Seconds MAY be derived, and are defined from the session's time origin (Part 02, R39 §2.1). A consumer lacking that origin MUST refuse to derive seconds rather than assume one.

A tick is a coordinate, not a label and not a quantity (R45 §3). A writer MUST NOT re-base a source's sample index: for a sample clock, tick 0 is sample 0.

### 2.3 Observation

A clock is observing during declared intervals, in that clock's own ticks (R38 §2). Anything timed by a clock inherits that clock's window and MAY refine it, but MUST NOT assert a window derived from its own timestamps.

An interval is **closed**: `start_tick` and `stop_tick` both name observed ticks, so an interval covers `stop - start + 1` ticks and a one-tick interval has `start == stop` (R45 §2).

### 2.4 Provenance

An imported core resource SHOULD be traceable to source data or source activities, and a derived analysis resource MUST declare lineage to the core resources it derives from.

Provenance is a source-file record, a processing-run record, and a link between them (R9 §2). A packet carrying no provenance is conforming; where provenance is present it is validated.

### 2.5 Units of measure

A measured quantity SHOULD declare its unit. A stored integer requiring conversion to physical units MUST declare the conversion.

A unit is declared on the column, not left to the column's name (R56 §2).

### 2.6 Currency

Where several derived results of the same kind and scope coexist, a consumer MUST NOT silently choose between them. A preference is declared, keyed on the producing run (R41 §2), and a run declares the scope it is about (R44 §2). A run declaring no scope is undeterminable, which a consumer MUST report separately from ambiguous.

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

- MUST declare the frame it is in.
- MUST declare the **basis** of its claim (R58 §2.1, R64 §2.1):

| basis | meaning |
|---|---|
| `planned` | where the probe was meant to go; intent, and possibly missed |
| `measured` | where it was, established after the fact by observation |
| `nominal` | where it is by construction; nothing aimed at it and nothing observed it |

The vocabulary is open. A consumer that does not recognise a basis MUST NOT treat the coordinate as `measured` (R58 §2.2).

A coordinate MAY carry an atlas annotation: the structure the position falls in, as an identifier and a label (R59 §2). An electrode is not in a region; a position is.

### 3.9 Clock

A monotonic counter with a declared rate and origin.

- MUST declare a tick rate, as a rational where the rate is not an integer.
- MAY declare a parent clock, and if so MUST be alignable to it.
- MUST declare either a linear transform or anchor points, never both (R13 §2).
- A counter that resets mid-session is two clocks (R27 §4).

Alignment beyond the terminal anchors is defined only while the estimator's error stays within tolerance (R37 §3, R40 §2).

### 3.10 Interval

A bounded span of experimental time within a session (R54 §2.1).

- MUST belong to one session.
- MUST have start and stop ticks on a declared clock, closed per §2.3.
- MUST declare its **kind**: the resource that specialises it.

A trial is one kind of interval. Blocks, epochs, and stimulation periods are others. What an interval *means* — condition, stimulus, choice, outcome, stimulation parameters — is declared by the specialising resource and MUST NOT be added to the core interval (R54 §2.3, §2.4).

### 3.11 Event

An instantaneous or near-instantaneous timestamped observation.

- MUST belong to one session.
- MUST have an event type and a tick on a declared clock.
- MUST belong to an event stream.
- MAY carry a structured payload.

An event does not reference an interval (R11 §5). Examples: stimulus onset, reward delivery, lick, threshold crossing, TTL edge, synchronization pulse.

### 3.12 Event stream

The context an event was observed in: what produced it, and on what clock (R23 §2).

### 3.13 Unit

A sorted or curated spiking entity.

- MUST be identified by session, unit, sorting run, and curation version together.
- MUST belong to one sorting run and one curation version.
- MAY sit on several electrodes, and MAY have a position in one or more frames.

A unit is not a neuron. It is what a sorting produced.

### 3.14 Spike event

One detected action potential of one unit, at one tick on one clock. Spike events are the canonical spiking representation (R5 §2).

### 3.15 Quality label

An assessment of a unit by one scorer. A unit has many, not one (R16 §2).

- MUST name the source that assigned it.
- MAY carry the source's own label verbatim, which is open.
- MAY carry a normalized label from a closed vocabulary (R22 §2).

### 3.16 ElectricalSeries

Sampled extracellular voltage over time and channels, represented as a dense array asset with a declared time axis and channel mapping.

### 3.17 Array asset

A dense array stored outside the table layer, with declared axes. An axis declares its coordinates; a regularly sampled axis declares them as an origin, a step, and a length rather than as stored values (R20 §2.1).

### 3.18 Media asset

An image or video stored in an ordinary container, with frame timing carried in tables.

### 3.19 Source file

An input the packet was built from.

### 3.20 Processing run

An activity that produced resources, declaring what it was, what it ran on, and the scope it was about.

### 3.21 Sorting run

A processing run that produced units from a recording, declaring the clock its ticks are on (R38 §3).

### 3.22 Curation version

A named state of a sorting's unit set, optionally derived from a parent curation.
