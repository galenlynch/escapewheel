# TODO

Live work first, then measurements worth reusing, then what was settled and when. Reasoning for a
settled item lives in the revision it produced and in git history, not here.

## State of the world

The generated state below is checked by `uv run --project escapewheel-writer python verify.py` —
which is the way to check it rather than by reading this block.

<!-- BEGIN facts: revisions -->
R1–R41, R43–R72 and R74–R125 accepted. R42 and R73 withdrawn. 1 proposal and 0 drafts are open. Neither is binding; a draft takes no number until it is accepted.
<!-- END facts: revisions -->
<!-- BEGIN facts: registry -->
43 tables, 351 columns, 111 references, 76 Tier 2 rules (2 advisory)
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

1. **Define the publication model.** The current registry and its meta-schema now identify the
   rule-language-enabled development shape as `0.3.0` (Part 02 §9.2). The dependent authority
   work still needs to define the released artifact set, publication state, and identifier
   discipline before a production trial.

---

# Live

## 1. Packet resource classification needs its own proposal

**Not started; follow the normative-ownership proposal.** Part 00 uses *layer* for the content
classification `core`, extensions, `analysis`, and the deferred `nwb` projection. Part 04 requires
every resource entry to carry `layer` without defining its values, while
`registry/manifest.schema.json` permits `core`, `analysis`, `extension`, and `docs`. The reader,
writer, validator, and fixtures all consume the field, so this is a packet-contract disagreement,
not an editorial rename.

The proposal should decide whether resource classification is declared or derived. The cleaner
starting point is to remove `layer` and derive the class from the `resource_id` namespace together
with the packet's declared extension registries; there is no released compatibility obligation
requiring the redundant field to survive. Audit `canonical` in the same proposal: Part 04 says it
is required, the manifest schema does not require it, and its value may also be derivable from the
resource class. The resulting revision would update Part 00, Part 04, the incorporated manifest
schema if applicable, reader/writer/validator behavior, APIs, fixtures, and packet regeneration.

## 2. Other normative-ownership follow-ups are deliberately split

These do not belong in the first authority revision. Each has its own decision boundary and can
land after the specification release and ownership model identifies its proper owner.

- **Identify packet registries precisely.** A separate proposal should decide how a packet names
  the released core registry and each extension registry by stable identifier, version, and
  digest; when an embedded copy is required; what a validator compares; and whether existing
  packets are regenerated. This is a packet-catalog change, not part of defining a specification
  release manifest.
- **Replace registry replay with direct declarative authoring.** Choose one reviewed registry
  document or deterministically assembled fragments, retain provenance in accepted history and
  Git rather than the registry document, and prove that the migration preserves the released registry bytes or a defined
  canonical form. This is ordinary repository maintenance if the published contract is unchanged;
  any change to the published form returns through the revision process.
- **Audit the remaining JSON Schemas before incorporating them.** Compare
  `registry/manifest.schema.json`, `resources.schema.json`, `sources.schema.json`, and
  `adapter.schema.json` with their owning prose, examples, and fixtures. Incorporate each only
  after conflicts are resolved; file location or successful validation alone does not make a
  schema normative.

## 3. No template scaffolds an extension project

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

## 4. The adapter boundary reaches nine of the ten adapters

R115 was accepted on 2026-09-11 and Part 03 §11 carries the whole contract between a build and a
source; every piece of it was built by 2026-09-14 — a declaration, a document, a command, three
protocols and a report. The nine are delivered out of process on real data (`ecephys_786867` at
`--sample 2000`), and `conformance/adapter-boundary/` holds the seven scripts that measured all
three protocols delivering one adapter's eighteen resources identically. What follows is what the
boundary does not yet reach.

**Where a protocol is needed it is `flight-v0.1`**, decided 2026-09-12. R115 §3.3 asks one of an
adapter released independently of the build and none of an adapter the build ships, so the ten need
nothing today; what the decision settles is which protocol the writer's own server speaks, and which
one an adapter leaving this distribution implements. Flight owns the least of the three: a
descriptor is the format's, so the protocol invents no metadata key, and `ListFlights` answers
Part 05 §4.1's discovery and `DoGet` the per-resource fetch from Arrow's own vocabulary rather than
from surface we would have to specify and version. Leaving is what makes an adapter need a protocol.

**Core ships adapters for standards and not for institutions.** SpikeInterface, Open Ephys, Harp and
NWB are read by many institutions, so support for them is worth carrying centrally; `rig.json`
serves one. Measured against what each module actually names, the ten sort four ways:

| | adapters |
|---|---|
| generic | `sorter`, `sync`, `openephys`, `harp` |
| generic once the dialect leaves with the NWB split | `nwb`, `lfp`, `waveforms` |
| one institution's, whole | `session`, `video` |
| not an adapter | `tables` |

`session` is 707 lines of AIND's metadata schema and carries both `aind.*` compensations. `video` is
311 lines requiring a **headerless three-column CSV read positionally** — `COLUMNS = ("rig_seconds",
"frame_counter", "camera_nanoseconds")` — beside every `.mp4` with the same stem, with `frame_index`
derived from `frame_counter` and the `rx:Zip` pairing repair on top. One `ffprobe` call for
container metadata is the only generic part, so it leaves whole rather than as a carving.

`lfp` **is generic**, since 2026-09-16, and nothing left it. `processing/ecephys/LFP` is where
pynwb's own `LFP` container lives, and the Zarr v2 referencing, the axis description and the band
declaration are all format-level. Its one line of dialect recovered a probe from a series name NWB
does not constrain — `series.name.removeprefix("ElectricalSeries").removesuffix("-LFP")` — and that
was repaired rather than moved: an `ElectricalSeries` declares an electrode region, the contacts in
one belong to a single `ElectrodeGroup`, and `probe_of` now reads that. Measured on the ten real
series, the derivation and the parse agree in **10 of 10**, so no committed packet's
`array_asset_id` moves. What it costs is a dependency: a series names its probe from the electrodes
table, where parsing its own name needed nothing.

`waveforms` reads `waveform_mean`, `waveform_sd` and the ragged `electrodes`/`electrodes_index`, all
base NWB, and matches an array row to a unit by a **pair**: `(device_name, ks_unit_id)`, the probe
plus the sorter's label. A run is one probe (R83) and R81 measured 810 distinct labels across 6,781
units over 12 runs, so the probe is what makes the pair unique.

**One half of that pair is base NWB and the other is in no base column**, measured 2026-09-15 on both
sessions' files. The probe is derivable: each unit's ragged `electrodes` region spans exactly one
`group_name`, equal to `device_name`, in **6,781 of 6,781** and **4,505 of 4,505** units, and the
adapter already reads that column to name its contacts. The label is not. Reading the `Units` table's
own `id` was recorded here as the fix and is wrong — `id` is `arange(n)`, the `DynamicTable` row
number, and differs from `ks_unit_id` in **6,775 of 6,781** and **4,138 of 4,505** rows, because a
sorter numbers from zero within each probe while the row id counts the table. `unit_name` is where
NeuroConv writes a sorter's unit ids and holds a UUID in both files; `original_cluster_id` repeats
`ks_unit_id`.

**Row position is not the way out either.** `ks_unit_id` strictly ascends within each probe in file
row order — 12 of 12 devices in one session, 10 of 10 in the other — so the nth row of a probe is its
nth label and no dialect column is needed to pair them. What that spends is the detection: the NWB
and the sorted asset it derives from hold different sortings, pairing 4,322 of 4,505 units with **0
of 4,322** agreeing on spike count (`STATUS.md`, "Benchmark revisited"), and a positional match hands
a template to the wrong unit there, where the pair match skips the row and says so.

**Identity is the part no option makes generic.** An option names the column holding the label and
cannot make one exist, so an adapter configured that way reaches producers that wrote the label
somewhere rather than base NWB. Everything around it is base NWB and even the probe half of the key
is derivable, so this is one dialect read in an otherwise generic adapter, and it moves with the
split below rather than becoming an option of its own: a per-column option is the dialect mapping
rejected further down, rebuilt one column at a time. R119 §2.5 argues for that option and is not
taken up; what its Decision rests on is §2.2's 28 undeclared options and §2.3's constructor failure,
neither of which needs a dialect option to exist.

The repair recorded here is done: `units: {n} NWB row(s) match no unit or are all zero; skipped`
summed two causes and now counts them apart, since a wrong key is a different finding from a row the
file padded.

**The NWB adapter is half a standard's and half one producer's, and the split is a lift rather
than a rewrite.** The paths it walks are all base NWB — `general/subject`, `general/devices`,
`general/extracellular_ephys/electrodes`, `intervals/trials`, `acquisition/` — and about fifteen of
the columns it pulls out of them are ones base NWB does not define, which R59 measured varying
between two exporters of one pipeline. Those columns share rows with the standard ones, and R108
§3.2 forbids composing a row from more than one source, so the dialect cannot be split off as a
second adapter contributing columns.

What splits is the **code**, and how was decided 2026-09-15. The base NWB reader **stays in
`escapewheel-writer`**, since core ships adapters for standards; the dialect becomes its own adapter
that calls the base one as a library for its internal processing and emits whole rows of whole
resources. Ownership between the two is the arbitration that already exists — the recipe declares
which owns `core.electrode_coordinates` (Part 05 §3.3), and R108 §3.1 refuses a preference that
discards a value the passed-over source stated — and whole rows rather than contributed columns is
R108 §3.2. Sharing the reader is safe across a release boundary because R115 §3.9 lets an
out-of-process adapter import whatever version it was written against: the boundary unshares the
environment, so a shared library is not a shared closure.

**`escapewheel-aind` exists and holds two of the three**, 2026-09-16. `session` (726 lines) and
`video` (323) moved with `git mv`, so `git log --follow` reaches back through it; the NWB dialect
follows once the carve below is done. The distribution depends on the writer as the writer depends
on the validator — a `[tool.uv.sources]` editable path — registers both kinds through the
`escapewheel.sources` entry-point group that `sources.discovered()` already loaded, and joins
`verify.py`'s `SUITES` and the CI package loop. Nothing in the writer imports it, which
`test_boundary.py` asserts by parsing the writer's imports rather than by matching the name, since
a docstring may name what it must not import.

**Two writer registries had to open for the boundary to be real.** Both named a departing kind and
neither could be checked from the writer once it left. `COMPENSATIONS` was the hard case:
`compensate()` raises on an unregistered id, and three of its six entries — the two `aind.*` and
`video.zip_pairing_repaired` — belonged to the movers. `PREFERRED` was the quiet one: nothing
breaks at build time, because `_resolve_ownership` and `_refuse_a_discarded_fact` both guard with
`in kinds`, but `core.subjects` named `session` and no writer test could see that kind again. Each
now merges built-ins with an entry-point group — `escapewheel.compensations` and
`escapewheel.preferences` — on the terms `extensions.installed()` already set: a broken
distribution is skipped with its reason, and a registered entry never replaces a built-in one.

**A recipe naming one of these kinds now declares how a build reaches it.** `_builtin()` is false
for a registered kind, so `_delivery_problems` refuses it unless the recipe sets `in_process` or a
`[source.delivery]` command (Part 05 §3.9). The refusal names the kind and says what to add, and no
recipe is tracked in this repository, so nothing broke — but a real AIND recipe needs the line.

**The three real recipes now deliver every registered kind out of process**, 2026-09-17. Each names
`aind_nwb` where it named `nwb`, and each of its `session`, `aind_nwb` and `video` entries carries a
`[source.delivery]` block: a `declaration` written by `escapewheel declare` into the packet's own
`declarations/`, and a `command` naming the environment `escapewheel-aind` is installed in. The
protocol is `stream-v0.1`, left to the document rather than restated in the recipe, since the
adapter is what knows it. Checked from the **writer's** venv, where `discovered()` is empty and
`aind_nwb` cannot be imported at all — so what settles ownership before a build launches anything is
the document, which is the boundary doing its work rather than being stepped around. All three
report **0 errors**, and `session.order` puts `aind_nwb` ahead of `session` in each.

**A kind is matched by name, so renaming one is a cross-package edit.** `session.order` raises on a
`CONSUMES` entry the recipe does not declare, and `escapewheel_aind.SessionSource` declared `nwb` —
which the rename made unsatisfiable, loudly and in every recipe at once. It now declares `aind_nwb`,
pairing the adapter with the NWB reader it ships beside. The cost is that this `session` can no
longer be ordered against the base `nwb` adapter; no recipe wants that pairing, since a recipe
reaching for AIND's session metadata is reading an AIND NWB.

**`df-packet` was four resources short and nothing had said so.** It owned `core.electrode_coordinates`
and `core.unit_coordinates` without `core.coordinate_frames`, `core.coordinate_frame_axes`,
`core.electrode_coordinate_values` or `core.unit_coordinate_values`, so two declared references
resolved to a table no source owned. R63 §2 is exactly this: an omission contradicts nothing, so the
recipe passed every test the tool applied until the reference check ran. The four are added; its
NWB carries `ccf_ap`, `ccf_dv`, `ccf_ml` and `brain_region_id` on its electrodes, so they are real
rows rather than an empty claim.

**`PREFERRED`'s one entry now arbitrates nothing.** `{"core.probes": "nwb"}` names a kind no real
recipe carries any more, and `_resolve_ownership` guards with `preferred in kinds`, so it is skipped
rather than wrong. It cannot simply move: `preferences()` keeps the built-in and warns when a
registered entry redefines a resource, so `escapewheel_aind` cannot claim `core.probes` for
`aind_nwb` even though it is the kind that should win it. Two writer tests still exercise the entry
against the built-in `nwb` kind and pass. This is the staleness R108 §3.4 found by hand and
`test_every_encoding_exception_names_a_column_that_exists` guards for encodings — a preference naming
a kind nothing registers wants the same check.

**The inventory is done**, 2026-09-16, and it is
[`inventory/nwb-adapter-base-and-dialect.md`](inventory/nwb-adapter-base-and-dialect.md): every read
classified against the schema the file itself caches, `specifications/core/2.9.0`. Base NWB defines
**36** of the names this adapter reads and one producer's pipeline **17**, plus three conventions no
call site shows — a device's model and serial packed into its `description`, an instrument named in
a stream's prose, and the `_time` suffix `event_type` strips.

**Moving methods will not separate them.** Of the 18 resources the adapter produces, 4 are base
throughout, 2 are dialect throughout, and **12 are base reads with a seam** of a line or two — a
column name, a dict entry, a regex. That is what the shape decided above handles and what a
method-level carve would have broken: the dialect adapter calls the base reader as a library and
emits whole rows, so no row is composed from two sources (R108 §3.2).

Two findings change what a base reader can do at all. `core.electrodes` takes its identifier from
`channel_name`, which **no version of the NWB schema defines** — SpikeInterface reads it out of
files it did not write, so it is the sorting ecosystem's convention rather than this rig's, and
`_electrode_ids` raises `KeyError` where it is absent. And `core.devices` loses the serial: **0 of
10** devices set the `serial_number` core 2.9.0 defines, all 10 pack it into `description`, so a
base reader emits ten devices with no serial and the collapse to seven physical objects does not
happen.

**The carve is done**, 2026-09-16. `NWBSource` keeps all eighteen resources and gains hook points —
`FRAME_AXES`, `UNIT_AXES`, `TRIAL_EVENTS`, `TRIAL_MAPPED` and `CARRIED_ELECTRODE` as class
attributes, `_device_identity`, `_local_electrode_label`, `_annotation`, `_unit_identity` and
`_signal_device_id` as methods reading only what core 2.9.0 declares — and
`escapewheel_aind.nwb.AindNWBSource` subclasses it, supplying the seventeen columns and three
conventions in about 120 lines. It declares the two unit-coordinate resources the base reader now
does not, and `units` in its `NEEDS` where the base reader dropped it. Both fixtures split the same
way: the writer's writes base NWB, and the dialect's writes base plus what this pipeline adds.

Both findings above were repaired rather than recorded. A contact falls back to `(group_name, id)`
where a file states no `channel_name`, so the reader opens a strictly base NWB instead of raising;
and `core.devices` reads the three attributes core 2.9.0 declares, leaving the packed-description
parse to the dialect. Neither changes a committed packet, since both real files carry
`channel_name` and both are read by `aind_nwb`.

**Every adapter now serves a standard, one institution, or nothing but a protocol.** Seven are
generic — `sorter`, `sync`, `openephys`, `harp`, `nwb`, `lfp` and `waveforms` — three are one
institution's and live in `escapewheel-aind` (`session`, `video`, `aind_nwb`), and `tables` is
`files-v0.1` wearing the interface. No adapter in the writer reads a column no standard declares.

**`waveforms` was never a dialect; it was mis-sourced**, and re-sourcing it on 2026-09-16 removed
the dialect read as a side effect. It read `waveform_mean` out of the NWB, which is a *derived
copy* of the analyzer's `extensions/templates/average` — the same array in both — and paid for the
copy three times over. `(device_name, ks_unit_id)` existed only to rejoin rows to the identity the
sorter had already minted, since the export renumbers by `DynamicTable` position. The export also
densifies to every channel, so `units/electrodes` was a constant `[0 … n]` on every unit and the
support could only be recovered by scanning for non-zeros. And it declares `unit: "volts"` with no
conversion on values reaching ±1654.

The analyzer states all three: `sorting/unit_ids`, equal to the `local_unit_label` that
`core.units` carries and identical to the curated sorting's own ids on **10 of 10** streams;
`sparsity_mask`, keeping **6.7%** of the rectangle at 14 to 26 contacts a unit; and
`settings.return_in_uV`. So the join is `self.units[(stream.device, str(label))]` — the key the
build already supplies — and the adapter reads no electrodes table at all, naming contacts from
the sorting's own channel list exactly as `sorting_run_channels` does. It also gains a fact the
export never carried: the sample axis begins at `-ms_before` rather than at a guessed centre.

**The evidence first published here described the wrong asset**, corrected 2026-09-16. Every figure
— 4,559 units, 210 samples, `ms_before 3.0` — came from
`ecephys_786867_…_sorted_2026-01-10_10-30-10`, a SpikeInterface 0.103.0 sorting **no packet uses**.
`/home/galen.lynch/Downloads/AnotherNWBCreationTracker-2026-09-06.xlsx` names the authoritative one
per session in its `Sorted file` column, and both recipes' `sorter` sources already pointed at it.
Measured against those instead: 786867's `sorted_2026-07-29_16-03-08` (SpikeInterface 0.104.7) is
10 streams and **4,505 units, exactly the committed packet**, 150 samples at `ms_before 2.0` so the
origin is −60, and 373 to 384 channels varying per stream as R83 predicts. 776259's
`sorted_2026-08-11_14-40-50` is 24 streams over two experiments, of which `experiment1` is 12
streams and **6,781 units, exactly its packet**. There was never a 54-unit discrepancy to explain;
it was two different sortings being compared.

**The three recipes now name the analyzer**, each matching its own `sorter` source:
`776259-packet` and `df-packet` and `786867-packet` all point `waveforms` at the `s3://` prefix
their sorting lives under, with `experiment = "experiment1"` on 776259 to match its sorter's scope.
`df-packet`'s sorted tree carries no `postprocessed/` at all, so it reads 786867's asset; its local
curated `unit_ids` agree with that analyzer's on **10 of 10** streams, checked rather than assumed.
Backups sit beside each as `recipe.toml.bak`.

**Reading a sorted asset on a store is what made that possible.** `zarr_compat.DenseV2` decodes a
rank-N Zarr v2 array from its chunk bytes as `read_array` does for rank 1, so it asks a path only
whether it is a file and for its bytes — which a cached `simplecache::s3://` path answers exactly
as a local one does, and which keeps the `#` in `…Record Node 109#Neuropix-PXI-100…` a path segment
rather than the URL fragment `zarr.open_array` truncates at. Verified identical to zarr on every
slab of a `(586, 210, 384)` array chunked `(74, 27, 96)`, edge chunks included, and run end to end
against S3: 534 units cut in 15.2 s with **0 missed and 0 blank**.

**One contact-naming rule now serves all three readers of an electrodes table.**
`nwb.contact_ids` composes every contact's name, falling back to the row `id` where a file states
no `channel_name`, and `nwb`, `lfp` and `waveforms` all call it. Before this they disagreed: the
base reader fell back while the other two refused outright, which would have minted one contact
under two spellings — and a writer numbers a name (Part 05 §8), so the packet would then reference
a row that is not there. This is the `prefix` coupling recorded below, fixed for the half that had
a rule to share.

**The plumbing is separated**, 2026-09-15 at `f1ef6f1`, which is the prerequisite: `SourceDefect`
and the sex and UTC-offset helpers left `nwb.py` for `sources/defect.py` and `sources/values.py`, so
lifting the NWB reading no longer drags the base exception type and two core-vocabulary helpers out
from under `harp`, `openephys`, `video` and `sorter`. `nwb.py` is imported by three files rather than
eight, and the two that remain take `electrode_name`, which is NWB contact naming and travels with
it.

It is cheap because the boundary work already done is the extraction. `sources/nwb.py` needs exactly
two things of the build — `Clock` and `StagedArray` — and R115 §3.1 has the reference clock cross as
its identifier and rational rate, while §3.8 has an array cross as a reference. What lifts is
`nwb.py`, `zarr_compat.py` and `store.py`, **1,677 lines touching nothing of the build**.

A **dialect mapping** — a recipe-named document of candidate column names per core column — was
designed and rejected: it existed only because the row-level split looked blocked, and a rename map
would not have covered what actually differs anyway — three columns becoming rows with an
`axis_index`, a delimited `ccf_structure_id_path` that R3 §3.0 forbids, or a unit. Where a source
needs converting rather than renaming, the general form already exists: a command producing Parquet,
delivered as `files-v0.1` (R109 §3.2).

**`tables` is the tenth and is not an adapter; it is `files-v0.1` wearing the interface.** It knows
no format and normalizes nothing: it runs the recipe's command, reads row counts from Parquet
footers, hands back `pq.ParquetFile(path).iter_batches(...)` per resource, and refuses where a
declared file is missing — which is the protocol's definition, Part 05 §4.1's discovery, and
Part 05 §4.4's completeness test respectively. It is the one adapter needing an exception to every
adapter rule: `PRODUCES` is empty with a comment saying what it supplies "is not a property of the
adapter at all", `STATES` is empty, and `records()` returns nothing. So it declares no protocol — a
build must support `files-v0.1` natively (Part 03 §11.1), and once it does, a source entry naming
`{resource: path}` with an optional command **is** a delivery and the class goes away. `kind =
"tables"` can stay as the recipe's spelling for one.

It delivers in process — the 2026-09-14 rebuild committed all six of its resources, including
`aind_unit_qc.metrics` at 4,505 rows — so the `extract_qc.py` defect recorded here previously, which
writes `session_id` as the integer `0`, bites only when the rows cross a protocol. Confirm which
before planning around it.

**An optional option cannot be declared, which is a gap in R115 §3.1.** A declared name resolves
against the terms first and the recipe's options second, and one resolving to neither is refused, so
declaring an option makes a recipe carry it. R115 §3.1 argues an adapter declares its options so a
build can refuse a recipe setting one the adapter ignores — and that reasoning wants every settable
option declared, which the refusal rule forbids for any option with a default. So `NEEDS` carries
terms plus the options an adapter cannot be constructed without, and every option carrying a default
keeps flowing through the recipe's own dict unvalidated. Worth a clause giving `needs` an optional
half.

Measured 2026-09-15: the ten adapters take **32 constructor options beyond their `NEEDS`**, 28 of
them the recipe's to set — the other four being `store` on three adapters, an injection point the
tests use, and `first_samples`, a term a build fills. The two committed recipes set
**10 distinct names** between them: `attachments`, `command`, `emit_clock`, `experiment`,
`interval_kind`, `parent_clock_id`, `sd`, `signals`, `tables` and `zone`. Nothing checks any of the
28 today, and the declared label column and series pattern above would each add one more.

**`prefix` is the coupling left behind**, and the fix is one reader, one function, three callers.
Three adapters must compose one contact's name identically, and a recipe setting `prefix` on one and
not the others makes two electrodes of one. It fails loudly rather than silently, which is why it is
not urgent.

**Five sites drop a prefix rather than a label**, all in `sources/nwb.py`: `device_name`,
`probe_name` and `event_stream_name` are set to the name without the recipe's prefix that the
identifier carries. Inert while every packet is built at prefix `""`, and an R85 collision the day
two sessions are merged under different ones. Recorded as exceptions in
`test_a_name_records_what_its_identifier_stands_for`, which reads the adapters statically, refuses a
sixth, and checks each exception still names a row that sets one.

**One fact of the harvest has no channel at all.** R99 §3.2's terminal-anchor result is per probe
clock, the sync source computes it, and the *sorter* owns those rows — so it is a fact about another
source's rows, which no resource carries and no report key holds. A delivered sync leaves
`withheld_first_anchor` and `withheld_last_anchor` null where an imported one fills them, and the
build says so rather than leaving the packet quietly poorer.

**A delivered source that states facts needs a `report_path`.** Without one it states nothing, its
`STATES` values never cross, and the recipe's declared values stand — which moved
`core.sessions.session_end_time` by 17 minutes in the trial run. Conforming and not silent: a build
notes each one as `went unchecked; session states none`, twice per fact. Name a report path in any
recipe that delivers `session` or `nwb`.

Done for the three real recipes, 2026-09-17: `session` and `aind_nwb` each name
`reports/<kind>.json`, and `video` names none because its `STATES` is empty and `REPORT_AS_FILE`
would carry nothing. The comparison is visible in the check's output — six warnings per recipe
reading `subject.subject_id is declared and aind_nwb, session states it; the build compares them`,
which is R87 §2 reaching a delivered source for the first time.

**Parked: what a nullable identifier's null means.** Nothing obliges an adapter to report a value it
could not fill — Part 09 §5.8's report is a MAY — so a consumer cannot tell
`core.array_channels.electrode_id` null meaning *this channel maps to no contact* from null meaning
*I gave up*, and that is true of every nullable reference in the registry. `lfp` now refuses rather
than writing such a null, and the column is null in **0 of 1,152 and 0 of 960** rows of the two
packets, so there is no instance to write a rule against. Worth a revision when something produces
one.

## 5. No code quality audit has run

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

## 7. The repository directory is still `nwb-lake/`

R84 §2.1 renamed the repository and everything inside it moved. The checkout directory did not,
because renaming it mid-session breaks absolute paths in flight and `git mv` cannot rename the
working tree's own root. Both recipes name absolute paths into it, so this and the rebuild want
doing in one order or the other, not at once.

## 8. Staging both packets to scratch needs a token

`aind-scratch-data` is not public, so `--no-sign-request` does not reach it. Roughly 1.2 GB and
700 MB excluding referenced LFP.

## 9. Parked: R42's write case survives its withdrawal

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

## 10. Smaller open items

- **Trial-in-block containment has no consumer.** The measurement below concluded that a trial
  needs no stored parent, and `dynamic_foraging` ships one anyway: `blocks` carries `start_tick`
  and `stop_tick` over 19 rows, and `trials.block_id` is populated in **450 of 450 and 708 of 708**
  rows with no nulls. That is not a contradiction — the measurement compared the *lookup* with the
  blocks given, while what the extension's producer does is derive the blocks, a contiguous-run
  grouping a consumer cannot get from a binary search. The general case, one `core.intervals` kind
  contained by another, arises in no packet: both hold exactly one `interval_kind`. So a reader
  operation waits for something to ask for it.
- **DuckDB's ASOF join is ten times worse than its range join, and nobody knows why.** It was
  expected to be the fix, being the formulation `alignment.aligned_spikes` already uses, and it
  measured 220 s against 21.7 s at a million trials. A follow-up probe timed out at ten minutes on
  100,000 rows, so the cause is unestablished. Nothing depends on it.
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
- **Part 02 §5.2's exclusion of `list` has lost its Julia argument.** R3 §2.3 excluded `list`, which
  it calls core Parquet, because Parquet2.jl cannot read one. Every Julia read of a packet now goes
  through DuckDB.jl, which reads lists (R3 §7.3), so what still supports the exclusion is the lower
  implementation floor R3 §2.3 also argues. Worth re-deciding before a table next wants a repeated
  value inline.

---

# Measured, for reuse

**Containment, four ways** (2026-09-02, five repeats), on blocks derived from a real session —
708 trials, 18 blocks, disjoint, minimum gap 5,750 ticks — and synthetic data at the same ratio.
Scripts in `/mnt/Data/escapewheel/bench/nesting/`, raw output in `results.txt`:

| trials | blocks | range join | ASOF join | searchsorted | stored column |
|---:|---:|---:|---:|---:|---:|
| **708** | **18** | 1.46 ms | 1.54 ms | **0.02 ms** | 0.60 ms |
| 10,000 | 250 | 5.58 ms | 32.70 ms | 0.07 ms | 1.00 ms |
| 100,000 | 2,500 | 267.68 ms | 2,202.66 ms | 1.02 ms | 3.05 ms |
| 1,000,000 | 25,000 | 21,708.92 ms | 219,594.04 ms | **15.95 ms** | 32.21 ms |

At real scale the lookup is free — 0.02 ms, cheaper than reading a stored `block_id`, because the
search returns indices where the column materialises a string per row. At a million trials it is
16 ms while DuckDB's range join is 21.7 s and its ASOF join 220 s, so the naive SQL is a trap that
springs only at a scale no packet has reached.

**The blocks are taken as given, which bounds what this settles.** `blocks.py` derives them from
the trials — a contiguous run sharing a reward-probability pair — because nothing recorded them
when this was measured. `dynamic_foraging` now does, and its `trials.block_id` is populated in
every row, so R43's "an alignment is a query" holds for the lookup and says nothing about the
grouping that produces the blocks.

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

# Settled 2026-09-15

- **R118 is accepted and applied.** Part 03 §5.5's encoding rules are four, over declared order and
  counted repetition, with 12 exceptions for core tables in the writer and 5 entries in the two
  recipes under `/mnt/Data`. Both packets were rebuilt under it the same day and
  promoted. Every table holds the same rows and values, except `core.processing_runs`, whose import
  run records the changed recipe; 213 and 222 columns changed encoding, none sits 1.15x or more off
  its best, and the tables shrank by 686 kB and 272 kB. Both validate at their paths with 0 errors
  and the one `core.clocks.tick_zero_plausible` warning. The packets they replaced, and the
  recipes' R110-era `[encoding]` blocks, were deleted the same day.
- **Julia reads a packet through DuckDB.jl, and the delta encodings stay.** Parquet2.jl, the
  pure-Julia reader, decodes none of `DELTA_BINARY_PACKED`, `DELTA_LENGTH_BYTE_ARRAY`,
  `DELTA_BYTE_ARRAY` or `BYTE_STREAM_SPLIT`, in 0.2.34, the latest registered version, or on its
  `master` branch at the commit of 2026-09-01, so all six tables of `ecephys_786867` tried fail on
  their first delta column. DuckDB.jl 1.5.2 reads every one, in process. R3 §2.3 had weighed DuckDB.jl
  and chosen Parquet2.jl, but R3 §7.3 tested list columns and never an encoding. Of three ways out —
  name DuckDB.jl, drop delta at 1.24x on `core.spike_events.t_tick` and a rebuild of every packet, or
  add delta decoding to a package this project does not own — the first was chosen, since no packet
  changes. `conformance/parquet-probe/readers.py` and `readers.jl` record and reproduce the
  DuckDB.jl result; Part 02 §5.2 and Part 07 §2.2 name no reader and stay true. What the
  choice leaves open about `list` is a smaller item under §8.

---

# Settled 2026-09-14

- **An extension can be checked.** `escapewheel extension check <document> --registry <core>` runs
  the invariants any registry document is held to, which were a script in this repository and are
  now `escapewheel_validator.registry_document`: **31 to 35 per document**, depending on what its
  tables declare. `registry/check.py` imports the same `structural` and `declarations`, so core is
  held to exactly what an extension is and the two cannot drift; its own report is unchanged at 206
  lines. `--packet` reads the core registry a packet embeds (R2 §8) instead of a path, since that is
  what an author has to hand, and `--all` lists the invariants that held as well as those that did
  not. Checking the four shipped extensions is now a test rather than a side effect of their sitting
  beside the script. `escapewheel extension` gains a verb: `draft` is what it did, `check` is new.
- **A build is driven end to end by a test.** `escapewheel-writer/tests/test_build_end_to_end.py`
  writes synthetic sources to disk, names them in a recipe, and runs `session.build` and
  `PacketWriter.commit`, which nothing did: `fixtures/build.py` calls `pq.write_table` directly, so
  every rule about how a packet is *written* was enforced on a path the corpus does not take. Five
  assertions, in **1.1 s** on ten spikes and two probes — the packet commits with 0 errors, a
  clock's name is what its identifier stands for (R95 §3.1), every session-scoped table's
  `session_id` is non-null including the streamed one (R88 §2.3), the encodings are the ones
  `encoding.encodings` chose (Part 03 §5.5), and the records path and the streaming path produce
  identical Parquet for one table. Each was checked by mutation rather than by assertion alone:
  writing the human label into `clock_name`, skipping the streamed session fill, and dropping delta
  encoding each fail exactly one test and the other four pass.
- **Both packets are rebuilt and promoted.** `packet-rebuilt-2` of 2026-09-14 replaced the
  committed original in `/mnt/Data/776259-packet/` and `/mnt/Data/786867-packet/`, and the original
  and the 2026-09-12 intermediate were deleted; each session now holds one packet, at the path its
  recipe's `out` names. Both validate at that path with **0 errors and 1 warning**, the warning
  being `core.clocks.tick_zero_plausible` on a harp counter running from device power-on 167 and 498
  days before its session. What the originals lacked, measured against them before they went:
  **32 and 34 tables against 40**, with calibrations, coordinate frames and their axes, electrode
  and unit coordinate values and clock phase steps absent entirely, and
  `core.clock_observation_intervals` holding **1 row where the rebuild holds 13 and 11** (R98 §2.1).
  That last defect made a derived table wrong rather than thin: `core.spike_events` is identical in
  both, so the originals' `analysis.spike_events` had silently dropped **19,704 and 9,398 spikes**
  falling outside a window that had one row.
- **A channel index resolves through the run's kept list.** `escapewheel_reader.channels` offers
  what Part 02 §12.2 requires of a consumer: `kept_channels` reads `core.sorting_run_channels`,
  `electrode_at` performs the lookup over one index or an array of them, and
  `runs_without_channels` names the runs no index can be resolved for. A run declaring no channels
  raises `UnresolvableChannelIndex` rather than falling back to `core.electrodes`, and the
  exception's `channels_declared` separates that from an index outside a list the run did declare.
  Measured on the two rebuilt packets: **3,375 of 4,510** indices in `ecephys_776259` and **1,651
  of 3,813** in `ecephys_786867` name a different contact than the contact list would, eleven of
  twelve runs and seven of ten having dropped channels, one diverging at index 2. One run dropped
  three contacts from the tail and shifts nothing, which is how the convention stayed invisible.
- **The source cache lands where the build names it.** `source_root` passed `cache_storage` nested
  under `simplecache={...}`, the chained-URL form fsspec documents and which UPath parses and then
  drops: the filesystem came back with `storage` at a `tempfile.mkdtemp()` while the directory
  `source_root` had just created stayed empty, so every fetched object went to tmpfs — RAM a cgroup
  cap does not bound, which is what killed two builds capped at 24 GB and 8 GB. The option goes at
  the top level with the target's options under the protocol name. `Recipe.load` now places the
  cache in the packet's parent directory before it resolves the first root, since a store root is
  opened through a chained path carrying the location; `ESCAPEWHEEL_SOURCE_CACHE` carries it to a
  delivering command, which is not a Part 03 §11.2 supplied term.

---

# Settled 2026-09-10

- **The actor audit is complete.** All **176 normative sentences that name an actor** were read
  against R111 §3.1's line — a reader is bound by what it returns, a consumer by what it concludes.
  **Seven were repointed**: Part 01 §3.9's reader became a consumer, Part 00 §5 and Part 06 §1's
  consumer became a writer, Part 03 §6 and Part 05 §11 left `implementation` for a validator and a
  writer, and Part 09 §8's five anti-patterns split across three actors. Every `build` clause was
  already correct and 36 of 37 consumer clauses were, which is the result worth keeping. The
  distribution now runs writer 75, consumer 37, validator 26, build 24, reader 20, and
  **implementation 2**.
- **The encoding residual is closed.** The item recorded **59 columns more than 15% off the best
  choice, worth about 400 kB**; R110 delivered all three predicted fixes and left **five columns and
  12.6 kB**, every one in `aind_unit_qc.metrics` — an extension's table, which is what R110 §3.4
  exists for. Three recipe declarations close it: `firing_range` and `amplitude_median` take the
  dictionary (1.30x and 1.32x over plain), `isi_violations_count` plain (1.15x). Both recipes carry
  them and `Recipe.encoding_problems` returns clean, leaving **zero columns over 15%** in either
  packet.

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
- **The recipes no longer say `owns` where two sources each hold part.**

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
