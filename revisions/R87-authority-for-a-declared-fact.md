# R87 — Authority for a Declared Fact

| | |
|---|---|
| **Status** | Proposed |
| **Amends** | `05` §3.1 (what a recipe declares), `05` §3.5 (checking a recipe) |
| **Depends on** | R63 (default ownership when a recipe omits `owns`), R86 (a reader presents many packets as one relation) |
| **Profile** | `escapewheel-portable-v0.1` |

Informative, except §2, which is normative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

A **recipe** is the TOML document naming a packet's sources and the facts none of them supplies.
`05` §3.1 lists the last of those as *"session and subject facts no source carries"*, and `05` §3.2
records the recipe verbatim as the packet's provenance. Where a source carries such a fact after
all, nothing says which of the two declarations wins.

## 1. Motivation

### 1.1 A recipe declared the wrong animal and nothing noticed

The recipe for **`ecephys_776259`** declared `subject_id = "786867"` — the other session's mouse,
copied across when the second recipe was written from the first. The committed packet still
carries it: `core.subjects.subject_name` reads `786867` in a packet whose one session is named
`ecephys_776259_2025-04-09`, asserting that its **6,781 units** came from an animal that was never
in the rig.

The source disagreed the whole time. That session's `session.json` carries
`subject_id: 776259`, and the `session` adapter reads that file for its stream windows without
ever looking at the field.

### 1.2 One question, three answers

`05` §3.5's check sees a resource owned twice, a resource no adapter produces, a dangling required
key, a broken clock declaration, an unset required option, and the unclaimed resource R63 §2.3
added. Every one of those is a statement the recipe makes about **itself**, so a declaration
contradicting a source passes: it contradicts nothing internally. R63 §1.1 made the same argument
about omission — *"a recipe naming four of a source's five resources passes every test the tool
applies and the fifth resource is absent from the packet"*.

What the writer does instead is decide the question three ways, in thirty lines and by no stated
rule:

| the fact | what happens when the two differ | |
|---|---|---|
| `subject_id` | the build is refused | `session.py:322` |
| `session_start_time`, `session_end_time` | the source's value is used and the recipe's is noted | `session.py:332-338` |
| every other `[session]` and `[subject]` field | the recipe wins outright | `recipe.py:41`, `RECIPE_SUPPLIES` |

### 1.3 A recipe corrects a source that is wrong

The third policy exists because sources are wrong. `session.json` for `ecephys_776259` stamps a
Pacific wall-clock reading as UTC — **seven hours** out — and the recipe carries a comment saying
it localizes the value because no adapter gets to correct it.

An adapter does correct it, by a route the recipe does not know about: `core.sessions.session_start_time`
in the committed packet is `2025-04-10T00:25:12Z`, taken from the earliest declared stream window
rather than from either the recipe or `session.json`'s own field. The recipe's transcription of
that window is discarded, which is visible only at the other end, where the packet holds
`02:38:44.147959` against the recipe's rounded `02:38:44`.

So a recipe overriding a wrong source is the ordinary case rather than a defect, and a rule that a
recipe must agree with its sources would refuse a correct build.

### 1.4 A wrong subject unifies rather than collides

R86 §2.1 makes `core.subjects` one of the two tables that are **not** session-scoped, because
`core.sessions` references it rather than the reverse. So a subject is the identifier meant to be
the same thing across packets, and a wrong one agrees with a different animal's rather than
colliding with the true value.

Read together, two packets of what should be two mice claim to be two sessions of one. That is the
failure R86 exists to prevent, arriving through the one door R86 does not watch.

## 2. Decision

### 2.1 A declared fact a source also states MUST agree with it

Where a recipe declares a fact and a source the same recipe reads states that fact, the two
**MUST** agree, and a build **MUST** refuse where they differ unless §2.4 declares an override.
The refusal names the field, the declared value, the source's value and the file it came from.

This extends `05` §3.5's refusal to a contradiction the recipe cannot show on its own. R63 §1.2
measured what the alternative costs: a defect surfacing ninety seconds into a build as another
table's rule failure. A recipe that contradicts its sources is the same defect, and it never
surfaces at all.

### 2.2 `subject_id` is the first compared fact

A recipe's `[subject].subject_id` **MUST** equal the subject the session source states, where it
states one. The `session` adapter exposes it for comparison.

No other field is required to be compared by this revision. `05` §3.1 says the recipe is for facts
**no source carries**, so a field a source does carry is one the recipe should not be inventing —
but which fields those are is per-adapter knowledge, and enumerating them ahead of a case is the
speculative generality R66 §1.4 refuses.

### 2.3 A source that states nothing is not a contradiction

Where a source carries no value for a declared fact, the declaration stands unchallenged and the
build proceeds. Silence is not disagreement, which is R83 §2.3's distinction between a fact about
what the source holds and a defect in the packet.

A writer **MUST NOT** report a missing source value as a mismatch, and **SHOULD** note that the
declaration went unchecked, so a reader of the build log can tell a verified fact from an
unverified one.

### 2.4 An override declares that the recipe is authoritative, and why

A recipe **MAY** declare that its own value for a fact supersedes the source's, by naming the
field in an `overrides` table beside the block that declares it:

```toml
[session]
session_start_time = "2025-04-10T00:25:12Z"

[session.overrides]
session_start_time = "session.json stamps a Pacific wall-clock reading as UTC; seven hours out"
```

The value **MUST** be a non-empty reason. A boolean would let a contradiction be silenced without
saying why, which is R63 §2.2's silent winner one level up, and the reason is the whole of what a
later reader has to judge the override by.

A build **MUST** refuse an override for a field whose declared value the source agrees with, and
for a field no source states. A stale override is the failure `registry/check.py` guards against
by checking that each declared exception is still needed, and an override that has quietly stopped
applying is an assertion nobody re-examined.

An override is not a licence to invent. It says a source is wrong about a fact the recipe knows
better, and §1.3 is the case it exists for: an upstream defect that will not be fixed in the file
this build reads.

### 2.5 The comparison runs where the source is opened

`05` §3.5's check runs before any I/O and cannot do this one, which needs the source read. The
comparison therefore happens as each source is built, and **MUST** refuse before any resource is
staged — early enough that a contradicted recipe costs nothing but the source's own open.

A source's statement of a fact is whatever its adapter exposes for that fact. Which of several
values inside a file the adapter stands behind is the adapter's judgement and not the recipe's:
§1.3's session states its start twice, once wrongly in its own field and once correctly across its
stream windows.

### 2.6 A fact the source derives is the source's

`core.sessions.session_start_time` and `session_end_time` come from the session source's declared
stream windows. A writer **MUST** use the source's value where a session source is present, and
**MUST** report a declaration it did not use rather than discarding it silently.

This states what `session.py:332-338` already does. It is not §2.1's rule, because the recipe's
declaration here is a transcription of the source's own derivation rather than a competing claim,
and it is not §2.4's override, because nothing is being corrected.

## 3. What this does not change

- **No table, column or rule.** The comparison is a writer check rather than a Tier 1 or Tier 2
  rule: the packet it would have refused never exists, so there is nothing for SQL to see.
- **`05` §3.1's list is unchanged.** A recipe still declares what no source carries; this says what
  happens when it declares something a source carries after all.
- **No new key in the run's parameters.** An override travels inside the recipe, which `05` §3.2
  already records there. It is not one of R92's keys, because no consumer needs it to read the
  value — the packet's value *is* the value, and the override says only where it came from.
- **No packet becomes invalid.** A committed packet is unaffected — except that
  `ecephys_776259`'s is wrong for the reason in §1.1 and must be rebuilt, which R61 §5 makes a
  rebuild that re-reads no external resource.
- **R63's pre-I/O check keeps its scope.** It still refuses what it can see without opening
  anything, and §2.5 adds a second point rather than moving the first.

## 4. Consequence

§2.1 to §2.3 and §2.5 are implemented: `session.py:311-328` compares, refuses with a
`SourceDefect` naming the field, both values and the file, and notes an unchecked declaration, and
`AindSessionSource.subject_id` exposes the source's value. §2.6 is implemented at
`session.py:332-338`.

§2.4 is the new work: an `overrides` table per declaring block, its reason carried through, and
two refusals — an override with an empty reason, and an override the source does not contradict.

`ecephys_776259` must be rebuilt: its recipe is corrected and its packet still names the wrong
subject. Nothing else in that packet changes, since `subject_id` reaches no other table's key —
`core.sessions.subject_id` references it and holds the same wrong number.

## 5. Open

- **Whether §2.6's note should become an override.** A recipe declaring a start time the source
  derives is transcribing, and a transcription that has gone stale is reported and ignored. Making
  it an override instead would put a reason beside it and refuse the stale case, at the cost of
  requiring one for every recipe that carries the field for readability.
- **Which other declared facts a source states.** Whether `date_of_birth`, `sex` and `genotype`
  are carried by a source wants a case rather than an enumeration, and §2.4 is what makes adding
  one cheap: a field that turns out to be compared can be overridden where the source is wrong.
- **Whether the wrong subject should have been caught downstream.** `core.subjects.subject_name`
  reads `786867` in a packet whose session is named `ecephys_776259_2025-04-09`, and no rule
  compares a subject's name with the session names that reference it. A Tier 2 rule could, and it
  would be a rule about a naming convention this specification does not define.
