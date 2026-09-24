# A Build Decides Ownership Only From the Recipe and Adapter Declarations

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `18c6ba66661674dd77022b4fe8b2c09a2e925b22` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 03 §11.5; Part 05 §§3.1, 3.3, 3.4, and 3.5; Part 07 §4; `registry/adapter.schema.json`; a new `registry/recipe.schema.json` |
| **Depends on** | [R63 §2.2](../accepted/R63-default-ownership-when-a-recipe-omits-owns.md#2-decision); [R98 §3.2](../accepted/R98-a-clock-declares-when-it-was-observing.md#3-decision); [R108 §§3.1 and 3.4](../accepted/R108-a-preference-discards-no-stated-fact.md#3-decision); [R115 §3.2](../accepted/R115-a-build-reaches-a-source-through-declarations.md#3-decision); [R119 §3.4](../accepted/R119-an-adapter-declares-the-options-it-accepts.md#3-decision) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5 |

Section 3 is normative. Sections 1, 2, and 4–6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

A session recipe names several sources, and a build decides which source supplies each resource
before it opens any of them.
[Part 05 §3.3](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-recipe-ownership)
puts every contested decision in the recipe, in a preference table keyed by resource, and forbids
a build to hold a preference of its own.
[Part 05 §3.4](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-source-declarations)
reads a source entry without `owns` as owning every resource its adapter can supply that no other
source owns.

The specification never spells the preference table, and the reference writer has no field for
one. The writer decides contested resources from a built-in table and from preferences that
extension packages register, and it turns six resources from a default ownership into a
contribution through a second built-in table. No recipe shows either table, so a recipe does not
record how its own packet was arbitrated, although
[Part 05 §3.2](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#32-the-recipe-is-the-provenance-record)
makes the recipe the provenance record. The recipe also has no schema, so an unknown block is
dropped without a diagnostic, and that is how a preference table written by hand disappears.

This revision spells the preference table and says what a preference decides. It makes the
resources an adapter supplies only part of a declared fact of the adapter, and redefines default
ownership over it. It publishes and incorporates a recipe schema and has a build refuse a recipe
that fails it. It lets a recipe list a source kind once, so a preference names exactly one source.

The change is structural because it replaces rules inside existing sections: Part 05 §3.3's
unspelled preference sentence, Part 05 §3.4's five declared facts and its default-ownership
sentence, Part 03 §11.5's key list, and the five class attributes Part 07 §4 names. Appended
sections would leave each of those contradicting its replacement.

### 1.1 Structural crosswalk

Commit `18c6ba6` added the canonical anchors `ew-recipe-purpose`, `ew-recipe-ownership`,
`ew-source-declarations`, and `ew-recipe-check` to Part 05 §§3.1, 3.3, 3.4, and 3.5,
`ew-adapter-declaration-document` to Part 03 §11.5, and `ew-reference-object-model` to Part 07
§4, and changed nothing else. No section is added, moved, or retired.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| [Part 05 §3.1](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-recipe-purpose), a recipe's contents listed abstractly | extend in place | same section | a recipe is a TOML document satisfying the incorporated recipe schema, listing each source kind once | §§3.4, 3.5 |
| [Part 05 §3.3](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-recipe-ownership), a preference in an unnamed table keyed by resource | replace in place | same section | the table is `[preference]`, and a preference makes its source the resource's owner | §3.1 |
| [Part 05 §3.4](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-source-declarations), five declared facts; a defaulted entry owns what no other source owns | replace in place | same section | a sixth fact names the resources an adapter supplies part of, and a defaulted entry contributes those | §§3.2, 3.3 |
| [Part 05 §3.5](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-recipe-check), the recipe refusals | extend in place | same section | adds refusals of a recipe failing the schema, a repeated kind, a preference naming an unlisted kind, and a declaration contributing what it does not produce | §§3.1, 3.2, 3.4, 3.5 |
| [Part 03 §11.5](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-adapter-declaration-document), the declaration document's seven keys | replace in place | same section | the document carries `contributes` as an eighth key | §3.2 |
| [Part 07 §4](../../escapewheel_poc_docs_v0.2/07_reference_implementation.md#ew-reference-object-model), five static class attributes | revise the informative list | same section | names a sixth, `CONTRIBUTES` | §3.2 |

## 2. Background

Section 2 is informative. Every observation was reproduced at `8b0f067`, and none changes at the
recorded baseline, which adds only anchors. Probes loaded throwaway recipes with `Recipe.load` and
checked them with `Recipe.check` against `registry/logical_schemas.json`, in the writer's
environment and, where stated, in the AIND package's.

### 2.1 A recipe cannot declare a preference

`Recipe.load` reads `packet`, `session`, `subject`, `overrides`, `encoding`, `clock`, `source`,
`materialize`, and `commit`, and nothing else. A recipe listing defaulted `sorter` and `nwb`
sources with `[preference."core.probes"] source = "sorter"` and an unrelated `[bogus]` block loads
and checks with no diagnostic for either table, and `nwb` still owns `core.probes`. R115 §3.2, the
source of Part 05 §3.3's preference rule, is recorded in the ledger as applied, but the writer
never implemented it.

### 2.2 The writer holds the preferences

`escapewheel_writer.recipe` declares `PREFERRED = {"core.probes": "nwb"}` and an entry-point group,
`escapewheel.preferences`, whose registrations `preferences()` merges in. `escapewheel-aind`
registers `{"core.subjects": "session"}` there. The writer's `test_arbitration.py` and
`test_recipe.py` and AIND's `test_declaration.py` assert these tables' contents.

The two tables are applied inconsistently. `_resolve_ownership`, which fills in default ownership,
reads only the writer's own table. The discarded-row report, the discarded-fact refusal, and the
`escapewheel init` scaffolder read the merged set. In the AIND environment, a recipe listing
defaulted `session` and `nwb` sources is refused with "core.subjects is owned by 2 sources (nwb,
session); use contributes", although AIND registers a preference for that resource.

### 2.3 The writer decides which resources are shared

`recipe.SHARED` names six resources, and `_resolve_ownership` makes a defaulted source contribute
to each one its adapter produces rather than own it, which Part 05 §3.4's default does not allow.
Across the seven built-in adapters and AIND's three, every adapter producing one of them supplies
only its own part:

| resource | adapters producing it |
|---|---|
| `core.clocks` | `nwb`, `sorter`, `sync`, `aind_nwb`, `session` |
| `core.clock_anchors` | `nwb`, `sync`, `aind_nwb` |
| `core.clock_observation_intervals` | `sorter`, `sync`, `session` |
| `core.array_assets`, `core.array_dimensions` | `lfp`, `nwb`, `waveforms`, `aind_nwb` |
| `core.devices` | `harp`, `nwb`, `openephys`, `aind_nwb` |

Each supplies its own streams' clocks and anchors, or its own arrays and devices. Sharing is
therefore a property of what an adapter supplies, which is the kind of fact Part 05 §3.4 already
has adapters declare.
[R98 §3.2](../accepted/R98-a-clock-declares-when-it-was-observing.md#3-decision) added two of these
resources to `recipe.SHARED` by name. Its normative rule, that a resource several sources supply
is declared `contributes`, is in Part 05 §3.3 and does not depend on the table.

### 2.4 The recipe has no schema, and a source kind can repeat

No recipe schema exists. Part 05 §3 names `owns`, `contributes`, `[subject]`, `[overrides]`,
`[encoding]`, and `command`, but no part names `[packet]`, `[[source]]`, `[[clock]]`,
`[[materialize]]`, `[commit]`, or TOML; the writer's README is the only complete description.
`Recipe.load` refuses only a file that is not TOML or that has no `[packet].id`. An unknown key
inside a source entry is read as an option and refused against the adapter's declaration under
R119, and an unknown top-level block is dropped.

Ownership is keyed by source kind throughout the writer, and nothing refuses a recipe listing one
kind twice. Two `[[source]] kind = "harp"` entries with different roots load and check, and no
report can tell them apart.

### 2.5 Alternatives

Keeping the writer's tables contradicts Part 05 §3.3 and leaves the recipe silent about its own
arbitration. An adapter cannot declare a preference, because it cannot know which other adapters a
recipe lists. Making every recipe list `contributes` for the six shared resources would make each
multi-source recipe spell the same list and would refuse every current recipe that relies on the
default. Requiring explicit empty sets, as the project review suggested, adds nothing: an omitted
`owns` already means the whole, and an absent preference table means no preference. A per-source
name would let a recipe read two roots of one kind, which no current adapter or recipe needs, at
the cost of changing every ownership key and report.

### 2.6 Feasibility and overlap

No other proposal or draft is open. A following adapter-contract decision will make the
declaration document's keys required and incorporate its schema, so it depends on §3.2's key.

The writer resolves a declaration through one function, `declared`, whether it comes from a class
or a document, so a sixth fact reaches every reader of a declaration through the existing path. A
JSON Schema can validate a decoded TOML document where it leaves fact values untyped: TOML dates
and times decode to values JSON Schema has no type for, and the registry types a fact when Part 05
§3.6 normalizes it. The writer's 568 tests and the AIND package's 66 pass at `8b0f067`.

## 3. Decision

Five subsections spell and bound the preference table, add the declared fact that a resource is
supplied in part, redefine default ownership over it, fix the recipe's shape, and make a source
kind identify one source.

### 3.1 Preferences

A recipe declares each preference as an entry of its top-level `preference` table, keyed by the
resource's dotted identifier. The entry carries `source`, the kind of the source the recipe
prefers, and `reason`, a non-empty statement of why that source knows more, and nothing else. A
preferred source owns the resource: a build keeps its rows and discards every other source's rows
for that resource.

A build MUST apply each declared preference, and MUST NOT hold a preference of its own or accept
one from any artifact other than the recipe. A build MUST refuse a preference whose `source` names
a kind the recipe does not list, naming the resource and the kind.

### 3.2 Partly supplied resources

An adapter declares, as a sixth static fact beside those Part 05 §3.4 lists, the resources whose
rows it supplies only in part, such as the clocks of its own streams. Each such resource is also
one the adapter declares it can supply. The declaration document carries the set under
`contributes`, an array of dotted resource identifiers, and a document without it declares none.

A build MUST refuse a declaration whose `contributes` names a resource its `produces` does not,
naming the adapter and the resource.

### 3.3 Default ownership

A build MUST read a source entry that declares no `owns` as:

- contributing every resource its adapter declares under §3.2; and
- owning every other resource its adapter declares it can supply, unless another source owns it or
  a preference names another source for it.

A build MUST refuse a recipe in which two such entries are left owning one resource, naming both
sources and the resource. An entry's own `owns` and `contributes` replace this reading for that
entry.

### 3.4 The recipe document

A recipe is a TOML 1.0 document whose decoded form satisfies the recipe schema published as
`registry/recipe.schema.json`, which Part 05 §3.1 incorporates. The schema admits exactly these
top-level members:

| member | form | constraint |
|---|---|---|
| `packet` | table | requires `id`; admits `out`, `registry`, `extensions`, `description`, and `in_process` |
| `session`, `subject` | table | keys are field names; values are untyped |
| `overrides` | table | keys are `block.field` names; each value a non-empty string |
| `encoding` | table | keys are `resource.column` names; each entry carries exactly `encoding`, one of `delta`, `plain`, or `dictionary`, and a non-empty `reason` |
| `clock` | array of tables | each requires `clock_id`, `name`, `tick_rate_num`, and `origin`, and admits `tick_rate_den` and `parent_clock_id` |
| `source` | array of tables | each requires `kind`; `owns` and `contributes` are arrays of dotted resource identifiers, `storage_options` a table, `in_process` a boolean, and `delivery` a table whose `command` is an array of strings; every other key is an option |
| `preference` | table | keys are dotted resource identifiers; each entry is §3.1's |
| `materialize` | array of tables | each requires `resource`; every other key is a parameter |
| `commit` | table | members are a build's own limits |

A build MUST refuse a recipe that is not TOML 1.0 or whose decoded form fails the schema, naming
where it fails, before it opens any source. An omitted member keeps the meaning this part gives
its absence.

### 3.5 Source identity

A recipe MUST NOT list a source kind in more than one `source` entry, and a build MUST refuse one
that does, naming the kind. A preference, an ownership refusal, and a build's reports name a source
by its kind.

## 4. What this does not change

A preference still names only a resource more than one listed source produces, and still refuses
to discard a value another source stated, under Part 05 §§3.3 and 3.4. A recipe still narrows a
source by declaring `owns` or `contributes`, and an option still travels as a key of its source
entry, checked against the adapter's `needs` and `accepts`.

## 5. Consequence

Packet bytes are unchanged, and a rebuild from a corrected recipe produces the same packet. A
recipe that relied on a built-in winner is refused, naming both sources, until it declares the
preference: at the baseline that is `core.probes` where `nwb` or `aind_nwb` is listed beside
`sorter`, and `core.subjects` where `session` is listed beside either NWB adapter. A recipe with an
unknown top-level member, a string `command`, or a repeated kind is refused. No recipe is tracked in
the repository; the local development recipes are updated by hand. A delivered adapter's document
without `contributes` owns by default what the writer's table made it contribute, so a recipe
listing it beside another producer is refused until the document is regenerated or the recipe
declares `contributes`.

No accepted clause is superseded. R63 §2.2's default narrows to exclude declared partly supplied
resources, and its remark that the writer's two tables decide between defaulted entries is
replaced by §§3.1 and 3.3. R98 §3.2's membership of `recipe.SHARED` becomes the adapters'
declarations; its rule stands. R115 §3.2 gains the table's spelling. The ledger notes that name
`recipe.SHARED` or `recipe.PREFERRED`, on R98 §§2.2 and 3.2 and R108 §§2.2, 2.3, and 3.4, are
rewritten.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. No scientific meaning changes. | None required. |
| logical prose and registry | Unchanged. Arbitration concerns a build's inputs, not a packet's resources. | None required. |
| physical profiles | Part 03 §11.5 lists `contributes` and refuses one naming a resource outside `produces`; `registry/adapter.schema.json` gains `contributes` as an optional array of dotted resource identifiers. | `evidence/R<N>.json` names the anchor; `registry/check.py` validates the example document. |
| packet manifest and JSON Schemas | The manifest schema is unchanged. `registry/recipe.schema.json` is added, vendored into the writer, checked by `registry/check.py`, and incorporated by Part 05 §3.1. | The vendoring check and the writer's schema tests. |
| validation and import | Part 05 §3.1 incorporates the schema and admits one entry per kind; §3.3 spells the preference table and what it decides; §3.4 adds the sixth fact and redefines default ownership; §3.5 adds the four refusals. | The writer tests below. |
| extensions | Registry content unchanged. AIND's adapters declare their partly supplied resources, and its `preferences` module and `escapewheel.preferences` entry point are removed. | The AIND suite. |
| reader, writer, validator, adapters | The reader and validator are unchanged, since neither reads a recipe. The writer validates the schema on load, reads `[preference]`, and resolves default ownership, the discarded-row report, the discarded-fact refusal, and the scaffolder from the recipe and the declarations. It removes `PREFERRED`, `SHARED`, `preferences()`, `arbitrated()`, and the entry-point group. Each built-in adapter declares `CONTRIBUTES`, and `escapewheel declare` writes it. For a contested resource, the scaffolder writes a commented-out preference naming a candidate and assigns the resource to no source, so the draft is refused until its author chooses. | Writer and AIND tests below. |
| conformance fixtures and tests | Packet fixtures are unchanged, because a validator never sees a recipe. Writer tests cover a declared preference deciding a contested default, a contested default refused without one, a preference naming an unlisted kind, a preference without a reason, an unknown top-level member, a repeated kind, a declared partly supplied resource contributed by default, and a declaration contributing what it does not produce. The tests asserting the built-in tables are rewritten against declarations, and the AIND suite covers a `core.subjects` preference declared in a recipe. | `escapewheel-writer` and `escapewheel-aind` suites. |
| revision process and tooling | The five ledger notes above are rewritten; otherwise the ordinary revision and evidence records. | `ledger.py` and `evidence.py`. |
| generated publications and developer documentation | The combined specification and heading index regenerate. The writer README documents the recipe schema and the preference table, and `registry/README.md` lists the recipe schema. | `verify.py`. |

## 6. Conformance and implementation evidence

Each clause is `applied`: §§3.1 and 3.3 at Part 05 §§3.3 and 3.4, §3.2 at Part 05 §3.4 and Part 03
§11.5, §3.4 at Part 05 §3.1 and §3.5, and §3.5 at Part 05 §3.1, each by its canonical anchor.

The negative cases distinguish the new rule from the current one:

- a recipe listing defaulted `nwb` and `sorter` without a preference is refused naming
  `core.probes`, where the current writer gives it to `nwb`;
- a `[preference]` entry naming a kind the recipe does not list is refused, where it is now
  ignored;
- a recipe with an unknown top-level member or a repeated kind is refused, where both now load;
- a declaration whose `contributes` names a resource outside its `produces` is refused; and
- an adapter declaring no partly supplied resource owns by default what the writer's table now
  makes it contribute.

The positive cases are a declared preference that decides `core.subjects` for `session` in the AIND
environment, which the current writer refuses, and a defaulted recipe of clock-bearing sources that
contributes its clocks through their declarations.
