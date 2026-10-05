# An adapter finds its source by `root`, not by its working directory

| | |
|---|---|
| **Status** | **Ready** |
| **Opened** | 2026-10-05 |
| **Based on** | `7c78b05b239fa2d81a3d2a9ef9a899140cab5eaf` |
| **Change form** | structural |
| **Amends** | Part 09 §5.7; Part 12 §4 |
| **Depends on** | R109 §3.2 (the sentence this replaces); R115 §3.4 (a build runs a command from an argument list) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Problem

Part 09 §5.7 describes the command a recipe names as "an argument list carried as a list and run in
the source's own root, never a shell line (Part 05 §3.7)". Part 05 §3.7, which owns how a build
runs a command, says nothing of a working directory, and neither does any other part. The clause
therefore states a requirement that its owner does not, in a section that describes how an
extension reaches a build rather than how a build runs a process.

A build cannot meet the clause for every source. The recipe schema Part 05 §3.1 incorporates
describes a source's `root` as "a local directory, relative to the recipe, or a store URI", and a
process cannot run in `s3://bucket/prefix`. An
adapter does not need the clause either: Part 12 §4 already supplies `root` as "the source's
location as a URI, which the adapter opens for itself". The clause reads instead as a promise an
adapter may rely on, and the reference writer does not keep it, so an adapter written against
Part 09 alone fails when it opens a path relative to its working directory.

This change removes the clause and states the rule an adapter can rely on in Part 12 §4, which owns
what a build supplies an adapter.

The change is structural because it replaces a sentence inside Part 09 §5.7. Appending a section
would leave that sentence promising a working directory beside a rule that denies one.

### 1.1 Structural crosswalk

Both amended sections already carry canonical anchors, `ew-extension-delivery` and
`ew-build-supplied-values`, so no anchor bootstrap is needed.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 09 §5.7, first paragraph: where a raw source needs converting first, a recipe names a command, an argument list run in the source's own root and never a shell line | replace in place | same section | the command is an argument list and never a shell line, as before; no working directory is promised | §3.1 |
| Part 12 §4, the vocabulary of what a build supplies | extend in place with one closing paragraph | same section | an adapter opens its source at `root` and depends on no working directory | §3.2 |

## 2. Evidence

Section 2 is informative. Each observation was made at the recorded baseline.

### 2.1 The clause came from a converting command and outlived it

R109 §3.2 introduced the sentence for a command that converts a raw source before a build reads
it. R115 §3.4 made the recipe's command the one a build reaches a source through, and restated
Part 09 §5.7's clause without examining it. The recipe schema now carries one command member,
`source.delivery.command`, and a build supplies terms to every command it names (Part 05 §3.7,
Part 12 §4). So the clause describes the command every adapter is reached by, not only a
converter.

### 2.2 The reference writer runs every command in its own working directory

The writer launches an adapter's command at three call sites, one per protocol of the group
(`files-v0.1`, `stream-v0.1` and `flight-v0.1`), in
`escapewheel-writer/src/escapewheel_writer/reading.py`. None of the three passes a working
directory, so each command runs in whatever directory the build itself runs in. The writer's
contributing guide states the same: the command "does not run in `root`, so a script it names is an
absolute path". The docstring of the recipe's delivery member in
`escapewheel-writer/src/escapewheel_writer/recipe.py` repeats Part 09's clause, and is stale.

Since the writer has never set a working directory, every adapter it has run, including
`escapewheel-aind`'s and the writer's own sources reached by `escapewheel deliver`, already opens its
source at `root`.

### 2.3 Alternatives

Keeping the clause and having a build run a command in `root` where `root` is a local directory
would make the working directory depend on the root's scheme, so an adapter tested locally would
fail on its first store root. Having a build run every command in the recipe's directory would
promise a directory an adapter has no reason to use, since `root` and every location a build
supplies are already terms. Removing the clause without a replacement would leave Part 09's
reader nothing to correct the belief the clause created.

## 3. Decision

Section 3 is normative.

### 3.1 Part 09 §5.7 promises no working directory

The first paragraph of Part 09 §5.7 says that a recipe reaches a source through a command, an
argument list and never a shell line (Part 05 §3.7), so that an extension isolates its dependencies
however it likes and a build states no opinion about how. It says nothing of the directory the
command runs in.

### 3.2 An adapter opens its source at `root`

Part 12 §4 closes with this rule. The working directory in which a build runs an adapter's command
is unspecified. An adapter MUST open its source at the `root` a build supplies, and MUST NOT depend
on the directory it runs in, since a `root` that is a store URI names no directory to run in. No
checker verifies this.

## 4. Questions

None. The rule an adapter relies on follows from Part 12 §4's `root` term, and no answer to a
question would change it.

## 5. Consequence

No packet changes. A build that runs commands in `root` today remains conforming, since the
directory is unspecified; an adapter that depends on its working directory becomes
non-conforming, and none in this repository does (§2.2).

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | unchanged: Part 01 states nothing about a command | none |
| logical prose and registry | unchanged: no declaration names a command | none |
| physical profiles | unchanged: a working directory is not a storage fact | none |
| packet manifest and JSON Schemas | unchanged: the recipe schema's `command` describes an argument list and promises no directory | none |
| validation and import | Part 09 §5.7 and Part 12 §4 change as §3 states; Part 05 §3.7 is unchanged | the two sections' text |
| extensions | unchanged: an extension registry declares no command | none |
| reader, writer, validator, adapters | the writer's behavior is unchanged; the recipe delivery member's docstring stops saying the command runs in `root` | the docstring |
| conformance fixtures and tests | unchanged: a validator cannot observe an adapter's working directory, and §3.2 says no checker verifies it | none |
| revision process and tooling | ledger entries for §3.1 and §3.2, both `applied` | `revisions/applied.toml` |
| generated publications and developer documentation | the combined specification is regenerated; the writer's contributing guide already states the rule | the regenerated rendering |

### 5.1 What this does not change

Part 05 §3.7 still mentions a command that converts a raw source before it is read and is supplied
nothing. No recipe member carries such a command (§2.1), but where one exists it receives its input
through the argument list its recipe author writes, which this change leaves as it is.

## 6. Conformance and implementation evidence

A packet cannot show where its adapters ran, so no fixture distinguishes this rule from the current
one. The evidence is an implementation property: the writer's three launch sites pass no working
directory (§2.2), so every build that names a source outside the directory the build runs in
exercises an adapter that depends on none.
