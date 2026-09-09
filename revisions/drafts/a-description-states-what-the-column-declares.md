# A Description States What the Column Declares

| | |
|---|---|
| **Status** | Draft |
| **Amends** | Six column descriptions in the registry; adds one structural check |
| **Depends on** | R101 §3.1 (every string column declares its vocabulary), R101 §3.3 (a discriminator declares none), R101 §3.5 (an open column's description states the form its values take), R55 §2.1 (a discriminator's value space is the declared resource IDs) |
| **Profile** | all |

Normative, except §2 and §5, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

R101 §3.1 made every string column declare which of three vocabularies its values are drawn from,
and R101 §3.3 made a discriminator declare none, its value space being fixed by R55 §2.1 to the
resource IDs the registry itself declares. Six descriptions still say the column is open.

A description sits beside the declaration it describes and nothing compares them, so the two can
disagree indefinitely. This part corrects the six and adds the check that would have caught them.

Measured on the registry as R103 left it: 39 core tables and 4 extension registries, 494 columns
between them.

## 2. Background

Informative.

### 2.1 Six descriptions claim a vocabulary the column does not declare

| column | declares | description says |
|---|---|---|
| `core.intervals.interval_kind` | discriminator, no vocabulary | "Open (R8 §4)" |
| `core.preferred_runs.scope_kind` | discriminator, no vocabulary | "Open." |
| `core.processing_runs.scope_kind` | discriminator, no vocabulary | "Open (R8 §4)" |
| `core.calibrations.detail_kind` | discriminator, no vocabulary | "Open, and `resolves: optional`" |
| `core.event_streams.detail_kind` | discriminator, no vocabulary | "Open, and `resolves: optional`" |
| `core.processing_runs.scope` | `vocabulary: free` | "Open, as `activity_type` is" |

The first five are what R101 §3.3 forbids claiming: a discriminator's values are not a vocabulary
a writer extends, and saying they are open invites a reader to write one the registry does not
declare. The sixth is a classification R101 §3.1 settled the other way — a scope value is an
identifier in another table's key space, meaningless without the `scope_kind` beside it, which is
`free` rather than open.

### 2.2 The right form is already in the registry

Each of the six was written before the revision that settled what the column declares. R54 §2.1,
R49 §2.1, R89 §2.1 and R91 §3.1 each wrote "Open" of a discriminator at a time when nothing said
what a discriminator's value space was; R55 §2.1 said it, R101 §3.3 made the declaration explicit,
and neither swept the prose.

R100 §2.1 wrote the two `coordinate_resource` descriptions after R55 and did not make the claim:
"The table whose rows are this axis's positions, as a dotted resource ID." Two of the registry's
seven discriminators already describe themselves correctly, which is the form the other five take
here.

## 3. Decision

### 3.1 What a description may claim

A column's `description` **MUST NOT** claim a vocabulary the column does not declare. A
discriminator's description **MUST NOT** call its values open, closed or free at all: R55 §2.1
fixes them to the dotted resource IDs the registry declares, and `resolves` says what an
unmatched one means.

`registry/check.py` checks it, taking its structural invariants from 28 to **29**. The check is
exact rather than approximate: a claim is written "Open" where the word describing a mechanism is
written lowercase, so `dynamic_foraging.sessions.left_valve_open_time` and its right-hand twin
are not caught and need no declared exception.

### 3.2 The six descriptions

Each of the five discriminators states what its values are and stops, as R100 §2.1's two already
do. `core.processing_runs.scope` states that its value is an identifier in the table
`scope_kind` names, which is why comparing one across packets establishes nothing and why R101
§3.1 classified it `free`.

## 4. Consequence

Six descriptions change and `registry/check.py` gains one structural invariant, going from 28 to
**29**. No column, table, reference, rule or declaration moves, and no packet is invalidated: a
description is registry text, so what changes is the registry each packet embeds.

## 5. Open

- **Whether the same drift reaches the parts.** This swept the registry's 494 columns and found
  the six. `01` and `02` name four of the discriminators and call none of them open, so nothing
  here is owed there — but the sweep that found these was a search for one word, and prose can
  disagree with a declaration in ways no pattern catches.
