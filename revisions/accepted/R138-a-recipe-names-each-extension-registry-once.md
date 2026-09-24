# A Recipe Names Each Extension Registry Once

| | |
|---|---|
| **Status** | **Accepted** 2026-09-24 |
| **Based on** | `06b11fb29285fe90890ae84054ca33807bf9abfb` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 05 §3.1 |
| **Depends on** | R127 §3.3; R130 §§3.3 and 3.4; R133 §§3.4 and 3.5 |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2 |

Section 3 is normative. Sections 1, 2, 5, and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

A session recipe's `[packet]` table admits `extensions`, a list naming the extension registries the
packet binds. Part 05 §3.1 incorporates the recipe schema and says its own prose owns what each
recipe member means, but it gives `extensions` no meaning, and Part 05 §3.5 does not refuse a list
naming one extension twice. A packet binds at most one registry per extension, so a build given two
such entries keeps one, and nothing says which or requires the build to report the other.

This revision says what an `extensions` entry names and has a build refuse a recipe listing one
extension in two entries, however each entry names it. Part 05 §3.1 gives no meaning to `id`,
`out`, `registry`, or `description` under `[packet]` either; that gap is independent of this
decision and outside it.

The change is structural because it extends Part 05 §3.1 in place. That section owns what each
recipe member means and already holds the parallel rule that a recipe lists each source kind once;
an appended section would give one member its meaning away from the section that owns every
member's.

### 1.1 Structural crosswalk

Part 05 §3.1 already carries the canonical anchor `ew-recipe-purpose`, so no anchor bootstrap is
needed. No section is added, moved, split, merged, or retired.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 05 §3.1, which lists `extensions` among the members `[packet]` admits and gives it no meaning | extend in place | same section | an entry names an extension registry the build binds, and a recipe listing one extension in two entries is refused | §§3.1, 3.2 |

## 2. Background

Section 2 is informative. Observations were read from the parts, `registry/recipe.schema.json`,
and `escapewheel-writer`. Probes were rerun at the recorded baseline in the writer's environment
against throwaway recipes and extension registry documents.

### 2.1 The recipe gives `extensions` no meaning

Part 05 §3.1's table lists `extensions` among the members `[packet]` admits, and no sentence of
Part 05 says what an entry names. The recipe schema declares `extensions` an array of strings
without `uniqueItems`, so a recipe listing one string twice satisfies it; the schema's `resources`
definition, which `owns` and `contributes` use, does carry `uniqueItems`. The member's schema
description calls each entry "a path or an installed registry's id", which no numbered part states.

Sources already have the rule extensions lack. Part 05 §3.1 has a recipe list each source kind in
one `source` entry and a build refuse a recipe that lists a kind twice, naming the kind.

### 2.2 A packet binds one registry per extension

Part 04 §8 keys a manifest's registry descriptors by registry ID, and Part 02 §9.1 makes an
extension registry's `registry_id` equal its `extension_id`, so a packet binds at most one registry
per extension. A manifest cannot carry two, because a repeated registry ID is a duplicate JSON
member, which Part 04 §10 reports as `packet.manifest.duplicate_member`. Two entries naming one
extension are therefore reduced to one inside the build, before any manifest exists, and no packet
check can see which was dropped.

### 2.3 The reference writer binds whichever entry comes last

The writer resolves and checks every `extensions` entry before its recipe check, and then keeps one
registry document per `extension_id`, a later document replacing an earlier one.

Two extension documents with `extension_id` `task` were written, at `registry_version` 0.1.0 and
0.2.0, the second admitting one more `enum` value. A recipe listing the first document's path twice,
and one listing the paths to both versions, each passed the writer's recipe check with no finding
about `extensions`, and both documents checked `valid`. Given the two versions directly, the writer
kept version 0.2.0 and raised and reported nothing. A packet built from the second recipe binds
whichever version its recipe lists last.

### 2.4 Alternatives

Adding `uniqueItems` to the schema alone catches a repeated string but neither a path and an
identifier naming one registry nor paths to two versions, the case that loses a version, and beside
§3.2 it would report one fault twice. Accepting two entries that resolve to identical bytes would
pass a mistake the recipe's author would want reported and gain nothing. Keeping the current rule
leaves the last entry to decide silently which version a packet binds.

### 2.5 Feasibility and overlap

The test compares `extension_id`, which only a resolved document carries. Part 05 §14.2 already
requires a build to obtain a complete Part 02 result for each registry before it checks a recipe,
and Part 05 §3.5's refusals read the resources of every loaded registry, so a build holds every
resolved document when it checks the recipe.

No open proposal or draft amends Part 05 §3.1. The other open drafts amend Part 05 §5.1 (non-finite
float values), §5.3 (the Zarr reader floor), and §11 (resource digests), and R135 amended
Part 05 §§1, 2, and 4–8.

## 3. Decision

Two subsections give a recipe's `extensions` member its meaning and refuse a recipe that lists one
extension in two entries. Both land in Part 05 §3.1, beside the rule that a recipe lists each source
kind once.

### 3.1 An `extensions` entry names a registry the packet binds

Each entry of the `[packet]` member `extensions` names one extension registry, and a build MUST bind
every registry so named under Part 09 §5.3. This specification does not fix how a build resolves an
entry to a registry document, whether it reads the entry as a path beside the recipe or as the
identifier of a registry an implementation has installed.

### 3.2 A build refuses an extension listed twice

A recipe MUST NOT list one extension in more than one `extensions` entry, and a build MUST refuse
one that does, naming the `extension_id` and each entry that resolves to it, before it opens any
source. Two entries list one extension when the registry documents they resolve to carry the same
`extension_id`, whether the entries repeat one string, pair a path with an identifier, or name two
versions of the registry.

## 5. Consequence

Packet bytes and packet conformance are unchanged, and no packet is rebuilt. A recipe whose
`extensions` entries resolve to one extension is refused until its author removes all but one, and
the author then chooses the version the packet binds, which the last entry chose before. No
tracked recipe lists an extension twice. The recipe schema keeps its `$id` and shape, so every
recipe it admitted still satisfies it. No accepted clause is superseded; R133 §3.5's refusal of a
repeated source kind gains a counterpart for extensions.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged; no concept's meaning changes. | None required. |
| logical prose and registry | Unchanged; the rule governs a recipe, which no logical schema declares, and reads `extension_id` without changing it. | None required. |
| physical profiles | Unchanged; a recipe is not a physical artifact. | None required. |
| packet manifest and JSON Schemas | Unchanged; a manifest already cannot bind one registry ID twice, and `registry/recipe.schema.json` keeps its `$id` and shape, since `uniqueItems` would catch only a repeated string. | None required. |
| validation and import | Part 05 §3.1 states what an `extensions` entry names and refuses a recipe listing one extension in two entries, beside its source-kind rule. Part 05 §3.5 is unchanged. | `evidence/R<N>.json` names `ew-recipe-purpose`. |
| extensions | Registry content unchanged; the rule reads each registry's `extension_id` and changes no declaration. | None required. |
| reader, writer, validator, adapters | The writer refuses at its recipe check a recipe whose `extensions` entries resolve to one `extension_id`, naming the `extension_id` and each entry. Given extension registry documents directly rather than through a recipe, it refuses two with one `extension_id` instead of keeping the later. The reader and validator are unchanged, since neither reads a recipe, and an adapter never sees `extensions`. | The writer tests below. |
| conformance fixtures and tests | Packet fixtures are unchanged, because a validator never reads a recipe and a manifest cannot carry the defect. Writer tests cover the cases in §6 and two registry documents with one `extension_id` given to the writer directly. | `escapewheel-writer` suite. |
| revision process and tooling | Ordinary ledger and evidence records; no revision check reads a recipe. | `ledger.py` and `evidence.py`. |
| generated publications and developer documentation | The combined specification regenerates. No heading changes, and no README describes the `extensions` member. | `verify.py`. |

## 6. Conformance and implementation evidence

Each clause is `applied` at Part 05 §3.1 by its canonical anchor, `ew-recipe-purpose`.

Writer tests distinguish the new rule from the current one:

- a recipe listing one extension document's path twice is refused, naming the `extension_id` and
  both entries, where the writer now builds;
- a recipe listing paths to two versions of one extension is refused, where the writer now binds
  the version listed last;
- a recipe listing a path and an installed identifier that resolve to one `extension_id` is
  refused; and
- each refusal comes before any source is opened.

The positive case is a recipe listing two extensions with distinct `extension_id` values, which
builds and binds both, as the writer does today and so confirms the corrected text rather than
distinguishing it. No packet fixture applies, since the defect cannot reach a manifest.
