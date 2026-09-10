# R108 — A Preference Discards No Stated Fact

| | |
|---|---|
| **Status** | **Accepted** 2026-09-09 |
| **Amends** | `05` §3.3 and `05` §3.4 (what a preference permits and what it exempts); adds one refusal to a build |
| **Depends on** | R98 §3.2 (a resource several sources supply is `contributes`), R98 §3.3 (a discarded row is reported unless a preference explains it), R87 §2.5 (an override declares the recipe authoritative, and why), R63 §2.2 (silence means the whole of `PRODUCES`), R63 §2.3 (a resource no source claims is reported as a warning before any I/O) |
| **Profile** | all |

Normative, except §2, which is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

A **preference** names, per resource, the source kind that wins where more than one produces rows
for it. `05` §3.4 spends exactly one thing on it: a build reports rows a source produced for a
resource another source owns, "except where the recipe declares a preference between them", because
a preference says the two offer the same rows and names the one that knows more. The loser's copy
is redundant by design, so the silence is bought.

Nothing checks that it is. A preference is a claim about two sources' rows, and it is declared
before either source is opened — so a preference naming a source that turns out to state less, or
to state nothing at all, buys the same silence and loses the difference. This part requires a build
to refuse where preferring a source discards a value another source stated.

Measured across the ten adapters this repository ships, which produce **8 resources that more than
one of them produces**, and on the two packaged sessions **`ecephys_776259`** (twelve probes, 6,781
sorted units, recorded 2025-04-09) and **`ecephys_786867`** (ten probes, 4,505 units, recorded
2025-09-25).

## 2. Background

Informative.

### 2.1 A preferred source that states nothing leaves an orphan

`core.subjects` is stated by two adapters. The NWB reads `general/subject`, and the AIND session
adapter reads the `subject.json` beside `session.json` — the record the NWB's block is a projection
of, carrying a `background_strain` key the projection has no field for and a date of birth with no
timezone, where the NWB writes `2024-09-24T00:00:00-07:53`.

Prefer the session adapter and the arrangement is correct until an asset ships without that
document. Then the preferred source produces no row, the NWB has already lost the resource, nothing
stages a subject at all, and `core.sessions.subject_id` becomes an orphan. The finding lands on
`core.sessions`, which is the table that *was* staged, so what a build reports names neither the
preference nor the source it named. R98 §2.2 is the same loss one table over: `owns` being
exclusive, the sorter's twelve clock windows were produced and discarded.

### 2.2 One preference of five arbitrates anything

`recipe.PREFERRED` carries five entries. Resolving ownership consults `SHARED` first and returns,
so for the three resources in both tables — `core.clocks`, `core.array_assets` and
`core.array_dimensions` — the preference decides nothing about who owns what. A fourth,
`core.unit_electrodes`, names a resource **one** adapter produces, so there is no contest for it to
settle. `core.probes` is the one that arbitrates, between the NWB and the sorter.

The three shadowed entries are not inert, because the report and the ownership resolution read the
table differently: `_note_unclaimed` treats any resource appearing in `PREFERRED` as discarded by
design, whatever `SHARED` did. A hand-written recipe is where that bites, since R98 §2.2 measured
that a defaulted resolution is the only thing `SHARED` ever reaches.

### 2.3 The subject is the contest no table covers

Of the eight contests, seven carry a `SHARED` entry, a `PREFERRED` entry, or both.
`core.subjects` carries neither, so two defaulted sources are left owning it and `Recipe.check`
refuses the recipe naming both — the state R87 §2.8 created deliberately by taking the table out of
`RECIPE_SUPPLIES`, so that a source may own it and R63 §2.3's warning finally fires. Neither
packaged recipe claims it today, so that warning is what a build reports.

Which source should win is not in doubt, and it is the question this part does not answer: it is a
judgement about the sources, which a recipe makes. What this part decides is what happens when the
judgement is wrong.

### 2.4 The rule fires on neither packet

Column by column, the two sources agree for both animals. `species` is `Mus musculus` in the NWB
and in `subject.json`; `sex` is `M` and `Male`, both mapping to `male`; `genotype` is `wt/wt` in
both; the dates of birth agree at 2024-09-24 and 2024-11-26; and `strain` is null in both, the NWB
having no such key and `background_strain` being unset.

So nothing is discarded either way today, and the rule this part adds is satisfiable on both
packets as they stand. That is what makes it safe to state as a **MUST** rather than a SHOULD: it
refuses a case neither packet is in.

## 3. Decision

### 3.1 A preference discards no stated fact

A build **MUST** refuse where a preference discards a value another source stated: where a
passed-over source's row holds a non-null value in a column the preferred source's row leaves null,
or does not produce at all. A preferred source that produces no rows for the resource while another
does is that rule's limiting case, every value being discarded, and needs no clause of its own.

The rule reaches a resource a preference **arbitrates**, which is not every resource one names:
where a resource is also declared shared, ownership resolution never consults the preference and
the sources hold different rows, so there is nothing displaced to compare (§4). Of the four
preferences remaining after §3.4, two arbitrate — `core.probes` and `core.subjects` — and two do
not.

Comparing means the build holds the passed-over source's rows for the resource rather than
discarding them as counted. That is bounded by where a preference may be declared: every resource
one names is metadata-scale — twelve probes, ten, one subject — and the one large contested table,
`core.clock_anchors` at 754,222 rows (R47 §2.4), carries no preference and is never compared.

The comparison is over **declared columns** and not over `metadata`. A bag is schemaless by design
(`02` §8.6), so two sources filling it differently is not a difference a build can weigh, and R97
§3.3 already binds what may go in one.

This is what makes `05` §3.4's exemption sound. That clause spends a preference to buy silence
about a discarded row, on the premise that the loser's copy is redundant; the premise is now
checked against what the sources actually stated rather than against what the recipe expected them
to state.

### 3.2 A build refuses rather than merging the rows

A build **MUST NOT** compose a row from more than one source. The merged row would be a fact no
source stated, which is the inference this specification refuses everywhere it arises: a writer
MUST NOT infer a run's channel list from unit support (R83 §2.2), a consumer MUST NOT infer
attachment from a device's name (R67 §2.4), and a writer MUST leave an axis direction null where
its source does not state one (R105 §3.4).

Refusing also puts the decision where the knowledge is. A merge would silently prefer whichever
source happened to fill a column, and there is no reason to believe that is the better value —
which is the whole argument for declaring a preference rather than letting one emerge.

### 3.3 A refusal is resolved in the recipe

An `[overrides]` entry naming a fact **MUST** silence §3.1's refusal for that fact. The table is
R87 §2.5's, keyed the same `block.field` way and carrying the reason it requires, and this is a
second use of it: R87 §2.5 declares the recipe authoritative over a *source*, where an entry here
declares the preferred source authoritative over the one it displaced. Both record that a value was
chosen and why, which is what a refusal exists to extract.

An override is per fact where §3.1's refusal names a column, so the two meet at the same
granularity, and an entry silences that column and no other.

The other two resolutions need no new mechanism: name the other source in the preference, or fix
the source that states less. A refusal is a build-time failure with the offending column named, so
all three are available before anything is committed.

### 3.4 A preference names a resource more than one source produces

A preference **MUST NOT** name a resource only one source produces. Such an entry arbitrates
nothing and exempts a report that will never be due, so it is a claim no build tests, and it goes
stale exactly as `core.unit_electrodes` did when the sorter stopped producing that table.

This is the discipline `02` §4 states for a declared naming exception, which must carry a reason
and which `registry/check.py` verifies still breaks a convention, applied to the other table a
recipe layer keeps.

## 4. What this does not change

- **A resource several sources supply *part* of keeps `contributes`.** R98 §3.2 governs that case
  and §3.1 does not reach it: where the rows are disjoint there is no passed-over row to compare,
  so the refusal has nothing to weigh. R98 §3.3 says why a preference is the wrong instrument
  there — it asserts that two sources offer the same rows — and this part adds no rule about
  declaring one.
- **No packet is invalidated and no stored value changes.** This binds a build, so what it changes
  is which builds succeed.

## 5. Consequence

`recipe.PREFERRED` loses its `core.unit_electrodes` entry under §3.4, going from five entries to
four, of which three are shadowed by `SHARED` for ownership and one arbitrates. One test enumerates
the table against every adapter's `PRODUCES`, so a second producer disappearing fails a suite rather
than leaving an entry nothing tests. `05` §3.3 gains
§3.4's bound on where a preference may be declared and `05` §3.4 gains §3.1's refusal beside the
exemption it makes sound.

The comparison runs where a source's rows are staged, and costs one pass over the passed-over
source's rows per preferred resource — §3.1's bound is what keeps that small.

Neither packet changes and neither is rebuilt for this. §2.4 measures that the two sources agree on
every declared column of `core.subjects` for both animals, and `core.probes` has been arbitrated by
the same preference since it was written.

## 6. Open

- **Whether a preference should be declared per fact rather than per resource.** The key space
  exists: R87 §2.2 names a fact `block.field` and R87 §2.5's overrides are keyed by it, so a
  per-fact preference would reuse a spelling a recipe already carries rather than inventing one.
  Nothing measured needs it — §2.4 finds no column where one source states a value and the other
  does not — and §3.1 is what would find the first case, since a refusal that no choice of source
  resolves is exactly two sources each holding a column the other lacks. Until then a resource-level
  preference expresses everything the sources disagree about, which is nothing.
