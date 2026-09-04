# NWB-Lake v0.2 Spec Review and Recommended Changes

Status: implementation handoff / design review  
Scope: current v0.2 specification and handoff  
Focus: semantic standard, logical schema model, physical profile, packet catalog, validation/import, extensions, and analysis layer

## Executive summary

The current design is substantially stronger than the earlier POC. The major architectural choices should be retained: a small domain-general `core`, task- and lab-specific canonical data in typed extensions, long-form canonical spike events, a registry-driven logical schema, validation as the import boundary, a portable Parquet/Zarr profile, and an optional analysis layer justified by measured access cost.

The spec is coherent enough to continue implementation, but several clauses should be tightened before treating it as stable. Two changes have already been agreed and should be made now:

1. intervals should be half-open, `[start_tick, stop_tick)`;
2. identifier columns should be signed `int64`, with mandatory checked conversion and overflow/wraparound failure.

A second important clarification follows from the interval-extension design: **core is not literally the sole source of canonical truth**. This is intentional and desirable. `core.intervals` provides the domain-general temporal identity of a trial/block/epoch, while an extension such as `dynamic_foraging.trials` owns the canonical task-specific facts. The canonical dataset is therefore the union of canonical core resources and canonical extension resources. The analysis layer remains derived and disposable.

The remaining high-priority changes are to make cross-extension validation explicit, define checksums for packet-owned multi-object resources such as Zarr stores, make commit semantics object-store-safe, and weaken or scope the current byte-identical import requirement. A few lower-priority changes would improve future-proofing: broaden the analysis materialization rule beyond physical layout alone, make the physical layout of `analysis.spike_events` normative if its performance properties are part of its reason for existing, and define an actual mandatory-to-read Zarr codec floor for the portable profile.

---

# 1. Design decisions to keep

## 1.1 Keep `core.intervals` generic and specialize it through extensions

Do **not** put a canonical `core.trials` table back into the core schema.

The current design solves an important problem correctly: a trial has a domain-general temporal identity, but the shape of trial metadata is task-specific. Dynamic foraging, visual discrimination, VR navigation, optogenetic perturbation, and passive stimulus experiments should not be forced into one universal trial table whose nullable columns grow without bound.

The intended model should remain:

```text
core.intervals
  session_id
  interval_kind
  interval_id
  clock_id
  start_tick
  stop_tick

           specializes as
                  |
                  v

dynamic_foraging.trials
vr_foraging.trials
some_other_task.trials
...
```

The extension table is not merely descriptive metadata. It may contain **canonical experimental facts** such as choice, reward, condition, block membership, odor identity, or task parameters.

The shared-key discriminator design is therefore worth keeping:

- `core.intervals.interval_kind` names the specializing resource;
- the extension table carries the same complete key;
- the extension table references the whole key back into `core.intervals`;
- packet-level validation verifies that required discriminator targets resolve.

This is cleaner than either a universal trial ontology or an untyped key/value mechanism.

## 1.2 Keep long-form `core.spike_events` as the sole canonical spike representation

This is a good simplification. Ragged/list/chunk representations may be useful materializations, but they should not compete with the canonical event table. One canonical representation avoids synchronization rules between equivalent spike stores.

## 1.3 Keep assigned IDs plus `*_name`, and carried IDs without a second identity

The spec already has the correct naming model. No new alias mechanism is needed.

For assigned identifiers:

```text
session_id   int64
session_name string
```

For a carried source identifier, the source number itself is the identity and a second `*_name` identity should not be invented.

Local/source labels such as `local_unit_label` remain provenance labels, not packet identifiers.

## 1.4 Keep metadata minimalism and typed extensions

The core inclusion rule is strong: put a fact in core only when common interpretation, validation, joining, or analysis would break without it. Rich task, institutional, procedural, or lab-specific schemas belong in extensions. Free-form human context belongs in documents.

The prohibition on arbitrary name/value accretion in core should remain.

## 1.5 Keep the registry as the normative logical schema

The registry-driven design is a major improvement. The prose should define the rules the registry obeys; the registry should define concrete resources, columns, references, and Tier 2 rules. Generated human-readable tables should remain non-editable renderings.

## 1.6 Keep Iceberg deferred

The portable profile is the right first target. Iceberg should remain a later table-management profile, not a dependency of the logical standard.

---

# 2. Required change: canonical data is `core` plus canonical extensions

## 2.1 Problem

Part 00 currently describes `core` as:

> canonical normalized facts; the sole source of truth

and Part 06 says analysis products must be recomputable from core and that anything not recomputable from core belongs in core.

That is no longer true after R54/R55. A task-specific fact such as `choice` may intentionally exist only in `dynamic_foraging.trials`. Moving it into core would defeat the purpose of the extension architecture.

This is not a flaw in the extension model. The wording should change.

## 2.2 Recommended model

Define:

```text
canonical resources
  = canonical core resources
  + canonical extension resources

analysis resources
  = derived resources reproducible from canonical resources
```

Core is the **domain-general canonical substrate**, not the complete semantic content of every experiment.

## 2.3 Suggested normative replacement for Part 00 section 3

```text
A packet is divided into namespaces.

The `core` namespace contains canonical domain-general facts defined by this
standard. Extension namespaces MAY contain canonical domain-specific facts that
specialize or augment core resources. The `analysis` namespace contains derived
resources reproducible from the packet's canonical resources. The `nwb`
namespace is reserved for a deferred compatibility projection.

The canonical state of a packet is the union of its canonical core resources
and its canonical extension resources.
```

Suggested layer table:

| namespace class | contents | required |
|---|---|---|
| `core` | canonical domain-general facts | yes |
| extension namespace | canonical domain-specific facts and metadata | when required by present data |
| `analysis` | derived/materialized products | no |
| `nwb` | deferred compatibility projection | no |

## 2.4 Fix Part 00 section 4.1 wording

Replace:

```text
One row per trial in core.intervals
```

with:

```text
One row per bounded interval in core.intervals. The interval's domain-specific
meaning is carried by the resource named by interval_kind.
```

## 2.5 Fix Part 06 normative rule

Replace the core-only language with:

```text
An analysis resource MUST declare lineage to the canonical resources it derives
from.

An analysis resource MUST NOT be the only place a non-derived fact exists. A
domain-general canonical fact belongs in core. A domain-specific canonical fact
belongs in the appropriate extension.
```

The analysis layer may therefore derive from both core and extensions.

---

# 3. Required change: make interval semantics half-open

## 3.1 Decision

All interval resources should use:

```text
[start_tick, stop_tick)
```

`start_tick` is included. `stop_tick` is excluded.

## 3.2 Why

Half-open intervals compose naturally and match array slicing and most query/programming conventions:

```text
[100, 200)
[200, 300)
```

are adjacent with neither overlap nor gap.

Duration is exact and simple:

```text
duration_ticks = stop_tick - start_tick
```

Containment is unambiguous:

```text
start_tick <= t_tick AND t_tick < stop_tick
```

An array window on a sample-index clock is naturally:

```python
data[start_tick:stop_tick]
```

## 3.3 Suggested normative replacement for Part 01 section 2.3

```text
An interval is half-open: [start_tick, stop_tick). start_tick names the first
included tick and stop_tick names the first excluded tick.

A tick t is contained in the interval if and only if:

    start_tick <= t < stop_tick

For an ordinary non-empty interval, stop_tick MUST be greater than start_tick.
The duration in clock ticks is stop_tick - start_tick.

An instantaneous observation SHOULD be represented as an event rather than as a
zero-duration interval unless a specializing schema explicitly defines a reason
for an empty interval.
```

Part 01 section 3.10 should say that start and stop ticks are half-open per section 2.3.

## 3.4 Import conversion rules

Replace the current normalization rule in Part 05.

Recommended text:

```text
Core intervals are half-open, [start_tick, stop_tick).

A source already expressing half-open integer intervals MUST be carried through
without changing either bound.

A source expressing a closed discrete interval [first_tick, last_tick] MUST be
converted to [first_tick, last_tick + 1). The addition MUST use checked int64
arithmetic and the import MUST fail if it would overflow.

Where a source provides a stop event or boundary rather than a last included
sample, the adapter MUST document whether that source value is already an
exclusive boundary. It MUST NOT blindly add or subtract one.
```

The last clause matters. "last included sample" and "time at which the stop event occurred" are different source semantics even if both are named `stop` upstream.

## 3.5 Update containment queries and validators

All interval membership logic should use:

```sql
e.t_tick >= i.start_tick
AND e.t_tick < i.stop_tick
```

not `BETWEEN`.

Validators should check `stop_tick > start_tick` for interval kinds that do not explicitly allow empty intervals.

---

# 4. Required change: identifiers become signed `int64`

## 4.1 Decision

Every column with role `identifier` should be stored as signed `int64`.

`int32` should remain in the permitted primitive type set for ordinary data/index fields where appropriate; it simply stops being the mandated identifier representation.

## 4.2 Suggested normative replacement

Part 01 section 2.1:

```text
An identifier is a signed 64-bit integer. Implementations MUST NOT encode
semantic meaning in identifier values and MUST NOT derive an identifier from a
value's position in a file.
```

Part 02 section 5.3:

```text
Tick columns MUST be int64. Identifier columns MUST be int64. Wall-clock
columns MUST be timestamp with microsecond precision in UTC and MUST NOT use
INT96.
```

Part 03 section 5.1 should likewise change `int32` to `int64`.

## 4.3 Checked conversion and wraparound are mandatory

Add a global numeric safety clause, preferably to Part 02 or Part 05:

```text
A writer or importer MUST NOT use wraparound semantics for identifiers, ticks,
structural indices, sequence positions, or interval-bound arithmetic.

A conversion, cast, assignment, increment, offset, or arithmetic operation that
would produce a value outside the declared integer type MUST fail before the
value is written.

Silent truncation, modular wraparound, and saturation are non-conforming.
```

In particular:

```text
closed [first_tick, INT64_MAX]
```

cannot be converted to a half-open interval and must fail loudly.

## 4.4 Preserve the existing name model

No additional string alias fields are needed. The current distinction should remain:

```text
assigned ID -> owning table also carries *_name
carried ID  -> source number is the identity; no *_name is added
```

A source identifier that cannot be represented as `int64` must not be silently truncated. If the importer maps it into an assigned packet identifier instead, that mapping must be explicit and provenance-preserving.

---

# 5. Required clarification: validation has three scopes

## 5.1 Problem

The current spec says all of the following:

- core validation must not require an extension schema;
- extension verdicts are separate from the core verdict;
- `core.intervals.interval_kind` may have `resolves: required`;
- a packet carrying intervals must contain the extension resource named by the discriminator;
- an unresolvable required discriminator is a defect because the row is uninterpretable.

These ideas are compatible, but the current text does not name the validation phase that performs the cross-namespace resolution. Two implementers could place that check in different verdicts and disagree about whether a packet passes.

## 5.2 Recommended validation scopes

Define three explicit verdicts:

### A. Core structural verdict

Validates core against the core registry only.

It MUST NOT require or load an extension registry.

### B. Extension verdict(s)

Each declared extension validates against its own embedded registry and its references into core.

An extension failure MUST NOT change the core structural verdict.

### C. Packet binding/integrity verdict

Runs after registries are known and validates cross-namespace bindings, including required discriminators.

For example, for:

```text
core.intervals.interval_kind = dynamic_foraging.trials
```

it verifies that:

1. the extension registry is declared and available;
2. `dynamic_foraging.trials` is a declared resource;
3. the resource uses the required shared-key relationship;
4. the corresponding detail row exists.

Failure is a **packet conformance error**, not a retroactive core structural error.

## 5.3 Overall packet status

Recommended rule:

```text
A packet's overall validation status is passed only when its core structural
verdict passes, every committed resource passes the schema applicable to it,
all required cross-resource bindings resolve, and all required physical-profile
checks pass.

An extension error MUST NOT alter the core structural verdict, but an invalid
committed extension resource or an unresolved required discriminator MUST make
the overall packet verdict fail.
```

This preserves separable diagnostics without allowing an uninterpretable packet to claim overall conformance.

---

# 6. Required fix: define checksums for packet-owned Zarr/prefix resources

## 6.1 Problem

Part 03 currently says a packet-owned resource records a `sha256` and describes this as cheap because it is "whole-file, one file per resource."

That is true for a Parquet table but not for a Zarr store. A packet-owned Zarr v3 resource is normally a directory/prefix containing multiple metadata and chunk/shard objects. The example packet nevertheless gives owned Zarr resources a single `sha256`.

The specification currently does not define what bytes that digest covers, so two conforming implementations could calculate different hashes for the same store.

## 6.2 Recommended digest model

Make the digest scope explicit.

Prefer a catalog object such as:

```json
"digest": {
  "algorithm": "sha256",
  "scope": "file",
  "value": "..."
}
```

or:

```json
"digest": {
  "algorithm": "sha256",
  "scope": "tree",
  "value": "..."
}
```

For `scope: file`, hash the raw file bytes.

For `scope: tree`, define a canonical member manifest containing, at minimum:

```text
relative member path
member size
member SHA-256
```

sorted lexicographically by normalized relative path. The tree digest is the SHA-256 of a precisely specified canonical serialization of that manifest.

`size_bytes` for a tree resource should be defined as the sum of member byte sizes.

A simpler field layout is acceptable, but the algorithm must be normative. Do not leave "hash the Zarr" implementation-defined.

## 6.3 Benefit

The same primitive can later support owned directory resources, multipart scientific assets, and optional strong verification of external prefixes. It also makes amendment validation well-defined.

---

# 7. Required fix: commit semantics must work on object stores

## 7.1 Problem

Part 05 currently makes commit atomic by renaming a candidate manifest to `nwb.packet.json` last.

That is a good local-filesystem implementation, but the architecture explicitly permits an object-store prefix. Object stores generally do not provide directory rename as the commit primitive.

## 7.2 Recommended semantic contract

Specify **publication**, not rename:

```text
A packet commit becomes visible when the final packet catalog is atomically
published at the packet's catalog location.

All packet-owned resources named by that catalog MUST already exist at their
final immutable locations and MUST have passed validation before publication.

The mechanism used to publish the catalog is profile-specific. A local
filesystem implementation MAY use atomic rename of a temporary catalog. An
object-store implementation MAY use a single-object atomic PUT/replacement or
another profile-defined atomic publication primitive.

A writer MUST NOT require atomic directory rename.
```

For concurrent amendment, the implementation should use a conditional catalog update when the backing store supports one, so two writers cannot silently overwrite the packet head.

The important invariant is:

> readers either see the previous committed catalog or the new committed catalog, never a catalog naming resources that are still being moved into place.

---

# 8. Required clarification: determinism vs byte-identical packets

## 8.1 Problem

Part 05 requires:

> produces byte-identical output from two runs over the same sources

while the packet contains fields such as `created_at`, `validated_at`, and processing-run timestamps. Physical encoders may also legitimately emit different bytes across library versions while representing identical Parquet/Zarr logical content.

As written, the requirement is either impossible or much stronger than the interoperability contract needs to be.

## 8.2 Recommended split

Make **logical determinism** normative:

```text
For the same recipe, source bytes, and declared normalization policy, an
importer MUST produce the same canonical rows, values, assigned identifiers,
resource identities, and required physical ordering.
```

Make **byte determinism** a reference-implementation/test property:

```text
A deterministic-build mode SHOULD pin volatile timestamps, writer settings,
codec parameters, and implementation versions such that repeated runs produce
byte-identical packet-owned resources.
```

If byte-identical regression builds are important, keep them in Part 07 or in implementation tests rather than making every independently written conforming importer produce identical Parquet bytes.

A content fingerprint for canonical normalized resources can be defined separately from execution metadata if useful.

---

# 9. Recommended change: analysis resources may derive from extensions

This follows from section 2.

Any generic clause saying analysis is "reproducible from core" should become "reproducible from canonical resources."

For example, a task-specific trial view may legitimately derive from:

```text
core.intervals
+ dynamic_foraging.trials
+ dynamic_foraging.blocks
```

without moving those task facts into core.

---

# 10. Recommended change: broaden the materialization criterion slightly

## 10.1 Problem

The current analysis philosophy says materialization is justified by **layout, not arithmetic**. That was a useful corrective to the early proposed tables: `trials_wide`, `good_units`, and several spike/trial products were cheap enough to compute as views.

As a general spec rule, however, it is too narrow. Expensive signal processing or feature extraction may be worth persisting even when the physical sort order is not the primary reason.

Examples include:

```text
filtered/resampled signals
spectral decompositions
CSD
large waveform features
deep-model embeddings
pose estimates
expensive decoding feature matrices
```

These are legitimate derived analysis assets if their lineage and parameters are recorded.

## 10.2 Suggested rule

```text
An analysis resource SHOULD be materialized only when doing so materially
reduces repeated computational or I/O cost, changes an otherwise unsuitable
access layout, preserves the result of an expensive transformation, or provides
a stable reusable interface to an explicitly parameterized derivation.

A cheap filter, projection, rename, or small join SHOULD remain a view or query.
```

The measurements that caused the v0.1 resources to be withdrawn remain valid; this just avoids turning that local finding into an unnecessarily restrictive universal rule.

---

# 11. Recommended fix: make the performance contract of `analysis.spike_events` normative

`analysis.spike_events` exists specifically because its physical organization supports time-window and unit pruning. Part 06 says that a row group lies inside one time bucket, but section 4 is informative and the portable profile does not currently state that row-group boundary rule.

If this layout is the reason the resource exists, make it part of the physical contract.

Suggested portable-profile rule:

```text
For analysis.spike_events, a Parquet row group MUST NOT span more than one
`time_bucket_tick` value. Rows MUST be ordered by time_bucket_tick followed by
the declared unit identity/order within each bucket.
```

The shim validator should verify the row-group condition.

Otherwise a writer can produce logically correct `analysis.spike_events` that loses the performance property the resource was introduced to provide.

---

# 12. Recommended fix: actually define the portable Zarr codec floor

Part 03 says:

> The floor a reader is required to support is stated per Zarr version

but the current document does not actually enumerate that floor.

This needs one of two changes:

1. define a small mandatory-to-read codec subset for packet-owned Zarr v3 resources; or
2. delete the statement that a floor exists and explicitly declare that portable conformance does not imply ability to open every packet-owned array.

The first option better matches the goal of a **portable** profile.

Recommended policy:

```text
A portable reader MUST support a small named baseline codec set.
A portable writer SHOULD use only that baseline for packet-owned canonical
arrays unless it explicitly declares an extended feature requirement.
Readers MAY support additional declared codecs.
```

This matters particularly because the current real example uses codecs such as `numcodecs.delta` and `blosc`; cross-language availability, not Python availability, should determine the baseline.

Do not hard-code the baseline until it has been checked against the non-Python implementations the project actually wants to support.

---

# 13. Recommended clarification: provenance conformance classes

Part 01 says a packet with no provenance can conform, while Part 05 requires a conforming importer to record source files, processing runs, and run inputs.

These clauses can coexist, but the distinction should be explicit:

```text
packet structural conformance
  may be evaluated on a packet regardless of how it was created

importer conformance
  requires provenance for the import activity and its inputs
```

If the long-term philosophy is truly "validation is importation," it would also be reasonable to tighten packet conformance later and require minimal provenance for every canonical packet. For the current POC, simply naming the two conformance classes is sufficient.

---

# 14. Recommended future fix: Iceberg snapshot vs packet version semantics

This does not block the portable POC, but the current future-facing statement should be revisited before implementing the Iceberg profile.

The spec currently says:

```text
packet_version versions the bundle
```

but also says a rewrite of a future Iceberg table's rows must not increment `packet_version`.

If a packet is reproducible, the packet should eventually pin an Iceberg snapshot/tag for every canonical table. Changing the pinned snapshot changes the packet's canonical state and therefore appears to be a packet amendment.

Before the Iceberg profile is written, choose one of these models explicitly:

### Recommended model

```text
packet resource entry pins Iceberg snapshot/tag
changing the pinned snapshot changes the bundle
changing the bundle increments packet_version
```

Iceberg snapshots then provide table history, while packet versions provide coherent cross-resource dataset releases.

That matches the existing definition of `packet_version` more naturally.

---

# 15. Versioning impact of the agreed changes

Half-open intervals and `int64` identifier columns are both breaking changes:

- closed versus half-open changes semantic interpretation;
- `int32` versus `int64` changes logical and physical schemas.

Therefore a packet written under the new rules cannot honestly claim compatibility solely through the same old semantic/logical/profile identifiers unless version-aware readers are expected to inspect the embedded registry and semantic document every time.

The current deliberate version hold is understandable during rapid iteration, but this set of changes is a good point to decide whether to lift it.

At minimum:

```text
- regenerate the embedded registry;
- update all affected fixture packets;
- update the generated tables reference;
- make the embedded registry the explicit authority during the hold;
- add a registry content digest if quick exact compatibility checks are useful.
```

Before external release, the semantic standard, logical standard, registry, and portable profile identifiers should accurately distinguish the old closed/int32 packets from new half-open/int64 packets.

---

# 16. Spec release completeness

A standalone spec release should ship the normative/generated artifacts needed to implement it, not just prose:

```text
registry/logical_schemas.json
registry meta-schema
registry/tables.md
packet catalog JSON schema
normative extension registry examples
at least one conforming fixture packet or compact fixture manifest
expected validation findings for negative fixtures
```

The handoff documents refer to these artifacts in the implementation repository. The important requirement is that a tagged spec release always binds the prose and generated registry artifacts together.

---

# 17. Suggested implementation order

## P0 - do before packaging more sessions

1. Change intervals to half-open.
2. Change all identifier-role columns to `int64`.
3. Add checked integer conversion/arithmetic and overflow tests.
4. Regenerate registry, table docs, fixtures, and validators.
5. Change "core is sole source of truth" to "canonical resources = core + canonical extensions."
6. Add explicit packet-level discriminator/binding validation.

## P1 - fix before treating the portable profile as stable

7. Define digests for multi-object packet-owned resources such as Zarr.
8. Replace rename-specific commit semantics with profile-neutral atomic catalog publication.
9. Separate logical determinism from byte-identical regression builds.
10. Define the mandatory-to-read Zarr codec floor.
11. Make the row-group/bucket layout of `analysis.spike_events` normative.
12. Clarify packet versus importer provenance conformance.

## P2 - settle before external adoption / Iceberg work

13. Broaden the general analysis materialization criterion beyond layout alone.
14. Lift or formalize the registry-version hold.
15. Resolve packet-version versus Iceberg-snapshot semantics.
16. Publish a complete tagged spec bundle with registry/meta-schema/fixtures.

---

# 18. Regression tests implied by these changes

At minimum, add fixtures/tests for:

## Half-open intervals

- `[0, 1)` contains tick 0 and has duration 1.
- `[0, 1)` and `[1, 2)` do not overlap.
- a tick exactly equal to `stop_tick` is not contained.
- closed source `[4, 9]` imports as `[4, 10)`.
- closed source ending at `INT64_MAX` fails conversion.
- an already half-open source is unchanged.

## Identifiers

- maximum representable `int64` ID reads/writes exactly.
- an out-of-range source integer fails before cast.
- assigned IDs are stable across deterministic imports.
- `*_name` remains unique within its declared identity scope.
- carried IDs do not gain a second `*_name` identity.

## Extensions and canonicality

- `core.intervals` can pass core structural validation without loading an extension registry.
- a packet with a required `interval_kind` but missing extension registry fails packet binding validation.
- an extension row with no matching whole-key `core.intervals` row fails extension validation.
- a core interval with a required discriminator but no matching extension detail row fails packet binding validation.
- a valid core plus invalid extension retains `core=passed`, `extension=failed`, `packet=failed`.
- analysis resources can declare lineage to both core and extension resources.

## Zarr/resource digests

- the same Zarr member tree yields the same tree digest independent of directory enumeration order.
- changing a chunk changes the resource digest.
- adding/removing a member changes the resource digest.

## Commit

- a reader never observes a manifest referencing an unpublished resource.
- local atomic rename and object-store-style atomic catalog publication satisfy the same visible invariant.

## Analysis layout

- every `analysis.spike_events` row group contains one `time_bucket_tick` value only.

---

# 19. Final assessment

The architecture should continue in its current direction. In particular, the extension model should **not** be weakened merely to make core self-contained. A useful general data standard cannot prescribe the shape of every behavioral trial. The right abstraction is:

```text
core
  stable domain-general identities, time, instruments, arrays, units, spikes,
  intervals, provenance

extensions
  typed canonical domain-specific facts, including behavior/task trial tables

analysis
  reproducible derived products over the canonical resource set
```

The most important near-term work is therefore not another redesign. It is tightening the normative boundaries so that independent implementations agree on interval semantics, integer safety, extension resolution, packet conformance, resource digests, and commit visibility.

With those changes, the spec is a strong basis for continuing the proof-of-principle and for packaging additional sessions without baking one experiment's task schema into the format.
