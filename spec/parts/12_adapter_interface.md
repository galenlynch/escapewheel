# Part 12 — Adapter Interface

Normative. Profile identifier: `escapewheel-portable-v0.1`.

<a id="ew-adapter-interface-scope" data-spec-anchor="canonical"></a>
## 1. Scope

This part specifies what passes between a build and the adapters it reaches under
`escapewheel-portable-v0.1`: the routes an adapter delivers by, the protocols rows cross by, what a
build supplies an adapter, what a delivery states, how an adapter declares itself and reports its
run, and where an adapter may keep what it reads from a source for later builds. Its rules bind a
build writing a packet whose manifest declares `profile_id: escapewheel-portable-v0.1` and each
adapter such a build reaches, and bind no other build. With Part 03, which specifies how the
profile stores a packet, it forms the physical level
([Part 00 §3.1.3](00_architecture.md#ew-physical-profile)).

This part incorporates `artifacts/resources.schema.json`, whose `$id` is
`https://escapewheel.org/schemas/resources/0.5.0`, as the exact shape of the resource document of
§5. Its closed envelope admits an optional `$schema` string and requires `resources`, an array
of closed entries. An entry requires `resource_id`, `declaration_id`, and `uri`, and admits
`external`, `source`, `digest`, `size_bytes`, `verified_at`, and `members`. The delivery schema
defines each of those members, and the entry's conditional shape, exactly as the manifest schema
[Part 04 §1](04_packet_catalog.md#ew-packet-catalog-scope) incorporates defines them; a difference
makes the specification candidate internally inconsistent.

Its requirements directly invoke the shared JSON, URI, JSON Schema, and Parquet authorities
identified in [Part 00 §9](00_architecture.md#ew-normative-references) and the Arrow authorities
identified in [§11](#ew-adapter-interface-normative-references). The application columns in those
sections state their extent.

<a id="ew-reaching-a-source" data-spec-anchor="canonical"></a>
## 2. Reaching a source

An adapter reads one source and delivers what it read, and a build assembles a packet from several (Part 05 §3.1). An adapter delivers only where a build points it ([Part 05 §2](05_validation_and_import.md#ew-import-pipeline)), and in this profile by these routes:

- rows, returned to the build where it runs the adapter in process, or across the protocol a build reaches the adapter by (§3), with a `flight-v0.1` adapter serving them at `socket`;
- a packet-owned array, written into `array_location` where it crosses a protocol, and in process either written there or handed to the build with its values (§5);
- a packet-owned opaque resource, written into `opaque_location` where it crosses a protocol, and in process either written there or handed to the build with its bytes (§5);
- a `files-v0.1` delivery, written into `delivery_root` (§3), with the resource document for any referenced resource it delivers (§5); and
- a report, written at the `report_path` the recipe names (§9).

An **adapter** here is code that reads one source, whether the reference implementation ships it or a third party does. A clause binding an adapter binds one it does not ship identically.

<a id="ew-protocol-groups" data-spec-anchor="canonical"></a>
## 3. Protocol groups

A profile names a **group** for each way rows cross a process boundary, and the protocols in it. `escapewheel-portable-v0.1` names one group, out of process, holding three:

| protocol | rows cross as | a failure's diagnosis travels on |
|---|---|---|
| `files-v0.1` | Parquet in `delivery_root`, one file per resource, named by its resource identifier with the suffix `.parquet` | standard error |
| `stream-v0.1` | a sequence of Arrow IPC streams on standard output, each schema naming its resource | standard error |
| `flight-v0.1` | Arrow Flight over a Unix socket the build names, one descriptor per resource | the error's message and detail, on the connection the adapter was asked over; a failing adapter writes nothing to standard error |

A build MUST NOT require an adapter to be importable in the writer's environment, except one its recipe opts into the writer's process (Part 05 §3.9), and MUST be able to reach an adapter that is not. An adapter **released independently of a build** MUST declare and support at least one protocol in a group, and a build MUST support every protocol in every group this profile names. The asymmetry is deliberate: there is one build and there will be many adapters, so no negotiation can fail. A build meeting such an adapter that declares no protocol of the group MUST refuse it, naming the group, before any source is opened.

An adapter a build ships with need not declare one, and a build reaches it directly. The test is the release boundary rather than who wrote the code: an adapter inside a build's distribution is upgraded in the commit that changes a dependency, where one released apart is on the far side of a version boundary the build moves without asking, and the protocol is what keeps that move from being an outage. A build MAY serve an adapter it ships over any protocol of the group, which is how one becomes reachable out of process without declaring anything.

A build reaching out of process an adapter that declares its protocols MUST reach it by one of them: the protocol the recipe entry names, or any the adapter declares where the entry names none. A build MUST refuse a recipe entry naming a protocol its adapter does not declare, naming the source and the protocol, before it opens any source. A build reaches an adapter it ships that declares no protocol, where it runs that adapter out of process, over the protocol the entry names or any of the group. A build runs an adapter in the writer's process only as Part 05 §3.9 says, and reaches it there by no protocol, whatever the adapter declares. Nothing in this profile makes using an implementation a writer ships a condition of an adapter's conformance, and a build MUST NOT refuse an adapter for speaking a protocol without one.

A protocol carries its version in its name, semantically versioned from `v0.1`. A profile MUST NOT change what a named protocol means; a protocol that changes how rows cross is a new member of the group, and a build MUST NOT read support for one version as support for another. Retiring a protocol is a change to this profile and not a decision a build makes.

An adapter a recipe opts into the writer's process (Part 05 §3.9) is bound by this section too: the opt-in decides where a build runs an adapter, not what the adapter supports.

<a id="ew-build-supplied-values" data-spec-anchor="canonical"></a>
## 4. What a build supplies

An adapter MUST declare every value a build supplies it, and a build MUST supply exactly what the adapter declares and MUST NOT decide it from the source's kind. Everything supplied is data: a build MUST NOT require an adapter to accept a live handle — an open store, a connection, an object of the implementation's own — because what crosses a process boundary is text, and an adapter with two ways in has one that depends on where it is running.

The vocabulary is closed. Each term names one value and the form it takes, so an adapter and a build written by different people pass the same thing:

| term | what a build passes |
|---|---|
| `root` | the source's location as an absolute local path or a URI, which the adapter opens for itself |
| `session_id` | the session's own name, never the integer a build assigns (§5) |
| `reference_clock` | the reference clock's row: identifier, rational tick rate, origin |
| `clocks` | one such row per clock declared before this source runs |
| `first_samples` | one record per stream: its name, and the integer its samples start at |
| `units` | one record per unit: the source's label for it, and the identifier assigned |
| `wanted` | the resource IDs the recipe leaves this source owning, so it produces no more |
| `array_location` | a location under the build's staging area ([Part 05 §2](05_validation_and_import.md#ew-import-pipeline)) to write an array to (§5) |
| `opaque_location` | a location under the build's staging area to write packet-owned opaque resources to (§5) |
| `source_cache` | the absolute path of the build's **source-cache location**, a directory in which an adapter may keep what it reads from a source for later builds (§10) |
| an option, by its name | the value the recipe carries under it — a `zone`, an `interval_kind` |

A build MUST resolve each declared name against that list first and the recipe's options second, and MUST refuse a recipe where a name resolves to neither. A profile adding a term amends this section.

An adapter MUST declare in `accepts` every option it reads and can be constructed without, and in `needs` every value it cannot; it MUST NOT name one option in both. `source_cache` is the one term `accepts` may name: an adapter MUST NOT name any other term of the list above, or a term a protocol requires, in `accepts`, and MUST NOT name `source_cache` in `needs`. An adapter that keeps source data in the source-cache location names the term in `accepts`, since a build supplies it to no other adapter. Declaring a name in `needs` is what makes a recipe carry it, so an option holding a default is declarable only as an accepted one. An adapter MUST apply its own default where the recipe sets no value, so what an omitted option means is the adapter's statement rather than a value the build invents.

A build MUST supply an option the recipe sets and the adapter names in either list, and MUST NOT require a recipe to set one named in `accepts`. A build MUST refuse a recipe whose source entry sets an option the adapter names in neither, naming the source and the option, before any source is opened. A build MUST NOT supply an option the adapter names in neither list, including one it adds itself rather than reading from the recipe, and MUST NOT apply a facility of its own to an adapter that does not name the option carrying it.

A build MUST refuse a recipe where a term the list carries, other than `source_cache`, cannot be filled, naming the term and the source, and MUST NOT pass such a term absent or empty: `first_samples` needs a source that states them and `units` one that produced them, and an adapter cannot tell a term nobody filled from one whose value is legitimately empty.

A build that has a source-cache location MUST supply it as `source_cache` to every adapter naming the term in `accepts`. A build that has none supplies the term to no adapter and MUST NOT refuse a recipe for lacking one. An adapter supplied no `source_cache` reads its source or keeps data elsewhere, under §10.

A build MUST pass a collection as records carrying its key as columns. A mapping's keys are a type the crossing does not keep: an integer key returns as a string, and a compound key does not cross at all.

Some terms belong to a protocol rather than to an adapter. `flight-v0.1` requires `socket`, the address to serve on; `files-v0.1` requires `delivery_root`, the directory to write the delivery into; both `files-v0.1` and `stream-v0.1` require `report_path` where a report is expected (§9). A build MUST supply the terms of the protocol it reaches an adapter by (§3), and no other protocol's; in process it supplies no protocol's terms. An adapter MUST NOT declare one, because the protocol it is reached by is what asks for it.

What crosses is one JSON object keyed by the term. A build MUST write it to the command's standard input and MUST close that stream when it has, MUST NOT pass it as an argument, and MUST NOT add any argument to the command the recipe carries. An adapter MUST read its standard input to end of file and parse it as that object before it writes any rows, and a build supplies nothing else on that stream. An option appears under `options`, keyed by its name, so no option collides with a term.

An argument list is not the channel because it has a size no profile can raise — 131,072 bytes for one argument on Linux, 32,767 characters for a whole command line on Windows — and a term carrying one record per unit reached 322,799 bytes on a real session, where an adapter's whole object measured 721 against a fixture that had none. Standard input carries nothing under any protocol of the group and has no such limit.

The wanted set is a term a build supplies and an adapter MAY act on. A build settles ownership before any source is opened (Part 05 §3.4), so an adapter told what is wanted may extract no more; acting on it is permitted rather than required, because for some sources producing three resources costs what producing all of them costs, and a build cannot tell an adapter that extracted three from one that extracted everything and discarded the rest.

Where a recipe states a local `root` relative to itself, a build MUST resolve it against the directory holding the recipe and supply the absolute path. The working directory in which a build runs an adapter's command is unspecified. An adapter MUST open its source at the `root` a build supplies, and MUST NOT depend on the directory it runs in, since a `root` that is a store URI names no directory to run in. No checker verifies either rule: a packet records each `root` as its recipe states it ([Part 05 §7](05_validation_and_import.md#ew-import-provenance)) and not as it was supplied.

<a id="ew-referenced-resource-delivery" data-spec-anchor="canonical"></a>
## 5. What a delivery states

A delivery carries one table per resource asked for. Which columns that table holds is a statement: an adapter MUST deliver a column wherever any row of that resource carries a value, and an absent column says the source produced no value for it in any row, which is [Part 02 §6](02_core_logical_schemas.md#ew-column-presence)'s presence and nothing else. A build MUST NOT read an absent column as saying anything more.

An adapter MUST hand over identifiers as the names its source used and never as numbers, because a writer mints every assigned identifier packet-wide and the numbers do not exist until it has (Part 05 §4.3). Types, column order, numbering and the declared sort are the build's: it holds the registry and settles all four on arrival.

A resource an adapter owns and has no rows for MUST arrive empty rather than not arriving. An empty delivery states that the source had nothing to say; a resource that does not arrive states that the run failed, and a build that cannot tell them apart cannot report either.

An adapter's arrays MUST NOT cross as rows. A dense array crosses by identity and location. Where
the packet will own the array, a build MUST supply a location under the staging area (Part 05 §2),
and an adapter reached by a protocol MUST write the array there, so promotion (Part 05 §6) moves it
to its final path by a rename within one filesystem ([Part 03 §3.4](03_portable_physical_profile.md#ew-staging-area)). An adapter a build runs in process MAY instead hand the build the
array's values, and the build writes the array there. Where the array is external (Part 03 §8.2), a build
supplies no location and the producer returns the URI its source already has.

**A packet-owned array crosses as the bytes themselves.** A build MUST supply `array_location`, one
directory per source, since two sources may each deliver an asset of one name and a shared directory
would make them one array. Whichever of the adapter and the build writes an array into it MUST write
it as Zarr v3 ([Part 03 §6.1](03_portable_physical_profile.md#ew-array-version)), in a directory named by the catalog row's `resource_id` with the suffix
`.zarr`. The build resolves the unique catalog-family declaration for that table-and-column pair,
uses the row's `resource_id` as packet identity, and MUST NOT substitute an assigned row ID or
source label. It MUST refuse a delivery where bytes and catalog rows do not bind one-to-one.

Nothing else crosses for such an array, and a build MUST NOT require an adapter to restate a Zarr
version, codec pipeline, layout, or other self-describing physical fact. A build inspects reachable
output as needed; `size_bytes` and `digest` come from the packet-owned bytes it digests
(Part 03 §8.1). An adapter delivering an array therefore writes bytes where one delivering rows
performs no I/O at all, which is the cost of an array not being records.

**A packet-owned opaque resource crosses as a payload**
([Part 03 §11](03_portable_physical_profile.md#ew-opaque-storage)). An adapter that delivers one
declares `opaque_location` in `needs`, and a build MUST supply it one directory per source, since
two sources may each deliver a resource of one resource ID and a shared directory would make them
one. An
adapter reached by a protocol MUST place each payload, under its own name, alone in a **resource
directory**: a directory directly in `opaque_location` named exactly by the resource's
`resource_id`.

A build binds each payload to the opaque resource its resource directory names: the catalog row of
an opaque catalog family whose `resource_id` equals the directory's name, whose declaration it
resolves under [Part 02 §2.6](02_core_logical_schemas.md#ew-resource-catalog-binding), or otherwise
the opaque singleton declaration whose ID equals it (Part 02 §2.4). It MUST NOT bind a payload by
its name, suffix, or contents. A build MUST refuse a delivery, naming the source and the path,
where:

- `opaque_location` holds anything other than directories;
- a resource directory holds no payload, or more than one;
- a payload holds anything other than regular files and directories, such as a symbolic link, since
  the packet would then own a pointer rather than bytes;
- a directory within a payload, the payload included, holds nothing, since a prefix consists of
  objects and an empty directory does not survive a copy to an object store; or
- a name within a payload, the payload's own included, is not representable (Part 03 §11).

A build MUST refuse, before it validates the staged packet, naming each such directory and resource
ID, where a resource directory's name is the `resource_id` of no catalog row of an opaque catalog
family and the ID of no opaque singleton declaration a loaded registry declares, or is both; where a
catalog row of an opaque catalog family is bound by no payload or referenced resource; or where one
resource ID is bound by more than one payload or referenced resource. A build MUST also refuse a
payload bound to an opaque singleton declaration that
[Part 05 §3.4](05_validation_and_import.md#ew-source-declarations) does not leave the delivering
source owning, naming the source and the declaration.

Nothing else crosses for a payload. A build MUST NOT require an adapter to state a payload's format,
media type, size, or digest; it takes `size_bytes` and `digest` from the staged bytes (Part 03 §10) and
records no format. A payload in `opaque_location` is staged by its delivery, as a packet-owned array
in `array_location` is (Part 05 §2), and promotion moves it to its final path by a rename within one
filesystem (Part 03 §3.4).

An adapter a build runs in process MAY instead hand the build each payload's resource ID, name, and
bytes, or for a directory the path of each file relative to it and that file's bytes. The build then
writes the payload into `opaque_location` as an adapter reached by a protocol would, and the
refusals above apply to what it writes.

**A referenced resource crosses as a resource document.** An adapter that delivers one MUST deliver
that document with it, under the reserved resource identifier `resources` (§6), which under
`files-v0.1` is the file `resources.json` in `delivery_root`: a JSON object carrying `resources`, an
array with one entry per such resource. Each entry is a manifest resource entry as
[Part 04 §4.1](04_packet_catalog.md#ew-packet-resource-entry-fields) declares one, without the members a
build supplies, so it MUST NOT carry `validation_state` or `derived_from`. A build MUST preserve each
entry's `declaration_id` in the packet resource entry it creates from it, and MUST refuse a document
holding an entry whose `declaration_id` resolves to no declaration of a loaded registry or does not
admit the entry's `resource_id`. It merges each entry it accepts into the manifest. The document's
shape is the delivery schema §1 incorporates. A build MUST refuse a document that does
not satisfy it before writing a manifest, naming what is wrong.

A build MUST record every resource-document entry as external, and MUST refuse one that declares
`external: false`, naming the source and the entry's `resource_id`; a packet-owned opaque resource
crosses only as a payload. An adapter MUST write an entry's `uri` that is not absolute as a relative
reference (Part 03 §4), in any form RFC 3986 admits for its segments. A build MUST refuse an entry whose
`uri` is neither, naming the source and the entry's `resource_id`, and MUST record each entry it
accepts with its `uri` rewritten in Part 03 §4's one form.

The document is part of the delivery and not a report. A build MUST NOT require a report and MUST NOT fail on one's contents (§9), so a fact a manifest cannot be written without does not travel in one; a resource that does not arrive is already a failed run (Part 05 §4.4), which is the rule this needs and does not restate. A build MUST NOT count the document among the resources the recipe left the source owning.

**An adapter's compensations cross as a table.** A delivery MAY carry one table under the reserved
resource identifier `compensations` (§6), with one row for each compensation the adapter applied
([Part 05 §4.3](05_validation_and_import.md#ew-import-normalization)). The table crosses as a table
of the delivery crosses under the protocol in use (§3). It has these columns, each of a string type:

| column | presence | holds |
|---|---|---|
| `id` | required, and no row is null or empty | the compensation's identifier |
| `defect` | required, and no row is null or empty | the defect |
| `action` | required, and no row is null or empty | the action |
| `evidence` | the column may be absent, and a row may be null | the evidence for the defect |

An adapter that applied no compensation MAY deliver no such table, or an empty one. A build MUST
read an absent table, and an empty one, as a run that applied none.

A build MUST refuse a delivery, naming the source, whose `compensations` table lacks a required
column or holds a row that is null or empty in one. A build MUST NOT refuse the table for carrying
a column this section does not name.

The table is no resource of the packet. A build MUST NOT stage it, MUST NOT resolve a declaration
for it, and MUST NOT count it among the resources the recipe left the source owning
(Part 05 §4.4).

<a id="ew-arrow-ipc-floor" data-spec-anchor="canonical"></a>
## 6. The Arrow IPC floor

An Arrow IPC stream carries one schema and an adapter returns many resources, so under `stream-v0.1` the streams concatenate: each ends with the format's own end-of-stream marker, and the resource identifier rides in the schema's key-value metadata under the key `resource_id`. That key and three reserved values of it — `end`, `resources` for the document §5 requires of an adapter delivering a referenced resource, and `compensations` for the table §5 carries an adapter's compensations in — are the whole of what this protocol adds to Arrow. A resource identifier is dotted, so no undotted token collides with any of them, and a reserved value names no resource of a registry. An adapter MUST NOT deliver anything but that table under `compensations`. A document carried this way travels as text in a single-row table rather than as a column per field, so the manifest's schema stays the one description of an entry.

"Arrow IPC" names a family, so this profile pins one member of it, as Part 03 §5.5 pins Parquet's compressions. An adapter MUST write uncompressed record-batch bodies at metadata version V5, and MUST send each dictionary whole rather than as a delta against one already sent. Compressing buys nothing on a pipe and costs an adapter author a codec in a language whose Arrow binding may not carry one; V5 has been the default since Arrow 1.0, and a delta dictionary is the least evenly implemented part of the format.

An adapter MUST terminate every resource's stream with the end-of-stream marker and a build MUST consume exactly to it, so the next resource's schema begins at the next byte. An adapter that omits one delivers bytes no reader can frame; a build that consumes past one loses every resource after it and reports a truncation on a delivery that finished.

A reader treats end of file as end of stream, so a delivery cut at a message boundary parses clean and cannot be told from a short one. `stream-v0.1` therefore ends a delivery with an empty stream whose `resource_id` is `end`. A build MUST refuse a delivery that did not end with it, and MUST name the last resource it read as the one the adapter died inside rather than the first that never arrived. A resource identifier is dotted, so no undotted token can collide with the reserved value.

Where rows travel on standard output they are bytes. An adapter MUST write the stream to a binary handle and a build MUST read one, because a platform translating a line ending corrupts the stream, which then fails as malformed data rather than as an encoding error.

<a id="ew-adapter-declaration-document" data-spec-anchor="canonical"></a>
## 7. The declaration document

A build reads what an adapter declares before it opens any source, and for a class it reads that by importing the adapter — which this part forbids requiring. An adapter a build cannot import MUST publish its declarations as a JSON document the recipe names, and a build MUST read that document before it launches anything.

The document carries what belongs to the adapter and nothing that belongs to the machine: `kind`, `protocols`, `produces`, `contributes`, `states`, `needs`, `accepts` and `consumes`. The command, the root and the options stay in the recipe, because which interpreter is installed where is the recipe author's fact and the resources an adapter can supply is not. This section incorporates `artifacts/adapter.schema.json`, whose `$id` is `https://escapewheel.org/schemas/adapter/0.1.0`, as the exact shape of the document. The schema owns member names, JSON types, required members, closure, and patterns; this prose owns what each member means and every refusal. The schema's descriptions are informative.

A document MUST carry all eight members, and each member listing names is an array. `protocols` names every protocol the adapter supports, at least one and none twice (§3); in any other member, an empty array declares none. `accepts` names options, and the one term §4 lets it name, in the same form as `needs` (§4), and `contributes` names, as dotted resource identifiers, the resources the adapter supplies only in part (Part 05 §3.4). `consumes` names the kinds of the sources whose output the adapter reads, which is what orders a build (Part 05 §3.4).

A build MUST treat a document and an importable declaration of the same facts as one declaration, and MUST NOT prefer either where both are present. An implementation shipping both MUST generate the document rather than maintain it.

A build MUST check an importable declaration as the document holding the same facts, so a class and a document are refused for the same defects under the same terms. An importable declaration of an adapter a build ships may omit `protocols`, as §3 lets it; one of an adapter released independently of a build may not, even where a recipe runs it in process.

A build MUST refuse a declaration that fails the schema, naming where it fails, and one whose `protocols` names a protocol of no group this profile names, whose `produces` names a resource no loaded registry declares, whose `contributes` names a resource its `produces` does not, whose `states` names a field no recipe block carries, or whose `needs` names what §4 resolves to neither a term nor an option. A build MUST also refuse one whose `accepts` names a term other than `source_cache`, names an option its `needs` also names, or is not an array of names, and one whose `needs` names `source_cache`, naming the adapter. None of those need the adapter opened or imported.

`states` names the recipe fields a source can state and the values need the source read, so no static document carries them: they travel under `stated` in the run's report (§9), keyed by the same `block.field` name. An adapter declaring a non-empty `states` MUST return them. A build MUST read a declared field absent from the report as unstated rather than as disagreeing, since a source stating nothing is a fact and not a mismatch (Part 05 §3.6).

<a id="ew-reaching-a-running-adapter" data-spec-anchor="canonical"></a>
## 8. Reaching an adapter that must be running

Where a protocol needs the adapter running — `flight-v0.1` does, `files-v0.1` and `stream-v0.1` do not — the protocol MUST say how a build establishes that. `flight-v0.1` says it by connection: a build retries the address it supplied until the socket answers or the adapter's process exits, and reports the exit. A readiness line on standard output is weaker, because a build waiting for a line that never comes cannot tell *not yet* from *never* unless it watches the process as well, which is the whole of what retrying already does.

The retry puts one obligation on the adapter: it MUST NOT bind before it can answer `ListFlights`. A build's first call arrives as soon as the socket answers, so an adapter that binds and then extracts serves discovery from a half-built server.

A build that started a process owns it and terminates it once it holds the rows and the report, so an adapter MUST NOT rely on running code after its last response.

<a id="ew-adapter-run-report" data-spec-anchor="canonical"></a>
## 9. What an adapter may state about its own run

An adapter MAY validate the tables it delivers before returning them, against the registry that declares them and on the same terms a validator applies to core. A build MUST NOT rely on its having done so; its own validation runs over every staged resource whatever produced it.

An adapter MAY write a report of its run at a path the recipe names, and a build MUST report what one contains where it is present. A build MUST NOT require one, and MUST NOT fail on a report's contents alone.

Where the report is a file, a build MUST remove that path before it runs the command and MUST treat a report it did not see appear as absent. A file at a path the recipe names is present after any run that ever wrote one, so last week's findings are otherwise reported as this run's with nothing to distinguish them.

Which channel carries a report is the protocol's. Under `files-v0.1` and `stream-v0.1` it is a file at the path the recipe names, supplied to the adapter as `report_path` (§4), because rows have taken standard output and a file is the channel left. Under `flight-v0.1` it is `DoAction("report")`, because the connection is that channel and no file outlives the run; an adapter with a report MUST name `report` among its actions, and a build MUST NOT ask one that did not.

No finding travels in a listing. `flight-v0.1` gives no meaning to the `app_metadata` field of a `FlightInfo`, the entry `ListFlights` returns for each resource, and a build MUST ignore that field. No checker verifies this.

A report carries what a build cannot derive, and a build SHOULD ignore what it can: rows per table, which tables exist, and whether their schemas conform are each established without asking. What no artifact holds is what the command read, what it skipped and why, and whether a table that is short is legitimately short.

A report is JSON. An optional `problems` array carries an entry per finding, each with a `level` of `error`, `warning` or `info`, a `message`, and optionally the `resource` the finding concerns; an optional `read` array names what the command consumed; an optional `stated` object carries, per `block.field` name the source declares it states, the value the source holds (§7). A build MUST report every problem it is given and MUST NOT refuse a report for carrying keys it does not recognise.

A build MUST look for a report after a failure as it does after a success, since the run that went wrong is the one with something to say.

<a id="ew-source-cache" data-spec-anchor="canonical"></a>
## 10. The source cache

A build takes its source-cache location, which it supplies as `source_cache` (§4), from its own
configuration. A build MUST supply as `source_cache` only a directory the adapter can write that
lies outside the root of the packet being built and outside every location the build supplies for a
delivery ([Part 05 §2](05_validation_and_import.md#ew-import-pipeline)), and MUST create the
directory where it is absent. A build whose configuration names no such directory has no
source-cache location. A build MUST NOT empty or remove the location or remove anything in it,
whether the build publishes, refuses, or fails.

The location is not a delivery location: a build reads no delivery from it, and Part 05 §2's rules
that a build supplies a delivery location empty and that an adapter does not rely on what one held
do not govern it. Builds at different packet roots MAY share one location. Removing what the
location holds outside any build, to bound its size, is an implementation's matter.

An adapter's **run** is its execution for one build. **Kept source data** is anything an adapter
uses in a run, in place of reading its source, that holds bytes read from a source before the run
began or is derived from such bytes, wherever it is kept and whatever keeps it.

An adapter MUST NOT use kept source data in a run unless, during that run, it has confirmed that the
source still holds the bytes the data holds or was derived from, or the URI those bytes were read
from names content that cannot change, such as an object version a store identifies. An adapter
confirms that a source still holds bytes only by comparing a value the source reports for the
object now, an entity tag, a full-object checksum, or a version identifier, with the same value
recorded when the bytes were read; a modification time, with or without a size, confirms nothing.
An adapter relying on an entity tag relies on the source to change the tag when the bytes change.
An adapter that cannot confirm reads its source, and within a run it MAY reuse what it read in that
run wherever it keeps it. No build or validator verifies this obligation, since neither observes
what an adapter keeps; an adapter complies in every case by reading its source.

A **storage format** is the layout in which an implementation keeps data in a source-cache location.
An adapter MUST keep what it stores in a source-cache location under one subdirectory of it, named
by an identifier of its storage format that the format's implementation controls, such as a package
or domain name it holds, and MUST NOT change or remove anything outside that subdirectory. A name
beginning `cache-v` is reserved for a storage format this specification defines, and an adapter MUST
NOT use one for any other. An adapter MUST NOT make data it stores there readable to another run
until the data is complete.

An adapter SHOULD keep the source data it keeps across builds only in the source-cache location the
build supplied it. Before using kept bytes, it SHOULD compare their size, and their full-object
checksum where the source reports one, with the source's, and it MAY remove from its own
subdirectory data that fails that comparison. How a storage format names, publishes, replaces, and
evicts what it keeps is the format's own. No build or validator verifies these obligations, since
neither observes the location's contents.

<a id="ew-adapter-interface-normative-references" data-spec-anchor="canonical"></a>
## 11. Normative references

The application column states the extent to which this part invokes each external authority:

| reference | candidate edition | application |
|---|---|---|
| [Apache Arrow columnar format](https://arrow.apache.org/docs/format/Columnar.html), [IPC](https://arrow.apache.org/docs/format/Columnar.html#serialization-and-interprocess-communication-ipc), and [Flight](https://arrow.apache.org/docs/format/Flight.html) | unversioned | Arrow data, IPC, and Flight |
