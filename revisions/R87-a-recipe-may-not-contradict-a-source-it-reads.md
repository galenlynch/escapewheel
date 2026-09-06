# R87 — A Recipe May Not Contradict a Source It Reads

| | |
|---|---|
| **Status** | Proposed |
| **Amends** | `05` §3.1 (what a recipe declares), `05` §3.5 (checking a recipe), R63 §2.3 (what a check can say before any I/O) |
| **Depends on** | R63 (a recipe declares what it narrows), R86 (assigned identifiers do not cross packets) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

A **recipe** is the TOML document naming a packet's sources and the facts none of them supplies;
`05` §3.1 lists the last of these as *"session and subject facts no source carries"*, and `05` §3.2
records the recipe verbatim as the packet's provenance.

## 1. Motivation

### 1.1 A recipe declared the wrong animal and nothing noticed

The recipe for **`ecephys_776259`** declared `subject_id = "786867"` — the other session's mouse,
copied across when the second recipe was written from the first. Every packet built from it,
including those committed today, asserts that its **6,781 units** came from an animal that was
never in the rig.

The source disagreed the whole time. That session's `session.json` carries
`subject_id: 776259`, and the `session` adapter reads that file for its stream windows without
ever looking at the field.

### 1.2 The check `05` §3.5 describes stops at the recipe's own edge

R63 §2.3 gave a recipe a check that runs before any I/O, and `05` §3.5 requires it: a resource
owned twice, a resource no adapter produces, a dangling required key. Every one of those is a
statement the recipe makes about **itself**.

A declaration contradicting a source contradicts nothing internally, so it passes. R63 §1 made
exactly this argument about omission — *"an omission contradicts nothing, so a recipe naming four
of a source's five resources passes every test the tool applies"* — and the same gap admits a
declaration that is present and wrong.

### 1.3 A wrong subject unifies rather than collides

R86 §2.3 makes `core.subjects` one of the two tables that are **not** session-scoped, because
`core.sessions` references it rather than the reverse. So a subject is the identifier meant to be
the same thing across packets — and a wrong one does not collide with the true value, it agrees
with a different animal's.

Read together, two packets of what should be two mice now claim to be two sessions of one. That is
the failure R86 exists to prevent, arriving through the one door R86 does not watch.

## 2. Decision

### 2.1 A declared fact a source also states MUST agree with it

Where a recipe declares a fact and a source the same recipe reads states that fact, the two
**MUST** agree, and a build **MUST** refuse where they differ. The refusal names the field, the
declared value, the source's value and the file it came from.

This is R63 §2's rule with its scope corrected. A recipe that contradicts itself is refused rather
than built, because the alternative is a defect surfacing ninety seconds into a build as something
else's rule failure; a recipe that contradicts its sources is the same defect, and it does not
surface at all.

### 2.2 `subject_id` is the first such fact

A recipe's `[subject].subject_id` **MUST** equal the subject the session source states, where it
states one. The `session` adapter exposes it for comparison.

No other field is required to be checked by this revision. `05` §3.1 says the recipe is for facts
**no source carries**, so a field that a source does carry is by that definition one the recipe
should not be inventing — but which fields those are is per-adapter knowledge, and enumerating
them ahead of a case is the speculative generality R66 §1.4 refuses.

### 2.3 A source that states nothing is not a contradiction

Where a source carries no value for a declared fact, the declaration stands unchallenged and the
build proceeds. Silence is not disagreement, which is R83 §2.3's distinction between a fact about
what the source holds and a defect in the packet.

A writer **MUST NOT** report a missing source value as a mismatch, and **SHOULD** note that the
declaration went unchecked, so a reader of the build log can tell a verified fact from an
unverified one.

### 2.4 The check runs where the source is opened

R63 §2.3's check runs before any I/O and cannot do this one, which needs the source read. The
comparison therefore happens as each source is built, and **MUST** refuse before any resource is
staged — early enough that a contradicted recipe costs nothing but the source's own open.

## 3. What this does not change

- **No table, column or rule.** The comparison is a writer check, not a Tier 1 or Tier 2 rule:
  the packet it would have produced never exists, so there is nothing for SQL to see.
- **`05` §3.1's list is unchanged.** A recipe still declares what no source carries; this says
  what happens when it declares something a source does carry after all.
- **No packet becomes invalid.** A committed packet is unaffected — except that
  `ecephys_776259`'s is wrong for the reason in §1.1 and must be rebuilt, which R61 §5 makes a
  rebuild that re-reads no external resource.
- **R63's pre-I/O check keeps its scope.** It still refuses what it can see without opening
  anything, and §2.4 adds a second point rather than moving the first.

## 4. Consequence

One comparison, one adapter property, one refusal path. The `session` adapter gains
`subject_id`, read from the `session.json` it already parses.

`ecephys_776259` must be rebuilt: its recipe is corrected and its packet still names the wrong
subject. Nothing else in that packet changes, since `subject_id` reaches no other table's key —
`core.sessions.subject_id` references it and holds the same wrong number.

## 5. Open

- **Which other declared facts a source states.** `[session].session_start_time` is already
  compared against the earliest declared stream window and reported as a note rather than refused,
  which is the softer treatment of the same shape. Whether that should harden, and which of
  `date_of_birth`, `sex` and `genotype` a source carries, wants a case rather than an enumeration.
- **Whether a note is enough for an unchecked declaration.** §2.3 asks for a note where no source
  states the fact. A packet that recorded which declarations were verified would let a consumer
  tell a checked subject from an asserted one, and that is a manifest field rather than a note —
  more than this revision needs.
- **Whether the wrong subject should have been caught downstream.** `core.subjects.subject_name`
  read `786867` in a packet whose sessions are named `ecephys_776259_2025-04-09`, and no rule
  compares a subject's name with the session names that reference it. A Tier 2 rule could, and it
  would be a rule about a naming convention this specification does not define.
