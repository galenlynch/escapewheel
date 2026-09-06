# R72 — A Discriminator Resolves in Both Directions

| | |
|---|---|
| **Status** | **Accepted** 2026-09-04 |
| **Amends** | R55 §2.4 (the checks a discriminator implies), `05` §? (what a packet's verdict covers) |
| **Depends on** | R55 (a discriminated reference), R54 §2.4a (a kind must name a resource the packet declares) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R54 §2.4a states that an interval whose kind resolves to nothing leaves the row uninterpretable,
and R55 §2.4 generates the checks that enforce a discriminator. One direction is missing.

### 1.1 Measured: the reverse anti-join is not generated

Generating every check for the current registry and the `dynamic_foraging` extension:

| direction | check | generated |
|---|---|---|
| the kind is a dotted resource ID | `core.intervals.interval_kind.is_a_resource_id` | yes |
| the kind names a declared resource | `core.intervals.interval_kind.kind_declared` | yes |
| the **detail row** has a core row | `dynamic_foraging.trials.session_id_interval_kind_trial_id_resolves` | yes |
| the **core row** has a detail row | — | **no** |

The last is what R54 §2.4a's *"a kind that resolves to nothing is a name again"* describes, and
nothing tests it. A `core.intervals` row may name `dynamic_foraging.trials`, the packet may carry
that table, and the row may have no counterpart in it — and every check passes.

### 1.2 Why the existing checks do not cover it

`kind_declared` compares a value against the set of resources the packet declares. It is satisfied
by the *table* existing. The reference R55 §2.3.1 requires of the detail table generates an
anti-join pointing from the detail row to the core row, which is the direction a foreign key
always points: it catches an orphan detail row and cannot catch a core row with no detail.

Neither is wrong. Together they leave the one case R54 §1 is about — a bare interval that nothing
specialises — undetected.

## 2. Decision

### 2.1 A required discriminator implies a reverse check

Where a discriminator declares `resolves: required`, a check **MUST** be generated per named kind,
returning every row of the discriminating table whose key has no counterpart in the resource its
discriminator names.

Level **error**, matching `resolves: required`. Where a discriminator declares `resolves:
optional` — R49's `scope_kind`, whose unresolvable value is a fact rather than a defect — no
reverse check is generated, since there is nothing the packet promised to hold.

### 2.2 Generated per kind, from the values present

The check is generated over the kinds a packet's rows actually name, not over every resource it
declares: a kind naming a resource the packet does not carry is already `kind_declared`'s finding,
and reporting it twice tells a reader nothing new.

Where the named resource is not carried, `kind_declared` fires and the reverse check for that kind
is **not** generated.

### 2.3 Shared key only

The check joins on the discriminating table's key, which R55 §2.3.1 requires the named resource to
carry in full. A **paired-value** discriminator (R55 §2.3) names a resource through a single
column and has no shared key to join on; §2.1 does not apply to one, and R55 §2.4's existing
value-to-key check remains its whole coverage.

### 2.4 A packet's verdict

A packet whose core passes and whose extension fails **MUST NOT** be reported as conforming. R17
§4's separable verdicts stand — a core verdict, an extension verdict per extension — and this adds
that the packet's overall verdict is the conjunction, because R71 §2.1 makes an extension's
canonical resources part of the packet's canonical data.

A consumer **MAY** still read core from a packet whose extension failed. What it MUST NOT do is
read the packet's verdict as if the failure were external to it.

## 3. What this does not change

- **No column, no table.** One generated check and one sentence about how verdicts combine.
- **No change to `resolves: optional`.** R49 §2's scope still names a rig the packet need not hold.
- **No change to R17 §4.** The verdicts stay separable and separately reported; §2.4 says how they
  compose, which R17 left open because before R54 nothing canonical lived in an extension.
- **No packet on hand becomes invalid.** Measured: all 450 intervals of the built session have a
  `dynamic_foraging.trials` counterpart, and the conformance corpus's single extension likewise.

## 4. Open

- **Whether a packet may declare a kind it deliberately does not specialise.** An epoch that means
  nothing beyond its bounds has no detail table, and today it must still name one. The honest
  answer may be a reserved kind naming no resource, which `resolves: required` currently forbids;
  nothing has needed it.
