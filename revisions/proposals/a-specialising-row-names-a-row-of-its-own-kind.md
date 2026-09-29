# A specialising row names a row of its own kind

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-29 |
| **Based on** | `5537b79cb09e2854beb5baf88516f5b6313c58f7` |
| **Decision domain** | specification |
| **Affects** | Part 02 §8.3's shared-key discriminator and the checks generated from it; the registry meta-schema; the extension tables specialising `core.intervals`; the reference validator's check generator |

## 1. Problem

Part 01 §3.10 has an interval declare its kind, "the resource that specialises it". Part 02 §8.3
makes `core.intervals.interval_kind` a shared-key discriminator: the interval and the row
specialising it share a key, and the kind names the table holding that row. A packet can hold a
row specialising an interval whose kind names another table, and nothing reports it.

Beside the check that a kind is a dotted resource ID, three generated checks touch a shared-key
discriminator resolving `required`, and none compares a specialising row with its interval's kind:

- the forward anti-join finds a kind naming a resource the packet does not declare;
- the reverse check, one per named kind, finds an interval with no counterpart in the table its
  kind names; and
- the anti-join generated from the specialising table's reference finds a specialising row naming
  no interval.

A trial row naming an optotagging pulse's interval passes all three wherever every trial interval
and every pulse interval also has a row of its own kind. The pulse's interval then has two
specialisations, and one of them is a trial.

### 1.1 The constant column guards the kind only where it is right

Each table specialising an interval carries its interval's kind as a constant column, so its
reference covers (`session_id`, `interval_kind`, `interval_id`). Where the column holds the table's
own resource ID, the reference forces the interval's kind to match. Nothing checks that it does:
`dynamic_foraging.trials.interval_kind` is `data` with an `open` vocabulary, and "Always
`dynamic_foraging.trials`" is its description rather than a rule. Under the draft
`an-interval-is-numbered-by-its-packet`, the column goes and the reference covers `interval_id`
alone, so a specialising row states no kind at all.

### 1.2 The other shared-key discriminators generate no check

`core.devices.device_kind`, `core.calibrations.detail_kind` and `core.event_streams.detail_kind`
are shared-key discriminators resolving `optional`, for which Part 02 §8.3 generates nothing.
`resolves` decides whether a kind naming a resource the packet lacks is a defect. A detail row
whose device names another kind, or none, contradicts the packet's own rows whichever `resolves`
declares. No registry yet declares a detail table for any of the three. The third declares
`discriminates_via`, so its kind sits on a stream while the rows it specialises are the stream's
events in `core.events`.

## 2. Evidence

The census covers the core registry and the four extension registries at the baseline. A
discriminator specialises the rows of its own table, or of the table `discriminates_via` names, and
a whole-key reference is one targeting that table's whole primary key.

| shared-key discriminator | table it specialises | whole-key references from another table | from a specialising table |
|---|---|---:|---:|
| `core.intervals.interval_kind` (`required`) | `core.intervals` | 2 | 2 |
| `core.devices.device_kind` (`optional`) | `core.devices` | 7 | 0 |
| `core.calibrations.detail_kind` (`optional`) | `core.calibrations` | 2 | 0 |
| `core.event_streams.detail_kind` (`optional`) | `core.events` | 0 | 0 |

The two specialising tables are `dynamic_foraging.trials` and `vr_foraging.sites`.

### 2.1 A misdirected specialising row passes validation

The valid fixture packet was extended with a fixture-local extension declaring `kind_probe.pulses`,
a table shaped like `dynamic_foraging.trials`: a constant `interval_kind` column and a whole-key
reference to `core.intervals`. One interval of that kind and its pulse row were added, and each
variant was validated by the reference validator at the baseline.

| packet | findings at error or warning |
|---|---|
| two kinds, each interval specialised by its own kind | none |
| the same, plus a trial row naming the pulse's interval | none |
| the same, plus a pulse row naming a trial's interval | none |
| two kinds, with the pulse row naming a trial's interval in place of its own | `core.intervals.interval_kind.kind_probe_pulses_is_specialised` |

The fourth packet shows that the pulse kind is checked. The reverse check fails only where a
misdirected row leaves an interval of its own kind without a counterpart, and an added row leaves
none.

A check joining each specialising row to its interval through the table's reference, and returning
the row where the interval's kind is not the table's resource ID, returns 1 row on each of the two
misdirected packets and none on the other two. On the `packet-r147` builds of the two session
packets, `ecephys_786867` and `ecephys_776259`, it returns none of 450 and 708 trials: every trial
carries `dynamic_foraging.trials` in its constant column, and every interval is of that kind.
Queries ran in DuckDB 1.5.5.

### 2.2 A whole-key reference does not identify a specialising table

The reference validator takes a table declaring a whole-key reference to a discriminated table as a
possible specialisation. That is harmless for the reverse check, which is generated only for kinds
a packet's rows name. A check in the other direction starts from the specialising table, so it
needs those tables identified.

Of the 11 whole-key references in §2's census, 2 come from a specialising table. The other 9 are
of two sorts:

- 7 name a related row: tables naming a device, such as `core.probes` and `aind_opto.emissions`;
  and
- 2 come from `core.calibration_points` and `core.calibration_devices`, which hold several rows
  per calibration and whose keys begin with the reference's columns as Part 02 §8.3 has a detail
  table's key begin.

Under the interval draft, any reference on `interval_id` is a whole-key reference to
`core.intervals`, so a table naming the trial an event fell in would qualify as well. None of the
11 references comes from a table keyed by exactly its columns today. After the interval draft, the
two from specialising tables do, since Part 02 §8.3's detail-table key then leaves those tables
keyed by their interval's identifier.

### 2.3 Provenance

R55 and R90 set the shared-key shape and required the whole-key reference so that the generated
anti-join identifies one row; R54 put the kind in the interval's key, which made the constant
column necessary. None addresses a specialising row whose interval names another kind. R104
added `device_kind` on the same shape, resolving `optional`.

## 3. Desired outcome and constraints

A resolution lets a validator report a specialising row whose discriminated row names another kind,
or none, for every shared-key discriminator. It identifies specialising tables without taking a
table that names a discriminated row, or holds several rows per one, for a specialisation. It keeps
core checkable alone: core names an extension's table through a discriminator and never references
one (Part 02 §8.3). It holds under the interval draft, where a specialising row carries no kind.

## 4. Options and tradeoffs

| option | effect |
|---|---|
| keep Part 02 §8.3 as written | Part 01 §3.10's kind binds a writer and no check tests it; after the interval draft, a writer mapping a source's trial numbers to the wrong interval identifiers builds a packet that validates wherever no interval is left unspecialised |
| generate a kind check for every table with a whole-key reference | no new declaration; the tables behind 9 of the 11 references today, and every table naming an interval after the interval draft, would draw a finding for each row whose discriminated row is not of the referencing table's kind |
| generate it for every table keyed by exactly a whole-key reference | no new declaration, and it finds both shipped specialising tables once the interval draft re-keys them; a table holding one row per interval without being a kind, such as a quality flag for every interval, would be taken for a specialisation and draw a finding for every interval of another kind |
| a specialising table declares what it specialises (preferred direction) | one registry field, on the whole-key reference Part 02 §8.3 already requires, and the check is generated for declared specialisations only; the registry meta-schema changes, and each specialising table declares it, two extension tables today |
| each extension declares a Tier 2 rule | no core change; an extension omitting the rule passes in silence, which Part 02 §8.3's generation over every declared resource exists to prevent |

Under the preferred direction the check applies to every shared-key discriminator, whatever it
declares for `resolves`. `resolves` governs a kind naming a resource the packet lacks, and the check
compares two rows the packet holds: a specialising row whose discriminated row names another kind,
or none, is one a consumer resolving from the discriminated row never reaches. A discriminator with
no declared specialisation generates no check, so an `optional` one costs nothing until an
extension declares its first detail table.

The check sits on the specialising table at level `error` and reads the discriminated table, which
Part 05 §15.4's input set already covers as a discriminator branch the check reads. For
`core.event_streams.detail_kind` it joins a detail row to its event, and the event to its stream,
through the reference `discriminates_via` names. For an `optional` discriminator, reporting a null
kind checks what R104 §3.3 asked of a writer, to set `device_kind` wherever it writes a detail row;
that clause is recorded as rationale, and no current part states it.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. Part 01 §3.10 already defines an interval's kind as the resource that specialises it. |
| logical prose and registry | Part 02 §8.3 states the declaration and adds the check to *What is generated*. The registry meta-schema gains the field, so the registry-contract descriptor advances after the drafts `an-interval-is-numbered-by-its-packet` and `unit-labels-order-by-length-then-by-unicode-scalar-value`. The core registry declares no specialising table, so its declarations are unchanged. |
| physical profiles | Unchanged. The check reads two tables and changes no storage. |
| packet manifest and JSON Schemas | The registry meta-schema, as above. The packet manifest is unchanged. |
| validation and import | One generated check per declared specialisation. Part 05 §15.4's input set is unchanged. |
| extensions | `dynamic_foraging.trials` and `vr_foraging.sites` each declare what they specialise, in their own registry version. `aind_opto` and `aind_unit_qc` specialise nothing. |
| reader, writer, validator, adapters | The validator's generator emits the check from the declaration, and can take its reverse-check candidates from it. The writer is unchanged. Unknown: whether the reader's discriminator resolution should use the declaration. Adapters are unchanged. |
| existing packets | Both session packets draw no finding, and the interval draft rebuilds them anyway. |
| conformance fixtures and tests | A fixture-local extension with a second specialising table, as in §2.1: a conforming packet with two kinds, and a misdirected trial and a misdirected pulse, each drawing the check. |
| revision process and tooling | Unchanged. |
| generated publications and developer documentation | `registry/tables.md` renders the declaration, and the registry guide documents the field. |

## 6. Open questions

1. **Is a specialising table declared, or inferred?** Resolved 2026-09-29: declared, on its
   whole-key reference. The only inferable shape, a table keyed by exactly that reference, also fits
   a table holding one row per interval without being a kind, and the declaration lets a registry
   check a specialising table's shape.
2. **Does the check apply to every shared-key discriminator, or only to those resolving
   `required`?** Resolved 2026-09-29: every one, since `resolves` governs an absent resource and
   the check compares two present rows (§4).

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [x] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.
