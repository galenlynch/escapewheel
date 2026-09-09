# A Column Declares Its Vocabulary

| | |
|---|---|
| **Status** | Draft |
| **Amends** | `02` §9.3 (a vocabulary is declared, not defaulted), R8 §4 (the test a reservation must pass), R11 §4 (strikes `event_type`'s reserved set), the registry meta-schema, and every string column's declaration |
| **Depends on** | R8 (open vocabularies and reserved values), R11 (the reserved event types), R22 §3 (a scorer's label and its source), R48 (a column declares its role), R55 §2.1 (a discriminator's value space), R91 §3.1 (which table declares `event_type`) |
| **Profile** | all |

Normative, except §2 and §6, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

R8 §4 declares a vocabulary **open** so a packet may name what the standard has not seen, and
**reserves** some values so two packets cannot spell one thing two ways. `02` §9.3 supplies the
default that makes openness free: a vocabulary is open unless the column declares an `enum`.

That default is what this part removes. A column saying nothing about its values is
indistinguishable from a column whose vocabulary nobody classified, and the registry holds 102
string columns of which 84 say nothing — `core.probes.probe_type`, whose values a consumer
compares across packets, beside `core.curation_versions.notes`, whose value means something only
to whoever wrote it.

Every string column now declares which of three kinds it holds, a reservation gets a test, and
the three sets reserved so far are settled: one recorded, one struck, one deferred.

Measured on the registry as built at R100, and on the two packaged sessions — **`ecephys_776259`**
(twelve probes, 6,781 sorted units, recorded 2025-04-09) and **`ecephys_786867`** (ten probes,
4,505 units, recorded 2025-09-25).

## 2. Background

Informative.

### 2.1 Nothing reads the field that says a vocabulary is open

15 columns declare `vocabulary: open`, and no code reads the field. The validator's Tier 1
generator builds its membership check from `enum` alone (`generate.py:301`), `registry/render.py`
counts closed vocabularies and not open ones, `registry/check.py` has no check on it, and
`registry/build.py` is its only writer.

A validator therefore behaves identically on the 15 columns declaring it and the 84 that do not,
which `02` §9.3 guarantees by making open the default. The field is a comment in the shape of a
declaration, and which columns carry it records which revision remembered.

### 2.2 Three sets were reserved and none reached the registry

R8 §4 reserved four values for `core.array_assets.kind` — `raw`, `ap`, `lfp`, `waveform` — with
declared meanings, R11 §4 reserved six for `event_type`, and R19 §3 reserved `probe`, `ccf` and
`stereotaxic` for `coordinate_frame`. The registry carries **none of the three**.

`kind`, the column the mechanism was invented for, never received a set, and neither did
`coordinate_frame`. `event_type` did:
`build.py` sets `reserved_values` on `core.events.event_type`, and R91 §3.1 moved `event_type`
onto `core.event_streams` while R91 §3.2 struck the original, taking the reservation with it. The declaration
was not reconsidered and not restated — it went with the column it was attached to.

So `reserved_values` is a field the meta-schema declares, one build block sets on a column that no
longer exists, and **no column in the registry carries**. `registry/rules.json` names it 0 times.

### 2.3 A marker rides on a column, so it does not travel

The reservation was lost the way a marker is lost whenever it belongs to a column rather than to
the vocabulary the column holds. Four vocabularies span more than one column, and three of them
are declared inconsistently:

| vocabulary | columns holding it | declaring open |
|---|---|---|
| a physical unit (`unit`, `*_unit`) | 8 | 1 |
| `coordinate_frame` | 2 | 1 |
| `activity_type` | 2 | 1 |
| `semantic_type` | 3 | 3 |

`core.unit_coordinates.coordinate_frame` shows what the omission costs. Its description reads
*"The frame these coordinates are in. Open, as R19 §3 left it."* — the openness stated correctly,
in a string no rule can read, which is R66 §1.4's argument turned on the registry rather than on
`metadata`. Its neighbour `coordinate_basis` did travel, because R58 §2.1 wrote both rows at once,
and `semantic_type` held for the same reason. Nothing separates the cases except who was writing.

### 2.4 What the packets write, and why `left_lick` refines

Both packets declare seven kinds of event: `delay_start`, `go_cue`, `reward_outcome`,
`left_lick`, `right_lick`, `left_reward_delivery`, `right_reward_delivery`. Since R91 §3.1 each is
a stream's `event_type` rather than a column on every event, which changes where the value is
written and nothing about what it says.

Four of them name something R11 §4's reserved set describes, so that set read literally forbids
them — and reading it as intended does not help, because the adapter is not inventing a synonym.
It is adding **which spout**, a distinction the reserved vocabulary has no room for. Nor is the
side carried anywhere else: each of the seven streams holds exactly one event type, but what a
stream contributes is `core.event_streams.event_stream_name` holding `left_lick_time`, the
source's own field name, which this specification constrains no more than a device's (R67 §2.4,
R85 §2.2). Reading a side out of it means parsing a name.

The refinement is not an accident of this adapter. An event is named for what happened in an
experiment, and an experiment refines: a lick has a spout, a reward has a size, a TTL edge has a
line and a direction — both packets already declare `FIP_rising_time` and `FIP_falling_time`
streams, so even the instrument-side values would want refining once those carried events.

R11 §4's six also mix two vocabularies, which is why no single test admits them. `sync_pulse` and
`ttl_edge` name the instrument and mean one thing in every rig; `stimulus_onset`, `reward` and
`lick` name the experiment; `threshold_crossing` names a signal without saying of what or past
which threshold. `raw`, `ap`, `lfp` and `waveform` are all of the first kind.

## 3. Decision

### 3.1 Every string column declares one of three vocabularies

Every `string` column **MUST** declare `vocabulary`, whatever its role, except a discriminator
(§3.3). It holds one of:

- **`closed`** — the column also declares `enum`, and a validator **MUST** reject a value outside
  it.
- **`open`** — the values name kinds of thing, comparable between packets. A validator **MUST
  NOT** reject an unrecognized one, and the column **MAY** declare `reserved_values`.
- **`free`** — the values are not a vocabulary. A name, a description, a URI, a digest, a version
  string, a person: comparing one across packets establishes nothing, so nothing may be reserved
  and no report is due.

A column of any other type **MUST NOT** declare one. `02` §9.3's default is struck: an absent
declaration is a defect rather than a claim of openness.

### 3.2 Required, with no default

The field is required and has no default, for R48 §2.2's reason — a default makes a forgotten
classification indistinguishable from a deliberate one, which is exactly how
`core.unit_coordinates.coordinate_frame` came to state its openness in prose.

It is also not derivable, on the three tests R48 §3 applied. Not from type: all 102 are `string`.
Not from `role`: 95 are `data`, covering `probe_type` and `notes` alike. Not from name: of the 99 that
declare no `enum`, 70 follow a convention (`*_name`, `*_description`, `*_version`, `uri`, `sha256`
and `local_*_label` are free; `*_type`, `*_unit`, `*_frame`, `*_basis`, `format`, `origin` and
`kind` are open) and **29 need a person**, `manufacturer` being a vocabulary where `model` is not and `species` being
one where `institution` is not.

### 3.3 A discriminator declares none

7 string columns carry `role: discriminator`: `core.intervals.interval_kind`, `detail_kind` on
two tables, `scope_kind` on two, and `coordinate_resource` on two. Their value space is not a
vocabulary a writer extends — R55 §2.1 fixes it as the dotted resource IDs the registry declares,
and `resolves` already says whether an unmatched value is a defect or a fact.

A discriminator therefore **MUST NOT** declare `vocabulary`. A fourth state restating R55 would be
the duplication R3 §3.0 forbids, and `check.py` refuses a discriminator that declares one.

### 3.4 A reserved value is one that is read whole

A value **MAY** be reserved only where it is read **whole**: where a consumer comparing two
packets learns something from the value alone, without knowing what either packet was doing.

`lfp` passes. It names what a signal is, which acquisition determines, so `kind = 'lfp'` selects
comparable arrays from packets built by different labs. `reward` does not: two experiments'
rewards are not comparable without knowing each paradigm, so matching the string returns rows a
consumer cannot use and suggests an alignment that is not there. A task's shape is not the
format's (R43 §3, R54 §2.3), and its vocabulary is not either.

Passing that test is necessary and not sufficient. A reservation records values **this
specification** defines, and where an external nomenclature defines them instead, R3 §3.0 forbids
copying it: NCBI Taxonomy holds some 2.4 M names and the Allen CCF some 1,300 structures, so any
set the registry carried would be a partial copy that goes stale and implies the omitted values
are less conforming — which §3.1 denies. `raw`, `ap`, `lfp` and `waveform` have no authority to
defer to, R8 §4 having declared their meanings itself. That is what makes them reservable.

### 3.5 A large vocabulary states its form in its description

A column declaring `vocabulary: open` **MUST** carry a `description`, and where an external
nomenclature fixes how its values are spelled, that description **MUST** name it.

Measured across the 39 columns §3.1 classifies as open, this is where the registry is thinnest.
Every one carries a description and **12 of them state no form** — ten restate the column's own
name (`Species.`, `Manufacturer.`, `Physical unit.`, `Strain/background.`, `Origin description.`)
and two give a single example (`e.g. mp4.`). A writer reading those learns nothing about whether to
write `Mus musculus` or `mouse`, which is the only question a species column raises.

- `core.subjects.species` states the **scientific name** of the organism the subject derives
  from, as NCBI Taxonomy spells it. Null where it derives from none: `01` §3.4 makes a subject
  "the animal or preparation recorded from", and a phantom or a simulated recording has no
  species where a slice or a culture has its donor's.
- `core.subjects.strain` states the strain in its registry's nomenclature: MGI for mouse, where
  the substrain letter of `C57BL/6J` is what distinguishes it from the *Nnt*-deleted `C57BL/6N`,
  and RGD for rat stocks such as `Long-Evans`.
- `core.electrode_coordinates.region_label` and `core.unit_coordinates.region_label` state the
  structure's acronym **in the atlas `coordinate_frame` names** (R59 §2.2).
- `coordinate_frame` on both tables states the **space** a triple is in, and the atlas where that
  space is one. What it does not state is which way the axes point, which §6 records.

A writer **MUST** spell a value as the named nomenclature does, and **MUST NOT** recase or
re-punctuate one to fit a house style: values are compared exactly, so `mouse`, `Mus Musculus` and
`mus_musculus` are three ways of failing to name one animal.

### 3.6 A column may name the nomenclature its values come from

Where one nomenclature covers a whole column, the registry says so as a value rather than as
prose. A column **MAY** declare `authority`, an array of absolute URIs naming the nomenclatures
its values are drawn from — `species` names NCBI Taxonomy, `strain` names MGI and RGD, and `sex`
names HL7 FHIR.

Any vocabulary may carry one, closed included. Drawn from is not equal to: a closed column's
`enum` is the set a validator enforces, and its authority says where that set's spelling came
from, which is what lets `sex` name FHIR while adding `hermaphrodite` and carrying `unknown` as
null. Barring it from a closed column would leave the provenance in prose, which is what §2.3
indicts. Identity, not a fetch instruction: a validator **MUST NOT** dereference one
(R14 §2.3.2) and **MUST NOT** reject a value for being absent from it, which is R57 §2.2's rule for
`$schema` one level down. An array rather than a scalar because a column's values may honestly
come from two registries, as a strain's do from mouse and from rat.

`region_label` declares none, and the reason is the general one: R59 §2.2 makes `coordinate_frame`
name the atlas, so its authority varies **per row**, which no column-level field can express. That
is why the description obligation stays — a URI is an identity where "the scientific name, not the
common name" is an instruction.

`registry/check.py` checks that the description is present, that an authority is an absolute URI,
and that two columns of one name name one nomenclature — which is
§2.3's drift caught mechanically, where the description alone leaves it to review.

### 3.7 `event_type` reserves nothing

R11 §4's reserved set is **struck**. The registry already carries none, §2.2's move having dropped
it, so what this settles is the revision rather than the declaration: `left_lick` becomes
conforming rather than a breach nothing could see, and `build.py` loses the line that sets a field
on a struck column. `core.event_streams.event_type` declares `vocabulary: open`, so a validator
still **MUST NOT** reject any value.

R11 §4's six stay in that revision as **examples**, which is what `01` offered them as, and what
`02` should have said instead of "etc." A writer naming an event may use them and is not obliged
to.

### 3.8 `kind` records the four values R8 reserved

`core.array_assets.kind` and `analysis.array_assets.kind` **MUST** declare `reserved_values` of
`raw`, `ap`, `lfp` and `waveform`, each carrying the meaning R8 §4 declares for it.

`coordinate_frame`'s three are **deferred**, not recorded. R19 §3 reserved them "with those
meanings" and the meanings it points at are the frames' own, which no packet states — so what a
reservation would record is a name whose content is missing, and supplying that content is a table
rather than a declaration. §6 carries it.

Every other open column declares no set: `semantic_type`, `activity_type`, `species` and `strain`
draw on nomenclatures §3.5 and §3.6 name instead, and declaring an empty set and declaring nothing
are the same claim, so the field stays absent.

### 3.9 `sex` is closed, and a writer normalizes onto it

`core.subjects.sex` **MUST** declare an `enum` of `male`, `female`, `hermaphrodite` and `other`,
becoming core's fourth closed vocabulary.

Three of those are HL7 FHIR's `AdministrativeGender` — `male`, `female`, `other`, `unknown` —
which the column names as its `authority` under §3.6. The spelling is FHIR's because it is
published and lowercase; ISO/IEC 5218 is numeric and PATO is a set of IRIs, so neither is a code a
column could hold.

FHIR's fourth value is left out, and **not** because it duplicates null. `unknown` says a subject
has a sex nobody recorded; null on a phantom says there is none to record. Julia's DataFrames
separate those as `missing` and `nothing`, and Parquet cannot: a definition level says present or
absent and offers no second marker, so both arrive as one null. What decides it is reach —
`unknown` recovers one of null's readings for one column, where §6's `subject_kind` recovers a
different one across `species`, `strain`, `sex`, `genotype` and `date_of_birth` at once. R44 §2.3
chose the same way, giving a run without a scope a scope column rather than a sentinel.

`hermaphrodite` is the addition, and it names a determinate sex rather than a residue:
*Caenorhabditis elegans* is hermaphrodite or male and has no females, so `other` would collapse
the sex of every worm in every packet into the value reserved for what cannot be classified.

A writer **MUST** map the source's spelling onto one of the four. Where the source states an
unknown sex, states none, or describes a preparation that has none, the column **MUST** be null:
NWB writes `U` for unknown, and recording that as `other` asserts a sex the source never claimed.
Null therefore carries three readings, which §6 records rather than settles.

Keeping the source's spelling alongside is R22's shape and is not needed here. R22 §3 retains a
scorer's own `label` beside a closed `normalized_label` because `non_soma` has no honest
projection onto `sua`/`mua`/`noise`; `Male` projects onto `male` exactly, and sex carries no
per-source meaning to lose.

Nothing conforms today. Both packets carry `Male` and `fixtures/build.py` carries `M`, so every
packet fails Tier 1's membership check until it is rebuilt — the only clause here that invalidates
a packet, and the reason §5 owes a corpus change.

### 3.10 What a validator does

A validator **SHOULD** report, at `info`, a value outside the reserved set of a column declaring
one. It **MUST NOT** report a failure: the vocabulary is open, and an unrecognized value is exactly
what openness admits.

Whether a value is a *synonym* for a reserved one stays uncheckable — `local_field_potential`
describes what `lfp` describes and no query can see it — so R8 §4's prohibition binds a writer and
no rule. That is the shape R67 §2.4 has: a named actor bound to a determinable behaviour, with
nothing able to observe a breach, which is a requirement rather than a wish because the actor can
comply.

## 4. What this does not change

- **No open vocabulary closes except `sex`.** Every other one stays open, `event_type` included;
  what changes is that each says so, and which of them makes a claim about particular values.
- **No table, column or reference is added or removed, and no Tier 2 rule.** What the meta-schema
  gains is one field, `authority` (§3.6); `vocabulary` and `reserved_values` already existed, and
  are filled where they were absent and emptied on one struck column.
- **`core.units.quality_label` keeps its values.** Closed since R11 §3 and R22 §3, it gains the
  `closed` marker naming what it already was.
- **R11 §4's meanings are not restated.** They stay in R11 as examples, with the definitions it
  gave them.
- **A discriminator's `resolves` is unchanged.** §3.3 says a discriminator declares no vocabulary,
  not that its values are unconstrained.

## 5. Consequence

The meta-schema replaces `vocabulary`'s `const: "open"` with a required three-value enum on a
string `data` column and gains `authority`, an optional array of URIs; `registry/build.py` vendors
both into two packages as it does every meta-schema change.

102 string columns declare one: **4 closed** — `core.processing_runs.status`,
`core.units.quality_label`, `core.unit_quality_labels.normalized_label` and `core.subjects.sex` —
**39 open**, 24 of them for the first time, and **52 free**. The 7 discriminators declare none.
The 24 newly open are a few vocabularies spread thin: seven `unit` columns, four `format`, plus
`origin`, `calibration_type`, `probe_type`, `event_type`, `activity_type`, `coordinate_frame` and
the seven subject and device columns.

Two columns carry `reserved_values`, the first the registry has ever held, and three carry an
`authority` — `core.subjects.species`, `core.subjects.strain` and `core.subjects.sex`, with the
eight `unit` columns following if §6's UCUM question resolves yes. `build.py` loses the line setting `reserved_values`
on `core.events.event_type`, a column R91 §3.2 struck, and **12 descriptions** are rewritten,
being the open columns that state no form.

Tier 1's closed-vocabulary checks go from 3 to **4**, and `registry/check.py` from 19 structural
invariants to **25**: a string column that is not a discriminator declares a vocabulary and one
that is does not,
`closed` holds exactly where `enum` does, `reserved_values` appears only under `open`, an
authority is an absolute URI, an `open` column carries a description, and one column
name carries one vocabulary and one authority across every table holding it. That last check holds
across all 102 columns today, and is what §2.3's drift would have caught.

`fixtures/build.py` writes `sex` as `male` rather than `M`, so every packet in the corpus changes;
the NWB adapter gains the mapping §3.9 requires, and both packets are rebuilt, which R87 §2.1,
R88 §2, R91 §5, R95, R96, R97, R98 and R99 already require. A validator gains §3.10's report.

## 6. Open

- **Whether `sync_pulse` and `ttl_edge` should be reserved somewhere.** They pass §3.4's test — a
  sync pulse means one thing in every rig — and this part strikes them with the rest because they
  are reserved on `event_type`, where the surrounding values do not. A vocabulary naming what a
  **stream** carries, rather than what an event is, would be the place, and `core.event_streams`
  has no such column.
- **Whether a subject declares what kind of thing it is.** `01` §3.4 admits "the animal or
  preparation recorded from" and `core.subjects` carries an animal's columns alone, so a slice, a
  culture, an organoid, a phantom and a simulated recording are all subjects and only the first
  three have a donor species. The distinction collapses onto null, on `species`, `sex`, `strain`,
  `genotype` and `date_of_birth` together, which is the collapse R44 §2.3 refused for scope. A
  `subject_kind` would separate them; being a column and a writer obligation, it is a revision of
  its own.
- **Whether a frame declares which way its axes point.** `x_um`, `y_um` and `z_um` are described
  as micrometres "in that frame" and nothing says whether x runs anterior or posterior, over
  **16,512 coordinate rows** in the two packets. `coordinate_frame` is the wrong home — it names
  the space, where RAS and LPS name the convention, and R58 §2.1 already split a frame from a
  basis for that reason. It is also inapplicable to the 8,448 `probe` rows, whose axes are
  along-shank and across-shank rather than anatomical. The shape this wants is
  `core.coordinate_frames`, one row per frame, which would also give `coordinate_frame` the
  reference it has never had despite sitting in two primary keys — a table, a reference and a
  writer obligation, so a revision of its own — drafted as
  `a-coordinate-frame-declares-what-its-axes-mean`, which also settles the three names R19 §3
  reserved and §3.8 defers.
- **Whether a `unit` column should name UCUM.** Eight columns hold a physical unit and §3.6 names
  no nomenclature for them, because the values on hand would not conform: R77 §1.2 records
  `percentage` and `milliliter` from a live pipeline, where UCUM writes `%` and `mL`. Naming
  it is one line and a rebuild of every array asset's unit.
- **Whether an extension should make a refinement structural.** §3.7 leaves `lick_left` or
  `left_lick` a string a consumer filters on and cannot join. Making the spout structural is an
  extension's work, keyed through `event_type` in R90 §3.5's shared-key shape; nothing has asked
  for it, and `dynamic_foraging.trials` already carries the seven `_left`/`_right` pairs this task
  needs.
- **Whether the four array kinds are the right four.** R8 §4 took them from `02`'s examples rather
  than from what sources emit. §3.8 records them and does not revisit them.
