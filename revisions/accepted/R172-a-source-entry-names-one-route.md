# A source entry names one route to its source

| | |
|---|---|
| **Status** | **Accepted** 2026-10-05 |
| **Opened** | 2026-10-05 |
| **Based on** | `e881d86ef231c0081087c8cab8ebae5a6f82153b` |
| **Change form** | ordinary |
| **Amends** | Part 05 §3, by a new subsection at its end |
| **Depends on** | R115 §3.5 (a recipe opts a source into the writer's process); R133 §3.4 (the recipe's `in_process` and `delivery` members) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Problem

A recipe reaches a source in one of two ways. A `[source.delivery]` table names the command a
build runs the adapter with, out of process (Part 05 §3.7), and `in_process` says the adapter runs
in the writer's own process (Part 05 §3.9). The recipe schema admits both members on one entry, and
`[packet].in_process` sets the second for every entry "unless its entry says otherwise".

Part 05 §3.9 does not say what a build does with an entry carrying both. Its first rule lets a
recipe run in process an adapter that declares a protocol, and says nothing of a command the same
entry names. Its second has a build serve an adapter it ships, which declares no protocol, over a
protocol where the entry names a command, and says nothing of an `in_process = true` beside it. Nor
does any section say whether an entry's `delivery` table is that entry saying otherwise to
`[packet].in_process`.

The reference writer refuses an entry carrying both, citing Part 05 §3.9 for a rule the section
does not state, and refuses it too where the entry inherits `in_process` from `[packet]`. Another
build could as reasonably run the command, or run the adapter in process and skip the command, so
one recipe builds three ways.

This change states both rules in a new section closing Part 05 §3. Which adapters may run in
process, and what an in-process adapter is supplied, are unchanged.

## 2. Evidence

Section 2 is informative. Each observation was made at the recorded baseline.

### 2.1 The specification admits both and settles neither

The recipe schema (`recipe/0.5.0`) declares a source entry's `in_process` as a boolean and its
`delivery` as a table with `command`, `protocol`, `declaration` and `report_path`, with no
constraint between them. It describes `[packet].in_process` as "whether every source runs in the
writer's process unless its entry says otherwise (Part 05 §3.9)". Part 05 §3.9 never mentions
`[packet].in_process`, and neither it, Part 05 §3.1, which incorporates the schema, nor Part 12
states a rule for an entry carrying both members.

### 2.2 The reference writer refuses both, including an inherited `in_process`

`escapewheel-writer/src/escapewheel_writer/recipe_check.py` reports `RecipeFault.TWO_ROUTES` for
any entry with a `delivery` table whose `in_process` resolves true: "a source is reached one way or
the other (Part 05 §3.9)". The test `test_a_source_is_reached_one_way_or_the_other` in
`escapewheel-writer/tests/test_recipe_check.py` holds it for an entry setting `in_process = true`.

The writer resolves an entry's `in_process` from `[packet].in_process` where the entry sets none
(`escapewheel-writer/src/escapewheel_writer/recipe.py`), so a recipe with `[packet] in_process =
true` and one delivered source is refused unless that entry also sets `in_process = false`. No test
covers that case.

### 2.3 Alternatives

- **Let the command win over an entry's `in_process = true`.** The `delivery` table is the more
  specific statement, but a build would ignore an opt-in the author wrote on the same entry.
- **Let `in_process` win.** A build would run in process an adapter whose recipe names how to run
  it elsewhere, and skip the command without saying so.
- **Leave it unspecified.** Keeps three conforming readings of one recipe.
- **Have `[packet].in_process` conflict with a delivered entry, as the writer does.** The
  packet-level member is one statement about the set of adapters a machine installs together, and a
  recipe mixing delivered and in-process sources would have to contradict it on every delivered
  entry.

## 3. Decision

Section 3 is normative. Part 05 §3 gains a subsection at its end, "A source entry names one
route", stating the rules below.

### 3.1 A build refuses an entry naming both routes

A build MUST refuse a recipe in which a source entry carries a `delivery` table and sets
`in_process` to true, naming the source, before any source is opened. The entry states two routes
to one source and only its author knows which was meant, so a build choosing one would build
something the recipe did not say.

### 3.2 An entry's `delivery` table overrides `[packet].in_process`

`[packet].in_process` applies to each source entry that sets no `in_process` and carries no
`delivery` table; an entry's `delivery` table is that entry saying otherwise. A build MUST NOT
refuse a recipe for a `[packet].in_process` beside an entry carrying a `delivery` table.

## 4. Questions

1. Does a build refuse an entry naming both routes, or does one route win?

   **Answered 2026-10-05:** a build refuses it (§3.1).

2. Does `[packet].in_process` conflict with an entry's `delivery` table, or does the table count as
   the entry saying otherwise?

   **Answered 2026-10-05:** the table counts as the entry saying otherwise, so a packet-level
   opt-in does not conflict with a delivered entry (§3.2).

## 5. Consequence

No packet changes: both rules are settled before a build opens anything. A recipe the reference
writer refuses today for an inherited opt-in becomes buildable, and its delivered sources run out of
process. A recipe setting `in_process = true` beside a `delivery` table stays refused.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | unchanged: Part 01 states nothing about how a source is reached | none |
| logical prose and registry | unchanged: no declaration names a route | none |
| physical profiles | unchanged: a route is not a storage fact | none |
| packet manifest and JSON Schemas | unchanged: the recipe schema's description of `[packet].in_process` already defers to an entry saying otherwise, and cites Part 05 §3.9, which stays where the opt-in is stated | none |
| validation and import | Part 05 §3 gains the subsection §3 states | the subsection's text |
| extensions | unchanged: an extension registry names no route | none |
| reader, writer, validator, adapters | the writer stops copying `[packet].in_process` onto an entry carrying a `delivery` table, and its two-routes refusal cites the new subsection | the existing two-routes test, citing the new subsection, and a new writer test that a delivered entry under `[packet] in_process = true` is reached through its command |
| conformance fixtures and tests | unchanged: a refused recipe produces no packet, and a packet does not record how a source was reached | none |
| revision process and tooling | ledger entries for §3.1 and §3.2, both `applied` | `revisions/applied.toml` |
| generated publications and developer documentation | the combined specification is regenerated, and `headings.toml` records the new section | the regenerated rendering |

## 6. Conformance and implementation evidence

A packet does not record whether its sources ran in or out of process, and a refused recipe writes
no packet, so no fixture distinguishes these rules from the current ones. The evidence is in the
writer's recipe check: the existing test for an entry naming both routes, and a new test that a
recipe with `[packet] in_process = true` and a delivered source passes the check and resolves that
source to its command.
