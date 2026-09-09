# Every Clock Declares When It Was Observing

| | |
|---|---|
| **Status** | Draft |
| **Amends** | `05` §3.3 (ownership), `05` §3.4 (what a source can produce); adds one Tier 2 rule on `core.clocks` |
| **Depends on** | R38 (observation belongs to the clock), R39 (the session's time origin), R63 (default ownership when a recipe omits `owns`) |
| **Profile** | all |

Normative, except §2 and §6, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

R38 §2.1 gave a clock a table saying when it was observing, and R38 §2.3 made everything else
depend on it: a unit or an event stream is observed during its clock's declared intervals, and may
narrow them but never replace them. Nothing says a clock must declare any.

Both packaged packets declare one interval for thirteen and eleven clocks. This part requires one
per clock, gives the requirement a rule, and closes the two mechanisms that let the rows be dropped
without a word.

Measured on **`ecephys_776259`** (twelve probes, 6,781 sorted units, recorded 2025-04-09) and
**`ecephys_786867`** (ten probes, 4,505 units, recorded 2025-09-25).

## 2. Background

Informative.

### 2.1 One window for thirteen clocks

| | clocks | with anchors | with an observation interval | with both |
|---|---|---|---|---|
| `ecephys_776259` | 13 | 12 | 1 | **0** |
| `ecephys_786867` | 11 | 10 | 1 | **0** |

The one interval in each packet belongs to `harp`, the reference clock, which has no parent and no
anchors of its own. Every probe clock — the clocks that carry the spikes — declares none.

The rows exist and are discarded. `SorterSource.observation_intervals` produces one window per
stream's sample clock, taken from the extent of the recording it counts and explicitly not from the
spikes, which is what R38 §2.3 requires of a window: a unit that fires nothing was still observed.

### 2.2 A recipe says `owns` where two sources each hold part

`core.clock_observation_intervals` has two suppliers for the same reason `core.clocks` and
`core.clock_anchors` do — the sync source knows the reference clock's window, the sorter knows each
probe clock's — and the recipe declares the first two `contributes` and the third `owns`:

```toml
[[source]]
kind = "sync"
contributes = ["core.clocks", "core.clock_anchors"]
owns = ["core.clock_observation_intervals"]
```

`05` §3.3 makes `owns` exclusive, so the sorter's twelve windows are produced and discarded.

Two mechanisms exist to catch this and neither does. `recipe.SHARED` names the resources several
sources each supply part of, so that a scaffolded recipe writes `contributes`; it lists
`core.clocks`, `core.array_assets`, `core.array_dimensions` and `core.devices`, and neither table
this defect touches. It would not have helped in any case, because it is consulted only for a
source that declares no `owns` of its own — a hand-written recipe never reaches it.

The unclaimed-rows reports are the second. R63 §2.3 requires `Recipe.check` to warn, before any
I/O, about a resource **no** source claims, and the writer adds a runtime note for rows a source
produced that nothing claims — the case a count is not knowable for until the source is read. Both
ask whether *any* source claims the resource, and one does, so both stay silent.

The runtime note states the reasoning behind that test: two sources may offer the same rows, and
where a preference names the better-informed one the loser's copy is discarded by design. It holds
where the rows are the same. Here they are **disjoint** — one window from the sync source and
twelve from the sorter, thirteen distinct clocks — and no preference is declared for this resource
at all.

### 2.3 What the missing windows cost

**The alignment bound cannot be measured.** A writer decides how far past its anchors it must map
by comparing each clock's anchors against that clock's observation window. No clock in either
packet has both, so the comparison runs over an empty intersection and the writer records the
default without measuring anything. Whether either session needs a wider bound is unknown, and no
packet built this way can say.

**R38 §2.3's inheritance is empty for twelve clocks of thirteen.** A unit or an event stream on a
probe clock inherits a window from a clock that declares none.

**R39's origin is a minimum over one clock.** `t_zero_tick` is the earliest observation start
across all of a session's clocks (R39 §2.1), and both packets declare exactly the `harp` window's
own `start_tick`. Measured against the earliest probe anchor on the reference clock, that is **8
ticks — 256 µs — early** in `ecephys_776259` and exact in `ecephys_786867`. The value is right
because this rig starts its reference clock first, not because the packet computed what R39 §2.2
requires.

### 2.4 The corpus narrows a window it does not carry

`fixtures/build.py` writes `core.unit_observation_intervals` and
`core.event_stream_observation_intervals` across its 26 packets and never writes
`core.clock_observation_intervals`. Those two tables are R38 §2.3's *refinements* of a clock's
window, so the corpus carries narrowings of something it does not declare — and no packet in it
declares a `t_zero_tick`, which is consistent, since R39 §2.2 says a packet with no observation
intervals declares none.

The artifact whose purpose is to prove two implementations agree does not exercise the table R38
added, which is why nothing here was caught by the corpus either.

## 3. Decision

### 3.1 A clock declares at least one interval

A packet **MUST** declare at least one row of `core.clock_observation_intervals` for every clock it
declares in `core.clocks`. More than one stays permitted, for an acquisition paused and resumed
(R38 §2.1).

One Tier 2 rule, `core.clocks.observation_declared`, returns every clock with no interval. It is an
anti-join and needs no new column.

A packet declaring no `core.clock_observation_intervals` at all fails on every clock. A validator
creates an empty stand-in for a registry table a packet does not carry, so the rule evaluates
rather than being skipped, and the anti-join then returns everything. That is the right answer: a
packet declaring clocks and no windows is this defect at its largest, not an exemption from it.

R39 §2.2 contemplates such a packet, requiring it to declare no `t_zero_tick`. That sentence stands
and becomes unreachable on a conforming packet, as R82 §2.3 left R41 §2.4.

### 3.2 A resource several sources supply is declared `contributes`

A recipe **MUST NOT** declare `owns` for a resource that more than one of its sources produces rows
for, unless the recipe declares a preference between them. `05` §3.3's exclusivity is for a
resource one source is responsible for; where two sources each hold part, `contributes` is the
declaration and `owns` silently discards the part the owner does not hold.

`core.clock_observation_intervals` and `core.clock_anchors` are both such resources and both are
added to `recipe.SHARED`, so a scaffolded recipe declares them `contributes`.

### 3.3 A discarded row is reported unless a preference explains it

A build **MUST** report rows a source produced for a resource another source owns, except where
the recipe declares a preference between them. That another source claims it is not the exemption;
a declared preference is.

R63 §2.3 requires the neighbouring warning — a resource *no* source claims, reported by
`Recipe.check` before a byte is read. This is the case where one source does claim it, so that
check passes and the rows discarded are a different source's. The count is not knowable until that
source is read, which is why it is a report at build time rather than a refusal at check time.

The exemption follows the reasoning rather than the mechanism: a preference says two sources offer
the same rows and names the one that knows more, which makes the loser's copy redundant. Without
one, two sources producing rows for one resource are producing different rows, and discarding
either is an omission rather than a decision.

## 4. What this does not change

- **No table, column or reference.** The table R38 §2.1 added is unchanged; what changes is that a
  packet must fill it for every clock.
- **A refinement is still optional.** R38 §2.3's `core.unit_observation_intervals` and
  `core.event_stream_observation_intervals` narrow a clock's window where something measured drift,
  and a packet carrying neither is conforming — which is now true against a window that exists.
- **`owns` keeps its meaning.** §3.2 narrows where it may be declared, not what it does when it is.

## 5. Consequence

70 Tier 2 rules become **71**. No table, column or reference changes.

`fixtures/build.py` writes `core.clock_observation_intervals` for both of its clocks across the 26
corpus packets, which the rule forces rather than invites: every packet in the corpus declares
clocks and no windows, so all 26 fail until they carry them. One variant is added whose expected
finding is a clock without one, and the corpus gains a `t_zero_tick` it could not previously
compute.

The two recipes declare `core.clock_observation_intervals` under `contributes`, and both packets
are rebuilt — which R87 §2.1, R88 §2, R91 §5, R95, R96 and R97 already require. After the rebuild
`ecephys_776259` carries 13 intervals rather than 1 and `ecephys_786867` carries 11, and the
alignment bound becomes measurable for the first time.

`recipe.SHARED` gains two entries and `session._note_unclaimed` compares against declared
preferences rather than against every source's claims.

## 6. Open

- **Whether a clock that is only a parent needs a window.** Every clock in both packets is either
  observed or is the reference, and the reference declares one, so §3.1 costs nothing here. A
  packet declaring a purely notional parent — a UTC clock a rig clock is offset from — would have
  nothing to declare for it, and would need either an exemption or a clock it does not declare.
- **Whether the bound, once measurable, changes either packet.** §2.3 says the comparison has never
  run. It may find that both sessions sit within one median anchor interval after all, or it may
  widen the bound and place spikes that are dropped today.
