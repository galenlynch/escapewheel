# A Requirement Binds a Named Actor

| | |
|---|---|
| **Status** | Draft |
| **Amends** | `00` §2 (adds the actors to Terms and definitions); `05` §10 (the conformance classes name the actor they are properties of); eight clauses across `00`, `01`, `03`, `04` and `05` that bind no actor |
| **Depends on** | R79 §2.2 (a packet obligation and an importer obligation are reported apart), R75 §2.1 (logical determinism binds an importer), R67 §2.4 (a requirement may bind an actor no tool can watch), R93 §3.6 (each part states what it binds) |
| **Profile** | all |

Normative, except §2, which is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

The specification requires things of a writer, a reader, a validator, a consumer, a build, an
adapter, an importer, an implementation and a client. It defines none of them. `00` §2 is titled
**Terms and definitions** and defines seven terms — the three vocabulary
levels, a packet, its catalog, an Iceberg catalog, and resource identity — and no actor at all.

This part adds the actors to that section, says what a requirement may bind, and gives an actor to
the eight clauses that bind none.

Measured over the eleven v0.2 parts as they stand: **12 actor nouns and 249 mentions, of which 146 sentences
carrying a MUST, SHOULD or MAY name one.** Seven of those name two, mostly because they bind two.

## 2. Background

Informative.

### 2.1 A validator cannot tell which obligations bind it

`05` §10 sets two conformance classes against each other and makes a validator's report depend on
telling them apart. Packet conformance is a property of the bytes; **importer conformance is a
property of a process**; and a validator **MUST NOT** report a packet as non-conforming for an
obligation that binds only an importer.

Applying that rule means deciding, clause by clause, whether an obligation binds the process. `05`
does not make that decidable, because it spreads its own writing-side obligations across three
nouns:

| part | writer | build | importer |
|---|---:|---:|---:|
| `05` validation and import | **8** | **12** | **3** |

Nothing says whether those are one actor or three. A validator implementing `05` §10 has to guess,
and a guess either suppresses a finding a packet deserved or reports one against a packet that
never had the chance to comply.

### 2.2 The read side already draws a line the document never states

The other pair is not confusion. `01`, the semantic standard, binds **19** clauses to a consumer
and 2 to a reader; `03`, the portable physical profile, binds **6** to a reader and none to a
consumer. The split follows what the part is about: `03` governs how bytes come back, `01` governs
what the values mean once they have.

Both clauses below are correct under that reading, and neither part says so:

- `03` — a reader **MUST NOT** depend on stored order for correctness.
- `01` — a consumer that does not recognise a basis **MUST NOT** treat the coordinate as
  `measured` (R58 §2.2).

A reader is bound by what it **returns**; a consumer by what it **concludes**. That distinction is
load-bearing — R58 §2.2's rule cannot be discharged by a reader, which has no way to know what its
caller is about to assume — and it survives only as a habit of whoever was writing.

### 2.3 Eight requirements bind something that cannot comply

Where no actor fits the sentence, the modal attaches to whatever noun is there:

- `05` — "The check MUST refuse:", "The check MUST report as a **warning**:", "A source entry that
  declares no `owns` **MUST be read as** owning every resource in its adapter's `PRODUCES`"
- `03` — "The test **MUST be over-inclusive where it is uncertain**", "A check MUST be re-run
  when it is attached to a resource the amendment writes"
- `04` — "A verification pass MUST report what it skipped"
- `00` — "A rewrite of rows MUST NOT increment `packet_version`"
- `01` — "Both versions … MUST NOT be normalised, padded, or parsed into components"

A check does not refuse; whoever runs it does. This is the same defect as the two above rather than
a third one: with no roster to reach for, an author reaches for the nearest noun, and sometimes the
nearest noun is the process itself.

The eight are those whose subject is an abstract process. A larger class phrases a requirement in
the **agentless passive** — 38 clauses of the form "X MUST be *verbed*" with no "by" — and most of
those are sound: "`INT96` MUST NOT be used" and "The `transpose` codec MUST NOT be used" state
properties of a packet, which §3.3 permits. Telling the two apart needs the definitions this part
adds, which is why §6 leaves that audit open rather than attempting it here.

## 3. Decision

### 3.1 The specification names four actors

`00` §2 gains four definitions, and every requirement in every part binds one of them:

- A **writer** produces a packet from sources. It stages, validates and commits, and it is the
  actor `05` binds throughout.
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
  writer performing it, which is what makes `05` §10 decidable: an obligation on a build or a
  writer is an importer obligation, and one on a packet is not.
- An **adapter** is the part of a writer that reads one source. An obligation on an adapter binds
  the writer that ships it.
- An **implementation** is software performing one or more of the four actors. It is the right
  subject only where a requirement binds every actor alike — `00` §2.7's ban on HDF5 object
  references is one.

### 3.3 A requirement binds an actor, or states a property of an artifact

Every MUST, MUST NOT, SHOULD, SHOULD NOT and MAY in this specification **MUST** do one of two
things, and a clause doing neither is a defect in this specification rather than a rule anything
can fail:

1. **Bind an actor** named in §3.1 or resolving to one by §3.2, which says who complies.
2. **State a property of an artifact** — a packet, a table, a column, a manifest entry — which is
   inspectable. "A packet carrying sorted units MUST carry `core.sorting_runs`" binds nobody and is
   sound, because the packet either carries them or does not.

This clause binds whoever writes this specification, and nothing else in it does. No validator
inspects the specification, so a clause failing it is corrected here rather than reported anywhere.

A requirement no tool can check is permitted under the first form and is not this defect: a
consumer **MUST NOT** infer attachment from a device's name (R67 §2.4) binds a named actor to a
determinable behaviour, and no tool can watch it.

### 3.4 Four spellings are retired

`importer` is another name for a writer, `client` and `binding` for a reader, and `caller` for a
consumer. An accepted revision using one binds the actor it names. This is a definition and carries
no modal, as `00` §2's definitions do not and as `00` §9's precedence rule does not:

| retired | reads as | mentions |
|---|---|---:|
| `importer` | writer | 7 |
| `client` | reader | 3 |
| `binding` | reader | 2 |
| `caller` | consumer | 1 |

R75 §2.1 and `05` §10 both bind an importer, and both continue to bind the writer without amendment.
`05` §10's two classes are renamed to say what they are properties of: **packet conformance** and
**writer conformance**.

### 3.5 Eight requirements gain an actor

Each clause in §2.3 names the actor that performs it: a **validator** for the two checks, the
re-run and the verification pass; a **writer** for the rewrite and for recording both version
strings verbatim; and a **build** for the source entry whose `owns` is silent, which is what
resolves a recipe's ownership.

## 4. What this does not change

- **No table, column, reference, rule or vocabulary changes, and no packet is rebuilt.** This part
  binds how the specification is written, so what changes is which clauses a reader can act on.
- **No obligation moves between packet conformance and writer conformance.** §3.2 makes the
  existing boundary decidable rather than redrawing it: every clause binding a build or a writer
  today was already an importer obligation under `05` §10, and every clause about a packet's
  contents was already the other.

## 5. Consequence

`00` §2 gains four definitions and three derived terms; `05` §10 renames one of its conformance
classes; eight clauses gain an actor. Thirteen mentions of a retired spelling are repointed.

The reference implementation changes nothing. `escapewheel-reader`, `-validator` and `-writer`
already divide along three of the four actors, and the fourth has no code because a consumer is
whoever calls them.

What this buys is that `05` §10 becomes a rule a validator can apply. It could not before: the
part it governs binds 8 clauses to a writer, 12 to a build and 3 to an importer, and a validator
deciding which of those are importer obligations was deciding it by name.

## 6. Open

- **Which of the 38 agentless passives elide an actor.** §2.3 measures the class and fixes none of
  it: "X MUST be *verbed*" with no "by" is sound where X is an artifact — "`INT96` MUST NOT be
  used" — and elides a nameable actor where it is not, as "A recipe MUST be checked against the
  registry before any source is opened" elides a build. The definitions §3.1 adds are what make
  that separable, and separating it is a reading of 38 clauses rather than a rule.

- **Whether the 146 sentences that already name an actor name the right one.** §2.2 measures that the
  read side splits cleanly by part, which is evidence the habit was sound rather than proof of it,
  and this part audits none of them. What it provides is the definitions that make such an audit
  mechanical: read the clause, ask whether the obligation is about what is returned or what is
  concluded, and repoint it where the answer disagrees with the noun. Doing that as a sweep would
  put every clause in this specification into one revision, which is not a change anyone could
  review.
