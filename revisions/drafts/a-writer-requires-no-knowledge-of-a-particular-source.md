# A Writer Requires No Knowledge of a Particular Source

| | |
|---|---|
| **Status** | Draft |
| **Amends** | `05` §3 (a recipe declares a preference between two sources); `05` §3.4 (what an adapter declares); `07` §4 (what a build supplies an adapter) |
| **Depends on** | R63 §2.1 (an adapter declares `PRODUCES` before any I/O), R63 §2.2 (silence means the whole), R87 §2.2 (an adapter declares which recipe fields it states), R110 §3.4 (a choice about one packet's values belongs in its recipe) |
| **Profile** | all |

Normative, except §2, which is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

R63 §2.1 has a source adapter declare `PRODUCES` and R87 §2.2 has it declare `STATES`, both read
before any I/O. Everything else a build needs to know about an adapter is written down centrally
instead: which resource it wins when two sources offer one, whether it is handed an object store,
whether it may be sampled, and which recipe options it cannot be constructed without.

Measured across the writer package, **102 occurrences name a particular source kind**. Fifteen are
sound — `sources/__init__.py` maps the ten built-in kinds to their classes, which is core's registry
of its own adapters, and three modules name themselves — leaving **87 in the modules that decide
behaviour**, 51 of them in the one that drives a build.

This part moves each piece to whoever knows it: an adapter's own properties to the adapter, and an
arbitration between two of them to the recipe. How an adapter reaches a build at all is
`an-adapters-rows-cross-a-process-boundary`'s, and neither part depends on the other.

## 2. Background

Informative.

### 2.1 Four tables name a kind, and each holds one adapter's own property

`_SHARED_SOURCES` names the three kinds handed an object store. `SAMPLED` names the one kind a
`--sample` build may read partially. `REQUIRED_OPTIONS` names the two kinds that cannot be
constructed without a `zone`. Each is a fact about one adapter, recorded where that adapter is not.

`PRODUCES` and `STATES` are the same kind of fact and are declared on the class, which is what lets
a build read them with nothing open (R63 §2.1). Nothing distinguishes the four tables from those two
except where they were written.

### 2.2 A registered adapter cannot be given what a built-in is given

An adapter may already come from another distribution: `escapewheel.sources` is an entry-point group
and a build consults it after its own ten kinds. What it does with one is call
`build(root, session_id=…, **options)` — and nothing else. A built-in kind is constructed by name,
so `video` receives the reference clock, `sync` receives first samples, and three kinds receive an
object store; a registered kind receives none of them, because the branches that supply them test
for a literal name.

So a registered adapter can produce a resource and cannot read from an object store, which is the
case R80 makes ordinary.

### 2.3 A preference is a claim about a pair, and two of them exist

`PREFERRED` gives a contested resource to the source that knows most about it: the NWB knows a
probe's type and manufacturer where the sorter knows only the stream. That is a claim about a pair
of adapters over one dataset, not a property either one has, so no adapter can declare it.

Measured over all ten kinds: **35 resources are produced, 8 are contested by two or more adapters,
and 2 need arbitrating** once the shared ones and the recipe-supplied ones are set aside —
`core.probes`, between `nwb` and `sorter`, and `core.subjects`, between `nwb` and `session`. A
recipe cannot declare either; the table is the only place a preference can be written.

R110 §3.4 settled the same shape for an encoding, which is a fact about one packet's values and so
belongs in the recipe rather than the schema. A preference is a fact about one packet's sources.

## 3. Decision

### 3.1 An adapter declares what a build must supply it

An adapter **MUST** declare what a build supplies it beyond its root and the session identifier, as
a static declaration read with nothing open, in the shape `PRODUCES` and `STATES` already take. A
build **MUST** supply exactly what an adapter declares and **MUST NOT** decide it from the kind's
name.

A build **MUST** refuse a recipe naming an adapter that declares something the build cannot supply,
before any source is opened, which is where R63 §2.2 already refuses a recipe it cannot satisfy.

What may be declared is closed, because a build can only hand over what it holds: an object store
for the root, the session's reference clock, the first sample of each stream, and the recipe options
the adapter cannot be constructed without. A profile adding to that list amends this section.

### 3.2 A recipe declares a preference between two sources

A recipe **MAY** declare which source owns a resource that more than one of its sources produces, in
a table keyed by resource, each entry naming a source and the reason it knows more. A build
**MUST** apply a declared preference and **MUST NOT** hold a preference of its own for any resource
a recipe does not name.

Where two sources produce one resource and the recipe declares neither the preference nor an
explicit `owns`, a build **MUST** refuse the recipe naming both sources and the resource. That is
R63 §2.2's rule unchanged — a contradiction is refused before a byte is read — and it replaces a
built-in winner that no recipe could see.

## 4. What this does not change

- **No table, column, reference, rule or vocabulary changes, and no packet is rebuilt.** This binds
  where a build learns about a source, so what changes is who may add one.
- **`PRODUCES` and `STATES` are untouched.** R63 §2.1 and R87 §2.2 stand; §3.1 says the rest of what
  an adapter needs is declared the same way, not that those two change shape.

## 5. Consequence

`05` §3 gains a preference table, `05` §3.4 gains what an adapter declares, and `07` §4 gains what a
build supplies one.

The reference implementation loses four tables that name a kind — `_SHARED_SOURCES`, `SAMPLED`,
`REQUIRED_OPTIONS` and `PREFERRED` — and gains one declaration per adapter. Both packaged recipes
gain two lines, `core.probes` to `nwb` and `core.subjects` to `session`, which is what §2.3 measures
the whole preference table to be. Neither packet's rows change: the same source wins each contest,
declared where a reader of the recipe can see it.

What §3.1 fixes for a registered adapter is §2.2's asymmetry. One can produce a resource today and
never reach an object store, because the branches that supply one test for a literal kind; after
this it declares what it needs and a build either supplies it or refuses the recipe.
