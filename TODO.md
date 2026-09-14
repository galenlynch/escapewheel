# TODO

Live work first, then measurements worth reusing, then what was settled and when. Reasoning for a
settled item lives in the revision it produced and in git history, not here.

## State of the world

Last checked 2026-09-09, by `python verify.py` — which is the way to check it, rather than by
reading this block. Everything below is what that command reports.

<!-- BEGIN facts: revisions -->
R1–R41, R43–R72 and R74–R115 accepted. R42 and R73 withdrawn. No draft is open.
<!-- END facts: revisions -->
<!-- BEGIN facts: registry -->
43 tables, 351 columns, 111 references, 77 Tier 2 rules (2 advisory)
<!-- END facts: registry -->
<!-- BEGIN facts: corpus -->
28 conformance packets
<!-- END facts: corpus -->

<!-- BEGIN facts: extensions -->
4 extension registries: aind_opto, aind_unit_qc, dynamic_foraging, vr_foraging
<!-- END facts: extensions -->

Each drawn from columns measured in a real
session rather than invented — see `registry/extensions/README.md`. The conformance corpus carries
one, because R54 §2.4a leaves a packet holding intervals no way not to.

**Phases 0–6 complete.** `escapewheel verify` closes R36 §2.4 and `escapewheel prune` closes R61 §3.
Phase 7 (Iceberg) untouched.

**This is one repository.** It was ten until 2026-09-04; each history was preserved through the
join, so `git log -- revisions/` and `git blame` reach back through it.

### What stands between here and a production trial

1. **Resolve a channel index for a caller.** The reader and consumer obligations were walked on
   2026-09-11 against the parts, which R111 made the statement of record: **58 normative
   sentences** name a reader or a consumer. One was unmet — the codec floor, fixed — and Part 02
   §8.3's SHOULD is now offered by `escapewheel_reader.discriminators`. What remains is Part 02
   §12.2: `extremum_channel_index` counts the channels a sorting run **kept**, and resolving it
   against the contact list named the wrong electrode for **5,071 of 6,781 units** (R83 §1).
   Nothing here resolves it through `core.sorting_run_channels`, and a consumer meeting an index
   for a run that declares no channels MUST report it unresolvable rather than resolve it
   anyway — which is a rule nobody can follow against an API that does not offer the resolution.
2. **Bump `registry_version` when the schema settles.** It is held at `0.1.0` by decision, not by
   oversight: the field is for compatibility and follows semantic versioning, and R48, R53, R56
   and R59 would each have forced a major increment. While the hold lasts, two packets declaring
   `0.1.0` can carry incompatible schemas, so the embedded registry is the authority and
   `registry_version` alone cannot decide compatibility (Part 02 §9.2). Lift the hold at release
   and increment on the next breaking change.

---

# Live

## 1. Both packets are rebuilt, and not yet swapped in

Each sits in `packet-rebuilt/` beside the original, which is untouched. Committed with **0 errors
and 0 warnings**: `ecephys_776259` in 467 s with 286,896,563 spikes, `ecephys_786867` in 296 s with
7,570,450 media frames. Replacing the originals is a separate decision, governed by R32's amendment
discipline and `escapewheel prune`.

What the rebuild corrected, measured on the committed bytes rather than predicted:

| | before | after |
|---|---|---|
| `core.subjects.subject_name` | `786867` in **both** packets (R87 §1) | `776259` and `786867` |
| `species` | null | `Mus musculus`, from `subject.json` |
| `sex` | `Male`, outside R101 §3.9's closed set | `male` |
| clock windows | 1 of 13, and 1 of 11 (R98 §2.1) | 13 of 13, 11 of 11 |
| `animal_response` | `0`, `1`, `2` with the key elsewhere | left/right/no_response, R106 §5's counts exactly |
| coordinate frames | — | `ccf` and `probe`, five axes named as R105 §5 said |
| calibrations | — | 3 from `rig.json`, R89's first real rows |

**R68's prediction is confirmed against real data.** `core.media_frames` is **0.43 MB** against the
**0.40 MB** R68 §5 predicted, down from 11.73 MB, with `pts` at **0.04 bits/row** on
`DELTA_BINARY_PACKED`. The 0.03 MB over is R88's `session_id`, which R68 predates.

## 1a₀. Five writer bugs, all one shape

Every blocker the rebuild hit was an accepted revision implemented on **one code path and not the
other**, and no packet had been built since to notice:

| revision | what drifted |
|---|---|
| R95 §3.1 | `Clock.record` wrote a human label into `clock_name`, so no recipe spelling resolved |
| R96 §3.4 | the materializer read `spike_events.clock_id` after it was struck |
| R88 §2.3 | the central `session_id` fill read the session out of a table staged last |
| R98 §3.1 | the sorter never claimed the twelve clock windows only it knows |
| R88 §2.3 | `add_batches` never applied the fill at all, so a streamed table had nulls |

Two of the five are `add()` against `add_batches()`. The records path and the streaming path have
drifted apart and nothing compares them, which is a sharper statement of §1b than could be written
before: the pair is where a rule gets implemented once and forgotten once.

## 1₊₊₊. An extension copier template, and the instructions to go with it

**Not started.** Writing an extension is now well enough defined to scaffold, and nothing scaffolds
it: the four here were written by hand, and `registry/extensions/README.md` covers *what to model* —
what varies belongs on the row, a source's columns are evidence rather than a schema, deriving a
document from a pydantic model — while saying nothing about how to build and deliver one.

**The template.** Base it on `~/Documents/Code/aind-python-copier-template`, which already carries
the shape: `_templates_suffix: .jinja`, `_subdirectory: template`, copier ≥ 9.0.0, and conditional
`_exclude` blocks for docs, notebooks, a CLI and a `CLAUDE.md`.
`~/Documents/Code/aind-capsule-copier-template` is the other one to read before choosing which to
fork. What it should generate:

- `registry/<namespace>.json`, a skeleton declaring one table with every attribute a column owes,
  and a test running it against `registry/registry.schema.json`;
- an `extract.py` matching the shape a recipe's `command` invokes — an argument list run in the
  source root, writing Parquet to declared paths;
- an optional self-validation step against the extension's own document (R109 §3.5) and an
  optional run report (R109 §3.6);
- a `[source]` block and an `[encoding]` block to paste into a recipe.

**What the instructions must state**, because each is a rule an author will otherwise break:

- The document is a registry document in Part 02's format, namespaced (R17 §2, Part 09 §5.2), and the
  packet declares it in the catalog (Part 09 §5.3).
- Every column declares a type, a presence and a role (R2 §5, R48 §2.1); a string column declares
  its vocabulary (R101 §3.1); an identifier declares `carried` or `assigned` (R53 §2.3); a
  session-scoped table carries `session_id` and declares the reference (R88 §2.1).
- Rows arrive with identifiers as the **names** their source used, never numbers: the writer mints
  those packet-wide (R53 §2.5).
- The document **MUST NOT** be derived from the rows it delivers (R109 §3.2). Declare the **union**
  of what the pipeline may emit, as `nullable` — `aind_unit_qc.waveform_metrics` declares 13
  columns where the extraction delivers 10, and that difference is what says a run did not compute
  `half_width` rather than that the extension lacks it.
- The command **MUST** be a function of its inputs (R109 §3.7). Where it cannot be, deliver a file
  produced beforehand instead.
- An encoding exception goes in the recipe's `[encoding]`, never in the schema, because it is a
  fact about one packet's values (R110 §3.4).

**Best practices worth stating beside the rules.** Isolate dependencies however you like — the
command is an argument list, so `uv run`, a pinned interpreter and a container are all just
commands, and that freedom is what R109 §3.1 exists to protect. Print for a person on stdout and
put anything a build should parse in the report file. Do not restate what the build already
derives: rows per table come from the Parquet footer at Part 05 Stage 1.

## 1₊₄. The actor audit is done, and what it found

**Complete, 2026-09-10.** Every one of the **176 normative sentences that name an actor** was read
against R111 §3.1's line — a reader is bound by what it **returns**, a consumer by what it
**concludes** — and against §3.2, where a build is one run of a writer. **Seven were repointed**,
which is the yield the by-part test predicted:

- Part 01 §3.9 — "a **reader** MUST NOT assume any base beyond what the origin declares" became a
  consumer. R45 §3 copies a tick verbatim, so no reader converts one; assuming a base is a
  conclusion about the value, not a property of what came back.
- Part 00 §5 and Part 06 §1 — "A **consumer** MAY delete and recompute any of them" became a writer.
  Regenerating an analysis resource is a write, and no consumer mutates a packet.
- Part 03 §6's revalidation and Part 05 §11's deterministic-build mode left **implementation** for a
  validator and a writer: R111 §3.2 keeps that word for a requirement binding every actor alike,
  and neither did.
- Part 09 §8's five anti-patterns were one `implementation MUST NOT` list binding three actors, and
  are now a reader's one, a writer's three and a build's one.
- Part 09 §5.8 said "a build MUST NOT fail a build", which R109 introduced. It fails, or it does not.

**What the sweep did not find is the result worth keeping.** Every `build` clause was already
correct — all 24 are about one run against one recipe — and 36 of 37 consumer clauses were right,
which is §2.2's by-part habit holding up under a full reading rather than a sample. The distribution
now runs writer 75, consumer 37, validator 26, build 24, reader 20, and **implementation 2**, which
is where R111 §3.2 says it should sit.

## 1c. An extension can be drafted and cannot be checked

`escapewheel extension` drafts a registry document from tables that already exist, which is the
half of extension authoring that is shipped. The other half is not: `registry/check.py` runs **30
structural invariants over each registry document**, core's and every extension's — that a
reference relates columns of the same type (R114 §3), the same role, the same identity, that a
namespace prefixes its own tables, that a discriminator declares what it resolves to — and it is a
script in this repository, not a command anyone else can run.

So an author outside this repo scaffolds a document and has no way to find out whether it is
sound until a build refuses it, or worse does not. The four extensions here drift for the same
reason and are caught only because they sit beside `check.py`, which its own comment says: nothing
regenerates them.

This is the extension's version of what R115 §3.9 does for
an adapter — ship the thing an author would otherwise write badly — and the shape is the same:
`escapewheel extension check <document>`, the invariants already written, run against a document
and the core registry a packet embeds.

**The rest of the parallel is already there**, which is worth saying so nobody builds it twice. An
extension's *rows* cross by the same protocols an adapter's do, and R115 §3.9 ships both ends for
either.
Its *document* is already drafted for it by `escapewheel extension`, which reads what a Parquet file
can tell it and names what it cannot, so a human finishes a draft rather than starting one — and
that is not R109 §3.2's forbidden derivation, because what the extension delivers is the human's
document and not a function of the rows. The document already carries its own versions too:
`extends` names the logical standard (R17 §5) and `$schema` the meta-schema it is written in
(R57 §2.1). Checking is the only half that never shipped.

## 1d. The adapter boundary is specified and not built

R115 was accepted on 2026-09-11 and Part 03 §11 now carries the whole contract between a build and
a source. `conformance/adapter-boundary/` is the reference — seven scripts in which all three
protocols deliver the NWB adapter's eighteen resources identically, five of them empty — and every
piece below is the distance between that spike and the writer.

**Where a protocol is needed it is `flight-v0.1`**, decided 2026-09-12. R115 §3.3 asks one of an
adapter released independently of the build and none of an adapter the build ships, so the ten need
nothing today; what the decision settles is which protocol the writer's own server speaks, and which
one an adapter leaving this distribution implements. Flight owns the least of the three: a
descriptor is the format's, so the protocol invents no metadata key, and `ListFlights` answers
Part 05 §4.1's
discovery and `DoGet` the per-resource fetch from Arrow's own vocabulary rather than from surface we
would have to specify and version.

**Core ships adapters for standards and not for institutions.** SpikeInterface, Open Ephys, Harp and
NWB are read by many institutions, so support for them is worth carrying centrally; `rig.json`
serves one. Measured against what each module actually names, the ten sort four ways:

| | adapters |
|---|---|
| generic | `sorter`, `sync`, `openephys`, `harp`; `waveforms` once `ks_unit_id` goes; `nwb` once its dialect columns go |
| one option short | `lfp` |
| one institution's, whole | `session`, `video` |
| not an adapter | `tables` |

`session` is 707 lines of AIND's metadata schema and carries both `aind.*` compensations. `video` is
311 lines requiring a **headerless three-column CSV read positionally** — `COLUMNS = ("rig_seconds",
"frame_counter", "camera_nanoseconds")` — beside every `.mp4` with the same stem, with `frame_index`
derived from `frame_counter` and the `rx:Zip` pairing repair on top. One `ffprobe` call for
container metadata is the only generic part, so it leaves whole rather than as a carving.

`lfp` is nearly generic and worth keeping: `processing/ecephys/LFP` is where pynwb's own `LFP`
container lives, and the Zarr v2 referencing, the axis description and the band declaration are
all format-level. Its one line of dialect recovers a probe from a series name NWB does not
constrain — `series.name.removeprefix("ElectricalSeries").removesuffix("-LFP")` — and a declared
pattern option
settles it.

`waveforms` reads `waveform_mean`, `waveform_sd` and the ragged `electrodes`/`electrodes_index`, all
base NWB, and matches an array row to a unit by a **pair**: `(device_name, ks_unit_id)`, the probe
plus the sorter's label. A run is one probe (R83) and R81 measured 810 distinct labels across 6,781
units over 12 runs, so the probe is what makes the pair unique and nothing keys on `ks_unit_id`
alone. The build already keys `Context.units` by `(device_name, local_unit_label)`, which R81
measured equal to `ks_unit_id` in 6,781 of 6,781 rows, so the mapping needs no change; what changes
is the NWB-side read, `store.array(group / "ks_unit_id")` becoming a read of the `Units` table's own
`id` — base NWB, and where SpikeInterface writes a sorter's unit ids.

R115 §3.1 rewrites that crossing regardless: a units mapping keyed by a tuple was measured refused
at the boundary, so `units` arrives as records carrying the key as columns and the adapter builds
its own lookup. The dialect column goes with that work rather than as a change of its own. One
repair the rekeying forces — `units: {n} NWB row(s) match no unit or are all zero; skipped` sums two
causes, and a wrong key must be countable apart from a genuinely padded row.

Leaving is what makes an adapter need a protocol (R115 §3.3).

**`tables` is the tenth and is not an adapter; it is `files-v0.1` wearing the interface.** It knows
no format and normalizes nothing: it runs the recipe's command, reads row counts from Parquet
footers, hands back `pq.ParquetFile(path).iter_batches(...)` per resource, and refuses where a
declared file is missing — which is the protocol's definition, Part 05 §4.1's discovery, and
Part 05 §4.4's completeness test respectively. It is the one adapter that needs an exception to
every adapter rule: `PRODUCES` is empty with a comment saying what it supplies "is not a property of
the adapter at all", `STATES` is empty, and `records()` returns nothing. So it does not declare a
protocol — a build must support `files-v0.1` natively (Part 03 §11.1), and once it does, a source
entry naming `{resource: path}` with an optional command **is** a delivery and the class goes away.
`kind = "tables"` can stay as the recipe's spelling for one.

**No command runs one adapter and hands over its rows.** The writer registers `inspect`, `init`,
`extension`, `verify`, `prune` and `import` under the one `escapewheel` CLI, and none of them does
this. It is the same command a `tables` source names, so a built-in adapter reaches a build through
the door an extension already uses (R109 §3.2) rather than through a second mechanism.

**The ten adapters declare all four facts Part 05 §3.4 requires, done 2026-09-12.** `NEEDS` and
`CONSUMES` joined `PRODUCES` and `STATES` on the classes, `recipe.needs` and `recipe.consumes` read
them with nothing open, `Recipe.check` reports a declared name resolving to neither a term nor an
option the entry sets, and the build's ordering reads each adapter. `REQUIRED_OPTIONS` and the
`CONSUMES` table keyed by kind are deleted; `_SHARED_SOURCES` and `SAMPLED` remain, and go with the
one construction below. A protocol is not owed, since all ten ship with the build. `in_process`
exists for the case that does owe one — a kind another distribution registers — and `Recipe.check`
refuses such a source that declares neither.

**An optional option cannot be declared, which is a gap in R115 §3.1.** A declared name resolves
against the terms first and the recipe's options second, and one resolving to neither is refused, so
declaring an option makes a recipe carry it. R115 §3.1 argues an adapter declares its options so a
build can refuse a recipe setting one the adapter ignores — and that reasoning wants every settable
option declared, which the refusal rule forbids for any option with a default. So `NEEDS` carries
terms plus the options an adapter cannot be constructed without, and the other ten options across
the ten adapters keep flowing through the recipe's own dict unvalidated. Worth a clause giving
`needs` an optional half; measure how many options it would cover before writing one.

Writing those declarations out against `_build_source`'s ten branches turned up two things, found
2026-09-12. **`store` cannot be declared at all**: §11.2 forbids a build requiring an adapter to
accept a live handle and names an open store as the example, so `_SHARED_SOURCES` becomes an
in-process optimization the construction applies behind the declaration — three adapters reading one
`.nwb` may still share a parsed store, and none of them may ask for one.

**And the electrode mapping is deleted rather than declared, done 2026-09-12.** `lfp` and `waveforms`
each took an `electrodes` argument — the NWB's electrode row index to the `electrode_id` of that row
— which Part 03 §11.2's eight terms carry nothing for, so a draft proposed a ninth. Appraising it
found the boundary already carries the value: the mapping's values are the **composed name**
`f"{prefix}{group_name}.{channel_name}"`, not an assigned number, and `PacketWriter._preassign`
resolves every assigned identifier column's names to numbers packet-wide before any table is built
(Part 05 §8). So both adapters compose that name from the electrode table they open themselves,
`electrode_name` in `sources/nwb.py` is the one spelling all three share, and `Context.electrodes`
is gone. A name no `core.electrodes` row carries now orphans the declared reference and Tier 1's
anti-join reports it, where the old lookup wrote a null in `core.array_channels` and dropped the row
in `core.unit_electrodes`. `CONSUMES` loses `nwb` for both kinds, since neither reads its output any
more. The draft was withdrawn; `revisions/drafts/README.md` says where it went.

The coupling that replaces it is `prefix`: three adapters must compose one contact's name
identically, and a recipe setting `prefix` on one and not the others makes two electrodes of one.
It fails loudly rather than silently, and the fix is the extraction below — one reader, one
function, three callers.

**Parked: what a nullable identifier's null means.** Nothing obliges an adapter to report a value it
could not fill — Part 09 §5.8's report is a MAY — so a consumer cannot tell
`core.array_channels.electrode_id` null meaning *this channel maps to no contact* from null meaning
*I gave up*, and that is true of every nullable reference in the registry. `lfp` now refuses rather
than writing such a null, and the column is null in **0 of 1,152 and 0 of 960** rows of the two
packets, so there is no instance to write a rule against. Worth a revision when something produces
one.

**`_build_source` is one construction, done 2026-09-12.** It was 72 lines carrying ten `spec.kind`
branches, each passing a different set of extras; it now reads the adapter's `NEEDS`, resolves each
name against Part 03 §11.2's terms and then the recipe's options, refuses a term this recipe cannot
fill, and passes the recipe's remaining options through. `_SHARED_SOURCES` and `_KINDS` went with the
branches — the shared store is supplied to whichever class accepts one, since a handle is not
something an adapter may declare — and a test asserts the function branches on no kind at all.
`SAMPLED` is the one kind-keyed table left; `PREFERRED` was already in the recipe layer where
Part 05 §3.3 puts it.

The reference clock crosses as its `core.clocks` row, since everything a build supplies is data.
`TickGrid` carries the identifier, the rational rate and the seconds-to-ticks conversion, which is
all a row can rebuild — a row has no label, `clock_name` being what `clock_id` stands for
(Part 02 §8.2) — and `Clock` delegates to it, so the conversion that refuses off-grid values has one
implementation and the future base NWB reader carries the grid rather than the writer's clock model.
`VideoSource.tick_rate` is struck: a required argument assigned and read by nothing.

**Nothing a build supplies is undeclared, done 2026-09-14.** Construction was unified first and the
*call* side was not, so three adapters were handed ten values none of them declared: `lfp` a mapping
of tick rates, `session` eight keyword arguments, and `sync` a **closure** — which no protocol can
carry, so the one adapter a delivery could not have reached was the one the boundary work existed
for. Eight of the ten were already expressible in Part 03 §11.2's vocabulary and two were not:

- **`clocks` crosses as rows**, which is what §11.2 says it is. It carried bare identifiers, and the
  rates they had been stripped of then travelled separately. `lfp` derives its axis step from the row
  it is given, and `sync` names a stream's clock only where the supplied rows carry that name, which
  is what the build's closure did.
- **`units` crosses as records**, the case §11.2 cites: keyed by `(device_name, local_unit_label)` it
  does not write down at all, and `conformance/adapter-boundary/probe.py` measures both that refusal
  and the integer key that crosses and comes back as a string. Each adapter builds its own lookup.
- **`first_samples` crosses as records** too. A recipe named a JSON file the build read and passed
  as a mapping; the read went with the ten branches, so the path string reached `dict()` and raised.
  Nothing caught it because `first_samples.json` is retired — the record nodes' own stamps supply
  those numbers — and every test constructs `SyncSource` with a mapping directly.
- **The reference clock reaches `session` as the term it already is.** Six of its eight arguments
  were that row, and `tick_zero_utc` is now the build's: it is derived from `sync_messages.txt`, so
  it can be filled once the source carrying those stamps has run and before the one that emits the
  row is built. An adapter emits the row it was handed and never rewrites it.
- **The build composes `core.event_stream_observation_intervals`.** One source declares the
  acquisition window and another declares the streams watched in it, and Part 05 §3.3 leaves a row to
  a single source, so the pairing is the build's act — keyed on what a spec claims rather than on its
  kind. `SessionSource` keeps the window and `PRODUCES` keeps the resource, since the recipe settles
  ownership from what makes a resource available.

What a build cannot reach any more is the JSON-derived epoch: pairing `session.json`'s whole-second
stream start with the first spike needs a tick, and no term carries one. `SessionSource.epoch` keeps
it for a caller reading one asset on its own, with its compensation, and R39's own argument is
against it — it pairs a wall clock with the datum being placed, and it is ~±1 s where the stamps are
~±50 ms. `_first_spike_tick` went with it.

Proved against `ecephys_786867` at `--sample 2000`, the recipe that names all ten kinds: **35 of 40
tables byte-identical** to the packet built before, `core.clocks` and
`core.event_stream_observation_intervals` among them, and the five that differ are the sample's
doing — both spike tables, `core.units`'s three spike-derived columns, the run's parameters, and one
extension table whose content is equal and whose bytes are not.

**What still reaches into an adapter is the harvest, and a delivery is what replaces it.** `_harvest`
calls `units()`, `clocks()`, `extent()`, `behavior()` and `event_streams()` per kind, and
`_recorded_epoch` calls `aligned()`, `started()` and `clock_id_for()` on the sync source. None of
that is a build *supplying* a value, which is what §11.2 governs; all of it is a build reading what a
source produced, and out of process it arrives as rows. Sequence it with the command below rather
than before it.

**The NWB adapter is half a standard's and half one producer's, and the split is a lift rather
than a rewrite.** The paths it walks are all base NWB — `general/subject`, `general/devices`,
`general/extracellular_ephys/electrodes`, `intervals/trials`, `acquisition/` — and about fifteen of
the columns it pulls out of them are ones base NWB does not define, which R59 measured varying
between two exporters of one pipeline. Those columns share rows with the standard ones, and R108
§3.2 forbids composing a row from more than one source, so the dialect cannot be split off as a
second adapter contributing columns.

What splits instead is the **code**: a base NWB reader as its own distribution, and an adapter that
speaks one institution's dialect as another, importing the reader and emitting whole rows of whole
resources. Ownership between the two is the arbitration that already exists — the recipe declares
which owns `core.electrode_coordinates` (Part 05 §3.3), and R108 §3.1 refuses a preference that
discards a value the passed-over source stated. Sharing the reader is safe across a release boundary
because R115 §3.9 lets an out-of-process adapter import whatever version it was written against: the
boundary unshares the environment, so a shared library is not a shared closure.

It is cheap because the boundary work above is the extraction. `sources/nwb.py` needs exactly two
things of the build — `Clock` and `StagedArray` — and R115 §3.1 has the reference clock cross as its
identifier and rational rate, while §3.8 has an array cross as a reference. After those, what lifts
is `nwb.py`, `zarr_compat.py` and `store.py`, **1,677 lines touching nothing of the build**.
Sequence it after the one construction, not before.

A **dialect mapping** — a recipe-named document of candidate column names per core column — was
designed and rejected in the same conversation. It existed only because the row-level split looked
blocked; splitting the code instead removes the need, and a rename map would not have covered what
actually differs anyway: three columns becoming rows with an `axis_index`, a delimited
`ccf_structure_id_path` that R3 §3.0 forbids, or a unit. Where a source needs converting rather than
renaming, the general form already exists — a command producing Parquet, delivered as `files-v0.1`
(R109 §3.2).

**`registry/adapter.schema.json` does not exist**, and Part 03 §11.5 publishes it. R80's
`registry/sources.schema.json` is the template and has three hookups: hand-written beside
`manifest.schema.json`, copied by `build.py`'s `VENDORED` map into the package that reads it, and
loaded by `check.py`. One thing differs — a **build** reads this document, so it vendors into the
writer rather than the reader.

**Nothing generates a declaration document.** R115 §3.12 requires generation rather than
maintenance, and measured on the ten classes it is 180 to 914 bytes each with no judgement in it,
from `PRODUCES`, `STATES`, `CONSUMES` and the protocol. The ten need none while they ship with the
build; what needs one is the first adapter to leave, and generating it here is how its author starts
from something correct.

**A build reads no report at all.** R109 §3.6 was specified and unimplemented before this, and
Part 09 §5.8 now adds the connection as a carrier, the rule that a build clears a report's path
before the run that writes it, and `stated`, which is where the values behind an adapter's declared
fields cross. All of it is unread today, so a source stating a fact out of process is compared
against nothing.

Nothing here invalidates a packet: R115 changes no table, column, reference, rule or vocabulary, and
the two built packets are conforming under it.

## 1a. The packets' physical layout and encoding

**Not started.** Several tables have changed shape substantially — R105's four coordinate tables at
74,223 value rows, R81's collapse of unit identity, R88's `session_id` on every session-scoped
table, R83's `core.sorting_run_channels`, R99's phase steps — and a rebuild is the moment to check
what Parquet actually does with them rather than what it was assumed to do.

R68 §1.3 is the precedent and the method: `core.media_frames.pts` was **96.9%** of its table because
a column declaring nothing else gets dictionary encoding, and a monotonic ramp of 7.5 M values is
its worst case. That closed without a revision, the writer's choice being the defect. Worth checking
per table: which encoding each column got, whether a sort makes a column compress away as R88 §4
measured for `session_id` at 1.0005x, and whether any row group is small enough that its footer
costs more than its rows.

## 1a₁. The corpus proves the format and not the writer

**Found by the rebuild.** Two accepted revisions had left the writer unable to build any packet at
all, and neither 448 tests nor 28 conformance packets saw it:

- `Clock.record` wrote a human label into `core.clocks.clock_name`, which R95 §3.1 defines as what
  `clock_id` stands for. Nothing could resolve a recipe's `harp` back to a clock, so materializing
  `analysis.spike_events` raised `NotAligned`. R53 is what exposed it — making `clock_id` an integer
  retired the path where the identifier *was* the string.
- `materialize.spike_events` read `core.spike_events.clock_id`, which R96 §3.4 struck in favour of
  §3.3's hop through `core.units.clock_id`, and died on a `KeyError`.

Both are on paths `fixtures/build.py` does not take: it writes rows directly rather than through
`Clock.record`, and the corpus has no packet whose `analysis.spike_events` the materializer derived.
So the corpus proves that an implementation agrees about the **format** and proves nothing about the
**writer**, which is where twenty-one revisions of drift accumulated unseen.

**Queued to work on**, and two more instances landed on 2026-09-10, both of the same shape.

- Three test fixtures carried columns the registry does not declare — `core.array_assets` rows with
  `name` and `kind`, where the table declares `array_asset_name` and no `kind` at all, and a
  `core.clocks` row with `name` for `clock_name`. `PacketWriter.add` documented such keys as ignored
  and dropped them, so an array asset went nameless through three tests for as long as they have
  existed. It refuses them now, and that refusal protects nothing in `fixtures/`.
- `fixtures/build.py` calls `pq.write_table` directly and never constructs a `PacketWriter`, so no
  corpus packet passes through the encoding rules at all. Measured: `core.spike_events.t_tick` is
  `RLE_DICTIONARY` in every corpus packet, which is the encoding R68 §3 wrote its SHOULD against and
  Part 03 §5.5 now tells a writer not to use.

The second is the sharper statement of the whole item. Every rule this repository has added about
how a packet is *written* — encodings, assigned identifiers, session fill, physical order — is
enforced on a path the corpus does not take, so the corpus can pass forever while the writer drifts.

**The corpus is not where this gets fixed, and that is settled rather than open.** 29 of its 30
packets are `valid` deliberately corrupted — `null_required` sets a required column to `None`,
`orphan_fk` points a row at a clock that does not exist, `unsorted_spikes` swaps two rows out of
order — and refusing exactly those corruptions is what `PacketWriter` is for: `unsorted_spikes`
raises `OrderViolation` while staging, and the other two fail Tier 1 at commit. `fixtures/build.py`
writes Parquet directly because that is the only way to produce a packet the writer would never
emit. Only `valid` could be built through the writer, and one packet is a test rather than a corpus.

The coverage says where to put that test. `clock.py` is at **95%** and `materialize.py` at **85%**,
so both modules that broke were covered and broke anyway; `session.py`, which drives a build — the
source loop, the harvest, the two staging paths — is the least covered module in the package at
**68%**, and its uncovered lines are that loop. Both bugs were interface mismatches between modules
that each pass their own tests, which is what an end-to-end test catches and a unit test cannot.

So the work is one test in `escapewheel-writer/tests/`: a small recipe with synthetic sources, run
through `session.py`, asserting the packet it produces — including that its encodings are the ones
Part 03 §5.5 asks for, which is the assertion no corpus packet can make. Sized at an afternoon, not a
restructuring, and best done after the open drafts are accepted, since it would assert what they
define and a test may not cite a draft any more than a revision may.

## 1a₃. The encoding residual is closed

**Done, 2026-09-10.** The item recorded **59 columns more than 15% off the best choice, worth about
400 kB**, and predicted where the fix would come from. R110 delivered all three: the float rule took
the high-cardinality floats, `core.unit_electrodes.electrode_id` became a declared exception, and the
recipe `[encoding]` block reached the extension columns "no rule reaches".

Measured against both packets as written, that left **five columns and 12.6 kB**, every one in
`aind_unit_qc.metrics` — an extension's table, which is exactly what R110 §3.4 exists for rather than
a gap in the rules. Three declarations close it: `firing_range` and `amplitude_median` take the
dictionary (1.30x and 1.32x over plain, both rounded by the analyzer), `isi_violations_count` takes
plain (1.15x, a small count with a long tail). Both recipes now carry them, `Recipe.encoding_problems`
returns clean, and re-encoding the table through the writer's own option path leaves **zero columns
over 15%** in either packet, taking `aind_unit_qc/metrics.parquet` down 9.8 kB and 5.0 kB.

The packets on disk are not rebuilt for it: 14.8 kB against a 1.16 GB packet does not earn a
fifteen-minute build, and the declarations apply to the next one. The recipes live outside this
repository, at `/mnt/Data/776259-packet/recipe.toml` and `/mnt/Data/786867-packet/recipe.toml`.

## 1a₂. The source cache defaults onto tmpfs

**Found by the rebuild, twice.** `sources/store.py`'s `cache_directory()` returns
`$TMPDIR/escapewheel-source-cache`, defaulting to `/tmp` — which on this machine is tmpfs, so every
object fetched from an S3 asset is held in **RAM that a cgroup cap does not bound**. Two builds of
`ecephys_786867` were killed for system memory pressure while capped at 24 GB and then 8 GB, because
the cap never applied to the pages that mattered.

The cache itself is right: `store.py` measures that an adapter reads `spikes.npy` twice and that the
second read costs another 344 MB over the network. What is wrong is where it lands by default, and
the honouring of `TMPDIR` is what makes the workaround one variable — `TMPDIR=/mnt/Data/tmp`.

Worth deciding whether a default that is RAM on any machine with a tmpfs `/tmp` is the right one, or
whether the cache should sit beside the packet as the materializer's scratch already does
(`dir=packet.root.parent`). The two temp locations in one build already disagree.

Threading the packet root down to `source_root` is the one shape to avoid: every adapter calls it
itself, so that is a parameter through ten constructors, which is what `_build_source`'s unification
just removed. `source_root` already takes a `cache` override, so a build setting the location once
before it constructs anything costs one call and no plumbing; `escapewheel inspect` constructs an
adapter with no packet in hand and is what still needs a default.

Two builds killed on 2026-09-13 were **not** this: both cache directories were empty, and `/tmp` held
**27 GB in four ~6.8 GB Python environments** that no build wrote. Attributing a kill to this item
needs the cache measured rather than assumed, since anything on a tmpfs `/tmp` presses on the same
pages.

## 1b. A code quality audit of the whole project

Asked for on 2026-09-06 and not started. Correctness, interpretability, maintainability, and
above all **which problem domains this project owns**: where a dependency already solves something
well, the code should not be solving it again. The reader's `Location`, the writer's store
abstraction, the registry's generators and the clock arithmetic are the places to look first.

The writer's arbitration layer is the newest candidate. `STATES`, `PREFERRED`, `SHARED` and
`RECIPE_SUPPLIES` are four tables consulted in different orders by `_resolve_ownership` and
`_note_unclaimed`, which is how they came to disagree about what a preference means — R108 §2.2
measures three entries where one reads the table and the other does not. One relation, derived from
each adapter's `PRODUCES`, would make every arbitration rule a query over it and make a stale entry
a failure rather than a silence; `core.unit_electrodes` sat in `PREFERRED` uncontested until R108
§3.4 struck it. Not a query engine: the relation is dozens of rows, and what SQL buys in
`rules.json` is that the queries are authored outside the code, which is not true here.

## 2. `registry_version` — still `0.1.0`

Unchanged through R48, R53's string-to-int32 change, R56, R81, R83 and every revision since. Two
packets claiming one version with incompatible schemas is what the field exists to prevent, and it
is preventing nothing. Free to settle while nobody outside holds a packet, and free to batch into
the rebuild. The four extension registries do bump: `dynamic_foraging` is at 0.3.0 and the other
three at 0.2.0.

## 2b. The repository directory is still `nwb-lake/`

R84 §2.1 renamed the repository and everything inside it moved. The checkout directory did not,
because renaming it mid-session breaks absolute paths in flight and `git mv` cannot rename the
working tree's own root. Both recipes name absolute paths into it, so this and the rebuild want
doing in one order or the other, not at once.

## 2c. Staging both packets to scratch needs a token

`aind-scratch-data` is not public, so `--no-sign-request` does not reach it. Roughly 1.2 GB and
700 MB excluding referenced LFP.

## 3. Nesting: containment is cheap, but not in SQL

**Measured 2026-09-02**, five repeats, on blocks derived from a real session (708 trials, 18
blocks, disjoint, minimum gap 5,750 ticks) and synthetic data at the same ratio:

| trials | blocks | range join | ASOF join | searchsorted | stored column |
|---:|---:|---:|---:|---:|---:|
| **708** | **18** | 1.46 ms | 1.54 ms | **0.02 ms** | 0.60 ms |
| 10,000 | 250 | 5.58 ms | 32.70 ms | 0.07 ms | 1.00 ms |
| 100,000 | 2,500 | 267.68 ms | 2,202.66 ms | 1.02 ms | 3.05 ms |
| 1,000,000 | 25,000 | 21,708.92 ms | 219,594.04 ms | **15.95 ms** | 32.21 ms |

**At real scale containment is free** — 0.02 ms, cheaper than reading a stored `block_id`
column, because the join returns indices where the column materialises a string per row. R43's
"an alignment is a query" holds, and no parent column is needed.

**At scale, neither SQL formulation is usable.** The operation is 16 ms at a million trials;
DuckDB's range join takes 21.7 s and its ASOF join 220 s. **The ASOF result contradicts the
prediction** — it was expected to fix the range join, being the formulation the reader already
uses to assign a spike to its preceding event, and it is ten times worse. A follow-up probe to
find out why timed out at ten minutes on 100k rows, so **the cause is not established.** Worth a
separate look; the conclusion does not depend on it.

**What follows:** the reader should own containment as an operation, the way it already owns
`aligned_spikes` rather than telling callers to write the join. The naive SQL is a trap that only
springs at a scale no packet has reached yet.

`dynamic_foraging.blocks` now declares that blocks may not overlap, which is what makes the
binary search sound: a trial inside two blocks has no containing block. Scripts in
`/mnt/Data/escapewheel/bench/nesting/` with the raw output in `results.txt`.

## 4. Parked: R42's write case

R42 is withdrawn on the read measurement (§ Settled below), and that stands. What did not fall
with it is the **write** cost: adding a sorting rewrites 650 MB (~48 s, growing with each sorting)
where partitioning writes one member (~4 s, flat).

A revision for that would be most of R42 §2 with a different §1 — the member array as a **MUST**
for a packet-owned prefix, rows as members concatenated in declared order, and R35's bound applied
per member. The ordering rule is *not* optional even without the performance argument: R12's
physical-order check and the 14 uniqueness checks riding on adjacency need a defined row order
across files.

**Not drafted, deliberately.** No session in the corpus has a second sorting, so the win is
hypothetical, and a revision drafted against an unpaid cost is how R42 came to sit proposed for a
week before being withdrawn. R42 §5 records what would reopen it: accumulated sortings, tables
outgrowing one file for other reasons, or multi-session packets making `session_id` partitioning
natural.

## 5. Smaller, still open

- **A second ergonomic surface** for people who avoid both SQL and raw PyArrow: DuckDB relations,
  a polars `LazyFrame` behind an extra, or both. Does not block anything.
- **No conformance variant for R51 or the shape check.** The fixture packet has no array resources
  and no external ones, so exercising either there means introducing an external Zarr plus whatever
  table rows the registry's rules expect of one — a larger change to the shared fixture than the
  checks it would cover. The validator's own tests cover every path. Worth revisiting when the
  fixture next needs an array for another reason.
- **A second trials table from another paradigm** would settle whether an interval's task columns
  belong in core. R54 struck the four Part 02 defined and nothing wrote, so the question is now about
  what an extension carries rather than what core does.

---

# Measured, for reuse

Scripts in `/mnt/Data/escapewheel/bench/`: `s3_tires.py`, `s3_backends.py`, `clients.py`,
`duckdb_s3.py`, `s3_full_verify.py`, and `partition/` (`make_parts.py`, `bench2.py`,
`local_window.py`). Both staged prefixes under `s3://aind-scratch-data/galen.lynch/` are removed;
nothing of ours is left in the bucket. Restaging is `aws s3 cp --recursive` of a packet.

**DuckDB, R30 §6's query shapes against `analysis.spike_events`** (a throwaway query first, or
the first query is charged 3.4 s of setup and the comparison inverts):

| query | local | S3 cold | S3 warm | rows |
|---|---|---|---|---|
| `count(*)` whole | 0.03 s | **0.24 s** | 0.09 s | 286,896,563 |
| units + window | 0.04 s | 0.56 s | 0.11 s | 884 |
| 10 s window | 0.04 s | 0.56 s | 0.11 s | 348,913 |
| 24 adjacent units | 0.15 s | 3.38 s | 0.21 s | 572,551 |
| 24 scattered units | 0.15 s | 3.37 s | 0.21 s | 757,259 |

Counting 287 M rows costs 0.24 s — the footer only. Pruning becomes round trips: selective
queries 0.56 s against broad ones 3.4 s. Object cache worth 16x. Cold 6–22x local, warm 1.4–3x.
**The SQL is byte-identical local and remote** — no query rewriting was needed for any of it.

*Harness flaw:* the "scattered units" set strides an unordered `DISTINCT`, so its row count
differs between runs. Timings are unaffected.

**S3 clients**, all agreeing key-for-key on the listing:

| client | list | 1 worker | 8 workers | new dependencies |
|---|---|---|---|---|
| boto3 | 0.102 s | 14.8 MB/s | 79.4 MB/s | botocore |
| s3fs | 0.130 s | 26.8 MB/s | 95.8 MB/s | aiobotocore + botocore + aiohttp |
| pyarrow.fs | 0.099 s | 13.6 MB/s | 79.4 MB/s | none, already required |
| obstore | 0.117 s | **35.4 MB/s** | **100.2 MB/s** | one Rust wheel |

Within 26% once concurrent, so the choice is dependency weight and scheme coverage. `stores.py`
now lives in the validator, with two users and both on the verification side — this package
checks what a manifest claims and the writer establishes it through `verify`. **obstore on merit,
pyarrow.fs on conservatism** if the client is ever revisited.

**R36 verification:** the digest is identical computed from S3 and from local disk
(`3660170e5c3f2205…`), so the canonical member listing is store-independent as intended.
Whole packet, 2,496 objects and 6.83 GB across twelve arrays:

| | list | digest |
|---|---|---|
| S3 | 1.31 s | 88 s |
| local disk | 0.33 s | 75 s (91 MB/s, cold) |

Against a whole-packet build of 1 min 51 s, which is what §2 turns on.

---

# Settled 2026-09-09

- **R89 through R108 are accepted and applied.** The item that stood here said R89 to R93 were
  drafted and none accepted; twenty of them landed since. `revisions/drafts/` is empty.
- **`vr_foraging.json` is drafted and shipped.** The extension carries `sites`, `site_odors` and
  `sessions`, with the `(session_id, site_id, odor_channel_index, concentration)` child table R3
  §2.1 forces, `odor_channel_index` as a `structural_index`, and the eleven ordinals within a scope
  declared `sequence_position` as R48 distinguishes. Units are on the columns rather than in prose,
  which is what R56 was drafted against.
- **`core.events.payload` no longer smuggles `trial_id`.** The NWB source stops writing it, and the
  comment where it did records that R11 §5 struck the column. Payload now travels only where the
  stream's data varies.
- **An interval's task columns are gone from core.** R54 struck the four Part 02 defined and nothing
  wrote, so `choice`, `rewarded`, `stimulus_id` and `condition_id` appear nowhere in the registry.
- **`registry/tables.html` is tracked.** The note saying it was deliberately untracked is stale.
- **The recipes no longer say `owns` where two sources each hold part.** See §1.

---

# Settled 2026-09-03

- **The extension mechanism, end to end.** A recipe names extensions by id (installed, via the
  `escapewheel.extensions` entry point) or by path; `PacketWriter` resolves a resource against core
  then extensions; a packet carries `extensions/<id>.json` and `layer: "extension"` entries;
  the validator generates checks with no per-extension code and reports them apart from core.
  Three at once is three times one — tested.
- **A source may be files.** `kind = "tables"` reads Parquet that already exists, optionally after
  running a `command` — an argument list, not a shell, with no opinion about environments, so
  nothing requires uv. Rows arrive as **names** and the writer numbers them, which is what lets an
  adapter run outside this process at all. An extension can now be *entirely data*: a JSON
  document and some Parquet, nothing installed and so nothing to rot.
- **`escapewheel.sources` entry point**, for the case that genuinely needs `Context`. Built-ins are
  consulted first so a plugin cannot shadow `sorter`; a broken one is skipped with its reason.
- **`escapewheel extension`** drafts a registry from Parquet. It writes no role, so the draft does
  **not** validate until a human finishes it — the first version guessed and the draft validated,
  which a test asserting it should not is what caught.
- **The invariant, written down:** an extension declares; it never ships code on the read path.
  The only code it may require is a source adapter, only to write, at the import boundary.

# Settled

- **R53 — identifiers are `int32`.** Measured: 10.2x on a join, 13.8x on selecting 24 units, 5.3x
  on `ORDER BY`, parquet 1.1% smaller. 96 assigned, 14 carried, 14 `*_name` columns. The reader
  needed no change at all, being type-agnostic. Migration is regeneration.
- **R52 — packet-owned resources record a digest**, and `--checksums` recomputes them. 0.60 s for
  1,209 MB, 0.5% of a build. Whole-file, not per-row-group: Parquet cannot be appended to, so
  "which pages moved" is not a question the format can be asked.
- **R56 — a column declares its unit and its clock.** `core.clock_anchors` carried two coordinate
  columns on different clocks, distinguished only by a description, with `parent_clock_id` not
  even a column of that table. Seven columns now declare their context; `check.py` verifies it
  resolves.
- **R17 exercised, then plumbed.** `registry/extensions/dynamic_foraging.json`, 17 checks with no
  per-extension code, validated and reported apart from core. A recipe and the writer now carry
  one end to end.
- **`escapewheel verify` — Phase 6.** Records what is true once the bytes land, as a new packet
  version with both manifests retained. 208 members with 208 store digests in 1.2 s against S3.
- **`pkt.table()` reads a remote table**, through `pyarrow.fs`. Schema 0.80 s, 6,781 rows 0.52 s.
- **Five defects the work surfaced.** `core.media_frames.media_asset_id` referenced nothing (the
  class R46 fixed sixteen of, missed by its own sweep). A foreign key was numbered in its own map,
  so `parent_clock_id` and `clock_id` diverged and the parent chain named a clock that does not
  exist — caught by the conformance corpus. Numbering depended on staging order. A damaged Parquet
  file crashed the ordering scan instead of producing a finding. And a vendored meta-schema went
  stale for the third time, now fixed by making it a build artifact `check.py` compares.

## Earlier, 2026-09-02

- **R53 accepted and implemented** — identifiers are `int32`. Measured: 10.2x on a join, 13.8x on
  selecting 24 units, 5.3x on `ORDER BY`, parquet 1.1% smaller. 96 assigned, 14 carried, 14
  `*_name` columns. Registry 292 → 306 columns, 70 → 71 references. Writer, fixtures and the
  corpus regenerated; the reader needed no change at all, being type-agnostic about identifiers.
- **R17 exercised** — `registry/extensions/dynamic_foraging.json`, 17 checks with no
  per-extension code, `trials` keyed to `blocks` by column rather than containment join.
- **Three defects the work surfaced.** `core.media_frames.media_asset_id` referenced nothing, so a
  frame naming an asset that does not exist validated clean — the class R46 fixed sixteen of,
  missed by its own sweep. A foreign key was numbered in its own map, so `parent_clock_id` and
  `clock_id` diverged and the parent chain named a clock that does not exist. And numbering
  depended on the order tables were staged in.

- **R52 accepted and implemented.** Every packet-owned resource records a `sha256` at commit,
  and `--checksums` recomputes them: a mismatch is an error, and a resource recording none is
  reported rather than passed over. 0.60 s for 1,209 MB, 0.5% of a build. Settled whole-file over
  per-row-group — Parquet has no append, so "which pages moved" is not a question the format can
  be asked, and its page CRC32 is a corruption detector a rewritten file passes (0.06% of bytes,
  measured, shelved).
- **`escapewheel verify` — Phase 6.** Reaches a store once the bytes have landed and records what is
  there, as a new packet version with both manifests retained. Three levels (`size`, `members`,
  `sha256`); validation narrowed to level 3 with `scan` and `recheck` empty, for the reason an
  amendment narrows them to what it wrote — here that is nothing. It also fills in a packet-owned
  digest missing from anything committed before R52. Verified against `s3://aind-open-data`: 208
  members with 208 store digests in 1.2 s.
- **`pkt.table()` reads a remote table**, through `pyarrow.fs`, which pyarrow ships — no new
  dependency. Credentials stay the caller's (R14 §2.3). Schema 0.80 s, 6,781 rows 0.52 s against
  S3. R14 §2.3's warning is unaddressed and still stands: an external table's rules cannot run at
  all when it is unreachable.
- **The two array shape paths are unified.** The external check compared rank and axis lengths
  where the packet-owned one compared only rank, though an owned array's shape is already in hand.
- **Column names are checked, standing** — R50 §5's last open item. Nine conventions over 292
  columns; R48's `role` makes seven of them exact rather than heuristic, and they flag nothing.
  Five exceptions are declared with reasons (`offset` ×3, `n_spikes`, `size_bytes`), and a stale
  exception fails as loudly as a new violation.
- **A damaged file is a finding, not a traceback.** Found while testing R52: flipping one byte in
  a Parquet file crashed the ordering scan with a ZSTD error. It now steps its iterator, so a
  decompression failure becomes `resource.unreadable` — and stays streaming, because materialising
  287 M rows of key columns is the 26 GB that scan exists to avoid.

- **R51 accepted and implemented.** `members` on an external prefix, `store_digest` per member,
  `validate --store-digests` as the level between listing and reading, and `verify = "members"` in
  the writer. Its evidence was corrected first: 2,394 of 2,496 members are single-part, not 208 of
  208, because the largest array has 102 chunks uploaded multipart — which turned §2.3's skipped
  count from a nicety into what stops a clean pass on an array half unchecked.
- **The writer's `verify` default stays `size`**, on measurement: 75 s local and 88 s from S3 to
  digest, against a 1 min 51 s build. A digest is a publication cost (§2), not a per-build one. The
  hollow `external.verified` that made that unsafe is fixed — it now names what it compared, and
  reports what it had nothing to compare against.
- **External arrays get a shape check.** Rank against `core.array_dimensions` and axis length
  against a coordinate table keyed by `(array_asset_id, axis_index)`. Free — the metadata document
  was already read for codecs. This is what catches a change that actually invalidates the packet;
  a content digest catches one that does not, since the packet claims nothing about an array's
  values.
- **R42 withdrawn.** Read case measured negative in both engines; pyarrow's apparent win is scan
  parallelism, reproducing at the same ratio on local disk with no round trips. Write case parked
  above.
- **`escapewheel init` can draft an `lfp` source**, and `LFPSource.offers` reports
  `core.array_channels`. Between them, why no recipe had ever set `verify`.
