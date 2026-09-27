# Part 05 — Validation, Import, and Reader Operations

Normative.

<a id="ew-import-validation-principle" data-spec-anchor="canonical"></a>
## 1. Core principle

**Validation is importation.** Copying bytes into a packet directory is staging, not import.

A resource is imported when a build has staged it, validated it with the whole staged packet,
promoted it, and published a manifest naming it, in the order §2 states.

A staged resource MUST NOT appear in the committed manifest. Validation state does not change the
content class or canonicality selected by its declaration; publication is the gate.

<a id="ew-import-pipeline" data-spec-anchor="canonical"></a>
## 2. Pipeline

A build MUST perform these steps in this order:

1. discover what each source offers, writing nothing (§4.1);
2. deliver each source's resources through the locations and routes the build supplies (§4.2);
3. normalize them to the logical schemas and write the result to the staging area (§4.3);
4. record the import's provenance in the staging area (§7);
5. materialize analysis resources from the staged packet into the staging area (§8);
6. validate the whole staged packet (§5);
7. promote the staged resources to their final locations (§6); and
8. publish the packet manifest (§6).

A build MAY interleave steps 1 to 3 across sources, within the constraints §4.3 places on
normalization, and a packet-owned array or opaque payload delivered into the staging area is staged
by its delivery.
A build MUST finish steps 4 and 5 before it begins step 6, MUST NOT begin step 7 until step 6 has
returned a packet verdict of `passed` ([§9.5](#ew-verdict-composition)), and MUST NOT begin step 8
until step 7 has finished.

The **staging area** is the location a build or an amendment owns while it runs and into which it
writes what it will publish. What it holds belongs to no packet until promotion moves it to its
final location. A physical profile names where its staging area lies; the portable profile's is
[Part 03 §3.4](03_portable_physical_profile.md#ew-staging-area).

A writer MAY empty or remove a staging area:

- after it publishes the manifest of the build or amendment that owns it;
- when it begins a build at the same packet root; and
- when it begins an amendment of the packet at that root.

A writer MUST NOT empty or remove a staging area that holds a promotion record until it has acted
on the record as §6 requires.

A writer MUST NOT combine parsing, normalization, validation, and writing into one opaque step.

An adapter MUST deliver only through the channels and locations a build supplies it, and a build
MUST read a delivery from nowhere else. A build owns each location it chooses for a delivery, and
may choose the place the delivered bytes will stay, as
[Part 12 §5](12_adapter_interface.md#ew-referenced-resource-delivery) has a packet-owned
array written under the staging area. A build MUST supply each such location empty, a directory
holding nothing or a path where nothing exists, since a build identifies what an adapter wrote
there by name and a name an earlier run left would pass for the delivery. An adapter MUST NOT rely
on what a location held before its run, or on what it writes there remaining after the build. This
rule governs a delivery and nothing else an adapter writes;
[Part 12 §2](12_adapter_interface.md#ew-reaching-a-source) names the portable profile's
routes.

## 3. The session recipe

<a id="ew-recipe-purpose" data-spec-anchor="canonical"></a>
### 3.1 Purpose

One source is rarely sufficient: integer sample indices come from a sorter, task structure and registration from an exported file, and session identity from acquisition metadata. The unit of work is therefore a **recipe** naming several sources, not a single input file.

A recipe declares, for one packet:

- each source, once per kind: its kind, its root, and its options;
- which resources each source supplies;
- which source owns a resource more than one listed source can supply (§3.3);
- the clocks the packet declares, and their parents;
- what to materialize;
- session facts no source carries.

A recipe MAY declare a fact a source it reads also states; §3.6 says which of the two the packet gets. `core.subjects` is not a resource the recipe supplies unconditionally: a source that states a subject MAY own it, arbitrated as any other resource two sources can produce, and the recipe's `[subject]` block supplies the table only where no source owns it.

A recipe is a [TOML 1.0](#ew-validation-normative-references) document. This part incorporates `registry/recipe.schema.json`, whose `$id` is `https://escapewheel.org/schemas/recipe/0.1.0`, as the shape of a recipe's decoded form. The schema owns the member names, types, required members, closure and patterns; this prose owns what each member means and every refusal of §3.5. TOML dates and times decode to values JSON Schema has no type for, so the schema leaves the facts under `[session]` and `[subject]` untyped, and §3.6 types each when it normalizes it. An omitted member keeps the meaning this part gives its absence. The table is an informative projection of the schema.

| member | form | constraint |
|---|---|---|
| `packet` | table | requires `id`; admits `out`, `registry`, `extensions`, `description`, and `in_process` |
| `session`, `subject` | table | keys are field names; values are untyped |
| `overrides` | table | keys are `block.field` names; each value a non-empty string (§3.6) |
| `encoding` | table | keys are `resource.column` names; each entry carries exactly `encoding`, one of `delta`, `plain`, or `dictionary`, and a non-empty `reason` (§3.8) |
| `clock` | array of tables | each requires `clock_id`, `name`, `tick_rate_num`, and `origin`, and admits `tick_rate_den` and `parent_clock_id` |
| `source` | array of tables | each requires `kind`; `owns` and `contributes` are arrays of dotted resource identifiers, `storage_options` a table, `in_process` a boolean (§3.9), and `delivery` a table admitting `command`, an array of strings (§3.7), and `protocol`, `declaration`, and `report_path`; every other key is an option |
| `preference` | table | keys are dotted resource identifiers; each entry is §3.3's |
| `materialize` | array of tables | each requires `resource`; every other key is a parameter |
| `commit` | table | members are a build's own limits |

A recipe MUST NOT list a source kind in more than one `source` entry, and a build MUST refuse one that does, naming the kind. A preference, an ownership refusal, and a build's reports name a source by its kind.

Each entry of the `[packet]` member `extensions` names one extension registry, and a build MUST
bind every registry so named under
[Part 09 §5.3](09_metadata_and_extensions.md#ew-extension-registration). This specification does
not fix how a build resolves an entry to a registry document, whether it reads the entry as a path
beside the recipe or as the identifier of a registry an implementation has installed.

A recipe MUST NOT list one extension in more than one `extensions` entry, and a build MUST refuse
one that does, naming the `extension_id` and each entry that resolves to it, before it opens any
source. Two entries list one extension when the registry documents they resolve to carry the same
`extension_id`, whether the entries repeat one string, pair a path with an identifier, or name two
versions of the registry.

### 3.2 The recipe is the provenance record

A writer MUST record the recipe in the import run's parameters, and its digest as the run's `code_uri`. A committed packet therefore states what produced it.

<a id="ew-recipe-ownership" data-spec-anchor="canonical"></a>
### 3.3 Ownership

Each source declares its resources as `owns` or `contributes`.

| declaration | meaning |
|---|---|
| `owns` | this source is solely responsible; records another source emits for the resource are discarded |
| `contributes` | this source adds rows alongside others |

`contributes` exists because some resources genuinely have several suppliers. Without the distinction, the last adapter to run wins silently.

A recipe MUST NOT declare `owns` for a resource that more than one of its sources produces rows for, unless it declares a preference between them. Exclusivity is for a resource one source is responsible for; where two sources each hold part, `owns` discards the part the owner does not hold, and no check sees it because the resource is claimed.

A recipe declares each preference as an entry of its top-level `preference` table, keyed by the resource's dotted identifier. The entry carries `source`, the kind of the source the recipe prefers, and `reason`, a non-empty statement of why that source knows more, and nothing else.

A preference declares ownership. A build MUST read the preferred source as owning the resource whatever its entry declares, and MUST discard every other source's rows for it, subject to §3.4's refusal of a discarded stated value. A build MUST apply each declared preference, and MUST NOT hold a preference of its own or accept one from any artifact other than the recipe: a built-in winner is one no recipe can see, and a recipe that has not heard of a new contest is better refused than silently arbitrated.

A preference MUST NOT name a resource only one source produces. Such an entry arbitrates nothing and exempts a report that will never be due, so it is a claim no build tests, and it goes stale the moment the second producer stops producing.

<a id="ew-source-declarations" data-spec-anchor="canonical"></a>
### 3.4 What a source can produce

Every source adapter MUST declare the set of resource identifiers it can supply. It is static: a property of the adapter, readable with nothing open, and distinct from what a particular source root happens to hold.

An adapter declares six such facts, all read before any source is opened: the resources it can supply; those of them whose rows it supplies only in part, such as the clocks of its own streams; the recipe fields it can state (§3.6); the values a build must supply it (Part 12 §4); the options it reads and can run without, and the one term it may accept, `source_cache` (Part 12 §4); and the kinds whose output it reads, which is what orders a build. An adapter a build cannot import publishes them as the declaration document Part 12 §7 specifies, where they are `produces`, `contributes`, `states`, `needs`, `accepts` and `consumes`; what an implementation calls them in code is Part 07 §4's.

A build MUST read a source entry that declares no `owns` as follows. Of the resources its adapter declares it can supply, leaving out any another entry declares under `owns` and any a preference gives to another source, the entry contributes those its adapter supplies only in part and owns the rest. It also contributes every resource its own `contributes` names, and owns none of those. An entry that declares `owns` owns exactly what it names and contributes what its `contributes` names. **A recipe states what it narrows; silence means the whole.**

A build MUST refuse a recipe in which two entries without `owns` are left owning one resource, naming both sources and the resource.

A build MUST report rows a source produced for a resource another source owns, except where the recipe declares a preference between them. That another source claims it is not the exemption: a preference says two sources offer the same rows and names the one that knows more, and without one they are producing different rows. The neighbouring case, a resource *no* source claims, is reported as a warning before a byte is read.

A build MUST refuse where a preference discards a value another source stated: where a passed-over source's row holds a non-null value in a column the preferred source's row leaves null, or does not produce at all. Where a preferred source produces no rows for the resource and another does, that is the rule's limiting case. The comparison is over declared columns and not over `metadata`, which §8 of Part 02 makes schemaless by design, so two sources filling it differently is not a difference a build can weigh. That refusal is what makes the exemption above sound: the exemption rests on the loser's copy being redundant, and a preference is declared before either source is opened.

A build MUST NOT compose a row from more than one source. The merged row would be a fact no source stated. A recipe resolves the refusal by naming the fact in `[overrides]` with its reason, by preferring the other source, or by correcting the source that states less.

A build MUST also be able to determine, for each source a recipe names and without opening it, which recipe fields that source can **state**, and MUST refuse a recipe naming a source it cannot determine that for. What an implementation calls that declaration in code is Part 07 §4's, and the key it takes in a declaration document is Part 12 §7's.

<a id="ew-recipe-check" data-spec-anchor="canonical"></a>
### 3.5 Checking a recipe

A build MUST check a recipe against the registry before it opens any source. A build MUST refuse:

- a resource owned by more than one source;
- an owned resource the registry does not define;
- an owned table whose **required** foreign key targets a table nothing supplies;
- a clock declared twice, referenced but absent, or parented to nothing;
- a required source option that is not set.

A build MUST also refuse, on the same terms and before any source is opened:

- an adapter declaring a value Part 12 §4 resolves to neither a term nor a recipe option;
- an adapter declaring a term that list carries, other than `source_cache`, that this recipe cannot fill, naming the term and the source;
- an adapter released independently of a build declaring no protocol of a group the profile names, or any adapter declaring one it does not name;
- a declaration failing the schema Part 12 §7 incorporates, whether a document or an importable declaration, naming where it fails;
- a source entry naming a protocol its adapter does not declare, where the adapter declares any, naming the source and the protocol;
- a declaration whose resources include one no loaded registry declares;
- a declaration whose stated fields include one no recipe block carries;
- a source entry setting an option the adapter names in neither `needs` nor `accepts`, naming the source and the option;
- a declaration whose accepted options include a term other than `source_cache`, or one its `needs` also names;
- a declaration whose `needs` names `source_cache`, naming the adapter;
- a declaration naming a resource it supplies only in part that is not one it declares it can supply, naming the adapter and the resource;
- a preference whose `source` names a kind the recipe does not list, naming the resource;
- a preference whose `source` names a kind whose adapter does not declare that it can supply the resource, naming the resource;
- a preference for a resource another entry declares under `owns` or `contributes`, naming the resource and that entry's kind, since the recipe then says both that one source knows more and that the other supplies the resource.

A build MUST refuse a recipe that is not TOML 1.0 or whose decoded form fails the schema §3.1 incorporates, naming where it fails, before it opens any source.

A build MUST report as a **warning**:

- an owned table whose **nullable** foreign key targets a table nothing supplies;
- a resource some listed source declares in `PRODUCES` that no source claims;
- a field the recipe declares that some listed source states and no override covers.

A warning is not an error because narrowing is legitimate, and only the recipe's author knows whether this one was meant.

### 3.6 Authority for a declared fact

Where a recipe declares a fact and a source the same recipe reads states that fact, a build MUST report a difference between the two, naming the field, the declared value, the source's value and the file it came from. A build MUST refuse only where the fact identifies something a reader resolves across packets; otherwise it proceeds, and `--strict` refuses. `[subject].subject_id` is that case and the only one: a subject is not scoped to a session, so a wrong one agrees with another packet's animal instead of colliding with the true value.

Two values are compared at the type the packet will store, both normalized to it first. A source stating no value for a declared fact is not a disagreement: the declaration stands, a writer MUST NOT report it as a mismatch, and SHOULD note that it went unchecked.

A recipe MAY declare that its own value supersedes the source's, by naming the field in a top-level `[overrides]` table keyed `block.field`. The value MUST be a non-empty reason. Declaring an override is never required: it records a decision and silences the report, and a recipe declaring none is conforming. A build MUST report an override for a field the source agrees with, or that no source states, and MUST NOT refuse on either.

The comparison needs the source read, so it happens as each source is built, and a build MUST refuse before any resource is staged. A source's statement of a fact is whatever its adapter exposes for that fact; which of several values inside a file it stands behind is the adapter's judgement and not the recipe's.

A fact the source **derives** is the source's. `core.sessions.session_start_time` and `session_end_time` come from the session source's declared stream windows, and a writer MUST use the source's value where a session source is present and MUST report a declaration it did not use rather than discarding it silently.

<a id="ew-source-command" data-spec-anchor="canonical"></a>
### 3.7 When a source runs a command

A command that exits non-zero MUST fail the build, and a build MUST name the source whose command failed together with the resources that source owns, rather than reporting the first resource it then finds missing. A command belongs to a source and a source is not an extension: one command may produce tables of several extensions, so a finding naming one of them would be wrong about the rest.

A recipe MUST carry a command as an argument list, and a build MUST NOT derive one by splitting a string. A parse is a quoting convention the recipe never declared: POSIX rules applied on every host eat a backslash everywhere, so `C:\Python\python.exe` becomes `C:Pythonpython.exe` and fails as a missing executable rather than as a malformed command. A list needs no convention, because the host's own process interface takes one.

Where the command is one a build reaches a source through (Part 12 §4), the build MUST write what it supplies that source to the command's standard input and MUST close the stream when it has, without waiting for the command to exit, and MUST read what the command produces while it writes. A command that converts a raw source before it is read is not one of these and is supplied nothing. A pipe holds tens of kilobytes and a supplied object may be far larger, so a build that wrote one whole before reading rows would wait on an adapter that was waiting on it.

A build MUST capture a command's standard output and standard error, and MUST report them with a failure of that command. Where the command succeeds, a build SHOULD keep them readable afterwards. Where the recipe puts rows on standard output (Part 12 §3), a build MUST NOT report standard output as a diagnosis, and standard error is where a command that also emits data prints one. Holding them in memory is not what this asks: a command may run for minutes and its progress is worth watching while it does, so a build writes the streams to a file and reports that file and its last lines.

### 3.8 A recipe declares an encoding

A recipe MAY declare a column's Parquet encoding, in an `[encoding]` table keyed `resource.column`,
each entry naming one of `delta`, `plain` or `dictionary` and the reason it was measured. An entry
MUST carry a reason, since a bare choice cannot be re-judged when the data moves.

A writer's own exceptions MUST name only tables of the layer it implements, and an extension's MUST
be declarable without the writer importing anything the extension ships — a writer may require no
code of an extension, so a declaration arriving as a Python object would be one only an
importable extension could make.

The recipe is also the right granularity rather than the only reachable one. An encoding is a fact
about one packet's values: a column repeating often enough to want a dictionary in one session may
not in the next, where a schema-level declaration would claim it of every packet. §3.6's
`[overrides]` puts a chosen value and its reason in a recipe for the same reason — the choice
belongs to the build.

<a id="ew-in-process-opt-in" data-spec-anchor="canonical"></a>
### 3.9 Whether a source runs in the writer's process

A build MUST deliver a source whose adapter declares a protocol out of process unless the recipe declares that it runs in the writer's, and a writer MUST NOT run such a source in process where the recipe does not say so. A build MUST run an adapter it ships that declares no protocol in process unless its recipe entry gives it a `delivery` table naming a command (§§3.1 and 3.7), and then serves it over a protocol of the group (Part 12 §3); a build MUST NOT require a recipe to opt such an adapter into the writer's process.

The recipe declares it because the recipe author chose the environment. One process resolves one dependency closure, so whether a given set of adapters installs together is a fact about one machine on one day rather than a property of any adapter, and the person assembling the recipe is the only party who can find out and the one who carries it when the answer changes.

What the opt-in buys is a saved transfer and what it costs is a solvable environment. A build that cannot import an adapter the recipe opted in MUST refuse, naming the source and the import that failed, before any source is opened.

<a id="ew-import-sources" data-spec-anchor="canonical"></a>
## 4. Discover, deliver, and normalize

### 4.1 Discover

For each source, report what it offers per resource, and how many rows. Discovery MUST NOT write to the packet.

<a id="ew-import-delivery" data-spec-anchor="canonical"></a>
### 4.2 Deliver

A build reads each source's delivery where it supplied it (§2), which need not be the staging area,
and writes what it normalizes from it into the staging area (§4.3). A writer MUST stream a table
whose row count is large rather than materializing it as host objects.

<a id="ew-import-normalization" data-spec-anchor="canonical"></a>
### 4.3 Normalize

Map source objects onto the logical schemas: assign identifiers packet-wide before any table is written, apply the declared sort, and coerce types to the registry's.

Normalization MUST be deterministic in the recipe. Two runs of the same recipe over the same sources produce the same packet.

An interval is closed (01 §2.3). A writer MUST convert a source whose intervals are half-open — `[start, stop)` — which is a subtraction on the stop bound. A writer MUST NOT carry a half-open bound through unchanged.

An adapter compensating for a known defect in its source MUST declare the compensation, and a writer MUST record every compensation applied in the import run's parameters. Choosing not to correct a known defect is equally a compensation and is declared as a pass-through.

<a id="ew-delivery-completeness" data-spec-anchor="canonical"></a>
### 4.4 When a source's delivery is complete

What a build expects of a source is the set of resources it owns, settled from `owns` and what the adapter declares before any I/O (§3.4). A run succeeded when every resource in that set arrived and the process exited clean.

A resource an adapter owns and has nothing for MUST arrive empty rather than not arriving (Part 12 §5). That is what makes the test usable: a build reads a resource that did not arrive as the run having failed, and never as the source having had nothing to say.

A non-zero exit is a failure whatever arrived. A build MUST report one as a failure even where every resource is present, because an adapter saying it failed is not overruled by its own output, and a command dying between two resources delivers the first one complete and valid.

A build MUST report a delivery it cannot parse as a failure where the command exited zero, naming what was short. What no protocol catches is a short table from a run that exits zero: where an adapter declares a row count a build MUST check it, and an adapter that cannot know its size before it sends declares none, which a build MUST read as unknown rather than as zero.

A build MUST report everything the protocol it used carries about a failure — standard error for `files-v0.1` and `stream-v0.1`, and the error's message together with its detail for `flight-v0.1`, where a failing adapter writes nothing to standard error because the diagnosis travels on the connection it was asked over. A build SHOULD try every resource it was waiting for and report every failure together rather than stopping at the first: the answer a person wants is which resources did not arrive, not which one did not arrive first.

<a id="ew-import-validation" data-spec-anchor="canonical"></a>
## 5. Validate

<a id="ew-tier-1-validation" data-spec-anchor="canonical"></a>
### 5.1 Tier 1

Generated from structure (Part 02 §10.1): required-column non-null, primary-key uniqueness, foreign-key anti-joins, closed-vocabulary membership, and the finiteness of every column declaring `finite: true`.

<a id="ew-tier-2-validation" data-spec-anchor="canonical"></a>
### 5.2 Tier 2

Declared per table under Part 02 §10.2 and interpreted by the registry's selected language. Before
execution, a validator MUST support that exact language and MUST parse, statically validate, bind,
and type-check the rule as Part 11 requires. It MUST execute only a checked query. A language or
profile defect makes the registry invalid rather than producing a packet finding.

<a id="ew-validation-shim" data-spec-anchor="canonical"></a>
### 5.3 The shim

A validator MUST first evaluate manifest conformance under
[Part 04 §10](04_packet_catalog.md#ew-packet-manifest-conformance), which owns the declaration
resolution, instance, presence, dependency, catalog, reference-target, and lineage checks, before
dispatching kind-specific checks.

A validator MUST derive the physical interface from the checked logical kind and the selected
profile, then check available resource-owned metadata: physical order, file presence, Parquet
types and footer features, Zarr version, rank and codecs, and checksums outside SQL. A query cannot
observe them, so such a check written as SQL fails silently rather than loudly. Dense-array checks
obtain the axes table from the resolved declaration.

A validator MUST assess floor membership for every packet-owned resource whose interface declares a
reader floor, and for every external one whose format-owned metadata it reads under
[Part 04 §5.3](04_packet_catalog.md#ew-external-resource-verification). Membership is judged under
[Part 03 §5.5](03_portable_physical_profile.md#ew-parquet-reader-floor) for Parquet and
[Part 03 §6.4](03_portable_physical_profile.md#ew-array-codecs) for Zarr. For each assessed resource
using a feature outside its floor, it MUST report one finding under the check ID
`physical.outside_reader_floor`, naming:

- the resource;
- its interface and, for Zarr, its variant; and
- the observed features that matched no floor entry: each outside compression or encoding for
  Parquet, the whole observed pipeline for Zarr v3, and `filters` and `compressor` for Zarr v2.

The finding's level is `warning` for a packet-owned resource whose interface's floor role is
`reader_and_packet_writer`, and `info` for every other resource. A validator MUST NOT report it at
`error`. The finding concerns one resource, so [§9.5](#ew-verdict-composition) attributes it to the
registry whose declaration the resource's entry names.

Two names in one directory of a packet-owned opaque payload
([Part 03 §11](03_portable_physical_profile.md#ew-opaque-storage)) **collide** where
they differ and are a canonical caseless match under the Unicode Standard, Section 3.13, definition
D145, which equates names differing only in case, only in normalization form, or in both. A name
within such a payload, or a decoded segment of the payload's `uri`, is **unportable to Windows**
where it contains a code point from U+0001 through U+001F or any of `"`, `*`, `:`, `<`, `>`, `?`,
`\`, and `|`; ends in a full stop or a space; or, compared without regard to ASCII case, is `CON`,
`PRN`, `AUX`, `NUL`, or `COM` or `LPT` followed by one of the digits `1` through `9` or the
superscripts `¹`, `²`, and `³`, whether alone or followed by a full stop and anything else.

A validator MUST report each set of colliding names and each name unportable to Windows, one finding
per set and one per name, at `warning` under the check ID `physical.opaque_name_portability`, naming
the resource, the path under the packet root of the directory holding the names, and the names. The
packet is conformant: each name holds its own file under the packet root, and it fails only on a
copy to a filesystem that folds case or normalization or that Windows governs. The finding concerns
one resource, so [§9.5](#ew-verdict-composition) attributes it to the registry whose declaration the
resource's entry names. §15 identifies the Unicode Standard, Version 15.0.0, as an exact reference
for canonical caseless matching.

A validator MUST report each external resource whose interface declares a reader floor and whose
format-owned metadata it did not read, one finding per resource, at `info` under the check ID
`external.physical_unassessed`, naming the resource. [§9.5](#ew-verdict-composition) attributes it
as it does the outside-floor finding.

The shim MUST compare the manifest's session inventory with `core.sessions.session_name` under the
check ID `core.sessions.manifest_sessions_match`, at `error`, with the message carried by the
registry before that check moved here. It reports each non-null table value absent from the
manifest, preserving duplicates, and each manifest session absent from every table row. The shim
declares the packet manifest and `core.sessions` as inputs. No Tier 2 rule may depend on the shim's
implementation mechanism.

The shim MUST parse each distinct non-null value of each
[unit column](02_core_logical_schemas.md#ew-unit-and-clock-context) in every table resource whose
declaration a registry directing packet checks holds, under the UCUM edition Part 02 §8.4 names. It
MUST report each value that is not a unit code at `error` under the check ID
`<declaration_id>.<column>.ucum_code`, such as `core.units.amplitude_unit.ucum_code`, naming that
value once. The finding belongs to the registry holding that declaration under
[§9.5](#ew-verdict-composition). The shim declares each such table as an input.

A validator SHOULD report each pair of columns of one table resource that hold equal values in every
row, where those values are not all the same, at `info` under the check ID
`<resource_id>.columns_duplicated`, naming both columns. It MUST NOT report such a pair at `error`:
independently numbered identifiers can coincide, which is a fact about a packet rather than a
defect in it. The finding concerns one resource, so [§9.5](#ew-verdict-composition) attributes it
to the registry whose declaration the resource's entry names.

<a id="ew-validation-extensions" data-spec-anchor="canonical"></a>
### 5.4 Extensions

A validator MUST apply to each resource an extension declares every check of §§5.1–5.3 that a core
resource receives because of its logical kind or its declarations, directed by that extension's
checked context. A check that applies to one named core resource, such as the session-inventory
check of §5.3, does not extend. [§9.5](#ew-verdict-composition) assigns the extension's findings to
it and composes its verdict with core's.

<a id="ew-import-commit" data-spec-anchor="canonical"></a>
## 6. Commit

A **commit** is steps 7 and 8 of §2: **promotion**, which moves a validated staged packet's
resources to their final locations, and **publication** of its manifest at `packet.json`, last and
atomically. Commit MUST be atomic with respect to a concurrent reader: a reader MUST observe either
the previously committed manifest or the newly published one, and MUST NOT observe a manifest naming
a resource that is not yet in place. A writer MUST NOT publish a manifest until every packet-owned
resource it names is at its final location and has passed validation.

The publication mechanism is the profile's. A filesystem profile MAY publish by atomic rename
within one directory; an object-store profile MAY publish by a single-object write. A writer MUST
NOT be required to perform an atomic **directory** rename, which no object store
offers and which the packet layout does not need — the manifest is one object.

Where the store offers a conditional write, a writer publishing a new version SHOULD use it, so
two writers cannot silently overwrite one another's head. Where it offers none, a writer MUST NOT
claim it detected a conflict it could not detect.

A writer whose validation returns a packet verdict other than `passed` promotes nothing, MUST NOT
write a manifest at the packet root, and SHOULD leave its staging area in place for inspection.

Before a build or an amendment writes anything outside its staging area, the writer MUST write a
**promotion record** into the staging area and make it durable. The record states the
`packet_version` the writer will publish and lists, relative to the packet root, every file and
directory the writer will create outside the staging area before it publishes, other than the
manifest. For an import these are the promoted resource directories, the bound registries, the
source resolution document, and any file publication writes before it installs the manifest; for
an amendment, every file it writes and the superseded manifest it retains
([Part 03 §9.3](03_portable_physical_profile.md#ew-superseded-manifest-retention)). A writer MUST
refuse to promote where a path its record lists already exists, naming the path, and MUST NOT
create outside the staging area a path its record neither lists nor places inside a listed
directory. This specification does not fix the record's format.

A listed path, with everything inside it, belongs to the build or amendment that wrote the record
until a manifest carrying the record's `packet_version` is published. A writer beginning a build or
an amendment at a packet root whose staging area holds a promotion record MUST read the record
before it empties the staging area or writes anything else, and then:

- where no manifest is published at the packet root, or the published manifest's `packet_version`
  sorts before the record's as a semantic version, the writer MAY remove every listed path that
  exists, and then proceeds as a new build or amendment; and
- where the published manifest's `packet_version` equals the record's or sorts after it, the record
  is stale, and the writer MUST NOT remove a listed path.

A writer that cannot read a promotion record MUST NOT remove any path outside the staging area on
the record's account, and MUST refuse to build or amend at that packet root, naming the record.

<a id="ew-import-provenance" data-spec-anchor="canonical"></a>
## 7. Provenance

A writer MUST record, in the staging area at step 4 of §2:

- one `core.processing_runs` row for the import, declaring its `scope` and `scope_kind`;
- one `core.source_files` row for each distinct `root` among the recipe's sources (§3.1), whose
  `uri` is that root as the recipe states it; and
- one `core.processing_run_inputs` row linking each of those `core.source_files` rows to the import
  run.

A writer need not read a source to fill `sha256`, `size_bytes`, `format`, or `modified_at`, each of
which may be null.

<a id="ew-import-materialization" data-spec-anchor="canonical"></a>
## 8. Materialize

Materialization is step 5 of §2: a build opens the staged packet, computes each derived resource
from it, and writes the result to the staging area, so step 6 validates it with core before
anything is promoted.

Deriving into an already-committed packet is an amendment (03 §9.1), not part of an import.

## 9. Reporting

### 9.1 Findings

A finding declares a level, the check that produced it, and a message. Where a check is a query, the offending rows are the finding.

| level | meaning |
|---|---|
| `error` | the packet does not conform |
| `warning` | conformant, but likely not intended |
| `info` | recorded, not judged |

<a id="ew-error-policy" data-spec-anchor="canonical"></a>
### 9.2 Error policy

A writer MUST NOT publish a manifest, whether as a first commit or as a later version, unless the
verdict of the packet it describes is `passed` under [§9.5](#ew-verdict-composition), and MUST
record `passed` as that manifest's `validation.status`. A packet whose extension fails is therefore
published in no partial form; its writer corrects the extension or builds the packet without it.

A validator MUST NOT downgrade an error to make a packet pass. An advisory rule MUST NOT be an error (Part 02 §10.2), so enabling advisory checks cannot change whether a packet previously passed.

### 9.3 Comparison against a prior packet

Where an import replaces an existing packet, it SHOULD report every resource the prior manifest declared that the new one does not. This is a warning: narrowing is legitimate, and no other check sees a resource that is simply absent.

<a id="ew-incomplete-validation" data-spec-anchor="canonical"></a>
### 9.4 Incomplete validation

A report MUST distinguish an invalid registry rule, an unsupported selected language, an
incomplete valid evaluation, and a completed query that produced packet findings. An unreadable
input, engine failure, exact overflow, out-of-range timestamp, timeout, or resource limit makes the
affected required evaluation incomplete. A validator MUST NOT turn its inability to evaluate into
an error-level packet finding. Core and every extension retain separate evaluation state.

<a id="ew-verdict-composition" data-spec-anchor="canonical"></a>
### 9.5 Verdicts

A validator MUST attribute each finding to exactly one subject: the packet, its core registry, or
one extension registry its manifest binds.

- A `registry_binding` finding, and each outcome of a bound registry's
  [Part 02 §9.4](02_core_logical_schemas.md#ew-registry-conformance) result, belongs to the registry
  it concerns.
- A finding produced by a generated check or a declared rule belongs to the registry whose
  declaration generated or declares it.
- Any other finding about one resource entry, or the resource it locates, belongs to the registry
  whose declaration the entry's `declaration_id` names. For a reference, dependency, or lineage
  finding, that entry is the one holding the reference, the `requires` declaration, or the
  `derived_from` member, and for `packet.resource.required_missing` it is the absent singleton's
  declaration.
- Every other finding belongs to the packet, including every finding of the `json`, `shape`, and
  `entries` phases, `packet.resource.declaration_unknown`, and `packet.resource.lineage_cycle`.

A validator reports a **verdict** for the packet, for its core registry, and for each bound
extension registry. A verdict is `passed`, `failed`, or `incomplete`. A subject's verdict is:

1. `failed` where an error-level finding belongs to the subject, or its bound registry's Part 02
   result is `invalid`;
2. otherwise `incomplete` where an evaluation the subject requires did not complete or was withheld,
   or its bound registry's result is `unsupported` or `incomplete`; and
3. otherwise `passed`.

The packet verdict is the worst, in the order `failed`, `incomplete`, `passed`, of the verdict its
own findings give the packet, core's verdict, and every bound extension's verdict. Only a packet
verdict of `passed` supports the packet conformance claim of [§10](#ew-conformance-classes).

Where [Part 04 §10](04_packet_catalog.md#ew-packet-manifest-conformance) or
[§14.5](#ew-validator-registry-boundary) withholds an evaluation, the subject it was withheld from is
at best `incomplete`. A finding in the `json`, `shape`, or `entries` phase withholds every registry's
evaluation; a core registry that fails binding or whose result is not `valid` withholds every
extension's packet checks; and an extension registry that fails binding withholds its own.

A validator's report MUST state the packet verdict, core's verdict, and each bound extension's
verdict, and MUST state each finding's subject. This specification defines no validation-report
schema.

<a id="ew-conformance-classes" data-spec-anchor="canonical"></a>
## 10. Two conformance classes

A report says which of two claims it is making.

A packet conforms to this specification when it declares a profile defined here, carries every
resource that profile requires, satisfies every structural requirement of Part 02, completes every
required evaluation, and produces no error-level finding from the checks of this part. An invalid,
unsupported, or incomplete required evaluation cannot support a conformance claim. A conforming
packet MAY omit any optional instance, but every packet resource the manifest lists MUST resolve a logical
declaration. A payload that Escapewheel treats as opaque still requires a declaration; an extension
registry is the data-driven route for a resource core does not define.
[§9.5](#ew-verdict-composition) defines how the packet, core, and extension verdicts compose.

**Packet conformance** is a property of the bytes. It is evaluated on a packet regardless of how the packet was produced, and it is what `validate` reports. Provenance is SHOULD within it: a packet carrying none is conforming.

**Writer conformance** is a property of a process. A writer conforms when it satisfies this part, which includes recording provenance for the import activity and the inputs it read. A packet is not judged by it.

A validator MUST report packet conformance, and MUST NOT report a packet as non-conforming for an obligation that binds only a writer. Where it also checks writer obligations — a build-time run inside `import`, which has the process in hand — it MUST report the two separately, as it already does for core and extension verdicts.

<a id="ew-writer-acceptance-criteria" data-spec-anchor="canonical"></a>
## 11. Minimum acceptance criteria

A writer conforms when it:

1. refuses a recipe that cannot produce a valid packet, before opening any source;
2. produces a packet that passes Tier 1, Tier 2, and the shim;
3. records provenance for what it read and what it ran;
4. leaves no manifest at the packet root when it refuses;
5. is **logically deterministic**: for the same recipe, the same source bytes and the same
   declared normalization, it produces the same canonical rows, the same values, the same assigned
   identifiers, the same resource identities and the same declared physical ordering.
   Identifier assignment MUST be a function of the recipe and the sources, never of wall-clock
   time, iteration order over an unordered collection, or the order a filesystem listed a
   directory.

Byte-identical output is **not** required and cannot be: a manifest carries `created_at` and
`validated_at`, and encoders may encode identical logical content differently between library
versions. A writer MAY offer a deterministic-build mode that pins those, and a packet
a validator MUST NOT judge a packet non-conforming for lacking one.

A recorded digest therefore says what a packet's bytes **are**, not what a second build would
produce. Two conforming builds of one dataset may record different digests for the same rows.

## 12. Alternatives are resolved before a commit

Where two or more `core.processing_runs` rows share `(session_id, activity_type, scope_kind, scope)`, the packet **MUST** carry a `core.preferred_runs` row naming one of them, and a writer **MUST** refuse to commit one that does not. Where an activity has more than one run in a session, every one of those runs **MUST** declare `scope` and `scope_kind` — without a scope the runs cannot be grouped, so an ambiguity cannot be found rather than not existing.

Both are checked at `error` level. A consumer MUST NOT silently choose; on a conforming packet that case is unreachable. A consumer that meets an unresolved alternative is holding a packet that failed validation and reports that. Nothing here forbids a packet holding two sortings of one probe or two curations of one sorting; what it requires is that the packet says which is current.

<a id="ew-reader-operations" data-spec-anchor="canonical"></a>
## 13. Reader operations

Reader operations apply the logical identities and session scope defined by Part 02. They do not
widen a packet-local reference or infer identity from a label.

<a id="ew-reader-session-presentation" data-spec-anchor="canonical"></a>
### 13.1 Session presentation and correlation

A reader presenting one or more packets as one relation MUST carry a session discriminator on
every session-scoped table and MUST NOT carry one on a table that is not session-scoped. Part 02
§7.1 defines session scope.

The discriminator MUST distinguish the packet a row came from together with that packet's
`session_id`. A reader MUST NOT derive it from `session_name` or another `*_name`. A reader SHOULD
expose a compact integer for each such packet-and-session pair and SHOULD carry `session_name`
beside it as a non-identifying label.

A reader operation that correlates rows from two or more session-scoped relations MUST preserve
session scope. Within one packet, a correlation that does not follow a declared reference to a
packet-unique target MUST compare or match only rows with equal `session_id`. After presenting
packets together, a correlation MUST compare or match only rows with equal session discriminators.
If the caller supplies an explicit session restriction, the reader MUST apply it to every
participating relation and MUST NOT scope only one side of the operation. A declared packet-local
reference retains its exact key; the reader's discriminator supplies presentation context rather
than widening that reference.

Within one packet, a reader MUST join a unit-keyed relation to `core.units` through `unit_id`
alone. Across packets, it MUST include the session discriminator with `unit_id`; it MUST NOT widen
the packet-local unit reference itself. A reader SHOULD add the discriminator and label as scalar
projections over `session_id` rather than joining them from `core.sessions`, so an engine can prune
values a query does not select.

<a id="ew-reader-unit-selection" data-spec-anchor="canonical"></a>
### 13.2 Exact unit selection and currency

A reader operation given an exact packet-assigned `unit_id` or an explicit table of units MUST
treat that input as the selected unit or units. It MUST NOT reject that selection solely because
the packet leaves a sorting or curation preference unresolved, and MUST NOT require
`sorting_run_id` or `curation_id` as redundant identity arguments.

An operation that offers to choose the packet's current unit set MUST continue to report an
unresolved alternative rather than silently select or concatenate competing results. Passing the
result of that guarded operation into an exact spike read remains guarded at the selection step.
Exact selection does not declare a non-preferred result current and does not make a packet that
violates §12 conforming.

Where an exact-unit reader operation accepts `session_id`, it MUST use it only as query and
time-conversion scope. It MUST apply the restriction to every selected spike row and to the clock,
origin, and attached observation support used for the result, and MUST NOT use it to disambiguate
`unit_id`. A selection that does not match the named session MUST NOT attach support from another
session.

<a id="ew-reader-declared-types" data-spec-anchor="canonical"></a>
### 13.3 Declared identifier types

Where a reader's public API publishes a static type for a parameter, return value, or field that
directly carries a logical-table identifier, the reader MUST derive the corresponding host-language
scalar type from the incorporated registry's declared logical type. It MUST NOT infer the type from
an `_id` suffix or apply a logical-table identifier mapping to a catalog, manifest, vocabulary, or
discriminator-scope name governed by another declaration.

<a id="ew-registry-conformance-boundaries" data-spec-anchor="canonical"></a>

## 14. Registry-document conformance boundaries

<a id="ew-checked-registry-context" data-spec-anchor="canonical"></a>

### 14.1 Checked registry context

A **checked registry context** is an immutable in-process association of the exact evaluated
registry input; its decoded JSON value when decoding succeeded; its complete Part 02 result;
immutable representations of the local descriptor set and external-domain capabilities used; and,
for an extension, the exact checked core context supplied to its evaluation.

For a byte input, the context retains the exact bytes. For a mapping input, it retains an immutable
structural copy made before checking and records the skipped JSON phase required by Part 02 §9.4.
A valid context authorizes production or registry-derived checks only from the decoded document in
that same context. Another state authorizes no such interpretation. A context may be reused only
while all its associated elements remain identical. A path, declared version, mutable object
identity, or digest under an unspecified canonicalization does not prove that identity. This
specification defines neither a portable result cache nor a transferable validation receipt.

<a id="ew-registry-conformance-boundary" data-spec-anchor="canonical"></a>

### 14.2 Required boundaries

An implementation MUST obtain one complete Part 02 result before it interprets a registry to:

- publish or release that registry;
- start a packet build, before checking a recipe, opening a source, or staging output;
- construct a public writer directly from registry input;
- validate a packet using an embedded or caller-supplied registry;
- perform an extension-author registry check; or
- generate Tier 1, Tier 2, or another conformance check from registry declarations.

A boundary that owns source bytes uses the byte entry point. A boundary given only a decoded
mapping uses the mapping entry point and does not claim byte-level JSON checks. A low-level
generator either establishes the checked context or requires one; a mapping accompanied by a
result, Boolean, or caller assertion is insufficient.

<a id="ew-reader-registry-independence" data-spec-anchor="canonical"></a>

### 14.3 Reader independence

A reader MUST NOT require a registry result, checked context, or validation receipt to open a
packet, access its manifest or raw resources, present or correlate sessions, resolve
discriminators, references, or session scope, provide extension-aware access, or analyze one or
more packets. It may interpret declarations for those operations without making a conformance
claim, and the reference reader does not depend on the validator package to do so. An explicit
validation operation may evaluate the same input separately.

An unusable declaration need not produce a result for a reader operation. Its local failure or
partial-access behavior is not defined here, but ordinary analysis MUST NOT acquire a general
validation-receipt prerequisite.

<a id="ew-registry-producer-boundary" data-spec-anchor="canonical"></a>

### 14.4 Producer and authoring reactions

Registry publication, release, and generation of registry-derived conformance checks complete only
from a `valid` context. An extension-author check reports success only for `valid`. For another
state, the operation stops and exposes the complete result.

A writer rejects a non-valid registry before opening a source or staging output. A public mapping
constructor copies and checks the mapping before retaining or interpreting it. Rejection does not
open an adapter. A structured rejection exception makes the complete portable result retrievable;
a command-line boundary offers machine-readable output containing the same result. Authoring may
create an explicitly unfinished draft when it makes no conformance or publication claim.

<a id="ew-validator-registry-boundary" data-spec-anchor="canonical"></a>

### 14.5 Validator reactions

A packet validator obtains a complete result for every bound registry whose decoded bytes match
their digest under [Part 04 §10](04_packet_catalog.md#ew-packet-manifest-conformance). For a
bound registry that cannot be acquired, `packet.registry.missing`, `packet.registry.unreadable`,
or `packet.registry.digest` is the packet-level outcome. The validator identifies the checked core
context directing packet checks and supplies that exact context to every extension evaluation. If
it is non-valid, each acquired extension is still evaluated as far as Part 02 permits.

A validator MUST direct packet checks only from the checked contexts of bound registries that
passed the `registry_binding` phase. It MUST NOT substitute a caller-supplied, bundled, or remotely
resolved registry for a bound one. A validator MAY check a caller-supplied registry document on its
own under Part 02 but MUST NOT use it to direct packet checks or report its result as the
packet's.

Only a `valid` context directs generation or execution of registry-derived packet checks. For a
non-valid result, the validator retains the complete result, skips every dependent packet check,
preserves invalid outcomes as registry-document findings, and does not fabricate packet findings
for unsupported, incomplete, or skipped work. Independent checks may continue.
[§5.4](#ew-validation-extensions) extends the packet checks to extension resources, and
[§9.5](#ew-verdict-composition) composes the verdicts. A non-valid required evaluation remains
insufficient to support a conformance claim.

<a id="ew-registry-result-reporting" data-spec-anchor="canonical"></a>

### 14.6 Portable reporting

Each reported result has an external subject label. A bound registry's label is its registry ID,
and a registry checked outside a packet receives a source-distinguishing label. A label does not replace or manufacture the document's own identity.

Public checking APIs, machine-readable command output, validation reports, and structured
exceptions expose the same Part 02 §9.5 representation rather than reducing it to a Boolean or
invalid-finding list. Human rendering may differ. Diagnostic `detail` is not interoperable
identity. The result schema begins at version 0.1.0; this boundary and reporting change does not by
itself change a registry meta-schema, core registry, extension registry, packet manifest, or their
version identifiers.

<a id="ew-validation-normative-references" data-spec-anchor="canonical"></a>
## 15. Normative references

The application column states the extent to which this part invokes each external authority:

| reference | candidate edition | application |
|---|---|---|
| [TOML v1.0.0](https://toml.io/en/v1.0.0) | exact | a session recipe's syntax and decoded values (§3.1) |
| [The Unicode Standard, Version 15.0.0](https://www.unicode.org/versions/Unicode15.0.0/) | exact | canonical caseless matching of payload names, Section 3.13, definition D145 (§5.3) |
