# R63 — A Recipe Declares What It Narrows, Not What It Keeps

| | |
|---|---|
| **Status** | **Accepted** 2026-09-03 |
| **Amends** | `05` §3 (what a recipe declares), R2 §7 (what is checkable before I/O) |
| **Depends on** | R17 (an extension's tables are owned like core's), R53 (identifiers are assigned packet-wide) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

A recipe gives each source an `owns` list naming every resource that source supplies. The list
is written by hand, and it is a transcript of a fact the adapter already holds: `SorterSource`
knows it builds `core.unit_quality_labels`, because the method that builds them is in it.

`Recipe.check` refuses a resource owned twice, an owned resource the registry does not define,
and an owned table whose required foreign key points at a table nothing supplies — every one
of them a **contradiction** between two declarations. An omission is not a contradiction.
There is nothing in the document for the check to disagree with, so a recipe that names four
of a source's five resources is sound by every test the tool applies.

### 1.1 What that cost, measured on one packet

The dynamic-foraging packet for `ecephys_786867_2025-09-25` declares 6 sources and 31 claims
across `owns` and `contributes`. Four resources were lost, none of them by any failure of the
data or the adapters:

| lost | rows | how it surfaced |
|---|---|---|
| `core.unit_quality_labels` | 19,061 | a Tier 2 rule 90 s into the build, reported against `core.units` |
| `core.unit_electrodes` | 4,322 | a note added the same day, on its first run |
| `analysis.spike_events` | 131,396,535 | absent `[[materialize]]`; noticed by hand |
| `core.waveform_mean` | 4,322 × 26 × 210 | absent `waveforms` source; noticed by hand |

The first is the shape of the whole defect. `owns` is exclusive and discards in silence, so
the sorter emitted 19,061 rows that the recipe dropped, and the packet failed three layers
later on a rule that left-joins `core.unit_quality_labels` and fires where nothing matches —
reported against the table that *was* present. The cause was knowable from two documents with
no data in hand, and neither document was compared to the other.

### 1.2 Three ways to lose a resource, and what sees each

| | seen before I/O | seen during the build |
|---|---|---|
| a listed source claims less than it produces | no | yes, once opened |
| a source is not listed at all | no | no |
| a `[[materialize]]` block is absent | no | no |

Only the first is visible at all today, and only after the source has been opened — which on
this session is 90 s in. A source that is not in the recipe produces nothing to notice, so no
runtime check can reach the second or third.

### 1.3 The knowledge is already in the tree, in the wrong place

`cli.PREFERRED` records that `core.probes` goes to the NWB rather than the sorter, and
`core.unit_electrodes` to the waveform source rather than either, "because the waveform source
is the only one that can see a unit's channel support". `cli.SHARED` records that `core.clocks`
has two legitimate suppliers. Both live in the **scaffolder**, so they inform a draft and are
then frozen into a document that no longer consults them; a recipe written before an adapter
gained a table never learns of it.

## 2. Decision

### 2.1 An adapter declares what it can produce

Every source adapter **MUST** declare `PRODUCES`, the set of resource IDs it can supply, as a
class attribute. It is **static** — a property of the adapter's code, not of any dataset — and
so is readable with nothing open.

`PRODUCES` is distinct from `offers()`, which counts rows and therefore needs the data. An
adapter that builds a table only when the source carries the columns for it still declares that
table in `PRODUCES`: the declaration says what the adapter is capable of, and `offers()` says
what this root actually holds.

`TablesSource` is the exception and declares an empty `PRODUCES`, because the resources it
supplies are named by the recipe entry itself and are not a property of the adapter at all.

### 2.2 `owns` becomes optional, and its absence means everything

A `[[source]]` entry that declares no `owns` **MUST** be read as owning every resource in that
adapter's `PRODUCES` that no other source in the recipe owns. An entry that declares `owns`
narrows to exactly what it names, unchanged from today.

So a recipe states what it **narrows**, and silence means the whole. The default is safe in the
direction that matters: a resource included by accident is a validation finding, where one
excluded by accident is data that quietly is not there.

Arbitration between adapters that both declare a resource in `PRODUCES` moves out of the
scaffolder and into the recipe layer, so a build and a draft resolve it the same way. Where two
sources default to the same resource and no preference is declared, the recipe **MUST** be
refused naming both — a silent winner is what `owns` was introduced to prevent.

### 2.3 What a check can then say before any I/O

`Recipe.check` **MUST** report, as a **warning**, every resource some listed source declares in
`PRODUCES` that no source in the recipe claims. A warning and not an error, because narrowing is
legitimate and only the recipe's author knows whether this one was meant.

This is the first of §1.2's three cases, moved from 90 s into the build to before a byte is
read. The other two are not reachable this way and are addressed by comparing a finished packet
against the one it replaces, which is a separate mechanism and not part of this revision.

### 2.4 The obvious alternative

Leaving `owns` mandatory and reporting the gap at run time is what the writer does now. It
cannot see a source the recipe does not list, so it addresses one of three cases; and it fires
after the source is opened, which is where the 90 s went. A runtime note remains worth keeping
as the measured backstop — it reports actual rows discarded, where §2.3 reports a capability —
but it cannot be the whole answer.

## 3. What this does not change

- **No change to `contributes`.** It stays explicit: a resource several sources each supply
  part of is a claim about the data, not about an adapter's capability.
- **No stored value changes**, and no packet needs rebuilding. This is a recipe-reading rule.
- **An existing recipe keeps its meaning.** Every recipe today declares `owns` on every source,
  and §2.2 changes nothing for an entry that declares it.
- **`RECIPE_SUPPLIES` is untouched.** What the recipe itself writes is not an adapter's to
  claim.

## 4. Open

- **Whether a missing `[[materialize]]` can be defaulted.** A materialization is a choice about
  what to spend space on, not a capability, so there is no set to default to. Left as the case
  only a comparison against a previous packet catches.
- **Whether `PRODUCES` should be checked against what the adapter actually emits.** A
  declaration that drifts from the code reintroduces the defect one level up. A test asserting
  every key an adapter returns appears in its `PRODUCES` would close it, and costs a fixture per
  adapter this revision does not specify.
