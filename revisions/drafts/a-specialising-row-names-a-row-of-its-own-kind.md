# A specialising row names a row of its own kind

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `884ab72b6500805cc456f2ab755806ca993bb72f` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 02 §§1, 7, 8.3, 9.2 and 9.4; Part 08 §§2 and 3; the registry meta-schema; the registry-contract descriptor; the core registry |
| **Depends on** | R150 §3.10 (the meta-schema and descriptor this advances from); R151 §3.2 (the core registry version this advances from) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4 |

Section 3 is normative. Sections 1, 2 and 4–6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

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

A trial row naming a cue tone's interval passes all three wherever every trial interval and every
tone interval also has a row of its own kind. `core.devices.device_kind`,
`core.calibrations.detail_kind` and `core.event_streams.detail_kind` resolve `optional`, and for
them Part 02 §8.3 generates none of the three. A detail row whose device names another kind, or
none, contradicts the packet's own rows whichever `resolves` declares.

A check in that direction starts from the specialising table, and no registry says which tables
specialise. Part 02 §8.3 asks a named resource for a reference back covering the discriminated
table's whole key, and Part 02 §7 makes every reference cover its target's whole key, so every
table referencing an interval, a device or a calibration meets the condition.

This revision has a specialising table declare the discriminator it specialises on its reference,
generates a check that each detail row's specialised row names the detail table, for every
shared-key discriminator whatever `resolves` declares, and adds a registry invariant checking the
declaration.

The change is structural because it revises Part 02 §8.3's shared-key requirement and its *What is
generated* paragraph in place. An appended section would leave the first requiring a reference that
every reference to the table already is, and the second saying that an `optional` discriminator
generates nothing.

### 1.1 Structural crosswalk

Every affected existing section carries a canonical anchor, so no bootstrap is needed.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 02 §7, the members of a reference | extend in place | same section | a reference may declare the discriminator it specialises | §3.1 |
| Part 02 §8.3, the shared-key paragraph's reference back | revise in place | same section | a resource a shared-key discriminator may name declares a specialising reference naming it, and resolution joins on that reference | §3.1 |
| Part 02 §8.3, the detail table's key | revise in place | same section | a detail table's key begins with its specialising reference's columns | §3.1 |
| Part 02 §8.3, *What is generated* | revise in place | same section | a counterpart is found through the declaration, and every specialising reference generates a kind check whatever `resolves` declares | §3.2 |
| Part 02 §9.4, the meta-schema requirements, invariant table and invariant prose | extend in place | same section | the meta-schema admits `specialises`, and `registry.discriminator.specialisation` checks it | §3.3 |
| Part 02 §§1, 9.2 and 9.4, the incorporated identifiers | revise in place | same sections | the meta-schema, descriptor and core registry identifiers advance | §3.4 |
| Part 08 §§2 and 3, the generated layout and manifest excerpt | regenerate the informative example | same sections | none | none |

## 2. Background

Section 2 is informative. The census reads the core registry and the four repository extension
registries at the baseline. The probes use the reference validator at the baseline and DuckDB
1.5.5.

### 2.1 Census

A shared-key discriminator specialises the rows of its own table, or of the table
`discriminates_via` names. Every reference to that table covers its whole key (Part 02 §7).

| shared-key discriminator | table it specialises | references from another table | from a specialising table |
|---|---|---:|---:|
| `core.intervals.interval_kind` (`required`) | `core.intervals` | 2 | 2 |
| `core.devices.device_kind` (`optional`) | `core.devices` | 7 | 0 |
| `core.calibrations.detail_kind` (`optional`) | `core.calibrations` | 2 | 0 |
| `core.event_streams.detail_kind` (`optional`) | `core.events` | 0 | 0 |

The two specialising tables are `dynamic_foraging.trials` and `vr_foraging.sites`, each keyed by
exactly its reference's column, `trial_id` or `site_id`, onto `core.intervals.interval_id`. The
other 9 references are of two sorts. Seven name a related device, as `core.probes` and
`aind_opto.emissions` do, and no key among them begins with the reference's column. Two come from
`core.calibration_points` and `core.calibration_devices`, which hold several rows per calibration
and whose keys begin with `calibration_id`, as Part 02 §8.3 has a detail table's key begin.

### 2.2 A misdirected detail row passes validation

The valid fixture packet `fixtures/build.py` writes was extended with its fixture-local extension
declaring `cue.tones`, a table keyed by `tone_id` referencing `core.intervals.interval_id`, and
with one interval of that kind and its tone row. Each variant was validated, and a candidate check
was run on it: join each trial and tone row to its interval through the table's reference, and
return the row where the interval's kind is not the table's resource ID.

| packet | findings at error or warning | rows the candidate check returns |
|---|---|---:|
| two kinds, each interval specialised by its own kind | none | 0 |
| the same, plus a trial row naming the tone's interval | none | 1 |
| the same, plus a tone row naming a trial's interval | none | 1 |
| two kinds, with the tone row naming a trial's interval in place of its own | `core.intervals.interval_kind.cue_tones_is_specialised` | 1 |

The reverse check fails only where a misdirected row leaves an interval of its own kind without a
counterpart, and an added row leaves none.

The candidate check returns none of 450 trials in the `packet-r150` build of `ecephys_786867`, none
of 708 in that of `ecephys_776259`, and none of 450 trials and 120 `vr_foraging.sites` rows in the
first session's amended build. Over the 102 packets `fixtures/corpus.py` builds it returns no row.
It joins inner, so the corpus's `orphan_trial` variant, a trial naming no interval, stays with the
reference's anti-join; a left join would return it.

### 2.3 Inference takes related tables for specialisations

Run over every table referencing a discriminated table, the candidate check returns every joined
row of a table that is not a specialisation. In `ecephys_786867`'s `packet-r150` build it returns
all 10 `core.probes` rows and all 14 `core.calibration_points` rows. In `ecephys_776259`'s it
returns all 12 `core.probes` rows, all 14 `core.calibration_points` rows, and all 6
`core.calibration_devices` rows through each of that table's two references. The trials draw
nothing in either.

Inferring a specialisation from a key that begins with the reference's columns still takes the two
calibration tables. Inferring one from a key equal to the reference's columns finds both
specialising tables, and would also take a table holding one row per interval without being a
kind, such as a quality flag for every interval.

### 2.4 Alternatives

| option | effect |
|---|---|
| keep Part 02 §8.3 as written | an interval's kind binds a writer and no check tests it, so a writer mapping a source's trial numbers to the wrong interval identifiers builds a packet that validates wherever no interval is left unspecialised |
| check every table referencing a discriminated table | no new declaration; §2.3's tables draw a finding on every row |
| check every table keyed by exactly its reference | no new declaration; a table holding one row per interval without being a kind draws a finding for every interval of another kind |
| each extension declares a Tier 2 rule | no core change; an extension omitting the rule passes in silence, which Part 02 §8.3's generation over every declared resource exists to prevent |
| a specialising table declares its discriminator on its reference (preferred direction) | one optional reference member; the check is generated for declared specialisations only, and the registry can check a detail table's shape |

The check applies whatever `resolves` declares. `resolves` governs a kind naming a resource the
packet lacks, and the check compares two rows the packet holds. A detail row whose specialised row
names another kind, or none, is one a consumer resolving from the specialised row never reaches. A
discriminator with no declared specialisation generates no check, so an `optional` one costs
nothing until an extension declares its first detail table.

### 2.5 Provenance

R55 and R90 set the shared-key shape and required the reference back so that the generated
anti-join identifies one row. R148 removed the kind from the interval's key, and with it the
constant column through which a specialising table's reference forced its interval's kind. R104
added `device_kind` on the same shape, resolving `optional`, and asked a writer to set it wherever
it writes a detail row; that clause is recorded as rationale, and no current part states it.

## 3. Decision

Four subsections declare a specialisation on its reference, generate the checks it implies, check
the declaration in the registry contract, and advance the registry identifiers. The crosswalk in
§1.1 places each.

### 3.1 A specialising reference names its discriminator

A reference MAY declare `specialises`, a dotted `resource.column` naming a discriminator. A
reference declaring it is a **specialising reference**, its table is a **detail table** of that
discriminator, and a row of the detail table is a **detail row**. The row a detail row's reference
resolves to is its **specialised row**.

`specialises` MUST resolve, under the visibility and direction rules of a reference target, to a
discriminator column that declares no `discriminates`. The reference's target MUST be the table that
discriminator specialises: the table `discriminates_via` names where the discriminator declares it,
and the discriminator's own table otherwise. The detail table's primary key MUST begin with the
reference's `columns`, in their order. A table MUST NOT declare `specialises` on more than one
reference.

A resource a shared-key discriminator may name MUST be a detail table of that discriminator. This
replaces Part 02 §8.3's requirement of a reference back covering the discriminated table's whole
key, which Part 02 §7 makes of every reference. Where the discriminator resolves `optional`, no
checker verifies this; where it resolves `required`, §3.2's reverse check reports every row naming a
resource that is not a detail table of it.

Shared-key resolution joins the discriminated row to the named resource through that resource's
specialising reference naming the discriminator.

The incorporated registry meta-schema MUST admit `specialises` in the `reference` object as an
optional member after `resource_columns`, declared as:

```json
{
  "type": "string",
  "pattern": "^[a-z][a-z0-9_]*\\.[a-z][a-z0-9_]*\\.[a-z][a-z0-9_]*$"
}
```

### 3.2 Every specialisation generates a kind check

A packet MUST NOT hold a detail row whose specialised row's discriminator value is null or names a
resource other than the detail table. The value is read on the specialised row where the
discriminator is on that row's table, and otherwise on the row of the discriminator's table that
the specialised row's `discriminates_via` column references.

Every specialising reference generates a check at **error** on its detail table, whatever the
discriminator declares for `resolves`. The check returns every detail row whose reference resolves
and whose specialised row's discriminator value is null or is not the detail table's resource ID. A
detail row whose reference resolves to nothing is left to the reference's anti-join.

A shared-key discriminator resolving `required` keeps its reverse check per named kind, which finds
each row's counterpart through the declaration: the row of the named resource whose specialising
reference naming this discriminator resolves to it. A named resource declaring no such reference holds no counterpart, so the check
returns every row naming it.

Where `resolves` is `optional`, the forward anti-join, the reverse check and the paired-value checks
are not generated, and an unresolvable value is reported as `info`. The check this subsection
generates on a detail table is generated for every discriminator.

### 3.3 The registry contract checks the declaration

The registry-contract descriptor MUST append the invariant
`registry.discriminator.specialisation`, phase `semantic`, classes `core` and `extension`, anchors
`ew-discriminator-semantics` and `ew-registry-conformance`, after
`registry.amendment_groups.resolves`. A checker reports it for a `specialises` value naming no
visible column, naming a column that is not a discriminator, or naming a discriminator that
declares `discriminates`; for a specialising reference whose target is not the table its
discriminator specialises; for a detail table whose primary key does not begin with its
specialising reference's `columns` in their order; and for a table declaring `specialises` on more
than one reference. Its outcome points at the offending `specialises` member, at the later one of a
table declaring two, and is core-dependent where the discriminator lies in the core context.

### 3.4 The registry identifiers advance

These incorporated identifiers MUST advance:

| artifact | from | to |
|---|---|---|
| registry meta-schema `$id` | `https://escapewheel.org/schemas/registry/0.10.0`, which R150 assigns | `https://escapewheel.org/schemas/registry/0.11.0` |
| registry-contract descriptor ID | `escapewheel-registry-contract-v0.8`, which R150 assigns | `escapewheel-registry-contract-v0.9` |
| core registry `registry_version` | `0.13.0`, which R151 §3.2 assigns | `0.14.0` |

The v0.9 descriptor selects meta-schema 0.11.0, lists `escapewheel-rule-sql-v0.2` alone in
`rule_languages`, and otherwise differs from v0.8 only by §3.3's invariant. Part 02 §1 incorporates
it as `registry/registry_contracts/escapewheel-registry-contract-v0.9.json`. The core registry
declares no specialising reference.

An extension registry migrated to meta-schema 0.11.0 MUST carry a `registry_version` different from
the one it carried under 0.10.0; the core specification does not assign it (Part 09 §5.5). No checker
verifies this.

## 4. What this does not change

Part 05 §13.4 has a reader resolve in the shape Part 02 §8.3 declares, and §3.1 states that shape,
so Part 05 §13.4 is unchanged. Part 05 §15.4's input set already covers every specialisation or
discriminator branch a generated check reads, so the check §3.2 generates is admitted as it stands.
Paired-value discriminators, what `resolves` governs, and core's ban on a device-detail table are
unchanged. Part 01 §3.10 already defines an interval's kind as the resource that specialises it.

## 5. Consequence

Every packet is rebuilt, binding meta-schema 0.11.0 and core registry 0.14.0. No row changes in
either session packet or in any fixture packet, and none draws §3.2's check (§2.2). The two
repository extension tables specialising an interval draw the reverse check on every trial and site
until their extensions declare a specialising reference; each extension declares its own change, and
the core specification assigns no extension's version (Part 09 §5.5). An extension migrated without
the declaration fails where its kind resolves `required`, rather than losing the reverse check in
silence.

These accepted clauses change:

- R90 §3.6's ledger entry gains a note that §3.1 replaces the reference back with a specialising
  reference.
- R90 §3.4's and R90 §3.8's ledger entries gain notes that §3.2 generates a kind check on every
  detail table whatever `resolves` declares, and finds a counterpart through the declaration.
- R104 §3.3's rationale entry gains a note that §3.2's check reports a detail row whose device's
  kind is null or names another resource.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. Part 01 §3.10 already defines an interval's kind as the resource that specialises it. | None required. |
| logical prose and registry | Part 02 §7 names the member, Part 02 §8.3 takes §§3.1 and 3.2, and Part 02 §§1, 9.2 and 9.4 take §3.4's identifiers and §3.3's invariant. `registry/registry.schema.json` admits the member; the registry source's spelling of a reference carries it; `registry/check.py` implements the invariant and follows the new identifiers. The core registry's declarations are unchanged. | `evidence/R<N>.json` names each anchor and registry pointer; `registry/check.py` passes. |
| physical profiles | Unchanged. The check reads two or three tables and changes no storage. | None required. |
| packet manifest and JSON Schemas | The registry meta-schema, as above; `registry/build.py` copies it into the validator. The manifest schema is unchanged. | `registry/build.py` regenerates byte-identically. |
| validation and import | Unchanged in Part 05, as §4 states. The generated checks change as §3.2 states. | The validator suite. |
| extensions | A repository extension table specialising a discriminator declares a specialising reference, and each extension advances its `registry_version`; the core specification chooses neither. | `registry/check.py` over every extension registry. |
| reader, writer, validator, adapters | The validator generates §3.2's check from each declaration, takes reverse-check counterparts from it, generates the reverse check for a named resource declaring none, and implements §3.3's invariant. The reader's shared-key resolution follows the declared specialising reference. The writer and adapters are unchanged. | The validator and reader suites; both session packets rebuilt and validated with no error. |
| conformance fixtures and tests | The fixture-local `cue.tones` table declares its specialising reference, and §6's packets and registry variants join the corpus. | `fixtures/corpus.py`; the registry-conformance vectors. |
| revision process and tooling | The ordinary ledger and evidence records, and the notes above. | `ledger.py`, `evidence.py` and `verify.py`. |
| generated publications and developer documentation | `registry/tables.md` renders the member; Part 08 §§2 and 3 regenerate with the new registry versions; the registry guide documents the member; the specification README's identifier table, `framework.py`'s expected version, the combined specification and the heading index follow. | `verify.py`. |

## 6. Conformance and implementation evidence

§3.1 is `applied` at Part 02 §7 and Part 02 §8.3, and at Part 02 §9.4 for its meta-schema member.
§3.2 is `applied` at Part 02 §8.3 and §3.3 at Part 02 §9.4. §3.4 is `applied` at Part 02 §§1, 9.2
and 9.4. Each is placed by canonical anchor.

These cases distinguish the new rules from the current ones:

- a packet holding trials and cue tones, each interval specialised by a row of its own kind, is
  conforming, as are both session packets and the first session's amended packet;
- the same packet plus a trial row naming a tone's interval draws §3.2's check on
  `dynamic_foraging.trials`, and plus a tone row naming a trial's interval draws it on `cue.tones`,
  where today each validates clean;
- a tone row naming a trial's interval in place of its own draws §3.2's check and the reverse check;
- a fixture-local device-detail table whose row names a device whose `device_kind` is null, or names
  another resource, draws §3.2's check, though `device_kind` resolves `optional`;
- an interval whose kind names a declared resource that declares no specialising reference naming
  `core.intervals.interval_kind`, such as `core.sessions`, draws the reverse check on that row;
- a registry whose `specialises` names an absent column, a column that is not a discriminator, or a
  paired-value discriminator; whose specialising reference targets another table, such as
  `core.event_streams` for `core.event_streams.detail_kind`; whose detail table's key does not begin
  with the reference's columns; or whose table declares `specialises` on two references draws
  `registry.discriminator.specialisation`; and
- a `specialises` value that is not a dotted `resource.column` fails the `shape` phase.

The candidate check of §2.2 establishes feasibility: an inner join from each detail row through its
reference returns exactly the misdirected rows on the fixture packets and none on the session
packets or the corpus.
