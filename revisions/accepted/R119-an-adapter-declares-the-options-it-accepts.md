# An Adapter Declares the Options It Accepts

| | |
|---|---|
| **Status** | **Accepted** 2026-09-15 |
| **Amends** | Part 03 §11.2 (an adapter declares the options it can run without, and a build refuses an option no declaration names); Part 03 §11.5 (the declaration document carries `accepts`); Part 05 §3.4 (an adapter declares five facts rather than four); Part 05 §3.5 (what a build refuses a recipe for); Part 07 §4 (the reference spelling) |
| **Depends on** | R115 §3.1 (an adapter declares what a build supplies it, resolved against terms then options), R115 §3.12 (the declaration document and what a build refuses it for), R63 §2.1 (an adapter declares what it can supply, statically and as a class attribute), R87 §2.2 (the same discipline applied to the facts a source states) |
| **Profile** | all |

Normative, except §2, which is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

An adapter declares every value a build supplies it, and a build resolves each declared name against
Part 03 §11.2's closed vocabulary of terms first and the recipe's options second, refusing a recipe
where a name resolves to neither (R115 §3.1). Declaring a name is therefore how an adapter asks for
it — and, because the refusal fires on a name the recipe does not set, declaring one is also how an
adapter makes that name **mandatory**.

Most options are not mandatory: each carries a default a recipe is entitled to leave alone, and §2.2
counts them across the ten adapters the reference build ships. None can be declared without making a
legitimate recipe illegal, so none is declared, and nothing checks any of them. This revision adds
the half of the declaration that says *may* rather than *must*.

## 2. Background

### 2.1 Declaring an option makes a recipe carry it

Part 03 §11.2 has a build refuse a recipe where a declared name resolves to neither a term nor an
option this entry sets, and Part 05 §3.5 lists the same refusal as a required source option that is
not set. Both are correct for a value the adapter cannot be constructed without. For a value it can,
they convert a default into an obligation: the adapter would run perfectly well without the option,
and the recipe that omits it is refused before any source is opened.

`interval_kind` is the case R115 §3.1 itself reaches for, citing it as an option that reached the
NWB adapter "only because it declares it", against a measurement of six declared names of which two
were options. The shipped declaration has never been that. From the commit that introduced `NEEDS`
onward it has read five names — `root`, `session_id`, `reference_clock`, `units`, `zone` — of which
`zone` is the only option, and `interval_kind` is not among them. Both packaged recipes set
`interval_kind` anyway, so declaring it would refuse nothing today; what stops it being declared is
the recipe that legitimately omits it, since the adapter's default of no interval kind is the right
answer for a session carrying no intervals.

### 2.2 Twenty-eight options cross unchecked

Counted over the ten adapters by inspecting each constructor against its own declaration: `nwb`
takes 7 options beyond what it declares, `waveforms` 6, `sorter` 5, `sync` 5, `lfp` 4, `tables` 3,
`video` 2, and `harp`, `openephys` and `session` none. Four of those 32 are not the recipe's to set
— `store` on three adapters, an injection point the tests use, and `first_samples`, which is a term
— leaving **28**. Two of the ten adapters declare an option at all, `nwb` and `session`, and both
declare the same one, `zone`.

The two committed recipes set **10 distinct option names** between them: `attachments`, `command`,
`emit_clock`, `experiment`, `interval_kind`, `parent_clock_id`, `sd`, `signals`, `tables` and
`zone`. Nine of the ten are checked by nothing.

### 2.3 A misspelled option fails inside the adapter

Both construction paths pass the recipe's options through as keyword arguments — the in-process one
and the one serving a delivery — so a name the adapter does not take is whatever its constructor
makes of it:

    TypeError: WaveformSource.__init__() got an unexpected keyword argument 'sd_asste_id'.
    Did you mean 'sd_asset_id'?

That is the failure R115 §3.1 declares options in order to replace. It arrives after the build has
started rather than before any source is opened, it names a class rather than the recipe entry that
is wrong, and out of process it reaches the build as a subprocess that exited. All ten adapters
refuse an unknown keyword rather than absorbing one — none takes `**kwargs` — so a misspelling is
always caught. What is wrong is where: by the adapter once the build is running, rather than by the
build before it starts.

### 2.4 A build supplies a name no declaration carries

`--sample` narrows a build to the first spikes of each stream, and it reaches the adapter as an
option: the recipe layer adds `sample` to a sampled source's options, `sorter` is the one kind it
applies to, and `SorterSource` takes a `sample` argument. `sample` is in no adapter's declaration
and is not one of Part 03 §11.2's terms. So the reference build supplies a name the adapter never
declared, which is what Part 03 §11.2's "a build MUST supply exactly what the adapter declares"
forbids — and a third-party sorter adapter written to the declaration alone would meet an argument
it has no reason to accept.

### 2.5 Two adapters are waiting on an option that cannot be declared

`waveforms` matches an array row to a unit by the pair `(device_name, ks_unit_id)`, and
`ks_unit_id` is one exporter's column rather than base NWB. Measured on both packaged sessions, no
base column replaces it: the `Units` table's own `id` is `arange(n)`, the row number, differing from
`ks_unit_id` in **6,775 of 6,781** and **4,138 of 4,505** rows because a sorter numbers from zero
within each probe; `unit_name`, where NeuroConv writes a sorter's unit ids, holds a UUID in both
files. The probe half of the pair *is* derivable — each unit's ragged `electrodes` region spans
exactly one `group_name`, equal to `device_name`, in 6,781 of 6,781 and 4,505 of 4,505 units — so
what the adapter needs is one option naming the label column, defaulting to `unit_name`. `lfp` needs
the same shape for the series name it recovers a probe from, which NWB does not constrain. Both
default, so neither can be declared, so each would arrive unchecked beside the other 28.

## 3. Decision

### 3.1 `accepts` names an option an adapter can run without

An adapter **MUST** declare in `accepts` every option it reads and can be constructed without, and
**MUST** declare in `needs` every value it cannot. An adapter **MUST NOT** name one option in both,
and **MUST NOT** name in `accepts` a term of Part 03 §11.2's vocabulary or a term a protocol
supplies: a term is filled by the build rather than offered by the recipe, so naming one as optional
claims a choice the recipe does not have.

A build **MUST** supply an option the recipe sets and the adapter names in either list, and **MUST
NOT** require a recipe to set one named in `accepts`. An adapter **MUST** apply its own default
where the recipe sets no value, so what an omitted option means is the adapter's statement rather
than a value the build invents.

### 3.2 A build refuses an option no declaration names

A build **MUST** refuse a recipe whose source entry sets an option the adapter names in neither
`needs` nor `accepts`, naming the source and the option, before any source is opened — where
Part 05 §3.5 already refuses a declared name that resolves to nothing. This is the refusal
R115 §3.1 argues for and could not deliver: an option a recipe sets and an adapter ignores is a
statement about the packet that does not reach it, and the author's next evidence is its absence
from the output.

A build **MUST NOT** refuse a recipe that omits an option named in `accepts`, and **MUST NOT** treat
such an option's absence as a term it cannot fill.

### 3.3 A build declares the options it injects

A build **MUST NOT** supply an option the adapter names in neither list, including one the build
adds itself rather than reading from the recipe. §3.1 already puts such an option in the adapter's
`accepts`, `sample` being one an adapter reads and can run without, so what this adds is the build's
half: a build **MUST NOT** apply a facility of its own to an adapter that does not name the option
carrying it. Injecting silently is a recipe setting an option nothing reads, with the build as the
author of it.

### 3.4 The declaration document carries `accepts` beside `needs`

The document Part 03 §11.5 specifies **MUST** carry `accepts` where the adapter names any, as an
array of option names in the same form as `needs`, and a build **MUST** read a document without it
as an adapter accepting no option beyond what it needs. Its schema is published as
`registry/adapter.schema.json`, which closes the document to additional properties, so the property
is added there rather than tolerated.

A build **MUST** refuse a declaration whose `accepts` names a term, names an option its `needs` also
names, or is not an array of names, on the terms Part 03 §11.5 already refuses a declaration — none
of which needs the adapter opened or imported. An implementation shipping both a document and an
importable declaration **MUST** generate the one from the other, as Part 03 §11.5 requires of every
other key.

The reference spelling is `ACCEPTS`, a class attribute beside `PRODUCES`, `STATES`, `NEEDS` and
`CONSUMES`, and it belongs to Part 07 §4 with them: what a build must determine is this part's, and
what an implementation calls it is the implementation's (R115 §3.1).

## 4. What this does not change

- **`needs` keeps its meaning and its refusal.** A name declared there is still one a build must
  supply and still refuses a recipe that cannot fill it; what changes is that an adapter now has
  somewhere else to put an option, rather than the choice between declaring it mandatory and not
  declaring it.

## 5. Consequence

No packet is invalidated, no table, column or rule changes, and no packet is rebuilt: this is a
declaration a build reads before it opens a source.

What lands is one key and one check. The schema gains an `accepts` property; the generator that
writes a document from a class gains the key; the function refusing a declaration gains the two
tests §3.4 states; and the recipe check gains §3.2's refusal of an option no declaration names. The
ten shipped adapters gain an `ACCEPTS` listing the 28 options of §2.2, `sorter` names `sample` among
its own, and the two adapters of §2.5 can then take the option each is waiting on — which is what
moves `waveforms` and `lfp` from adapters carrying one producer's dialect to adapters a recipe
configures.

**Every declaration document written against R115 becomes one that accepts no option.**
Part 03 §11.5's schema requires `kind`, `protocol`, `produces` and `needs` and nothing else, so a
document written before this revision carries no `accepts`, §3.4 reads it as naming none, and §3.2
then refuses any recipe setting an option for that adapter, naming the source and the option. An
adapter reading an option with a default therefore stops building until its document declares one.
The break is deliberate: scoping the refusal to documents that already carry `accepts` would make it
inert on exactly the adapter it exists for — one a build cannot import, and so cannot check any
other way — and would leave a misspelled option arriving at a constructor as it does today (§2.3).
The ten shipped adapters are regenerated from their classes, which Part 03 §11.5 requires of an
implementation shipping both, so the cost falls on an adapter released apart from a build, which is
the case R115 §3.12 wrote the document for.

The cost is that an adapter's author now writes down every option they accept, and an option left
out of both lists is refused rather than ignored. That is the point of it, and it is the same cost
R63 §2.1 imposed for resources and R87 §2.2 for stated fields.

## 6. Open

**An option's type is still undeclared.** `accepts` names an option and says nothing about the value,
so a recipe setting `zone` to a number or `sd` to a string is refused by the adapter's own
constructor rather than by the build, which is §2.3's failure narrowed rather than removed. Declaring
a type means choosing a vocabulary for one — JSON Schema is the obvious candidate and would put a
schema document inside a schema document — and no measurement here says how many of the 28 would be
caught by it. Worth settling once something has counted that.
