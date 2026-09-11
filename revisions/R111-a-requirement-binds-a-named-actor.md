# R111 — A Requirement Binds a Named Actor

| | |
|---|---|
| **Status** | **Accepted** 2026-09-10 |
| **Amends** | Part 00 §2 (adds the actors to Terms and definitions); Part 05 §10 (the conformance classes name the actor they are properties of); 46 clauses across every part but Parts 07 and 08 and Part 10 that name neither an actor nor what they bind |
| **Depends on** | R79 §2.2 (a packet obligation and an importer obligation are reported apart), R75 §2.1 (logical determinism binds an importer), R67 §2.4 (a requirement may bind an actor no tool can watch), R93 §3.6 (each part states what it binds) |
| **Profile** | all |

Normative, except §2, which is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

The specification requires things of a writer, a reader, a validator, a consumer, a build, an
adapter, an importer, an implementation and a client. It defines none of them. Part 00 §2 is titled
**Terms and definitions** and defines seven terms — the three vocabulary
levels, a packet, its catalog, an Iceberg catalog, and resource identity — and no actor at all.

This part adds the actors to that section, says what a requirement may bind, and gives an actor to
the 46 clauses that name neither.

Measured over the eleven v0.2 parts as they stand: **12 actor nouns and 249 mentions, of which 146 sentences
carrying a MUST, SHOULD or MAY name one.** Seven of those name two, mostly because they bind two.

## 2. Background

Informative.

### 2.1 A validator cannot tell which obligations bind it

Part 05 §10 sets two conformance classes against each other and makes a validator's report depend on
telling them apart. Packet conformance is a property of the bytes; **importer conformance is a
property of a process**; and a validator **MUST NOT** report a packet as non-conforming for an
obligation that binds only an importer.

Applying that rule means deciding, clause by clause, whether an obligation binds the process. Part 05
does not make that decidable, because it spreads its own writing-side obligations across three
nouns:

| part | writer | build | importer |
|---|---:|---:|---:|
| Part 05 validation and import | **8** | **12** | **3** |

Nothing says whether those are one actor or three. A validator implementing Part 05 §10 has to guess,
and a guess either suppresses a finding a packet deserved or reports one against a packet that
never had the chance to comply.

### 2.2 The read side already draws a line the document never states

The other pair is not confusion. Part 01, the semantic standard, binds **19** clauses to a consumer
and 2 to a reader; Part 03, the portable physical profile, binds **6** to a reader and none to a
consumer. The split follows what the part is about: Part 03 governs how bytes come back, Part 01 governs
what the values mean once they have.

Both clauses below are correct under that reading, and neither part says so:

- Part 03 — a reader **MUST NOT** depend on stored order for correctness.
- Part 01 — a consumer that does not recognise a basis **MUST NOT** treat the coordinate as
  `measured` (R58 §2.2).

A reader is bound by what it **returns**; a consumer by what it **concludes**. That distinction is
load-bearing — R58 §2.2's rule cannot be discharged by a reader, which has no way to know what its
caller is about to assume — and it survives only as a habit of whoever was writing.

### 2.3 Eight requirements bind something that cannot comply

Where no actor fits the sentence, the modal attaches to whatever noun is there:

- Part 05 — "The check MUST refuse:", "The check MUST report as a **warning**:", "A source entry that
  declares no `owns` **MUST be read as** owning every resource in its adapter's `PRODUCES`"
- Part 03 — "The test **MUST be over-inclusive where it is uncertain**", "A check MUST be re-run
  when it is attached to a resource the amendment writes"
- Part 04 — "A verification pass MUST report what it skipped"
- Part 00 — "A rewrite of rows MUST NOT increment `packet_version`"
- Part 01 — "Both versions … MUST NOT be normalised, padded, or parsed into components"

A check does not refuse; whoever runs it does. This is the same defect as the two above rather than
a third one: with no roster to reach for, an author reaches for the nearest noun, and sometimes the
nearest noun is the process itself.

Those eight are the clauses whose subject is an abstract process. A second and larger group phrases
the requirement in the **agentless passive** — **38 clauses** of the form "X MUST be *verbed*" with
no "by" — and reading them individually splits three ways:

| | count | example |
|---|---:|---|
| elides an actor the roster names | **25** | "A recipe MUST be checked against the registry before any source is opened" — a build |
| names an artifact, and hides both the part and the action | **12** | "`INT96` MUST NOT be used"; "A table whose purpose is to hold arbitrary name-value pairs MUST NOT be added to core" |

The remaining one is Part 05 §3.4's, already counted above. The second group is not the first defect
in disguise: nobody is missing from "`INT96` MUST NOT be used", but **which part** of a packet is
also missing, and so is the verb. A wall-clock column is what may not use `INT96`, and saying so
turns a rule a reader must place into one that points at what a validator opens.

Doing both here rather than deferring either is what keeps §3.3 true on the day it lands: a part
stating that every requirement binds an actor or describes an artifact, over a specification with
46 clauses doing neither, would be violated by the document that contains it.

## 3. Decision

### 3.1 The specification names four actors

Part 00 §2 gains four definitions, and every requirement in every part binds one of them:

- A **writer** produces a packet from sources. It stages, validates and commits, and it is the
  actor Part 05 binds throughout.
- A **reader** opens a committed packet and returns its resources — rows, arrays, resolved
  references. It is bound by what it returns.
- A **validator** decides whether a packet conforms, and reports findings.
- A **consumer** interprets values a reader returned and acts on them. It is bound by what it
  concludes, and it is the only actor that may be a person rather than a program.

An actor is a **part someone plays, not a distribution**: one program is commonly all four, and
`escapewheel-reader` is a reader and a consumer at once when it resolves a discriminator. Naming
them separately is what lets a clause say who owes the obligation.

### 3.2 A build, an adapter and an implementation resolve to those four

Three terms already in use are defined in terms of the four rather than beside them, so the clauses
carrying them keep their meaning:

- A **build** is one execution of a writer against one recipe. A requirement on a build binds the
  writer performing it, which is what makes Part 05 §10 decidable: an obligation on a build or a
  writer is an importer obligation, and one on a packet is not.
- An **adapter** is the part of a writer that reads one source. An obligation on an adapter binds
  the writer that ships it.
- An **implementation** is software performing one or more of the four actors. It is the right
  subject only where a requirement binds every actor alike — Part 00 §2.7's ban on HDF5 object
  references is one.

### 3.3 A requirement binds an actor, or states a property of an artifact

Every MUST, MUST NOT, SHOULD, SHOULD NOT and MAY in this specification **MUST** do one of two
things, and a clause doing neither is a defect in this specification rather than a rule anything
can fail:

1. **Bind an actor** named in §3.1 or resolving to one by §3.2, which says who complies.
2. **State a property of an artifact** — a packet, a table, a column, a manifest entry — which is
   inspectable. "A packet carrying sorted units MUST carry `core.sorting_runs`" binds nobody and is
   sound, because the packet either carries them or does not. Such a clause **MUST** name the part
   of the artifact it constrains and **MUST** put the constraint in an active verb: "a wall-clock
   column MUST NOT use `INT96`" over "`INT96` MUST NOT be used", which leaves a reader to work out
   what the rule is about before they can apply it.

This clause binds whoever writes this specification, and nothing else in it does. No validator
inspects the specification, so a clause failing it is corrected here rather than reported anywhere.

A requirement no tool can check is permitted under the first form and is not this defect: a
consumer **MUST NOT** infer attachment from a device's name (R67 §2.4) binds a named actor to a
determinable behaviour, and no tool can watch it.

### 3.4 Four spellings are retired

`importer` is another name for a writer, `client` and `binding` for a reader, and `caller` for a
consumer. An accepted revision using one binds the actor it names. This is a definition and carries
no modal, as Part 00 §2's definitions do not and as Part 00 §9's precedence rule does not:

| retired | reads as | mentions |
|---|---|---:|
| `importer` | writer | 7 |
| `client` | reader | 3 |
| `binding` | reader | 2 |
| `caller` | consumer | 1 |

R75 §2.1 and Part 05 §10 both bind an importer, and both continue to bind the writer without amendment.
Part 05 §10's two classes are renamed to say what they are properties of: **packet conformance** and
**writer conformance**.

### 3.5 Thirty-four requirements gain an actor, and twelve name what they constrain

Each of §2.3's abstract-subject clauses and each of its agentless passives names the actor that
performs it — 34 in all, by part: 3 in Part 00, 2 in Part 01, 9 in Part 02, 9 in Part 03, 3 in Part 04, 14 in
Part 05, 2 in Part 06 and 4 in Part 09, counting the twelve restated as predicates. By actor: **13 a writer** — immutability, amendment order, `packet_version`, stray
removal, recording the recipe and its digest, streaming a large table, converting a half-open
interval, recording a compensation, materialization, and the two spike-omission clauses of Part 06;
**6 a validator** — the two checks, the shim's non-SQL tests, an extension's verdict in both Part 05
and Part 09, and the deterministic-build clause; **4 a consumer** — the source-provenance label, the
undecoded code, the joinability rules, and resolution through a different document; **3 a build** —
recipe checking, refusal on a defaulted resource, and a silent `owns`; and **1 a reader**, reporting
an unresolved `source`.

Twelve bind an artifact rather than an actor, and are restated under §3.3's second form so that each
names the part it constrains and states it actively: a **wall-clock column** does not use `INT96`, a
**column's type** is not `list`, `struct` or `map`, an **array's codec chain** does not include
`transpose`, a **catalog entry** for an external asset declares it external, a **`metadata` column's
presence** is `optional`, an **extension's resource identifier** begins with its namespace, a
**naming exception** carries a reason, a **Tier 2 rule** expresses no storage-layer test, and
**core** holds no arbitrary name-value table.

Three are a judgement call and are settled here rather than left to whoever implements the sweep.
Part 00 §4.1's "Core resources MUST be validated before they are committed" binds a **writer**, since
Part 05 §1 makes validate-then-commit the writer's own sequence and not a verdict anyone reports.
Part 03 §7's stray binds a **writer**, cleanup being a mutation of a packet whatever it is called.
Part 04 §5.5's unresolved source splits: a **reader** reports it, and a **validator** does not fail
structural validation for it.

## 4. What this does not change

- **No table, column, reference, rule or vocabulary changes, and no packet is rebuilt.** This part
  binds how the specification is written, so what changes is which clauses a reader can act on.
- **No obligation moves between packet conformance and writer conformance.** §3.2 makes the
  existing boundary decidable rather than redrawing it: every clause binding a build or a writer
  today was already an importer obligation under Part 05 §10, and every clause about a packet's
  contents was already the other.

## 5. Consequence

Part 00 §2 gains four definitions and three derived terms; Part 05 §10 renames one of its conformance
classes; 34 clauses gain an actor and 12 name the part of the artifact they constrain. Thirteen
mentions of a retired spelling are repointed.

The reference implementation changes nothing. `escapewheel-reader`, `-validator` and `-writer`
already divide along three of the four actors, and the fourth has no code because a consumer is
whoever calls them.

What this buys is that Part 05 §10 becomes a rule a validator can apply. It could not before: the
part it governs binds 8 clauses to a writer, 12 to a build and 3 to an importer, and a validator
deciding which of those are importer obligations was deciding it by name.

## 6. Open

- **Whether the 146 sentences that already name an actor name the right one.** §2.2 measures that the
  read side splits cleanly by part, which is evidence the habit was sound rather than proof of it,
  and this part audits none of them. What it provides is the definitions that make such an audit
  mechanical: read the clause, ask whether the obligation is about what is returned or what is
  concluded, and repoint it where the answer disagrees with the noun. Doing that as a sweep would
  put every clause in this specification into one revision, which is not a change anyone could
  review.
