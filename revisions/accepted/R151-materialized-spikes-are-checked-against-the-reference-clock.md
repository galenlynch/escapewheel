# Materialized spikes are checked against the reference clock

| | |
|---|---|
| **Status** | **Accepted** 2026-09-30 |
| **Based on** | `884ab72b6500805cc456f2ab755806ca993bb72f` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 02 §9.2; Part 08 §§2 and 3; the core registry |
| **Depends on** | R145 §3.7 (the statement the rule checks); R150 §3.10 (the core registry version this advances from) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2 |

Section 3 is normative. Sections 1, 2, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

`analysis.spike_events` holds core's spikes mapped onto one clock and bucketed by time. Part 06 §4,
which R145 §3.7 made normative, fixes that clock: "Its `clock_id` is the session's reference clock,
so the table holds no rows for a session declaring no reference clock." R145 §7 deferred whether a
Tier 2 rule checks it, noting that R145 §3.7 states the fact either way and that the reference writer
satisfies it. No rule has been declared since, so a validator passes a table whose spikes are on a
probe's clock.

This revision declares that rule in the core registry and advances the core registry's version. The
change is structural because it revises Part 02 §9.2's statement of that version in place.

### 1.1 Structural crosswalk

Every affected section carries a canonical anchor, so no bootstrap is needed. No section moves,
splits, merges or retires.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| core registry, the rules of `analysis.spike_events` | extend | same declaration | a row off its session's reference clock is reported | §3.1 |
| Part 02 §9.2, the core registry version | revise in place | same section | the version advances to 0.13.0 | §3.2 |
| Part 08 §§2 and 3, the generated layout and manifest excerpt | regenerate the informative example | same sections | none | none |

## 2. Background

Section 2 is informative. The measurements use the two session packets the reference writer built
under this baseline's registry, the `packet-r150` builds: `ecephys_786867`, whose
`analysis.spike_events` holds 131,396,535 rows in 1,009 row groups, and `ecephys_776259`, with
286,896,563 rows in 2,197. Queries ran in DuckDB 1.5.5 over their Parquet tables, with 4 threads and
an 8 GB memory limit; each timing is the median of 5 runs.

### 2.1 The declaration checks that a clock exists, not which clock

Three checks touch `analysis.spike_events.clock_id`, and none compares it with the session's
`reference_clock_id`:

- the foreign key to `core.clocks` confirms that the packet declares the clock;
- `determined_by: [session_id]` (Part 02 §8.5) declares that a session's rows share one clock, which
  Part 03 §5.3 has the stored-order scan verify; and
- the two declared rules compare each spike with its bucket, within one clock.

The valid corpus packet declares two clocks, with `imec_ap_s001` as its reference. A copy carrying
the 42 spikes of its `core.spike_events` as an `analysis.spike_events` table passes the reference
validator at the baseline, both with every row on the reference clock and with every row on
`behavior_s001`. With §3.1's rule installed in the copy's bound core registry, the first still
passes and the second draws one finding row, naming the session, the clock the spikes are on and
the reference clock.

### 2.2 The rule is cheap on the largest table

§3.1's rule returns no rows on either session packet, in 0.27 s over 131 M rows and 0.60 s over
287 M. The whole-packet validation that committed those builds took 5.1 s and 8.9 s. The rule
returns none on the amended `ecephys_786867` build either, in 0.55 s over its 262,793,070 rows, and
none of the 102 corpus packets carries the table. Moving one spike of each packet to another clock
makes the rule return that one (session, clock, reference) row, in 1.1 s and 2.4 s.

Every row group of both tables records `clock_id` statistics with minimum and maximum equal to the
session's reference clock, so a check reading only Parquet metadata would settle both packets.
A check reading Parquet statistics is physical, and Part 02 §10.3 leaves it to the Part 05 §5.3
shim. Querying the column costs under a second, so the rule is declared SQL instead.

The reference validator's static check accepts the rule under `escapewheel-rule-sql-v0.2`. The
parsed base-resource set is `analysis.spike_events` and `core.sessions`, and that set is the rule's
Part 05 §15.4 input set.

### 2.3 Alternatives

| alternative | why it falls short |
|---|---|
| keep Part 06 §4 unchecked | a writer mapping spikes onto a probe clock, or onto the wrong session's reference, publishes a table that validates, and a consumer windowing it across probes compares ticks of different clocks |
| declare the rule `advisory` | Part 02 §10.2 forbids an advisory rule at `error`, and a violation of Part 06 §4 is a defect of the table rather than a question of style |
| report only rows whose session declares a reference clock | Part 06 §4 has a session with no reference clock hold no rows, so a row there is off the reference clock by the same statement; `IS DISTINCT FROM` reports both in one predicate |
| return every offending spike | a table mapped onto the wrong clock returns every row of the session, 287 M on the second packet, where one row per session and clock names the defect |

## 3. Decision

Two subsections declare the rule and advance the version the rule changes. The crosswalk in §1.1
places each.

### 3.1 A spike off its session's reference clock is reported

The incorporated core registry MUST declare this rule on `analysis.spike_events`, at level `error`
and not advisory. It reports each session and clock whose materialized spikes are on a clock other
than the session's `reference_clock_id`, including every row of a session that declares no
reference clock (Part 06 §4). A finding row names the session, the clock its spikes are on, and the
session's reference clock, which is null where the session declares none.

| id | message |
|---|---|
| `analysis.spike_events.on_reference_clock` | `spikes are on a clock other than their session's reference clock, or their session declares none` |

```sql
SELECT DISTINCT e.session_id, e.clock_id, s.reference_clock_id
FROM analysis.spike_events AS e
JOIN core.sessions AS s ON s.session_id = e.session_id
WHERE e.clock_id IS DISTINCT FROM s.reference_clock_id
```

### 3.2 The core registry version advances

The core registry's `registry_version` MUST advance from `0.12.0`, which R150 assigns, to `0.13.0`.
The registry meta-schema, the registry-contract descriptor and the rule language are unchanged.

## 5. Consequence

Neither session packet nor any corpus packet changes verdict. Every packet binds core registry
0.13.0 once rebuilt, and nothing needs rebuilding sooner, since each packet validates against the
registry it binds. A validator running the rule on a packet it could not check before reports a
table that Part 06 §4 already made nonconforming, so the verdict changes only for such a packet.

R145 §3.7's ledger entry gains a note that §3.1 declares the rule R145 §7 deferred.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. Part 01 §3.3 already states when a session declares its reference clock. | None required. |
| logical prose and registry | The core registry source declares §3.1's rule and §3.2's version, and Part 02 §9.2 states the version. Part 06 §4, which states the fact the rule checks, is unchanged. | `evidence/R<N>.json` names the registry pointer and the anchor; `registry/check.py` statically checks the rule and executes it empty. |
| physical profiles | Unchanged. Part 03 §5.4's stored order already leads with `session_id` and `clock_id`. | None required. |
| packet manifest and JSON Schemas | Unchanged. The rule adds no field. | None required. |
| validation and import | Unchanged. Part 05 §15.4 already takes a Tier 2 rule's input set from its parsed base resources. | The corpus cases below. |
| extensions | Unchanged. The rule is declared in core, and no extension registry names `analysis.spike_events`. | `registry/check.py` over every extension registry. |
| reader, writer, validator, adapters | The validator runs the rule as any declared rule, with no code change. The writer already maps `analysis.spike_events` onto `core.sessions.reference_clock_id` alone, and its tests pinning core 0.12.0 follow the new version. The reader and adapters are unchanged. | The writer and validator suites; both session packets rebuilt and validated with no error. |
| conformance fixtures and tests | New clean variant: the valid packet carrying `analysis.spike_events` on its reference clock. New negative variants, each drawing `analysis.spike_events.on_reference_clock` alone: that table with its rows on `behavior_s001`, and a one-clock session declaring no reference clock whose spikes are materialized. | `fixtures/corpus.py`. |
| revision process and tooling | The ordinary ledger and evidence records, and the note on R145 §3.7. | `ledger.py`, `evidence.py` and `verify.py`. |
| generated publications and developer documentation | `registry/tables.md` lists the rule; Part 08 §§2 and 3 regenerate with the new registry version; the specification README's identifier table, `framework.py`'s expected version, the root `STATUS.md` rule count, `registry/README.md`, the combined specification and the heading index follow. | `verify.py`. |

## 6. Conformance and implementation evidence

§3.1 is `registry`, placed by a pointer to the rule in `analysis.spike_events`'s `rules`. §3.2 is
`applied` at Part 02 §9.2, placed by its canonical anchor.

These cases distinguish the new rule from the current registry:

- a packet whose `analysis.spike_events` rows are on a clock other than the session's reference
  draws `analysis.spike_events.on_reference_clock`, with one finding row per session and clock,
  where the current registry accepts it;
- a session declaring one clock and no reference clock, with materialized spikes, draws the same
  rule, and draws nothing else, since Part 01 §3.3 only recommends that such a session declare it;
- a packet whose materialized spikes are on the reference clock passes; and
- a packet with no `analysis.spike_events` passes, since the absent table binds as an empty relation
  (Part 11 §3).

The positive cases are the two rebuilt session packets and the new clean corpus variant. §2.1's
probe and §2.2's timings establish feasibility.
