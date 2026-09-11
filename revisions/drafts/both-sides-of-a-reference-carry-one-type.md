# Both Sides of a Reference Carry One Type

| | |
|---|---|
| **Status** | Draft |
| **Amends** | Part 02 §7 (a reference's two sides agree on type, as they already agree on role and identity) |
| **Depends on** | R2 §6 (a reference names the target resource and both sides' columns), R48 §2.3 (a reference relates columns of the same role), R53 §2.3 (an identifier declares `carried` or `assigned`), R53 §2.4 (an identifier is `int64` where its distinct values may exceed `int32`) |
| **Profile** | all |

Normative, except §2, which is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

Part 02 §7 requires a reference to relate columns of the same **role**, and of the same **identity**
where both are identifiers. It says nothing about their **type**, and a join is on values: two
columns of different types do not resolve to each other whatever their role and identity say.

This part adds the type to that sentence.

## 2. Background

Informative.

### 2.1 The role rule and the identity rule share the type's reason

R48 §2.3 requires the same role because R3 §6 has a 1-based client convert every
`structural_index` at the boundary, and converting one side of a join and not the other breaks it.
Part 02 §7 requires the same identity because an assigned identifier resolves through its target's
map where a carried one is copied (R53 §2.3), so relating the two numbers each side differently.

Both are the same argument: a reference is a promise that two columns hold the same values, and
anything that makes one side's values differ from the other's breaks it. A type does that most
directly of all — `string` `"7"` and `int32` `7` are not the same value, and no rule in the
registry compares them.

### 2.2 R53 §2.1 is the change that would have gone unseen

R53 §2.1 made every identifier column `int32`, where all 110 had been `string`. A reference from
outside core onto one of them — `aind_unit_qc.metrics.unit_id` joining `core.units.unit_id` is the
live example — agreed on type before that revision and would not afterwards unless it changed with
it.

Nothing would have said so. The role is `identifier` on both sides and matches; the identity is
`assigned` on both sides and matches; the target exists and the arity is right. `registry/check.py`
runs each of those over core and every extension, and follows Part 02 §7 exactly in comparing no
type.

The four extensions in this repository were updated with R53 and agree. What the case shows is
that agreement is not checked, and an extension authored elsewhere against an older registry is
what R109 §3.1 makes ordinary by requiring no code of an extension, and therefore no shared
environment through which a disagreement would surface as an import error.

## 3. Decision

Both columns of every column pair in a `references` entry **MUST** carry the same type, as they
already carry the same role (R48 §2.3) and the same identity where both are identifiers
(Part 02 §7).

Where R53 §2.4 requires `int64` of an identifier whose distinct values may exceed `int32`, every
column referencing it takes `int64` too. The escape is taken on both sides or on neither, which is
what this clause makes explicit: a narrow column referencing a wide one is the silent truncation
the rule exists to forbid.

This binds an extension's registry as it binds core's, because an extension is a registry document
in the same format (Part 09 §5.1) and Part 02's rules are what that format is.

## 4. What this does not change

- **No table, column, reference, rule or vocabulary changes, and no packet is rebuilt.** The rule
  is a constraint on what a registry may declare, and every registry in this repository already
  satisfies it.
- **A reference may still be composite, nullable or self-referencing** (Part 02 §7). This binds
  each column pair, so a composite reference satisfies it pairwise.

## 5. Consequence

Part 02 §7's sentence gains the type, and `registry/check.py` gains one invariant beside the role
and identity ones it already runs — over core and over every extension, as its others are. Building
it over core alone is the defect R55 was written for, and an extension is where this disagreement
arises, because nothing regenerates one when core moves.

Measured across the registry as it stands, **148 column pairs** are related by the **128**
references core and the four extensions declare — 124 pairs in core, 24 in the extensions, of
which 18 target core. **None disagrees on type**, so the check passes on the day it is written and
is a ratchet rather than a repair. All 126 identifier columns are `int32`, so R53 §2.4's escape is
unexercised and §3's second paragraph binds nothing yet.
