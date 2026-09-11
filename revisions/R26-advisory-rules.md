# R26 — Advisory Rules

| | |
|---|---|
| **Status** | **Accepted** 2026-08-27 |
| **Amends** | R2 §7.2 (Tier 2 rule shape), R18 §2 |
| **Depends on** | R2 (registry format), R18 (unit observation intervals) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

There is a class of finding the registry cannot currently express: **true, useful, and not a
defect**.

A packet that declares units and no observation intervals is conforming — R18 §2 says absence
is the honest state where a source designated nothing. It is also a packet in which every
firing rate is uncomputable, because R18 §5 gave `firing_rate_hz` its denominator and this
packet withheld it. Someone should probably be told. Nobody should be told at `error`, because
that would contradict the revision that permits it, and telling them at `warning` on every run
makes the warning count meaningless for packets that meant it.

The same shape recurs: provenance is SHOULD (R9 §5), a designated quality label is optional
(R16 §3), nullable columns may be entirely null. Each is legal, each is worth mentioning once
if asked, and none is a defect.

## 2. Why this is not a level, and not a filter over levels

The mechanism looks like it already exists. `info` is in the meta-schema's level enum, and
`Report.passed` counts only errors, so a non-blocking level costs nothing structurally. The
apparent fix is to author these at `info` and have the validator suppress `info` unless asked.

That breaks the one `info` finding that exists:

```python
report.add("info", "external.unverified",
           f"{len(external)} external resource(s) not resolved; their codecs, sha256 and "
           "size_bytes are unverified claims")
```

R15 §4 emits it so an unverified claim is **reported rather than silently unchecked** — the
comment in the source says "say so, rather than let `passed` imply otherwise". Hiding `info`
by default would restore exactly the silence R15 exists to prevent.

The two are different kinds of statement:

| | says | default |
|---|---|---|
| `external.unverified` | *the validator did not check this* | **shown** — it qualifies the verdict |
| `units.observation_declared` | *the data is legal but thin* | hidden — it is advice about content |

One is about the coverage of the run, the other about the packet. A filter over levels
suppresses the wrong one, because level describes how serious a finding is, not whether it was
asked for.

## 3. Rule

A Tier 2 rule MAY carry `"advisory": true`. Absent means false.

```json
{
  "id": "core.units.observation_declared",
  "level": "info",
  "advisory": true,
  "message": "units carry no observation intervals, so no rate over them has a denominator",
  "sql": "..."
}
```

An advisory rule MUST NOT run unless the caller asks for it. A validator MUST expose that
choice; the reference implementation takes `validate(packet, advisory=True)` and
`escapewheel validate --advisory`.

An advisory rule MUST NOT have `level: "error"`. A finding that does not run by default cannot
determine validity, and a packet whose conformance depended on a flag would be conforming or
not according to how it was invoked. `registry.schema.json` expresses this rather than leaving
it to authors.

Tier 1 checks are never advisory. They are generated from structure and every one of them is a
conformance check.

## 4. The guarantee: `passed` does not move

Because an advisory rule cannot be `level: "error"`, and `Report.passed` is `errors == 0`:

> Running with `advisory` enabled MUST NOT change whether a packet passed.

This is the property that makes the flag safe to add, and it is worth stating normatively
rather than leaving as a consequence someone has to derive. A reader who turns advisories on
is asking for more to read, never for a different verdict.

## 5. A report says whether advisories ran

A validation report with no advisory findings is ambiguous between "none fired" and "they were
not run". That is the same ambiguity R15 §4 refused to accept about external resources, and it
gets the same answer: the report records the choice.

```json
{
  "packet_id": "s001",
  "status": "passed",
  "advisory": false,
  "summary": { "errors": 0, "warnings": 0 }
}
```

## 6. First advisory rule

```sql
-- core.units.observation_declared  (info, advisory)
SELECT u.session_id, u.unit_id, u.sorting_run_id, u.curation_id
FROM core_units u
LEFT JOIN core_unit_observation_intervals o
  ON  u.session_id = o.session_id AND u.unit_id = o.unit_id
  AND u.sorting_run_id = o.sorting_run_id AND u.curation_id = o.curation_id
WHERE o.unit_id IS NULL
```

It reports the full four-column unit identity, per R24 §4: a finding naming `unit_id` alone
cannot say which unit, because unit identity is contextual on the sorting run and curation.

A packet that omits `core.unit_observation_intervals` **entirely** still gets this advice. The
validator creates an empty stand-in from the registry's own DDL for any table a packet does
not declare, so that cross-table Tier 2 rules evaluate rather than fail to run. The left join
then matches nothing and every unit is reported, which is the case the advice is most for.

R25, if accepted, adds the same rule for `core.event_streams` against its observation
intervals. Answering the question for units and never for streams is how two tables that
should behave alike drift apart — but R25 is not yet binding, so this revision does not depend
on it.

## 7. Why this vocabulary change is safe and R24's was not

R24 §2 rejected promoting interval rules to Tier 1 structure because every validator
implementation would then owe four more generation rules, permanently. This adds a key to the
registry too, and the objection does not transfer:

> A consumer that ignores `advisory` is still correct, merely more verbose. A consumer that
> ignores a Tier 1 generation rule misses checks.

An implementation that has never heard of `advisory` runs the rule and reports an `info`
finding. It remains conformant. That asymmetry — between a key whose neglect costs verbosity
and one whose neglect costs coverage — is the test to apply to any future addition to the
registry's vocabulary.

## 8. What this does not do

- **No new table, no new column, no change to `logical_schemas.json`'s shape** beyond one
  optional boolean on rules that opt in.
- **Not a severity system.** `error`/`warning`/`info` are unchanged (R8 §3's closed vocabulary
  still holds). `advisory` is orthogonal: level says how serious, `advisory` says whether it
  was asked for.
- **Not a policy engine.** Part 06's `analysis.good_units` is where a lab encodes what it counts
  as acceptable. This is a validator verbosity control, not a place to express quality policy.
- **No advisory rules beyond §6.** Provenance, designated labels and all-null columns are named
  in §1 as the same shape; each earns its own rule and its own argument that it is worth
  saying.

## 9. Open

- **Whether `warning` should ever be advisory.** §3 permits `warning` or `info`, but every
  rule proposed so far is `info`. If nothing ever wants an advisory warning, the level should
  be pinned to `info` and one degree of freedom removed.
