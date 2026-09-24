# A build decides ownership only from the recipe and adapter declarations

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-23 |
| **Based on** | `8b0f067fad65a120eec6f53bac9ff1d1475de6a2` |
| **Decision domain** | specification |
| **Affects** | Part 05 §§3.1, 3.3, 3.4, and 3.5; Part 03 §11.5; Part 07 §4; `registry/adapter.schema.json`; a new recipe schema; the reference writer's recipe loader, ownership resolution, scaffolder, and build reports; the AIND extension package's preferences |

## 1. Problem

A session recipe names several sources, and a build decides which source supplies each resource
before it opens any of them.
[Part 05 §3.3](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#3-the-session-recipe)
puts every contested decision in the recipe: a preference "is declared in the recipe, in a table
keyed by resource", and a build is forbidden to hold a preference of its own. Part 05 §3.4 reads a source entry that declares no `owns` as owning every resource
its adapter can supply that no other source owns.

The reference writer decides ownership from its own code instead. A recipe cannot declare a
preference, because the loader has no field for one and ignores the table. The writer holds a
built-in preference table, loads more from an entry-point group that the AIND package registers
with, and holds a table of shared resources that turns a defaulted source's ownership into a
contribution. None of these tables appears in any recipe, so a recipe does not record how its own
packet was arbitrated, although Part 05 §3.2 makes the recipe the provenance record.

The recipe itself has no schema. Its blocks are named piecemeal across Part 05 §3 and spelled out
only in the writer's README, and a block the loader does not know is silently dropped. That is how
a preference table disappears without a diagnostic.

## 2. Evidence

All observations below were reproduced at the recorded baseline. Probes loaded throwaway recipes
with `Recipe.load` and checked them with `Recipe.check` against `registry/logical_schemas.json`,
in the writer's environment and, where stated, in the AIND package's.

### 2.1 A recipe cannot declare a preference

`Recipe.load` reads `packet`, `session`, `subject`, `overrides`, `encoding`, `clock`, `source`,
`materialize`, and `commit`, and nothing else. A recipe listing defaulted `sorter` and `nwb`
sources with `[preference."core.probes"] source = "sorter"` and an unrelated `[bogus]` block loads
and checks with no diagnostic for either table, and `nwb` still owns `core.probes`.

[R115 §3.2](../accepted/R115-a-build-reaches-a-source-through-declarations.md#3-decision), from
which Part 05 §3.3's preference rule comes, is recorded in the ledger as applied, but only the
prose was ever changed. The specification also never spells the table's key.

### 2.2 The writer holds the preferences

`escapewheel_writer.recipe` declares `PREFERRED = {"core.probes": "nwb"}` and an entry-point group,
`escapewheel.preferences`, whose registrations `preferences()` merges in. `escapewheel-aind`
registers `PREFERRED = {"core.subjects": "session"}` there. The writer's `test_arbitration.py` and
`test_recipe.py` and AIND's `test_declaration.py` assert these tables' contents.

The two tables are applied inconsistently. `_resolve_ownership`, which fills in default ownership,
reads only the writer's `PREFERRED`. The build's discarded-row report, its discarded-fact refusal,
and the `escapewheel init` scaffolder read the merged `preferences()`. In the AIND environment, a
recipe listing defaulted `session` and `nwb` sources is refused with "core.subjects is owned by 2
sources (nwb, session); use contributes", although AIND registers a preference for exactly that
resource.

### 2.3 The writer decides which resources are shared

`recipe.SHARED` names six resources: `core.clocks`, `core.clock_anchors`,
`core.clock_observation_intervals`, `core.array_assets`, `core.array_dimensions`, and
`core.devices`. `_resolve_ownership` makes a defaulted source contribute to each of them that its
adapter produces, rather than own it, which Part 05 §3.4's default does not allow.

Across the seven built-in adapters and AIND's three, every adapter producing one of these resources
supplies only its own part of it:

| resource | adapters producing it |
|---|---|
| `core.clocks` | `nwb`, `sorter`, `sync`, `aind_nwb`, `session` |
| `core.clock_anchors` | `nwb`, `sync`, `aind_nwb` |
| `core.clock_observation_intervals` | `sorter`, `sync`, `session` |
| `core.array_assets`, `core.array_dimensions` | `lfp`, `nwb`, `waveforms`, `aind_nwb` |
| `core.devices` | `harp`, `nwb`, `openephys`, `aind_nwb` |

Each adapter supplies its own streams' clocks, its own anchors, or its own arrays and devices.
Sharing is therefore a property of what an adapter supplies, which is the kind of fact Part 05
§3.4 already has adapters declare.
[R98 §3.2](../accepted/R98-a-clock-declares-when-it-was-observing.md#3-decision) added two of
these resources to `recipe.SHARED` by name; its normative rule, that such a resource is declared
`contributes`, is in Part 05 §3.3 and does not depend on the table.

### 2.4 The recipe has no schema, and a source kind can repeat

No recipe schema exists in the repository. Part 05 §3.1 lists the recipe's contents abstractly,
and the parts name `owns`, `contributes`, `[subject]`, `[overrides]`, `[encoding]`, and `command`,
but no part names `[packet]`, `[[source]]`, `[[clock]]`, `[[materialize]]`, `[commit]`, or TOML.
`Recipe.load` refuses only a file that is not TOML or that has no `[packet].id`, and `Recipe.check`
tests everything else in Python. An unknown key inside a source entry is read as an option and
refused against the adapter's declaration. An unknown top-level block is dropped.

Ownership is keyed by source kind throughout the writer, and nothing refuses a recipe listing one
kind twice. Two `[[source]] kind = "harp"` entries with different roots load and check, and no
report can tell them apart.

### 2.5 Baseline, overlap, and feasibility

No other proposal or draft is open. The provenance of the affected rules is:

- [R63 §2.2](../accepted/R63-default-ownership-when-a-recipe-omits-owns.md#2-decision): default
  ownership, which also records moving `PREFERRED` and `SHARED` out of the scaffolder;
- R98 §3.2 and §3.3;
- [R108 §§3.1–3.4](../accepted/R108-a-preference-discards-no-stated-fact.md#3-decision): a
  preference discards no stated fact and names only a contested resource; and
- R115 §3.2.

Five ledger notes, on R98 §§2.2 and 3.2 and R108 §§2.2, 2.3, and 3.4, name the writer's tables.
[R119](../accepted/R119-an-adapter-declares-the-options-it-accepts.md) fixed the declaration keys
this proposal extends. A following adapter-contract proposal will make the declaration keys
required and incorporate the adapter schema, so it should take up the key this proposal adds.

The writer's 568 tests and the AIND package's 66 pass at the baseline. The writer already resolves
a declaration through one function, `declared`, whether it comes from a class or a document, so a
sixth declared fact reaches every consumer through the existing path.

## 3. Desired outcome and constraints

A reader of a recipe and of its sources' adapter declarations can derive every ownership decision
the build makes, and a build refuses a recipe it cannot read completely.

The resolution preserves:

- R63's reading of silence: a source entry without `owns` takes the whole of what its adapter
  supplies that nothing else claims;
- the refusal of two defaulted sources left owning one resource, and R108's refusal of a preference
  that discards a stated fact;
- the adapter declaration as a static fact, readable without opening a source and, for an adapter
  a build cannot import, from a document; and
- a writer that requires no code of an extension.

## 4. Options and tradeoffs

### 4.1 Where a preference lives

**Keep the writer's tables.** This contradicts Part 05 §3.3 and leaves the recipe silent about how
its packet was arbitrated.

**Let an adapter declare what it prefers to own.** An adapter cannot know which other adapters a
recipe lists, so it cannot state a preference between two of them.

**Declare each preference in the recipe.** A `[preference."<resource>"]` entry names the winning
source and the reason it knows more. This is Part 05 §3.3's existing rule, and this proposal
prefers it. It removes `PREFERRED`, the `escapewheel.preferences` group, and AIND's registration,
and the scaffolder drafts preference entries for contested resources.

### 4.2 Which resources a defaulted source contributes

**Keep `SHARED` in the writer.** It is a policy no recipe shows, and it conflicts with Part 05
§3.4's default.

**Make every recipe list `contributes`.** Every recipe with two clock-bearing sources would then
spell the same six resources, and every current recipe relying on the default would be refused.

**Have an adapter declare the resources it only ever supplies part of.** A defaulted source entry
contributes to those and owns the rest, and an explicit `owns` or `contributes` in the recipe still
narrows it. The declaration document carries the fact under `contributes`, the recipe's term for
it. This proposal prefers it: §2.3 shows sharing is a property of the adapter, and the fact
becomes static and published beside the adapter's other declarations. A document without the key
declares no shared resource, so a delivered adapter written before it was added owns by default
what it previously contributed, and a recipe listing it beside another producer is refused until
its document is regenerated or the recipe says `contributes`.

### 4.3 How the recipe's shape is fixed

**Keep ad hoc parsing.** An unknown block stays invisible, which is how §2.1's preference table was
lost.

**Publish a recipe schema that Part 05 §3 incorporates.** A JSON Schema validates the decoded TOML
document before any source is opened. Top-level blocks are closed, so an unknown block is refused.
A source entry stays open, because an option is a key of the entry itself and R119's checks
against the adapter's declaration already refuse an unknown one. Fact blocks leave their values
untyped, because the registry types them when they are normalized under Part 05 §3.6 and TOML
dates have no JSON Schema type. This proposal prefers it.

**Require explicit empty values for sets whose omission could be ambiguous.** The project review
proposed this for `owns`, `contributes`, and preferences. Omission of `owns` already has R63's
meaning, and an absent preference table means the recipe declares no preference, so neither
omission is ambiguous. This proposal does not require them.

### 4.4 How a preference names a source

**By kind, with a kind listed at most once.** Ownership, reports, and preferences already name a
source by its kind. Refusing a repeated kind removes the ambiguity §2.4 shows. This proposal
prefers it.

**By a new per-source name.** A name would let a recipe read two roots of one kind, which no
current adapter or recipe needs. It would change every report and ownership key, so it is left for
a decision that has a use for it.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. No scientific meaning changes. |
| logical prose, registry meta-schema, registry declarations, and declarative rules | Unchanged. Ownership arbitration concerns a build's inputs, not a packet's resources. |
| physical profiles | Part 03 §11.5 lists `contributes` among the declaration document's keys, and `registry/adapter.schema.json` gains it as an optional array of resource IDs. Part 07 §4, which is informative, names the sixth class attribute beside the five it lists. |
| packet manifest and incorporated JSON Schemas | Manifest unchanged. A new recipe schema, published under `registry/` and vendored into the writer, is incorporated by Part 05 §3.1. |
| validation and import | Part 05 §3.1 incorporates the schema and requires a kind to appear once. §3.3 spells the preference table. §3.4 adds the sixth declared fact and reads a defaulted entry as contributing what its adapter declares shared. §3.5 refuses a recipe failing the schema. |
| extension registries | Unchanged. |
| reader and validator | Unchanged. Neither reads a recipe. |
| writer | The loader validates the schema and reads `[preference]`. `_resolve_ownership`, the discarded-row report, the discarded-fact refusal, and the scaffolder read preferences from the recipe and shared resources from declarations. `PREFERRED`, `SHARED`, `preferences()`, and the entry-point group are removed. Built-in adapters declare their shared resources, and `escapewheel declare` writes them. |
| adapters and code generation | Each built-in and AIND adapter declares its shared resources. AIND's `preferences` module and its entry point are removed. Third-party declaration documents without `contributes` own by default what they supply, as §4.2 states. |
| existing packets and migration | Packet bytes are unchanged. A recipe relying on a built-in preference is refused, naming both sources, until it declares the preference: today that means a recipe listing `nwb` or `aind_nwb` beside `sorter` for `core.probes`, or `session` beside either NWB adapter for `core.subjects`. A recipe with an unknown block or a repeated kind is refused. No recipe is tracked in the repository, so the local development recipes are updated by hand. |
| conformance fixtures and tests | Packet fixtures are unchanged, since a validator never sees a recipe. Writer tests cover a declared preference that decides a contested resource, a contested default refused without one, a preference table without a reason refused, an unknown block refused, a repeated kind refused, and a declared shared resource contributed by default. The tests asserting the built-in tables are removed, and the AIND suite covers a `core.subjects` preference declared in a recipe. |
| revision lifecycle, ledger, evidence, and process tooling | The five ledger notes that name `recipe.SHARED` or `recipe.PREFERRED` are rewritten. Whether R63 §2.2 or R98 §3.2 is partly superseded is for the draft's appraisal; their normative rules stand. |
| generated publications and developer documentation | The combined specification regenerates. The writer README documents the recipe schema and the preference table and drops the sentence that an adapter never writes, which the adapter-contract decision replaces. The AIND README drops its preference entry point. |

## 6. Resolved direction

1. A recipe declares each preference in a `[preference."<resource>"]` table naming the preferred
   source's kind and a non-empty reason. A build holds no preference of its own, so the writer's
   `PREFERRED`, the `escapewheel.preferences` entry-point group, and AIND's registration are
   removed.
2. An adapter declares, as a sixth static fact, the resources it only ever supplies part of, under
   the declaration-document key `contributes`. A source entry without `owns` contributes to those
   resources and owns the rest of what its adapter supplies that no other source owns. The
   writer's `SHARED` table is removed.
3. A recipe schema is published and incorporated by Part 05 §3.1. A build refuses a recipe that
   fails it before opening any source. Top-level blocks are closed, source entries are open for
   options, fact values are untyped, and an omitted set keeps its current meaning.
4. A recipe lists a source kind at most once, and a preference names a source by its kind.

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
