# A Build Supplies the Electrode Identifiers It Assigned

| | |
|---|---|
| **Status** | Draft |
| **Amends** | Part 03 §11.2 (`electrodes` joins the closed supply vocabulary, and which source's rows fill it); Part 03 §11.3 (an adapter delivers `core.electrodes` in its source's own order, an identifier a build supplied crosses back as a number, and an adapter reports a supplied identifier it cannot resolve) |
| **Depends on** | R115 §3.1 (the closed supply vocabulary, its resolution order, and a build refusing a term it cannot fill), R115 §3.7 (an identifier crosses the boundary as a name, because an assigned number does not exist until a writer mints it), R53 §2.5 (a writer assigns identifiers when it commits), R81 §1.2 (a source's own label repeats, so the key is a pair), R83 §2.2 (a writer records a list rather than inferring it), R83 §2.3 (a consumer reports an index it cannot resolve rather than resolving it against the wrong list) |
| **Profile** | all |

Normative, except §1 and §4, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

### 1.1 Two adapters need an electrode map no term carries

Part 03 §11.2 lists what a build passes an adapter: eight terms, each naming one value and the form
it takes, so that an adapter and a build written by different people pass the same thing. A name an
adapter declares resolves against that list first and the recipe's options second, and a build
refuses a recipe where it resolves to neither (R115 §3.1).

Two adapters need a ninth. Both the LFP adapter and the waveform adapter take a mapping from the
index their source refers to an electrode by to the `electrode_id` the build assigned, filled from
the rows of whichever source owns `core.electrodes`. Neither an existing term nor an option can
carry it: an option is a literal the recipe writes down, and this value does not exist until another
source has run and the writer has numbered what it delivered (R53 §2.5). So a build reading either
declaration refuses every recipe naming either adapter, and the two resources those adapters own
cannot be produced at all.

What the mapping carries, measured on the two packaged sessions: `core.unit_electrodes` at
**171,280** and **114,945** rows, and `core.array_channels` at **1,152** and **960**. Every one of
those rows names an electrode the adapter reached through the mapping and could reach no other way.

### 1.2 The electrode label repeats across probes

`core.electrodes.local_electrode_label` is the source's own name for a contact, and keying the
mapping on it fails twice over. It is declared `string`, nullable, R48 role `data`, so it is not an
identifier and a source may state none. And it is not unique within a session: **1,920 distinct
labels over 4,608 electrodes on 12 probes**, and **1,920 over 3,840 on 10 probes**, where the
distinct `(probe_id, local_electrode_label)` pairs come to 4,608 and 3,840 — the row count exactly.
So a label key needs the probe beside it, exactly as a sorter's unit label needs its run: R81 §1.2
measured 810 distinct labels over 6,781 `(unit_id, sorting_run_id)` pairs across 12 runs.

What both adapters hold instead is an index. The NWB names the contacts of an electrical series and
of a waveform group by their position in its own electrode table, so the value the array hands the
adapter is a row number, and the assigned `electrode_id` for that row is the one thing the adapter
cannot derive.

### 1.3 An unresolved index disappears without a finding

An index the mapping does not carry is handled two ways in the reference implementation, neither of
them visible. `core.array_channels.electrode_id` is nullable, so the LFP adapter writes a null and
the row validates. `core.unit_electrodes.electrode_id` is required, so the waveform adapter drops
the row. The same waveform adapter reports an unmatched **unit** — `units: n NWB row(s) match no
unit or are all zero; skipped` — and says nothing at all about an unmatched electrode.

R83 §1.1 is what that costs when it goes unreported: an index resolved against a list nobody wrote
down named the wrong electrode for 5,071 of 6,781 units, and it was found only because 609 of them
landed outside the unit's own channel support. An index is wrong in the way that costs most, usually
right and never marked, so the mapping needs a rule about what to do when it misses as much as it
needs a term.

## 2. Decision

### 2.1 `electrodes` is a term of the supply vocabulary

Part 03 §11.2's table gains a row:

| term | what a build passes |
|---|---|
| `electrodes` | one record per electrode: the index the source refers to it by, and the identifier assigned |

A build **MUST** fill it from the rows of the source that owns `core.electrodes`, and **MUST** take
each index from the position of the row in the delivery that source made, 0-based as Part 02 §8.1.1
requires of every structural index. An adapter that owns `core.electrodes` **MUST** deliver its rows
in the order its source holds them, because the index counts them: a delivery reordered on the way
out leaves every index naming a different contact, and Part 03 §11.3 otherwise makes the declared sort
the build's, so nothing constrains the order a delivery arrives in. Carrying the index as a column of `core.electrodes` instead is rejected: the position is a fact
about the source's own table, which the packet exists to replace, so every packet would carry a
column serving one step of one build that no consumer resolves anything through.

**Opening the vocabulary is rejected, because an unreserved term has no filler.** The open half
already exists: a name outside the list resolves against the recipe's options, filled by whatever
the recipe carries. What is left over is a value computed mid-build from another source's rows, and
no recipe can write one down, so a build meeting an unreserved name can only refuse — which is what
it does today. Reserving a term buys a **pinned form** rather than a filler: `first_samples` is a
recipe option in the reference implementation and Part 03 §11.2 reserved it anyway, to fix the record
shape two implementations have to agree on. An open supply vocabulary is a set of names with no
agreed shapes, under which a third-party adapter and a build it never saw each pass something
reasonable and neither is wrong.

### 2.2 A supplied identifier crosses back as a number

Part 03 §11.3 requires an adapter to hand over identifiers as the names its source used and never as
numbers, because a writer mints every assigned identifier packet-wide and the numbers do not exist
until it has (R115 §3.7, R53 §2.5). That reason holds for an identifier the adapter learned from its
source and fails for one the build handed it, which exists already.

So an adapter **MUST** hand over an identifier it learned from its source as that source's name, and
**MAY** hand over an identifier a build supplied it as the number it was given. Without the second
half the term buys nothing: `core.unit_electrodes.electrode_id` is required and the adapter has no
name to put there. Returning `(probe_id, local_electrode_label)` pairs for the build to resolve is
the alternative, and it costs two string columns over the 288,337 rows of §1.1 plus a translation
the adapter must perform against a table the build has already read — and it would retire `units`
by the same argument, which R115 §3.1 settled the other way.

### 2.3 An adapter reports a supplied identifier it cannot resolve

An adapter meeting an index the records do not carry **MUST** report it and **MUST NOT** write a
null or drop the row in silence. Where it writes a report the finding is a `problems` entry
(Part 09 §5.8); in the build's own process it is a note of the delivery, and a build **MUST** report
what it is given either way.

The empty case needs no rule. R115 §3.1 already has a build refuse a recipe where a term cannot be
filled and forbids passing one absent or empty, so an adapter declaring `electrodes` is never handed
nothing; what remains is a mapping that is present and short.

## 3. What this does not change

- **No table, column, reference, rule or vocabulary of the registry.** §1.1 counts rows of
  `core.unit_electrodes` and `core.array_channels` and §2.1 declines a column on `core.electrodes`,
  so the three tables a reader would expect to move all stay as they are.
- **No packet is invalidated**, and neither packaged session is rebuilt. The rows those two adapters
  produced are the rows they would produce under this revision; what changes is how the value
  reaches them and what happens when it misses.

## 4. Consequence

The supply vocabulary goes from eight terms to nine, and `electrodes` is the second of them to carry
assigned identifiers after `units`. Those two are one family — the identifiers a build assigned for
the things a source names its own way — and parameterizing it is declined here, because they key
differently: `units` on a two-part label pair and `electrodes` on a row index, so a parameterized
term must carry its key and an adapter's declaration stops being a list of names. Two instances is where R55 §2.1 named
the mechanism it found under `scope_kind` and `interval_kind`, so what defers this one is the keys
and not the count.

Growth is bounded by what flows **into** an adapter rather than by how many adapters there are. Of
the fifteen fields the reference implementation's build context holds, five ever cross into an
adapter — the session's name, the reference clock, the clocks declared so far, the unit mapping and
this electrode mapping — while the other ten are things adapters produce and the build consumes. Ten
adapters draw on those five.

Nothing rebuilds. The two adapters declare the term, the two `spec.kind` branches that pass it today are
replaced by the declaration, and the silent misses of §1.3 become findings.
