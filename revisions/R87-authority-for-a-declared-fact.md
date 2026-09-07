# R87 — Authority for a Declared Fact

| | |
|---|---|
| **Status** | **Accepted** 2026-09-07 |
| **Amends** | `05` §3.1 (what a recipe declares, and which resources it supplies), `05` §3.5 (checking a recipe), `07` §4 (the object model) |
| **Depends on** | R63 (default ownership when a recipe omits `owns`), R86 (a reader presents many packets as one relation) |
| **Profile** | `escapewheel-portable-v0.1` |

Informative, except §2, which is normative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

A **recipe** is the TOML document naming a packet's sources and the facts none of them supplies.
`05` §3.1 lists the last of those as *"session and subject facts no source carries"*, and `05` §3.2
records the recipe verbatim as the packet's provenance. Where a source carries such a fact after
all, nothing says which of the two declarations wins.

## 1. Motivation

### 1.1 A recipe declared the wrong animal and nothing noticed

The recipe for **`ecephys_776259`** declared `subject_id = "786867"` — the other session's mouse,
copied across when the second recipe was written from the first. The committed packet still
carries it: `core.subjects.subject_name` reads `786867` in a packet whose one session is named
`ecephys_776259_2025-04-09`, asserting that its **6,781 units** came from an animal that was never
in the rig.

The source disagreed the whole time. That session's `session.json` carries
`subject_id: 776259`, and the `session` adapter reads that file for its stream windows without
ever looking at the field.

### 1.2 One question, three answers

`05` §3.5's check sees a resource owned twice, a resource no adapter produces, a dangling required
key, a broken clock declaration, an unset required option, and the unclaimed resource R63 §2.3
added. Every one of those is a statement the recipe makes about **itself**, so a declaration
contradicting a source passes: it contradicts nothing internally. R63 §1.1 made the same argument
about omission — *"a recipe naming four of a source's five resources passes every test the tool
applies and the fifth resource is absent from the packet"*.

What the writer does instead is decide the question three ways, in thirty lines and by no stated
rule:

| the fact | what happens when the two differ | |
|---|---|---|
| `subject_id` | the build is refused | `session.py:322` |
| `session_start_time`, `session_end_time` | the source's value is used and the recipe's is noted | `session.py:332-338` |
| every other `[session]` and `[subject]` field | the recipe wins outright | `recipe.py:41`, `RECIPE_SUPPLIES` |

### 1.3 A recipe corrects a source that is wrong

The third policy exists because sources are wrong. `session.json` for `ecephys_776259` stamps a
Pacific wall-clock reading as UTC — **seven hours** out — and the recipe carries a comment saying
it localizes the value because no adapter gets to correct it.

An adapter does correct it, by a route the recipe does not know about: `core.sessions.session_start_time`
in the committed packet is `2025-04-10T00:25:12Z`, taken from the earliest declared stream window
rather than from either the recipe or `session.json`'s own field. The recipe's transcription of
that window is discarded, which is visible only at the other end, where the packet holds
`02:38:44.147959` against the recipe's rounded `02:38:44`.

So a recipe overriding a wrong source is the ordinary case rather than a defect, and a rule that a
recipe must agree with its sources would refuse a correct build.

### 1.4 A wrong subject unifies rather than collides

R86 §2.1 makes `core.subjects` one of the two tables that are **not** session-scoped, because
`core.sessions` references it rather than the reverse. So a subject is the identifier meant to be
the same thing across packets, and a wrong one agrees with a different animal's rather than
colliding with the true value.

Read together, two packets of what should be two mice claim to be two sessions of one. That is the
failure R86 exists to prevent, arriving through the one door R86 does not watch.

## 2. Decision

### 2.1 A build reports a difference, and refuses only where identity is at stake

Where a recipe declares a fact and a source the same recipe reads states that fact, a build
**MUST** report a difference between the two, naming the field, the declared value, the source's
value and the file it came from. A build **MUST** refuse only where the fact identifies something
a reader resolves across packets; otherwise it proceeds, and `--strict` refuses.

**`subject.subject_id` is that case today, and the only one.** R86 §2.1 makes `core.subjects` one
of two tables not scoped to a session, so a wrong subject agrees with another packet's animal
rather than colliding with the true value — §1.4's failure, which no later reader can detect and
no note can undo. Everywhere else a difference is more often the recipe correcting a source
(§1.3), and refusing would tax every recipe to catch a rarer defect than the note already
surfaces.

The rule is put on the build rather than stated as an agreement the recipe owes its sources.
Nothing can check that a recipe agrees with a file it has not opened, so an obligation written
that way would bind nobody; the build is the one actor in a position to act.

Two values are compared at the type the packet will store, both normalized to it first.
`session.json` states `subject_id` as the number `776259` where a recipe declares the string
`"776259"`, so comparing raw values would refuse every recipe that is right.

Normalizing to the stored type is what keeps `subject.date_of_birth` from refusing: the recipe
declares `2024-09-24`, the NWB states `2024-09-24T00:00:00-07:53`, and R4 §3.3 makes the column a
calendar date, so both reduce to the same date.

This extends `05` §3.5's refusal to a contradiction the recipe cannot show on its own. R63 §1.2
measured what the alternative costs: a defect surfacing ninety seconds into a build as another
table's rule failure. A recipe that contradicts its sources is the same defect, and it never
surfaces at all.

### 2.2 An adapter declares the facts it can state

A build **MUST** be able to determine, for each source a recipe names and without opening it,
which recipe fields that source can state; and a build **MUST** refuse a recipe naming a source it
cannot determine that for. Refusing is what makes §2.1 total over the sources a recipe names,
rather than over a list of fields written here.

The obligation is on the build because an obligation on adapter code binds nothing. R63 §2.1
requires `PRODUCES` of every adapter, and `produces()` returns an empty set for one that declares
none, so a missing declaration reads as an adapter that produces nothing and the requirement
catches it never.

What the set is called and where it lives belongs to Part 07, which opens *"Informative. Nothing
here constrains a conforming implementation"* and whose §4 already names `Packet`, `PacketWriter`
and an adapter's return type. Part 07 §4 records that the reference implementation spells this
`STATES`: a static class attribute of `block.field` names — `subject.subject_id`,
`session.session_start_time` — beside `PRODUCES` and read the same way.

The split is what keeps both useful. Naming a class attribute in Part 05 would bind an
architecture where the rule needs only an answer, and leaving the spelling unwritten would make
this codebase harder to read for no gain.

That is R63 §2.1's discipline applied to facts instead of to resources, and for its reason: the
knowledge is already in the adapter, and a list of fields written into this specification would be
a transcript going stale the first time an adapter learns to read one more of them. §2.1's rule is
bounded by what the sources a recipe names can state, which is finite and declared, rather than by
the unbounded set of facts a recipe might get wrong.

`subject.subject_id` is the first, and `AindSessionSource` already exposes it. The next is
measured. `NWBSource` reads every member of `general/subject` and builds a whole `core.subjects`
row — `subject_id`, `species`, `sex`, `genotype`, `date_of_birth`, `strain`
(`sources/nwb.py:364-383`) — and declares `core.subjects` in its `PRODUCES`. `RECIPE_SUPPLIES`
takes that resource from every source, so the row is built and thrown away while the recipe's
hand-typed `[subject]` block wins. `ecephys_776259`'s block declares **four** of those fields, and
none is compared with the source that states it.

The build reads them closely enough to comment on them. `ecephys_776259`'s log carries
*"note: subject.date_of_birth: stored offset -07:53 disagrees with America/Los_Angeles's -07:00
for 2024-09-24T00:00:00; kept as stored"* — the source's date, examined, and then discarded
against a recipe declaring the same date by hand. R63 §2.4's runtime backstop does not report the
loss either, because `_note_unclaimed` counts `RECIPE_SUPPLIES` as claimed, so a recipe-supplied
resource is the one case that pays a source's full cost and yields neither the row nor the note.

### 2.3 The check reports what will be compared, before any I/O

`Recipe.check` **MUST** report, before any source is opened, every field the recipe declares that
some listed source's `STATES` names. A field no override covers is reported as a **warning**,
since only the build can tell whether the two agree; a field an override covers is reported as
**information**, so the log lists every place the recipe corrects a source.

A field the recipe declares that no listed source states is reported as nothing at all. That is
`05` §3.1's intended case, and it is what the recipe is for.

### 2.4 A source that states nothing is not a contradiction

Where a source carries no value for a declared fact, the declaration stands unchallenged and the
build proceeds. Silence is not disagreement, which is R83 §2.3's distinction between a fact about
what the source holds and a defect in the packet.

A writer **MUST NOT** report a missing source value as a mismatch, and **SHOULD** note that the
declaration went unchecked, so a reader of the build log can tell a verified fact from an
unverified one.

### 2.5 An override declares that the recipe is authoritative, and why

A recipe **MAY** declare that its own value for a fact supersedes the source's, by naming the field
in a top-level `[overrides]` table, keyed by the same `block.field` name §2.2 uses. Declaring one
is never required: it records a decision and silences §2.1's report, and a recipe that declares
none is conforming.

```toml
[session]
session_start_time = "2025-04-10T00:25:12Z"

[overrides]
"session.session_start_time" = "session.json stamps a Pacific wall-clock reading as UTC; seven hours out"
```

The table is top-level rather than a sub-table of the block it qualifies, because the writer turns
a declaring block into a row wholesale — `writer.add("core.subjects", [dict(recipe.subject)])` at
`session.py:700`, and the same for `core.sessions` at `session.py:745`. A `[subject.overrides]`
sub-table would arrive as a column no registry defines. One table keyed by `block.field` also
matches what §2.2 asks a source to declare, so the two sets are comparable without parsing.

The value **MUST** be a non-empty reason. A boolean would let a difference be silenced without
saying why, which is R63 §2.2's silent winner one level up, and the reason is the whole of what a
later reader has to judge the override by. Requiring a reason costs an author nothing they were
not already going to write in a comment, where no tool can read it.

A build **MUST** report an override for a field whose declared value the source agrees with, and
for a field no source states, and **MUST NOT** refuse on either. A stale override is the failure
`registry/check.py` guards against by checking that each declared exception is still needed; here
it costs a line of the log rather than a build, because an override that stopped applying leaves
the packet correct.

An override is not a licence to invent. It says a source is wrong about a fact the recipe knows
better, and §1.3 is the case it exists for: an upstream defect that will not be fixed in the file
this build reads.

### 2.6 The comparison runs where the source is opened

`05` §3.5's check runs before any I/O and cannot do this one, which needs the source read. The
comparison therefore happens as each source is built, and **MUST** refuse before any resource is
staged — early enough that a contradicted recipe costs nothing but the source's own open.

A source's statement of a fact is whatever its adapter exposes for that fact. Which of several
values inside a file the adapter stands behind is the adapter's judgement and not the recipe's:
§1.3's session states its start twice, once wrongly in its own field and once correctly across its
stream windows.

### 2.7 A fact the source derives is the source's

`core.sessions.session_start_time` and `session_end_time` come from the session source's declared
stream windows. A writer **MUST** use the source's value where a session source is present, and
**MUST** report a declaration it did not use rather than discarding it silently.

This states what `session.py:332-338` already does. It is not §2.1's rule, because the recipe's
declaration here is a transcription of the source's own derivation rather than a competing claim,
and it is not §2.5's override, because nothing is being corrected.

### 2.8 A source may own `core.subjects`

`core.subjects` is removed from the resources a recipe supplies unconditionally. A source that
states a subject **MAY** own it, arbitrated as any other resource two sources can produce
(R63 §2.2). A recipe's `[subject]` block supplies the table only where no source owns it.

Nothing has to clear a bar first: the table's only required column is `subject_id`, which R53 §2.3
makes **assigned**, so the packet mints it and every fact column is nullable. A source that states
one field can own the table as well as a source that states six.

Only this one of the three moves. `core.sessions` stays with the recipe because `session_id` is
the packet's own naming and `reference_clock_id` is a decision about which clock the packet reads
by, and no source states either. `core.processing_runs` stays because the import run records what
the **writer** did, and a sorter already contributes its own rows beside it.

Migration is opt-in and nothing breaks. A recipe whose `nwb` entry declares an explicit `owns` is
narrowed (R63 §2.2), so removing the table from the recipe-supplied set gives it to no one, and
the recipe keeps supplying it exactly as before. An author opts in by adding `core.subjects` to
that entry's `owns` and deleting the `[subject]` block.

What tells them to is a check that already exists and has been suppressed. R63 §2.3 reports a
resource a listed source can produce and no source claims, and `_note_unclaimed` counts the
recipe-supplied set as claimed, which is why §2.2's discarded row has never been reported. Removing
`core.subjects` from that set makes the existing warning fire on the exact case §2.2 measures, with
no new machinery.

## 3. What this does not change

- **No table, column or rule.** The comparison is a writer check rather than a Tier 1 or Tier 2
  rule: the packet it would have refused never exists, so there is nothing for SQL to see.
- **`05` §3.1's list is unchanged.** A recipe still declares what no source carries; this says what
  happens when it declares something a source carries after all.
- **No new key in the run's parameters.** An override travels inside the recipe, which `05` §3.2
  already records there. It is not one of R92's keys, because no consumer needs it to read the
  value — the packet's value *is* the value, and the override says only where it came from.
- **No recipe stops building.** §2.8 removes a resource from the recipe-supplied set and adds it
  to no source, so an existing recipe supplies `core.subjects` exactly as it does today and gains
  one warning telling it that a source could.
- **No packet becomes invalid.** A committed packet is unaffected — except that
  `ecephys_776259`'s is wrong for the reason in §1.1 and must be rebuilt, which R61 §5 makes a
  rebuild that re-reads no external resource.
- **R63's pre-I/O check keeps its scope.** It still refuses what it can see without opening
  anything, and §2.6 adds a second point rather than moving the first.

## 4. Consequence

§2.1, §2.4, §2.6 and §2.7 are implemented for one field: `session.py:311-328` compares
`subject_id`, refuses with a `SourceDefect` naming the field, both values and the file, and notes
an unchecked declaration; `session.py:332-338` prefers the derived extent. That refusal is the one
§2.1 keeps, so no implemented behaviour is loosened.

The new work is §2.2, §2.3 and §2.5. `STATES` is one frozenset per adapter and one accessor, and
the accessor exists already wherever a value does — `AindSessionSource.subject_id`, and
`NWBSource.subjects()` for the six fields §2.2 measures. `Recipe.check` gains a pass over the
union of the listed sources' `STATES`, which is R63 §2.3's pass with a different set. The override
gains an `overrides` table per declaring block, its reason carried through, and two refusals: an
empty reason, and an override the source does not contradict.

§2.8 is a one-line deletion from the recipe-supplied set, and the warning that follows is R63
§2.3's, already written and until now suppressed for that set.

`05` §3 gains §2.1 to §2.8's rules and names no attribute. `07` §4's object-model table gains one
row for `STATES`, which is where a reader of this codebase looks and where nothing binds.

`ecephys_776259` must be rebuilt: its recipe is corrected and its packet still names the wrong
subject. Nothing else in that packet changes, since `subject_id` reaches no other table's key —
`core.sessions.subject_id` references it and holds the same wrong number.

## 5. Open

- **Whether §2.7's note should become an override.** A recipe declaring a start time the source
  derives is transcribing, and a transcription that has gone stale is reported and ignored. Making
  it an override instead would put a reason beside it and refuse the stale case, at the cost of
  requiring one for every recipe that carries the field for readability.
- **When the default should tighten to refusal.** §2.1 reports where it could refuse, because the
  rate at which recipes and sources disagree has never been measured: `STATES` does not exist, so
  nobody knows how many fields would refuse once it does. R41 §2.4 and R37 §3.3 were both accepted
  before anyone ran them against real data, and R44 and R40 are the retractions. The measurement
  that settles this is small — populate `STATES`, run both recipes, count the fields that differ
  with no override. Near zero, tighten; otherwise the count says why the note was right. A note is
  weak evidence on its own: `ecephys_776259`'s log has carried *"subject.date_of_birth: stored
  offset -07:53 disagrees"* since the packet was built, and nobody acted on it.
- **What protects a recipe from an adapter that learned to state more.** `STATES` grows, so a field
  no source stated when a recipe was written may be stated later. Under a tightened §2.1 a recipe
  that built yesterday would refuse today with nobody having edited it, which makes improving an
  adapter a breaking change to every recipe — a worse cost than the authoring friction §2.1 weighs.
  `core.processing_runs` records `software_name` and `software_version`, but in the packet rather
  than beside the recipe, and a version string cannot reconstruct an old `STATES` without the old
  code. A lock file written beside the recipe, recording what each adapter it was authored against
  declared, would let a build report which fields are **newly** stated rather than refusing on all
  of them. It records what nothing else holds, so it is not the restatement R62 struck, and it sits
  beside the recipe rather than in the packet for R80 §2's reason: the knowledge goes stale and the
  artifact it would otherwise sit in may not change. It is the mechanism the tightening above
  depends on, so the two are decided together.
- **Whether a coarser declaration should need an override.** A recipe declaring a value less precise
  than the column stores is asserting a different value, and a packet carrying the coarser one
  records nothing about the loss. No field would be caught today: `date_of_birth` agrees once
  normalized, `subject_id` is settled by normalization rather than by precision, and the one coarser
  declaration — `ecephys_776259`'s `session_end_time = "2025-04-10T02:38:44Z"` against the packet's
  `02:38:44.147959` — is §2.7's, where the source's value already wins.
- **Where the comparison type comes from.** §2.1 compares at the type the packet stores, which for
  `subject.date_of_birth` is `core.subjects.date_of_birth` and the registry answers. Not every
  recipe field maps to a column — `packet.out` and `session.reference_clock_id` do not — so a field
  a source states and no column receives has no declared type to normalize to, and none exists yet.
- **Whether `05` §3.4's `PRODUCES` clause should be split the way §2.2 is.** It requires every
  source adapter to declare `PRODUCES` *as a class attribute*, so a normative part demands a
  particular class in a particular language where Part 07 exists to hold exactly that. The rule stays in `05` and the
  spelling moves to `07` §4, which is the same split §2.2 makes; it belongs to whichever revision
  next opens that clause.
- **Whether the wrong subject should have been caught downstream.** `core.subjects.subject_name`
  reads `786867` in a packet whose session is named `ecephys_776259_2025-04-09`, and no rule
  compares a subject's name with the session names that reference it. A Tier 2 rule could, and it
  would be a rule about a naming convention this specification does not define.
