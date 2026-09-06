# R77 — Two Permissions Become Obligations

| | |
|---|---|
| **Status** | **Accepted** 2026-09-04 |
| **Amends** | R29 §2 (`since` is a MAY on a table and a column), R56 §2.1 and §2.2 (`unit` and `clock_from` are MAYs) |
| **Depends on** | R29 (schema provenance), R48 (a column declares its role), R56 (a column declares its context) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

The v0.2 compilation strengthened two clauses that their revisions had left permissive, and
recorded nothing. Both strengthenings are right and are adopted here. What was wrong is that a
compiler decided them, which is the drift the clause ledger was built to surface and did.

### 1.1 `clock_from`: the MUST is already met, and the condition is why

R56 §2.2 makes `clock_from` a MAY, and R56 §4 records that as an uncomfortable choice:

> a MUST would need a list. Left as MAY, which risks it going unwritten

The compilation wrote the MUST anyway, scoped — *a `coordinate` column MUST declare `clock_from`
where the clock is not that row's `clock_id`*. That condition **is** the list R56 could not write,
expressed as a rule rather than an enumeration, and it partitions the registry exhaustively:

| coordinate columns | 20 |
|---|---|
| declare `clock_from` | 6 |
| resolve to their own row's `clock_id` | 14 |
| **neither** | **0** |

So the obligation costs nothing to adopt and closes the risk R56 §4 named. A coordinate that
declares no clock and sits on a table with no `clock_id` would be a tick on an undetermined
clock — R56 §1's whole subject — and there is now a rule that says so instead of a hope.

### 1.2 `unit`: a SHOULD is what the practice already is

R56 §2.1 makes `unit` a MAY. Every column in the registry that carries a physical quantity
declares one, and R56 §1 cites the counter-example it was written against: a live pipeline where
**every** unit lived inside a `Field(description=...)` — centimeter, second, percentage, milliliter
— because there was nowhere else to put them. A MAY permits exactly that regression.

### 1.3 `since`: the compilation dropped half the clause

R29 §2 says *"a table entry and a column entry MAY each carry a `since` field"*. The compiled spec
says a **column** SHOULD carry one, and does not mention tables.

The registry stamps both: 15 tables and 172 columns carry `since` today. The compilation described
less than exists, so a reader would not know that `core.intervals` records the revision that
created it.

## 2. Decision

### 2.1 A coordinate declares its clock where it is not the row's own

A column whose R48 role is `coordinate` **MUST** declare `clock_from` where the clock its ticks are
on is not the one that row's `clock_id` names. Where the table has no `clock_id`, the coordinate
**MUST** declare `clock_from`.

A consumer resolves it rather than guessing, because converting on the wrong clock produces a
number that is wrong and looks right.

### 2.2 A quantity declares its unit

A `data` column carrying a physical quantity **SHOULD** declare `unit`, or `unit_from` naming the
column that carries it (R56 §2.1's two forms, unchanged).

SHOULD rather than MUST: whether a column carries a *physical quantity* is a judgement the schema
cannot make. `n_spikes` is a count and `status` is a word, and a MUST would need the list R56 §4
declined to write — which §2.1 avoids only because `coordinate` is a declared role and "physical
quantity" is not.

### 2.3 A table or a column declares what introduced it

A table entry and a column entry **SHOULD** each carry `since`, naming the revision that introduced
or last changed it (R29 §2, with MAY raised and the table half restored).

## 3. What this does not change

- **No column, no table, no rule, no type.** Three obligations, on declarations that already exist.
- **No registry change.** Measured above: every coordinate already satisfies §2.1, and `since` is
  already on 15 tables and 172 columns. Adopting these makes the specification describe the
  registry rather than requiring anything new of it.
- **No change to R56's mechanism.** `unit`, `unit_from` and `clock_from` resolve exactly as R56
  §2.3 says, one hop, no search.
- **No change to what a validator does.** `registry/check.py` already decides all three
  structurally, with no packet in hand.

## 4. Open

- **Whether "physical quantity" can be declared rather than judged.** §2.2 is a SHOULD only because
  the schema cannot tell a quantity from a count. A role or a flag would make it a MUST; R48's
  vocabulary is closed and adding to it is a revision, so this waits for a case where the SHOULD
  is actually ignored.
