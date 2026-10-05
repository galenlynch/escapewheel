# A source entry may name both a command and the writer's process

| | |
|---|---|
| **Status** | **Open** |
| **Opened** | 2026-10-05 |
| **Based on** | `44f6e459d86d4bad6a99b9cd7f083e8a8a785c78` |
| **Affects** | Part 05 §3.9 (whether a source runs in the writer's process); the recipe schema's `in_process` members |

## 1. Problem

A recipe reaches a source in one of two ways. A `[source.delivery]` table names the command a
build runs the adapter with, out of process (Part 05 §3.7), and `in_process` says the adapter runs
in the writer's own process (Part 05 §3.9). The recipe schema admits both members on one entry, and
`[packet].in_process` sets the second for every entry that does not set its own.

Part 05 §3.9 does not say what a build does with an entry carrying both. Its first rule lets a
recipe run in process an adapter that declares a protocol, and says nothing of a command the same
entry names. Its second has a build serve an adapter it ships, which declares no protocol, over a
protocol where the entry names a command, and says nothing of an `in_process = true` beside it.

The reference writer refuses such a recipe, citing Part 05 §3.9 for a rule the section does not
state. Another build could as reasonably run the command, or run the adapter in process and ignore
the command, so the same recipe builds three ways.

The boundary of this change is the conflict between the two routes. Which adapters may run in
process, and what an in-process adapter is supplied, are unchanged.

## 2. Evidence

Section 2 is informative. Each observation was made at the recorded baseline.

### 2.1 The specification admits both and settles neither

The recipe schema (`recipe/0.5.0`) declares a source entry's `in_process` as a boolean and its
`delivery` as a table with `command`, `protocol`, `declaration` and `report_path`, with no
constraint between them. `[packet].in_process` is described as "whether every source runs in the
writer's process unless its entry says otherwise". Neither Part 05 §3.1, which incorporates the
schema, nor §3.9, nor Part 12 states a rule for an entry carrying both. The schema does not say
whether an entry's `delivery` table is that entry "saying otherwise".

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

- **Refuse an entry naming both**, before any source is opened, naming the source. The recipe
  author wrote two routes and only they know which was meant; this is the reference writer's
  behavior, and it matches the recipe schema's refusing a misspelled block rather than dropping it.
- **Let the command win.** The `delivery` table is the more specific statement, but a build would
  then ignore an `in_process = true` the author wrote on the same entry.
- **Let `in_process` win.** A build would run in process an adapter whose recipe names how to run
  it elsewhere, and silently skip the command.
- **Leave it unspecified.** Keeps three conforming readings of one recipe.

## 3. Preferred direction

A build refuses, before any source is opened, a source entry that carries a `delivery` table and
sets `in_process = true`, naming the source. An entry's `delivery` table is that entry saying
otherwise to `[packet].in_process`, so a packet-level opt-in does not apply to a delivered entry and
is no conflict.

The second sentence differs from the reference writer, which refuses an inherited opt-in too. The
preference rests on what `[packet].in_process` is for: one statement about the set of adapters a
machine installs together, which a recipe mixing delivered and in-process sources would otherwise
have to contradict on every delivered entry.

## 4. Questions

1. Does a build refuse an entry naming both routes, or does one route win? The preferred direction
   is to refuse (§2.3).
2. Does `[packet].in_process` conflict with an entry's `delivery` table, or does the table count as
   the entry saying otherwise? The preferred direction is that it counts as saying otherwise, which
   requires the writer to stop refusing an inherited opt-in.

## 5. Consequence

No packet changes: the conflict is settled before a build opens anything.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | unchanged: Part 01 states nothing about how a source is reached | none |
| logical prose and registry | unchanged: no declaration names a route | none |
| physical profiles | unchanged: a route is not a storage fact | none |
| packet manifest and JSON Schemas | affected: the recipe schema's `[packet].in_process` description may say a delivered entry is excluded | the schema's description |
| validation and import | affected: Part 05 §3.9 states the refusal and how the packet-level opt-in applies | the section's text |
| extensions | unchanged: an extension registry names no route | none |
| reader, writer, validator, adapters | affected under question 2's preferred answer: the writer stops refusing an inherited `in_process` beside a `delivery` table, and cites the new rule | writer tests for an entry-level conflict and an inherited opt-in |
| conformance fixtures and tests | unchanged: a refused recipe produces no packet | none |
| revision process and tooling | a ledger entry per Decision clause | `revisions/applied.toml` |
| generated publications and developer documentation | the combined specification is regenerated; the writer's contributing guide is checked for the route rules | the regenerated rendering |
