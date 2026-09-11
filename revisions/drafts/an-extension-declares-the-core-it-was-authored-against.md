# An Extension Declares the Core It Was Authored Against

| | |
|---|---|
| **Status** | Draft |
| **Amends** | Part 09 §5.5 (what an extension's version declaration names); Part 02 §9.2 (what a registry version may name) |
| **Depends on** | R17 §5 (an extension carries its own version and names what it extends), R2 §8 (the registry carries one `registry_version` and a packet records it), R109 §3.1 (a writer requires no code of an extension), R109 §3.2 (an extension delivers a registry document and rows as files) |
| **Profile** | all |

Normative, except §2, which is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

R17 §5 has an extension carry its own version and name, in `extends`, the logical standard version
it was written against. All four extension registries in this repository name
`escapewheel-logical-v0.1`, and each declares references into core: `aind_unit_qc.metrics.unit_id`
joins `core.units.unit_id`, and thirteen more like it across the four.

A reference joins two columns, so what it rests on is those columns' names, types and presence.
None of that is what `extends` names. This part says what an extension declares instead, what a
consumer may conclude from it, and what one registry version may name.

## 2. Background

Informative.

### 2.1 `extends` names the standard and an extension rests on the registry

The two are different artifacts with different rates of change. The **logical standard version**
names the standard's own revision, `escapewheel-logical-v0.1`, and R84 §2.2 kept `v0.1` through the
rename because no clause of the standard had changed. The **registry version** names the content:
which tables exist, what each column is called, what type it holds and whether it may be null.

An extension's references resolve against the second. `aind_unit_qc` declares six references into
core, all onto `unit_id` and `session_id`, both `int32` — and both were `string` until R53 §2.1
made every identifier an integer. An extension authored before that and pinning
`escapewheel-logical-v0.1` names the same standard version afterwards, while every one of its
references has changed the type it joins on.

### 2.2 The registry moves at a rate the standard version does not

Measured over the registry as it stands: **255 of 351 columns carry a `since`**, naming the revision
that introduced or last changed them, from **45 distinct revisions**, and 23 of 43 tables carry one.
Those stamps exist because R29 §2 wanted `tables.md` to answer both what a table is and why, and
they double as a record of how much an extension's join targets can move under one standard version.

R53 §2.1 is the case that matters, because it changed a type rather than adding a column. R88 §2.1
is the other: it made `session_id` required on every session-scoped table, so an extension
declaring the column nullable would disagree with core about whether a row may omit it.

### 2.3 A version that names two registries is what breaks a declaration

R2 §8 already makes a packet whose embedded registry disagrees with its recorded version invalid,
and a packet embeds its registry, so a validator settles that by comparing the two. What R2 §8 does
not say is that one version names one registry, and `extends_registry` is worth nothing without it:
an extension recording `0.1.0` records nothing if two registries answer to `0.1.0`.

A version that does not move while the registry does is not by itself the problem. This repository
holds `0.1.0` and rebuilds both packaged sessions rather than versioning each change, so one
registry answers to it and every packet agrees with that one — which is the state §3.3 requires,
reached by rebuilding rather than by numbering. The extensions version independently and do move:
`dynamic_foraging` is at 0.3.0, `aind_opto` and `vr_foraging` at 0.2.0, `aind_unit_qc` at 0.1.0.

## 3. Decision

### 3.1 An extension declares the registry version it was authored against

An extension registry **MUST** declare `extends_registry`, the `registry_version` of the core
registry its references were resolved against, alongside the `extends` R17 §5 already requires.
`extends` names the standard the document's *format* follows; `extends_registry` names the content
its *references* rest on, and a reference joins content.

An extension that declares no reference into core **MAY** omit it, having nothing to resolve.

### 3.2 A version mismatch is reported, not refused

A validator meeting an extension whose `extends_registry` differs from the core registry in the
packet **MUST** report it, and **MUST NOT** refuse the packet for it alone. The two versions
differing is a fact about how the packet was assembled, not a defect in its rows: R17 §4 keeps an
extension's verdict apart from core's, and a reference that still resolves is still sound.

A validator **MUST** check the references themselves whatever the versions say. A declared version
is a claim about what an author had in hand, and the anti-joins Tier 1 generates are what establish
that the rows agree.

### 3.3 A registry version names one registry

Two registries that differ in any table's name, or in any column's name, type, presence or role,
**MUST NOT** share a `registry_version`. Adding a table or an optional column is the case this
admits and it is not the common one: R53 §2.1 made all 110 identifier columns `int32` under one
version, and R88 §2.1 gave eight tables a `session_id` they did not have.

## 4. What this does not change

- **No table, column, reference, rule or vocabulary of core changes**, and no packet is rebuilt.
  What is added is a field on an extension's registry document, which is not a core resource.
- **An extension still versions independently.** R17 §5 is untouched: `registry_version` on an
  extension is its own, and `extends_registry` records what it was authored against rather than
  tying the two together.

## 5. Consequence

Part 09 §5.5 gains `extends_registry` and what a validator does with it; Part 02 §9.2 gains what a
registry version may name, beside R2 §8's rule that a packet disagreeing with its recorded version
is invalid. The four extension registries each gain one field, and `registry.schema.json`
gains an optional property beside `extends`.

Nothing is refused that was not refused before: §3.2 makes a version mismatch a report, and the
references are checked by the anti-joins that already run. What the field buys is that an extension
authored elsewhere records what it resolved against, which R109 §3.1 makes the ordinary case by
requiring no code of an extension and therefore no shared environment to agree through.
