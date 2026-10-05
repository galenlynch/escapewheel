# A build supplies its source to every command it runs

| | |
|---|---|
| **Status** | **Accepted** 2026-10-05 |
| **Opened** | 2026-10-05 |
| **Based on** | `44f6e459d86d4bad6a99b9cd7f083e8a8a785c78` |
| **Change form** | structural |
| **Amends** | Part 05 §3.7 |
| **Depends on** | R116 §3.2 (the sentence this removes); R170 §3.1 (removes the converting command that sentence cites) |
| **Profile** | all |
| **Decision clauses** | §3.1 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Problem

Part 05 §3.7 owns how a build runs a command a recipe names. Its third paragraph distinguishes two
kinds of command: "Where the command is one a build reaches a source through, the build supplies
that source on its standard input as Part 12 §4 requires", and "A command that converts a raw
source before it is read is not one of these and is supplied nothing."

A recipe cannot name the second kind. The recipe schema Part 05 §3.1 incorporates carries one
command, `source.delivery.command`, described as "the argument list that runs the adapter", and a
build reaches the source through every command it runs. So the paragraph's condition is always
met, and its last sentence describes a command that no recipe can express.

The sentence cited Part 09 §5.7 for its converting command, and R170 §3.1 removed that framing
from Part 09, so the sentence names a kind of command that no other section describes either.

This change removes the condition and the sentence, so the paragraph binds every command a build
runs for a source. It binds the commands a build runs rather than those a recipe names, because
Part 05 §3.9 lets a recipe run in the writer's process a source whose entry may also name a
command, and a build runs no command for such a source. It is structural because it rewrites sentences inside Part 05 §3.7; appending a section
would leave the paragraph describing a second kind of command beside a rule that there is one.

### 1.1 Structural crosswalk

Part 05 §3.7 already carries the canonical anchor `ew-source-command`, so no anchor bootstrap is
needed.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 05 §3.7, third paragraph: where the command is one a build reaches a source through, the build supplies it; a command converting a raw source is supplied nothing | replace in place | same section | every command a build runs for a source is supplied that source; no command is supplied nothing | §3.1 |

## 2. Evidence

Section 2 is informative. Each observation was made at the recorded baseline.

### 2.1 The sentence came from a converting command no recipe carries

R109 §3.2 introduced a recipe command for a raw source that needs converting, run before a build
reads it. R115 §3.3 made the recipe's command the one a build reaches a source through. R116 §3.2
then bound the standard-input obligation to that command "and no other", excluding the converting
command by citing Part 09 §5.7.

No revision added a recipe member for a converting command. The recipe schema at the baseline
(`recipe/0.5.0`) gives a source entry the members `kind`, `root`, `owns`, `contributes`,
`storage_options`, `in_process` and `delivery`, and `delivery` carries `command`, `protocol`,
`declaration` and `report_path`. Every other key in a source entry is an option checked against
its adapter's `needs` and `accepts`, so an option cannot name a command a build runs.

### 2.2 The reference writer runs one kind of command

The writer reads a source entry's members from the same closed set, and launches a command only
from `source.delivery.command`, at the three call sites in
`escapewheel-writer/src/escapewheel_writer/reading.py` that supply the source over `files-v0.1`,
`stream-v0.1` and `flight-v0.1`. It has no path for a command run before a source is read.

### 2.3 Alternatives

Adding a recipe member for a converting command would give the sentence something to describe,
but no adapter in this repository needs one, and a conversion has two places to run without it:
inside the adapter's own command, or outside the build, with the adapter reading what it wrote.
Keeping the sentence would leave Part 05 describing a command no recipe can name.

## 3. Decision

Section 3 is normative.

### 3.1 Part 05 §3.7 supplies a source to every command a build runs for it

The third paragraph of Part 05 §3.7 says that a build supplies a source on the standard input of
every command it runs for that source, as Part 12 §4 requires, without waiting for the command to exit, and
MUST read what the command produces while it writes. It describes no command that is supplied
nothing. The paragraph keeps its reason: a pipe holds tens of kilobytes and a supplied object may
be far larger, so a build that wrote one whole before reading rows would wait on an adapter that
was waiting on it.

## 4. Questions

None. The recipe schema carries one command member, so the rule follows from it, and adding a
member is the alternative §2.3 rejects.

## 5. Consequence

No packet changes, and no build or adapter changes behavior: every command a build runs is already
supplied its source (§2.2). R116 §3.2's ledger entry stays `applied`, since the rule that a build
writes without waiting for the command remains in Part 05 §3.7 and only the exclusion is removed.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | unchanged: Part 01 states nothing about a command | none |
| logical prose and registry | unchanged: no declaration names a command | none |
| physical profiles | unchanged: a command is not a storage fact | none |
| packet manifest and JSON Schemas | unchanged: the recipe schema already carries one command member | none |
| validation and import | Part 05 §3.7's third paragraph changes as §3.1 states | the section's text |
| extensions | unchanged: an extension registry declares no command | none |
| reader, writer, validator, adapters | unchanged: the writer runs only `source.delivery.command` | none |
| conformance fixtures and tests | unchanged: a packet records no command | none |
| revision process and tooling | a ledger entry for §3.1, `applied` | `revisions/applied.toml` |
| generated publications and developer documentation | the combined specification is regenerated | the regenerated rendering |

## 6. Conformance and implementation evidence

A packet cannot show which commands its build ran, so no fixture distinguishes this rule from the
current one. The evidence is the recipe schema's closed set of source members (§2.1) and the
writer's single launch path (§2.2).
