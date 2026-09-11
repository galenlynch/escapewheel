# An Extension Declares the Core It Was Authored Against

| | |
|---|---|
| **Status** | Draft |
| **Amends** | Part 09 §5.5 (what an extension's version declaration names); Part 02 §3 (what a registry version may be reused for) |
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
consumer may conclude from it, and what a registry version may not be reused for.

## 2. Background

Informative.

### 2.1 `extends` names the standard and an extension rests on the registry

The two are different artifacts with different rates of change. The **logical standard version**
names the standard's own revision, `escapewheel-logical-v0.1`, and R84 §2.3 kept `v0.1` through the
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

### 2.3 Holding a version steady is a decision, and needs to be a stated one

A registry version that does not move while the registry does is not automatically a defect. During
development, when every packet carrying that version is held by the project that produced it,
holding it costs nothing and rebuilding is what settles any disagreement — this repository has held
`0.1.0` deliberately for that reason, and rebuilds both packaged sessions rather than versioning
each change.

What makes it safe is the condition, not the choice, and the condition is unstated. A packet leaving
the project takes the version string with it, and from then on two registries sharing one version
and differing in a column is exactly what R2 §8's "a packet whose embedded registry disagrees with
its recorded version is invalid" exists to prevent. The extensions already version independently —
`dynamic_foraging` is at 0.3.0 and the other three at 0.2.0 — so the machinery works; what is
missing is what a held version means and when holding it stops being available.

## 3. Decision

### 3.1 An extension declares the registry version it was authored against

An extension registry **MUST** declare `extends_registry`, the `registry_version` of the core
registry its references were resolved against, alongside the `extends` R17 §5 already requires.
`extends` names the standard the document's *format* follows; `extends_registry` names the content
its *references* rest on, and a reference joins content.

An extension that declares no reference into core **MAY** omit it, having nothing to resolve.

### 3.2 What a consumer concludes from a version it does not recognise

A validator meeting an extension whose `extends_registry` differs from the core registry in the
packet **MUST** report it, and **MUST NOT** refuse the packet for it alone. The two versions
differing is a fact about how the packet was assembled, not a defect in its rows: R17 §4 keeps an
extension's verdict apart from core's, and a reference that still resolves is still sound.

A validator **MUST** check the references themselves whatever the versions say. A declared version
is a claim about what an author had in hand, and the anti-joins Tier 1 generates are what establish
that the rows agree.

### 3.3 A registry version names one registry

A `registry_version` **MUST NOT** name two registries that differ in any table's name, or in any
column's name, type, presence or role. Adding a table or an optional column is the case this admits
and it is not the common one: R53 §2.1 changed 110 columns' types under one version, and R88 §2.1
changed a column's presence on eight tables.

### 3.4 A version may be held while the project holds every packet

A project **MAY** hold `registry_version` steady across changes §3.3 would otherwise require it to
move for, while every packet carrying that version is under its own control and can be rebuilt. It
**MUST** record that it is doing so, and **MUST** move the version before a packet carrying it is
published where the project cannot rebuild it.

This is what makes §3.3 a rule about published registries rather than about every edit during
development, and it is the state this repository is in: `0.1.0` has been held deliberately through
45 revisions that changed a column, and both packaged sessions are rebuilt rather than versioned.

## 4. What this does not change

- **No table, column, reference, rule or vocabulary of core changes**, and no packet is rebuilt.
  What is added is a field on an extension's registry document, which is not a core resource.
- **An extension still versions independently.** R17 §5 is untouched: `registry_version` on an
  extension is its own, and `extends_registry` records what it was authored against rather than
  tying the two together.

## 5. Consequence

Part 09 §5.5 gains `extends_registry` and what a validator does with it; Part 02 §3 gains what a registry
version may name. The four extension registries each gain one field, and `registry.schema.json`
gains an optional property beside `extends`.

Nothing is refused that was not refused before: §3.2 makes a version mismatch a report, and the
references are checked by the anti-joins that already run. What the field buys is that an extension
authored elsewhere records what it resolved against, which R109 §3.1 makes the ordinary case by
requiring no code of an extension and therefore no shared environment to agree through.

## 6. Open

- **Whether a held version should be recorded in the packet or beside the registry.** §3.4 requires
  a project to record that it is holding one and does not say where. In the registry document is the
  obvious place and makes every packet carry it; in the project's own documentation keeps a
  development decision out of an artifact that outlives it. Neither has been tried, and the choice
  matters only when the first packet is published.
