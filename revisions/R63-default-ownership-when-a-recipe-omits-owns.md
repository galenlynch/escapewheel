# R63 — Default Ownership When a Recipe Omits `owns`

| | |
|---|---|
| **Status** | **Accepted** 2026-09-03 |
| **Amends** | `05` §3 (what a recipe declares), R2 §7 (what is checkable before I/O) |
| **Depends on** | R17 (an extension's tables are owned like core's), R53 (identifiers are assigned packet-wide) |
| **Profile** | `escapewheel-portable-v0.1` |

Informative, except §2, which is normative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

A **recipe** is the TOML file a packet is built from. It carries one `[[source]]` entry per source
of data, and each entry gives an `owns` list naming the resources that source supplies. `owns` is
**exclusive**: where a source emits rows for a resource it does not own, the writer discards them
with no trace.

The list is written by hand, and it transcribes a fact the adapter already holds. `SorterSource`
knows it builds `core.unit_quality_labels`, because the method that builds them is in it.

### 1.1 A recipe that leaves a resource out passes every check

`Recipe.check` reads a recipe against the registry before any source is opened, and refuses three
things: a resource two sources own, an owned resource the registry does not define, and an owned
table whose required foreign key points at a table no source supplies. Each is a **contradiction**
between two declarations in one document.

Leaving a resource out states nothing for the check to disagree with, so a recipe naming four of
a source's five resources passes every test the tool applies and the fifth resource is absent
from the packet.

### 1.2 Four resources lost from one packet

The dynamic-foraging packet for `ecephys_786867_2025-09-25` declares 6 sources and 31 claims
across `owns` and `contributes`. Four resources are missing from it, and neither the data nor any
adapter failed:

| lost | rows | how it surfaced |
|---|---|---|
| `core.unit_quality_labels` | 19,061 | a Tier 2 rule 90 s into the build, reported against `core.units` |
| `core.unit_electrodes` | 4,322 | a note added the same day, on its first run |
| `analysis.spike_events` | 131,396,535 | absent `[[materialize]]`; noticed by hand |
| `core.waveform_mean` | 4,322 × 26 × 210 | absent `waveforms` source; noticed by hand |

`core.unit_quality_labels` shows the whole defect in one run. The sorter emitted 19,061 rows and
the recipe claimed none of them, so the writer dropped them in silence. The build failed 90 s
later, on a Tier 2 rule that left-joins the missing table and fires where nothing matches, and the
finding named `core.units` — the table that was there. Two documents held the cause between them
before a byte was read, and nothing compared them.

### 1.3 Two of the three ways to lose a resource are invisible at run time

| | seen before I/O | seen during the build |
|---|---|---|
| a listed source claims less than it produces | no | yes, once the source is opened |
| the source is not listed at all | no | no |
| a `[[materialize]]` block is absent | no | no |

Only the first is visible at all, and only after the source has been opened, which on this session
is 90 s in. Nothing runs to notice the other two: an unlisted source produces no rows, and neither
does a materialization nobody asked for, so a runtime check has nothing to compare.

### 1.4 Arbitration between adapters lives in the scaffolder

Two adapters can both produce one resource, so something has to say which of them gets it.
`cli.PREFERRED` records that `core.probes` goes to the NWB rather than the sorter, and
`core.unit_electrodes` to the waveform source rather than either, "because the waveform source is
the only one that can see a unit's channel support". `cli.SHARED` records that `core.clocks` has
two legitimate suppliers.

Both live in the **scaffolder**, which drafts a recipe and is then never consulted again. The
draft freezes into a document that no longer knows what the scaffolder knew, so a recipe written
before an adapter gained a table never learns of it.

## 2. Decision

### 2.1 An adapter declares what it can produce

Every source adapter **MUST** declare `PRODUCES`, the set of resource IDs it can supply, as a
class attribute. It is **static** — a property of the adapter's code rather than of any dataset —
so reading it opens nothing.

`offers()` counts rows, so it answers a different question and needs the data. An adapter that
builds a table only when the source carries the columns for it still declares that table: the
declaration says what the adapter is capable of, and `offers()` says what one source root holds.

`TablesSource` is the exception and declares an empty `PRODUCES`. The resources it supplies are
named by the recipe entry itself, so they are not a property of the adapter at all.

### 2.2 A source that declares no `owns` takes what is left

`owns` becomes **optional**. An entry declaring one still narrows to exactly the resources it
names. An entry declaring none **MUST** be read as owning every resource in its adapter's
`PRODUCES` that no other source in the recipe owns.

A recipe therefore records only its departures from that default: **it states what it narrows, and
silence means the whole of `PRODUCES`.** The default errs in the direction that is recoverable,
because a resource a source picks up by accident becomes a validation finding and a resource
dropped by accident becomes nothing at all.

Two defaulted entries can land on one resource, and §1.4's `PREFERRED` and `SHARED` are what decide
between them. Both move out of the scaffolder and into the recipe, so a draft and a build resolve a
contested resource the same way. Where no preference decides it and two entries are left owning one
resource, the recipe **MUST** be refused naming both, since a silent winner is what `owns` was
introduced to prevent.

### 2.3 A check reports an unclaimed resource before any I/O

`Recipe.check` **MUST** report, as a **warning**, every resource some listed source declares in
`PRODUCES` that no source in the recipe claims. A warning rather than an error, because narrowing
is legitimate and only the recipe's author knows whether this one was meant.

That is the first of §1.3's three cases, moved from 90 s into the build to before a byte is read.
The other two stay out of reach this way. Catching them means comparing a finished packet against
the one it replaces, a separate mechanism this revision does not specify.

### 2.4 Keeping `owns` mandatory and reporting the gap at run time

That is what the writer does now. It cannot see a source the recipe does not list, so it reaches
one of §1.3's three cases, and it fires only after the source is opened, which is where §1.2's
90 s went. Keeping the runtime note is still worth it as the measured backstop: it reports the
rows actually discarded, where §2.3 reports a capability. It cannot be the whole answer.

## 3. What this does not change

- **`contributes` is unchanged.** It stays explicit: a resource that several sources each supply
  part of is a claim about the data rather than about an adapter's capability.
- **No stored value changes, and no packet needs rebuilding.** This is a rule for reading a recipe.
- **An existing recipe keeps its meaning.** Every recipe today declares `owns` on every source, and
  §2.2 changes nothing for an entry that declares it.
- **`RECIPE_SUPPLIES` is untouched.** `core.sessions`, `core.subjects` and `core.processing_runs`
  come from the recipe's own declarations, and what the recipe itself writes is not an adapter's to
  claim.

## 4. Open

- **Whether a missing `[[materialize]]` can be defaulted.** A materialization is a choice about
  what to spend space on rather than a capability, so there is no set to default to. Nothing
  catches an absent one before a build except a comparison against the packet it replaces.
- **Whether `PRODUCES` should be checked against what the adapter actually emits.** A declaration
  that drifts from the code reintroduces the defect one level up. A test asserting that every key
  an adapter returns appears in its `PRODUCES` would close it, at the cost of a fixture per adapter
  this revision does not specify.
