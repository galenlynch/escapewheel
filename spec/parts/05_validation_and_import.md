# Part 05 — Validation, Import, and Reader Operations

Normative.

<a id="ew-validation-import-scope" data-spec-anchor="canonical"></a>
## 1. Scope

This part binds four of the five actors of
[Part 00 §2.4](00_architecture.md#ew-specification-actors); it binds no checker. Its sections bind
each as follows:

| actor | sections |
|---|---|
| a writer, for each build it performs and each adapter it ships | §§2–4, 6–8, 9.2, 9.3, 11, 12, 14.4 and 15 |
| a validator | §§5, 9, 10, 14.5, 15.4 and 15.6 |
| a reader | §§13 and 14.3 |
| a consumer | §12 |

§3 also constrains a recipe, §6 what a reader observes of a commit, §12 a packet, and §§14.1, 14.2
and 14.6 and the first paragraph of §14.4 every implementation. §10 defines the two conformance claims.

<a id="ew-import-validation-principle" data-spec-anchor="alias"></a>
<a id="ew-import-pipeline" data-spec-anchor="canonical"></a>
## 2. Pipeline

**Validation is importation.** Copying bytes into a packet directory is staging, not import. A
resource is imported when a build has staged it, validated it with the whole staged packet,
promoted it, and published a manifest naming it, in the order this section states. A staged
resource MUST NOT appear in the committed manifest. Validation state does not change the content
class or canonicality selected by its declaration; publication is the gate.

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
[Part 03 §3.3](03_portable_physical_profile.md#ew-staging-area).

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
- which run is preferred among runs sharing an activity and scope (§12);
- session facts no source carries;
- each packet the build replaces (§9.3); and
- where it amends a packet, the version it amends (§15.1) and the held columns the amendment drops
  (§3.5).

A recipe MAY declare a fact a source it reads also states; §3.6 says which of the two the packet gets. `core.subjects` is not a resource the recipe supplies unconditionally: a source that states a subject MAY own it, arbitrated as any other resource two sources can produce, and the recipe's `[subject]` block supplies the table only where no source owns it.

A recipe is a [TOML 1.0](#ew-validation-normative-references) document. This part incorporates `artifacts/recipe.schema.json`, whose `$id` is `https://escapewheel.org/schemas/recipe/0.5.0`, as the shape of a recipe's decoded form. The schema owns the member names, types, required members, closure and patterns; this prose owns what each member means and every refusal of §3.5. TOML dates and times decode to values JSON Schema has no type for, so the schema leaves the facts under `[session]` and `[subject]` and a preferred run's `chosen_at` untyped. §3.6 types a fact when it normalizes it, and a build normalizes `chosen_at` to the type of `core.preferred_runs.chosen_at`. An omitted member keeps the meaning this part gives its absence. The table is an informative projection of the schema.

| member | form | constraint |
|---|---|---|
| `packet` | table | requires `id`; admits `amends`, a version matching `^\d+\.\d+\.\d+$`, `replaces`, a non-empty array of distinct non-empty strings, and `out`, `registry`, `extensions`, `description`, and `in_process` |
| `session`, `subject` | table | keys are field names; values are untyped |
| `overrides` | table | keys are field overrides, `session.field` or `subject.field`, and column overrides, `resource.column`; each value a non-empty string (§§3.4 and 3.6) |
| `encoding` | table | keys are `resource.column` names; each entry carries exactly `encoding`, one of `delta`, `plain`, or `dictionary`, and a non-empty `reason` (§3.8) |
| `clock` | array of tables | each requires `clock_id`, `name`, `tick_rate_num`, and `origin`, and admits `tick_rate_den` and `parent_clock_id` |
| `source` | array of tables | each requires `kind`; `owns` and `contributes` are arrays of dotted resource identifiers, `storage_options` a table, `in_process` a boolean (§3.9), and `delivery` a table admitting `command`, an array of strings (§3.7), and `protocol`, `declaration`, and `report_path`; every other key is an option |
| `preference` | table | keys are dotted resource identifiers; each entry is §3.3's |
| `preferred_run` | array of tables | each requires `activity_type`, `scope_kind`, a dotted resource identifier, `scope`, `processing_run_name`, and a non-empty `reason`, and admits `chosen_at` (§12) |
| `materialize` | array of tables | each requires `resource`; every other key is a parameter |
| `drop` | table | keys are `resource.column` names; each value a non-empty string; admitted only beside `packet.amends` (§3.5) |
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

`[packet].amends` gives the `packet_version` of the packet at the root the build writes, and makes
the build an amending build of that packet (§15.1).

`[packet].replaces` lists the packets a build replaces, each entry saying where the build reads one
(§9.3). This specification does not fix how a build resolves an entry to a packet, as it does not
for an `extensions` entry.

Each `preferred_run` entry names the run a build prefers among runs sharing the entry's
`activity_type`, `scope_kind` and `scope`, by that run's `processing_run_name`. An entry's `scope`
names the scoped row as
[Part 02 §8.3](02_core_logical_schemas.md#ew-discriminator-semantics) has a `string` paired value
name it: the row's key where that key is carried, and its `*_name` where it is assigned. A recipe
can therefore name a scope before any identifier is assigned. §12 states what a build writes for
each entry.

<a id="ew-recipe-provenance-record" data-spec-anchor="canonical"></a>
### 3.2 The recipe is the provenance record

A writer MUST record the recipe in the import run's parameters, and its digest as the run's `code_uri`. A committed packet therefore states what produced it.

A build decides which values of a recipe it recognizes as credentials. A value is the value of any
member the recipe states, an element of any array, or a component of either where it is a URI. A
build MUST document which values it recognizes. No checker verifies that it does.

A build MUST NOT include a value it recognizes as a credential in anything it composes and writes
to the staging area, to the packet, or to a source resolution document
([Part 04 §5.5](04_packet_catalog.md#ew-source-resolution)). A build composes the manifest, the
recipe it records, each other row it records for itself, the `core.source_files` rows among them
(§7), and the source resolution document. It does not compose what an adapter delivers, what a
command prints, or a row or resource the packet held before the build, and the rule reaches none of
these. Within the manifest, the `uri` of a referenced resource is one an adapter returned
([Part 12 §5](12_adapter_interface.md#ew-referenced-resource-delivery)), and §7 states what a build
owes there.

No validator checks this rule. Whether a string a packet holds is a credential cannot be decided
from the packet, so the rule binds the build, which alone knows what it recognized.

The recipe a writer records is the recipe the build read, differing from it in two ways and no
other. Where the build recognizes as a credential the whole value of a member or of an array
element, the record holds the string `[redacted]` under that member's name or at that element's
position. Where the build recognizes as a credential a component of a URI, the record holds the URI
without that component, as §7 has a build write it, and no marker stands in the component's place.

The run's `code_uri` is the digest of the recipe as the build read it, whatever the record
withholds.

A consumer MUST NOT take `[redacted]` in a recorded recipe for the value the build used. No checker
verifies this.

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

In an amending build (§15.1) the packet being amended is not a source. Ownership and preferences arbitrate among the recipe's sources only, and §4.3 settles each delivered row against the packet.

<a id="ew-source-declarations" data-spec-anchor="canonical"></a>
### 3.4 What a source can produce

Every source adapter MUST declare the set of resource identifiers it can supply. It is static: a property of the adapter, readable with nothing open, and distinct from what a particular source root happens to hold.

An adapter's static declarations, all read before any source is opened, are those Part 12 §7 specifies: among them the resources it can supply, those whose rows it supplies only in part, and the recipe fields it can state (§3.6). The kinds whose output an adapter reads order a build.

A build MUST read a source entry that declares no `owns` as follows. Of the resources its adapter declares it can supply, leaving out any another entry declares under `owns` and any a preference gives to another source, the entry contributes those its adapter supplies only in part and owns the rest. It also contributes every resource its own `contributes` names, and owns none of those. An entry that declares `owns` owns exactly what it names and contributes what its `contributes` names. **A recipe states what it narrows; silence means the whole.**

A build MUST refuse a recipe in which two entries without `owns` are left owning one resource, naming both sources and the resource.

A build MUST report rows a source produced for a resource another source owns, except where the recipe declares a preference between them. That another source claims it is not the exemption: a preference says two sources offer the same rows and names the one that knows more, and without one they are producing different rows. The neighbouring case, a resource *no* source claims, is reported as a warning before a byte is read.

A build MUST refuse where a preference discards a value another source stated: where a passed-over source's row holds a non-null value in a column a corresponding row of the preferred source leaves null, or is a row the preferred source does not produce. Where a preferred source produces no rows for the resource and another does, that is the rule's limiting case. The comparison is over declared columns and not over `metadata`, which §8 of Part 02 makes schemaless by design, so two sources filling it differently is not a difference a build can weigh. That refusal is what makes the exemption above sound: the exemption rests on the loser's copy being redundant, and a preference is declared before either source is opened.

For that refusal, a build MUST compare each source's row with the columns it fills when it stages a row already filled: the `session_id` [Part 02 §7.1](02_core_logical_schemas.md#ew-session-scope) has a writer fill, and any name of an owned assigned identifier ([Part 02 §8.2](02_core_logical_schemas.md#ew-identifier-semantics)) the build fills from the name its source delivered as the identifier ([Part 12 §5](12_adapter_interface.md#ew-referenced-resource-delivery)). Every other value is compared as its source delivered it.

A row of a passed-over source **corresponds** to a row of the preferred source where, so filled, the two hold equal non-null values in every column of the table's primary key. A row holding a null in a key column corresponds to no row. Where the preferred source delivers several rows with one key, each of them corresponds. A passed-over source's row to which no row of the preferred source corresponds is a row the preferred source does not produce.

A build MUST NOT compose a row from more than one source. The merged row would be a fact no source stated.

A column override (§3.6) names one column of a resource the recipe declares a preference for. Where a recipe carries one, a build MUST NOT refuse under this section over a value that a passed-over source's row holds in the named column and that every corresponding row of the preferred source leaves null, whether a row states a null or omits the column. The release reaches every such row and every passed-over source, and it reaches no other column. Where some corresponding rows state a value in the column and others leave it null, the build MUST refuse, and the column override releases nothing.

A build MUST still refuse over a row the preferred source does not produce, and over a preferred source that produces no rows while another source produces some. No column override releases either refusal.

A build that releases a value stages the preferred source's row as that source delivered it and discards the passed-over value, so the prohibition on composing a row from more than one source stands.

A recipe resolves a refusal over a null column by a column override, by preferring the other source, or by correcting the source that states less. It resolves each of the other two refusals by preferring the other source or by correcting a source.

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

A build MUST refuse, before it opens any source and naming the entry's key, a column override (§3.6):

- whose resource the recipe declares no preference for;
- whose column the resource does not declare, which includes every column named for a resource
  that is not a table;
- whose column is `metadata`; or
- whose column belongs to the resource's primary key.

A build admits a column override naming any other declared column of a preferred table, a
`required` column included.

A build MUST refuse a recipe that is not TOML 1.0 or whose decoded form fails the schema §3.1 incorporates, naming where it fails, before it opens any source.

A build MUST refuse, before it opens any source:

- a `[packet].replaces` entry at which it can read no published manifest, or one whose `packet_id`
  or `packet_version` is absent or does not satisfy the manifest schema, naming the entry;
- a recipe giving both `replaces` and `amends`; and
- two `replaces` entries at which it reads manifests of equal SHA-256, naming both.

A build MUST refuse, before it opens any source, a recipe with two `preferred_run` entries sharing
`activity_type`, `scope_kind` and `scope`, and one whose `chosen_at` it cannot normalize. It MUST
refuse, naming the entry, a `preferred_run` entry whose `processing_run_name` names no run the
packet holds or the build records, or names a run whose `activity_type`, `scope_kind` or `scope`
differs from the entry's.

A build MAY refuse, before it opens any source, a recipe carrying a value it recognizes as a
credential (§3.2), naming the member that holds the value, and the source where a source entry
holds it, and not the value. A build that does not refuse proceeds under §3.2 and §7.

An amending build (§15.1) MUST also refuse, before it opens any source:

- a packet root holding no published manifest, or one whose `packet_id` differs from `[packet].id`
  or whose `packet_version` differs from `[packet].amends`;
- a `[session]` member other than `session_id`, or a `session_id` the manifest's `sessions` does not
  list;
- a `[subject]` member, or a field override (§3.6);
- a `clock` entry whose `clock_id` equals the `clock_name` of a `core.clocks` row the packet holds;
- a registry it binds whose `logical_standard_version`, or for the core registry whose
  `semantic_standard_version`, differs from the manifest's, or that declares a table without
  `amendment_groups`; and
- a packet holding a null `*_name` for an assigned identifier a row owns.

An amending build MUST NOT refuse a column override on the ground that the build amends. A column
override in an amending recipe releases as §3.4 has it, among the recipe's sources only (§3.3).

An amending build MUST also refuse, before it opens any source and naming the table and the column,
a table resource the packet's current manifest names whose file holds a column that the table's
declaration, in the registry the build binds for it, does not declare
([Part 02 §6.1](02_core_logical_schemas.md#ew-undeclared-columns)), unless:

- a `drop` entry names that column; or
- a `materialize` entry names that resource, so that the build derives the table again rather than
  carrying its held rows.

A `drop` entry resolves the refusal in every case. Where the registry the packet's current manifest
binds under the registry ID of the table's declaration declares the column, a recipe also resolves
it by naming no registry under that ID, so that the build binds that registry (§15.1). The refusal
MUST name a `drop` entry as a remedy, and MUST name binding that registry only where that registry
declares the column.

A recipe's top-level `drop` table names held columns an amending build drops. An entry's key is a
resource's dotted identifier followed by a column name, spelled as a column override's key (§3.6),
and its value is a non-empty string saying why the recipe gives up the column's values. A recipe
carrying `drop` MUST give `[packet].amends`. Where a `drop` entry names a column that the file of the
resource the packet's current manifest names holds, an amending build MUST NOT refuse over that
column, and MUST write the table without it, whether or not it adds a row to the table (§4.3).

An amending build MUST refuse, before it opens any source and naming the entry's key, a `drop`
entry:

- whose resource the packet's current manifest does not name;
- whose resource a `materialize` entry also names; or
- whose column the resource's declaration, in the registry the build binds, declares.

A `drop` entry is **idle** where the packet's current manifest names no file of its resource that
holds its column. An amending build MUST report an idle entry as a warning and MUST NOT refuse on
it. It MUST report as information each column it drops, naming the table, the column and the
entry's reason. No checker verifies these reports or the remedies a refusal names.

For every other refusal of this section, the tables and clocks the packet holds count as supplied
and declared, so a required reference or a clock parent the packet satisfies draws no refusal.

A build MUST report as a **warning**:

- an owned table whose **nullable** foreign key targets a table nothing supplies;
- a resource some listed source declares in `PRODUCES` that no source claims;
- a field the recipe declares that some listed source states and no field override covers.

A warning is not an error because narrowing is legitimate, and only the recipe's author knows whether this one was meant.

A build MUST report as **information**, before it opens any source, a field the recipe declares that some listed source states and a field override covers, so that its reports list every field in which the recipe supersedes a source. No checker verifies this.

A column override covers no declared field, and draws neither report of a declared field nor the
report §3.6 makes of an override for a field.

<a id="ew-declared-fact-authority" data-spec-anchor="canonical"></a>
### 3.6 Authority for a declared fact

Where a recipe declares a fact and a source the same recipe reads states that fact, a build MUST report a difference between the two, naming the field, the declared value, the source's value and the file it came from. A build MUST refuse only where the fact identifies something a reader resolves across packets; otherwise it proceeds, and `--strict` refuses. `[subject].subject_id` is that case and the only one: a subject is not scoped to a session, so a wrong one agrees with another packet's animal instead of colliding with the true value.

Two values are compared at the type the packet will store, both normalized to it first. A source stating no value for a declared fact is not a disagreement: the declaration stands, a writer MUST NOT report it as a mismatch, and SHOULD note that it went unchecked.

A recipe's top-level `[overrides]` table holds two kinds of entry, and an entry's key says which it is. A **field override** has a key of two segments, `block.field`, whose block is `session` or `subject`, and declares that the recipe's own value for that field supersedes the source's. The value MUST be a non-empty reason. Declaring a field override is never required: it records a decision and silences the report, and a recipe declaring none is conforming. A build MUST report a field override for a field the source agrees with, or that no source states, and MUST NOT refuse on either.

A **column override** has a key of three segments, a resource's dotted identifier followed by one of
its column names, and §3.4 says what it releases. A recipe MUST give a column override a non-empty
string as its value, saying why the recipe gives up the value a passed-over source states.

A field override releases no refusal of §3.4, a field of `[subject]` included. A recipe that prefers
a source for `core.subjects` names a column of that table in a column override, and names a
`[subject]` field in a field override where it declares its own value for the field.

A build MUST report as information each column override that released a value, naming the column,
each passed-over source whose value it released, and the entry's reason. A column override is
**idle** in a build where it released no value. A build MUST report an idle column override as a
warning and MUST NOT refuse on it. No checker verifies either report.

The comparison needs the source read, so it happens as each source is built, and a build MUST refuse before any resource is staged. A source's statement of a fact is whatever its adapter exposes for that fact; which of several values inside a file it stands behind is the adapter's judgement and not the recipe's.

A fact the source **derives** is the source's. `core.sessions.session_start_time` and `session_end_time` come from the session source's declared stream windows, and a writer MUST use the source's value where a session source is present and MUST report a declaration it did not use rather than discarding it silently.

In an amending build (§15.1), the packet's `core.sessions` and `core.subjects` rows prevail over
every source for each fact they hold, derived facts included. A build reports a fact a source
states that differs from the packet's, as this section reports one differing from a declaration,
refuses where this section refuses, and otherwise keeps the packet's row.

<a id="ew-source-command" data-spec-anchor="canonical"></a>
### 3.7 When a source runs a command

A command that exits non-zero MUST fail the build, and a build MUST name the source whose command failed together with the resources that source owns, rather than reporting the first resource it then finds missing. A command belongs to a source and a source is not an extension: one command may produce tables of several extensions, so a finding naming one of them would be wrong about the rest.

A recipe MUST carry a command as an argument list, and a build MUST NOT derive one by splitting a string. A parse is a quoting convention the recipe never declared: POSIX rules applied on every host eat a backslash everywhere, so `C:\Python\python.exe` becomes `C:Pythonpython.exe` and fails as a missing executable rather than as a malformed command. A list needs no convention, because the host's own process interface takes one.

A build supplies a source on the standard input of every command it runs for that source, as Part 12 §4 requires, without waiting for the command to exit, and MUST read what the command produces while it writes. A pipe holds tens of kilobytes and a supplied object may be far larger, so a build that wrote one whole before reading rows would wait on an adapter that was waiting on it.

A build MUST capture a command's standard output and standard error, and MUST report them with a failure of that command. Where the command succeeds, a build SHOULD keep them readable afterwards. Where the recipe puts rows on standard output (Part 12 §3), a build MUST NOT report standard output as a diagnosis, and standard error is where a command that also emits data prints one. Holding them in memory is not what this asks: a command may run for minutes and its progress is worth watching while it does, so a build writes the streams to a file and reports that file and its last lines. A build MUST consume a command's standard output and standard error concurrently: one that read either to its end first would wait on a command that had filled the other's pipe. No checker verifies this.

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

<a id="ew-source-route" data-spec-anchor="canonical"></a>
### 3.10 A source entry names one route

A build MUST refuse a recipe in which a source entry carries a `delivery` table and sets `in_process` to true, naming the source, before any source is opened. The entry states two routes to one source and only its author knows which was meant, so a build choosing one would build something the recipe did not say.

`[packet].in_process` applies to each source entry that sets no `in_process` and carries no `delivery` table; an entry's `delivery` table is that entry saying otherwise. A build MUST NOT refuse a recipe for a `[packet].in_process` beside an entry carrying a `delivery` table.

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

A writer's normalization MUST be deterministic in the recipe and, for an amending build (§15.1), in
the content of the packet version it amends: two runs of one recipe over the same sources and the
same packet version produce the same packet. A packet's identifiers are therefore a function of the
sequence of recipes that built and amended it, each of which its import runs record (§3.2). A
single build over the same sources, where one recipe can name them all, reproduces them only where
it would number everything the amendments added after everything the packet held.

An amending build takes the packet's rows as delivered and normalized before any source runs, so
the terms of [Part 12 §4](12_adapter_interface.md#ew-build-supplied-values) include them. It
numbers a name the packet holds with the packet's identifier for it, and every other name from one
past the largest value the packet holds for that identifier, or from 0 where it holds none. It
orders the names it adds as a build orders a new packet's, so the units of a curation it adds are
numbered after every unit the packet holds.

It then settles against the packet each delivered row that ownership keeps (§3.3):

- a row of a non-canonical table the packet's manifest does not name is added;
- a row of `core.sessions` or `core.subjects` is dropped, the packet's row prevailing (§3.6);
- a row equal to one the packet holds, compared as §15.6 compares rows but for `metadata`, is
  dropped, together with any catalog instance the row catalogues;
- any other row of a table of class `documentation` that the packet's manifest names and that
  declares a primary key is added where no row the packet holds has its primary key;
- any other row is added where it forms, under at least one group list of its table (§15.2), a
  group the packet does not hold
  ([Part 02 §2.8](02_core_logical_schemas.md#ew-amendment-groups)).

An amending build MUST refuse every other delivered row, naming the table and the row, so it
refuses a delivered row of a documentation table that shares a held row's primary key and is not
equal to it. A table to which it adds no row and from which it drops no column (§3.5) keeps its
resource entry, so the amendment does not write it. A table from which it drops a column holds every
held row with its other columns' values unchanged, and the rows the build adds. A documentation table to which it adds rows holds the packet's rows and the added ones,
and the amendment replaces that resource as §15.2 permits. An amending build thereby adds sidecars
and scope rows to those a packet lists, and neither removes nor replaces one.

An interval is closed (01 §2.3). A writer MUST convert a source whose intervals are half-open — `[start, stop)` — which is a subtraction on the stop bound. A writer MUST NOT carry a half-open bound through unchanged.

A **compensation** is what an adapter does about a known defect in its source. Leaving a known
defect uncorrected on purpose is a compensation. A compensation states:

- an identifier, which is non-empty text that the adapter's author chooses;
- the defect, as non-empty text saying what is wrong at the source; and
- the action, as non-empty text saying what the adapter does about it.

A compensation MAY also state the evidence for the defect, as text. Two compensations with one
identifier and the same defect, action and evidence are one compensation.

An adapter MUST state to the build every compensation it applies in a run. An adapter that a build
runs in the writer's process states them by the means that build provides. An adapter reached by a
protocol (Part 12 §3) MUST state them in the table
[Part 12 §5](12_adapter_interface.md#ew-referenced-resource-delivery) gives a delivery for them. No
build or validator can check that an adapter stated every compensation it applied, so this rule
binds the adapter alone.

A writer MUST record every compensation stated to it in the import run's `parameters`, each with
its identifier, its defect, its action, and its evidence where one is stated. Where two
compensations stated to it share an identifier and differ in any other text, a writer MUST record
both.

A writer MUST examine a source in acquisition order and MUST NOT assume monotonicity. A reset is visible only in the order the samples arrived; sorting first hides it.

<a id="ew-delivery-completeness" data-spec-anchor="canonical"></a>
### 4.4 When a source's delivery is complete

What a build expects of a source is the set of resources it owns, settled from `owns` and what the adapter declares before any I/O (§3.4). A run succeeded when every resource in that set arrived and the process exited clean.

Part 12 §5 has a resource an adapter owns and has nothing for arrive empty, so a build reads a resource that did not arrive as the run having failed, and never as the source having had nothing to say.

A non-zero exit is a failure whatever arrived. A build MUST report one as a failure even where every resource is present, because an adapter saying it failed is not overruled by its own output, and a command dying between two resources delivers the first one complete and valid.

A build MUST report a delivery it cannot parse as a failure where the command exited zero, naming what was short. What no protocol catches is a short table from a run that exits zero: where an adapter declares a row count a build MUST check it, and an adapter that cannot know its size before it sends declares none, which a build MUST read as unknown rather than as zero.

A build MUST report everything the protocol it used carries about a failure, on the channel Part 12 §3 gives that protocol. A build SHOULD try every resource it was waiting for and report every failure together rather than stopping at the first: the answer a person wants is which resources did not arrive, not which one did not arrive first.

<a id="ew-import-validation" data-spec-anchor="canonical"></a>
## 5. Validate

<a id="ew-tier-1-validation" data-spec-anchor="canonical"></a>
### 5.1 Tier 1

Generated from structure (Part 02 §10.1): required-column non-null, primary-key uniqueness, foreign-key anti-joins, closed-vocabulary membership, the finiteness of every column declaring `finite: true`, and the uniqueness of the name of every owned assigned identifier.

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

For each table resource the current manifest names whose file's columns it reads, a validator MUST
report at `error`, naming the resource and the column:

- under the check ID `schema.column_absent`, a `required` or `nullable` column the file does not
  hold;
- under the check ID `schema.column_type`, a declared column the file holds at a type other than its
  declared type; and
- under the check ID `schema.column_undeclared`, a column the file holds that the resource's
  declaration does not declare
  ([Part 02 §6.1](02_core_logical_schemas.md#ew-undeclared-columns)).

A column of a packet-owned table is at a type other than its declared type where it is not at the
Parquet physical and logical type that
[Part 03 §5.1](03_portable_physical_profile.md#ew-table-encoding)'s type table gives that type, and
a column of an external table where it is at a type outside its declared type's family. For an
external table's column at another type of its family, a validator MUST instead report one finding
at `info` under the check ID `physical.outside_type_mapping`, naming the resource, the column, its
declared type and its observed Parquet physical and logical type, and MUST NOT report that column
under `schema.column_type`. Each finding concerns one resource, so
[§9.5](#ew-verdict-composition) attributes it to the registry whose declaration the resource's entry
names. The shim declares as the inputs of each check the packet manifest, which binds the registry
holding the declaration, and the table resource, so §15.4 re-runs each check on every amendment. A
file that only a superseded manifest names is not checked again.

For each dense array whose metadata it reads, a validator MUST report at `error`:

- a label row whose `position_index` is negative or not less than its axis's length;
- a label row whose `depends_on_position_index` is negative or not less than the length of the axis
  its axis row's `depends_on_axis_index` names;
- a position of a labelled axis with no label row, or, on a dependent axis, a pair of its position
  and a position of the axis it depends on with no label row;
- a `core.array_channels` row whose `channel_index` is negative or not less than the length of the
  axis its `axis_index` names; and
- for a packet-owned array, `dimension_names` that is absent or differs at any position from the
  axes table.

A validator finds an axis's label rows in the table that the `discriminates_via` of the axes
table's `coordinate_resource` names
([Part 02 §12.11](02_core_logical_schemas.md#ew-array-axis-coordinates)), and its names under
[Part 03 §6.4](03_portable_physical_profile.md#ew-array-metadata-placement).

A validator MUST assess floor membership for every packet-owned resource whose interface declares a
reader floor, and for every external one whose format-owned metadata it reads under
[Part 04 §5.3](04_packet_catalog.md#ew-external-resource-verification). Membership is judged under
[Part 03 §5.5](03_portable_physical_profile.md#ew-parquet-reader-floor) for Parquet and
[Part 03 §6.3](03_portable_physical_profile.md#ew-array-codecs) for Zarr. For each assessed resource
using a feature outside its floor, it MUST report one finding under the check ID
`physical.outside_reader_floor`, naming:

- the resource;
- its interface and, for Zarr, its variant; and
- the observed features that place it outside its floor: each outside compression or encoding for
  Parquet; the whole observed pipeline for Zarr v3; and for Zarr v2, `filters` and `compressor`
  where they match no metadata pattern, and `dtype` where the first character of one of its type
  strings is not a member of the floor's `dtype_byte_orders`.

Where a Zarr v2 array is outside its floor on both counts, a validator MUST name `filters`,
`compressor`, and `dtype` in the one finding it reports for the resource.

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
resource's entry names. §16 identifies the Unicode Standard, Version 15.0.0, as an exact reference
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

A validator SHOULD report a declared `metadata` column that a table resource's file omits or leaves
null in every row, at `info` under the check ID `<resource_id>.metadata_unfilled`. It MUST NOT
report such a column at `error`. The finding concerns one resource, so
[§9.5](#ew-verdict-composition) attributes it to the registry whose declaration the resource's
entry names.

A validator MUST check each session's declared time origin
([Part 01 §2.2](01_semantic_standard.md#ew-time-basis)) by mapping each of the session's
observation starts onto its reference clock, through the anchors or transform of every clock on the
path from that start's clock to the reference, within the alignment bound
[Part 02 §12.6](02_core_logical_schemas.md#ew-clock-alignment-record) records. It MUST report, at
`error`:

- under the check ID `time.origin_unmappable`, a session that declares an origin but no reference
  clock, or whose observation start does not map; and
- under the check ID `time.origin_not_earliest`, a declared origin more than one reference-clock
  tick from the earliest mapped start.

The tolerance is one tick because a writer's estimator may fit anchors the writer does not record.
Both findings belong to the core registry under [§9.5](#ew-verdict-composition).

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
([§15.3](#ew-superseded-manifest-retention)). A writer MUST
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

- one `core.processing_runs` row for the import, whose `activity_type` is `import`, declaring its
  `scope` and `scope_kind`;
- one `core.source_files` row for each distinct `root` among the recipe's sources (§3.1), whose
  `uri` is that root as the recipe states it, less each component in which the build recognizes a
  credential (§3.2); and
- one `core.processing_run_inputs` row linking each of those `core.source_files` rows to the import
  run.

A writer need not read a source to fill `sha256`, `size_bytes`, `format`, or `modified_at`, each of
which may be null.

Where a build recognizes a credential (§3.2) in a component of a URI the recipe states, it MUST
write that URI without the component wherever it writes it. Where an adapter returns for a
referenced resource ([Part 12 §5](12_adapter_interface.md#ew-referenced-resource-delivery)) a URI
carrying the same component, a build MUST write that URI without the component too. No validator
checks either rule, for the reason §3.2 gives. Two roots that are equal once such components are
removed are one root for this section.

An amending build (§15.1) records a `core.source_files` row only for a root among its recipe's
sources whose `uri` no `core.source_files` row of the packet carries, and links its import run to the
`core.source_files` row of every root among the recipe's sources, held or added. It compares a root
with the `uri` of each row the packet holds after removing from both every component it would
recognize as a credential.

<a id="ew-import-materialization" data-spec-anchor="canonical"></a>
## 8. Materialize

Materialization is step 5 of §2: a build opens the staged packet, computes each derived resource
from it, and writes the result to the staging area, so step 6 validates it with core before
anything is promoted.

Deriving into an already-committed packet is an amendment (§15.1), not part of an import. In an
amending build, materialization derives from the staged amended packet, and a derived resource
replaces the resource of the same ID the packet names.

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

<a id="ew-prior-packet-comparison" data-spec-anchor="canonical"></a>
### 9.3 Comparison against a prior packet

A build whose recipe gives `[packet].replaces` (§3.1) MUST record in its manifest's `replaces`
([Part 04 §3](04_packet_catalog.md#ew-packet-identifiers)) one item for each entry, carrying the `packet_id` and
`packet_version` of the manifest it read there and the SHA-256 of the exact bytes it read, and no
other item. No checker verifies this. It MUST set a `packet_version` whose major version exceeds
that of every named packet whose `packet_id` equals `[packet].id`.

Such a build SHOULD report, as a warning, every resource a named packet's manifest declares that its
own manifest does not. This is a warning: narrowing is legitimate, and no other check sees a
resource that is simply absent.

<a id="ew-incomplete-validation" data-spec-anchor="canonical"></a>
### 9.4 Incomplete validation

A report MUST distinguish an invalid registry rule, an unsupported selected language, an
incomplete valid evaluation, and a completed query that produced packet findings. A Tier 2
rule's evaluation is incomplete for a cause Part 11 §8 states. Any other evaluation a subject
requires is incomplete where an input it needs is unreadable, the engine evaluating it fails, or a
timeout or resource limit is reached. A validator MUST NOT turn its inability to evaluate into
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

**Writer conformance** is a property of a process. A writer conforms when it satisfies every obligation this part places on a writer, on a build it performs or on an adapter it ships, which includes recording provenance for the import activity and the inputs it read (§7), and meets §11's criteria. A packet is not judged by it.

A validator MUST report packet conformance, and MUST NOT report a packet as non-conforming for an obligation that binds only a writer. Where it also checks writer obligations — a build-time run inside `import`, which has the process in hand — it MUST report the two separately, as it already does for core and extension verdicts.

<a id="ew-writer-acceptance-criteria" data-spec-anchor="canonical"></a>
## 11. Minimum acceptance criteria

A conforming writer at least:

1. refuses a recipe that cannot produce a valid packet, before opening any source;
2. produces a packet that passes Tier 1, Tier 2, and the shim;
3. records provenance for what it read and what it ran;
4. leaves no manifest at the packet root when it refuses;
5. is **logically deterministic**: for the same recipe, the same source bytes, the same declared
   normalization and, for an amending build (§15.1), the same packet version amended, it produces
   the same canonical rows, the same values, the same assigned identifiers, the same resource
   identities and the same declared physical ordering. Identifier assignment MUST be a function of
   the recipe, the sources and, for an amending build, the content of the packet version it amends,
   never of wall-clock time, iteration order over an unordered collection, or the order a filesystem listed a
   directory.

Byte-identical output is **not** required and cannot be: a manifest carries `created_at` and
`validated_at`, and encoders may encode identical logical content differently between library
versions. A writer MAY offer a deterministic-build mode that pins those, and a validator MUST NOT
judge a packet non-conforming for lacking one.

A recorded digest therefore says what a packet's bytes **are**, not what a second build would
produce. Two conforming builds of one dataset may record different digests for the same rows.

<a id="ew-alternatives-resolved" data-spec-anchor="canonical"></a>
## 12. Alternatives are resolved before a commit

Where two or more `core.processing_runs` rows whose `activity_type` is not `import` share `(session_id, activity_type, scope_kind, scope)`, the packet **MUST** carry a `core.preferred_runs` row naming one of them, and a writer **MUST** refuse to commit one that does not. Runs whose `activity_type` is `import` are not alternatives to one another: two imports into one packet supply disjoint groups (§15.2). Where an activity has more than one run in a session, every one of those runs **MUST** declare `scope` and `scope_kind` — without a scope the runs cannot be grouped, so an ambiguity cannot be found rather than not existing.

Both are checked at `error` level. A consumer MUST NOT silently choose; on a conforming packet that case is unreachable. A consumer that meets an unresolved alternative is holding a packet that does not conform, and MUST report that, which no checker verifies. Nothing here forbids a packet holding two sortings of one probe or two curations of one sorting; what it requires is that the packet says which is current.

A build MUST write one `core.preferred_runs` row per `preferred_run` entry of its recipe (§3.1), in
the recipe's session, carrying the entry's `activity_type`, `scope_kind`, `scope`, `reason` and
`chosen_at`, and naming as `processing_run_id` the run whose `processing_run_name` the entry gives.
In an amending build, the row replaces the packet's row with the same primary key.
`core.preferred_runs.scope_matches_run` reports a preference whose `scope_kind` or `scope` differs
from its run's.

An amending build (§15.1) MUST give every run it records a `processing_run_name` the packet does not
hold, since §4.3 numbers a name the packet holds with the packet's identifier for it. Where a run it
records, of an activity other than `import`, shares its session, `activity_type`, `scope_kind` and
`scope` with a run the packet holds, the build MUST write a `core.preferred_runs` row naming it,
unless its recipe declares a preference of that key. A materialization run deriving a resource
again (§15.2) is such a run, as is the run of a curation added to a held sorting run.

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

<a id="ew-reader-discriminator-resolution" data-spec-anchor="canonical"></a>
### 13.4 Discriminator resolution

A reader SHOULD offer a discriminator's resolution in the shape
[Part 02 §8.3](02_core_logical_schemas.md#ew-discriminator-semantics) declares: read the kind, take
that resource's key from the registry, and join. A discriminator nothing reads is a free-form name
with extra steps, which is the observed fate of the mechanism it replaces.

<a id="ew-registry-conformance-boundaries" data-spec-anchor="canonical"></a>

## 14. Registry-document conformance boundaries

This section binds an implementation wherever it interprets a registry document. No checker
verifies a requirement of this section.

<a id="ew-checked-registry-context" data-spec-anchor="canonical"></a>

### 14.1 Checked registry context

A **checked registry context** is an immutable in-process association of the exact evaluated
registry input; its decoded JSON value when decoding succeeded; its complete Part 02 result;
immutable representations of the local descriptor set and external-domain capabilities used; and,
for an extension, the exact checked core context supplied to its evaluation.

For a byte input, the context MUST retain the exact bytes. For a mapping input, it MUST retain an
immutable structural copy made before checking and MUST record the skipped JSON phase that
Part 02 §9.4 requires. An implementation that a valid context authorizes to produce packet bytes or
registry-derived checks MUST use the decoded document in that same context, and MUST NOT reread the
source or use the caller's original mapping. A context in another state authorizes neither.

An implementation MAY reuse a context only while all its associated elements remain identical. It
MUST NOT take a path, declared version, mutable object identity, or digest under an unspecified
canonicalization as proof of that identity. This specification defines neither a portable result
cache nor a transferable validation receipt.

<a id="ew-registry-conformance-boundary" data-spec-anchor="canonical"></a>

### 14.2 Required boundaries

An implementation MUST obtain one complete Part 02 result before it interprets a registry to:

- publish or release that registry;
- start a packet build, before checking a recipe, opening a source, or staging output;
- construct a public writer directly from registry input;
- validate a packet using an embedded or caller-supplied registry;
- perform an extension-author registry check; or
- generate Tier 1, Tier 2, or another conformance check from registry declarations.

To obtain that result, an implementation that owns the registry's source bytes MUST use the
byte-oriented entry point of
[Part 02 §9.4](02_core_logical_schemas.md#ew-registry-conformance). An implementation given only a
decoded mapping MUST use the mapping-oriented entry point, which Part 02 §9.4 forbids to claim the
byte-level JSON checks. An implementation that generates conformance checks from a registry
document handed to it directly MUST either establish the checked registry context itself or require
one from its caller; a mapping accompanied by a result, a Boolean, or a caller's assertion does not
establish one.

<a id="ew-reader-registry-independence" data-spec-anchor="canonical"></a>

### 14.3 Reader independence

A reader MUST NOT require a registry result, checked context, or validation receipt to open a
packet, access its manifest or raw resources, present or correlate sessions, resolve
discriminators, references, or session scope, provide extension-aware access, or analyze one or
more packets. It MAY interpret declarations for those operations without making a conformance
claim, and the reference reader does not depend on the validator package to do so. An explicit
validation operation MAY evaluate the same input separately.

An unusable declaration need not produce a result for a reader operation. Its local failure or
partial-access behavior is not defined here, but ordinary analysis MUST NOT acquire a general
validation-receipt prerequisite.

A reader MUST NOT require a validation receipt or physical inspection of every resource to open a
packet's manifest, resolve its declarations, list its resources or select a session. Before exposing
a resource's logical values it inspects only the metadata that resource needs, and fails that
resource alone where it lacks support. Where the resource uses a format version or feature the
reader does not support, the reader MUST identify that version or feature in the failure.

<a id="ew-registry-producer-boundary" data-spec-anchor="canonical"></a>

### 14.4 Producer and authoring reactions

An implementation MUST complete the publication or release of a registry, or the generation of
registry-derived conformance checks, only from a `valid` context. An implementation performing an
extension-author registry check MUST report success only where the result is `valid`. For any other
state, the implementation MUST stop the publication, release, or generation, and in each case MUST
expose the complete result to its caller.

A writer MUST reject a non-valid registry before opening a source or staging output. A writer
whose public constructor accepts a registry as a mapping MUST copy and check that mapping before it
retains or interprets it. A writer that rejects a registry MUST NOT open an adapter for that build.
A writer that reports rejection by raising an exception MUST make the complete portable result
retrievable from it as structured data. A writer invoked from a command line MUST offer
machine-readable output containing the rejected registry's complete portable result. Authoring may
create an explicitly unfinished draft when it makes no conformance or publication claim.

<a id="ew-validator-registry-boundary" data-spec-anchor="canonical"></a>

### 14.5 Validator reactions

A validator MUST obtain a complete result for every bound registry whose decoded bytes match
their digest under [Part 04 §10](04_packet_catalog.md#ew-packet-manifest-conformance). For a
bound registry that cannot be acquired, Part 04 §10 makes `packet.registry.missing`,
`packet.registry.unreadable`, or `packet.registry.digest` the packet-level outcome. A validator
MUST supply the checked context it obtained for the bound core registry, and no other, to every
extension evaluation. Where it obtained none, Part 02 §9.4 gives the extension's result without a
usable core context. Where the core context is non-valid, the validator MUST still evaluate each
acquired extension as far as Part 02 §9.4 permits.

A validator MUST direct packet checks only from the checked contexts of bound registries that
passed the `registry_binding` phase. It MUST NOT substitute a caller-supplied, bundled, or remotely
resolved registry for a bound one. A validator MAY check a caller-supplied registry document on its
own under Part 02 but MUST NOT use it to direct packet checks or report its result as the
packet's.

Only a `valid` context directs generation or execution of registry-derived packet checks. For a
non-valid result, the validator MUST retain the complete result in its report, MUST skip every
dependent packet check, MUST preserve invalid outcomes as registry-document findings, and MUST NOT
fabricate packet findings for unsupported, incomplete, or skipped work. The validator MAY continue
checks independent of that registry.
[§5.4](#ew-validation-extensions) extends the packet checks to extension resources, and
[§9.5](#ew-verdict-composition) composes the verdicts. A non-valid required evaluation remains
insufficient to support a conformance claim.

<a id="ew-registry-result-reporting" data-spec-anchor="canonical"></a>

### 14.6 Portable reporting

A validator's report MUST pair each registry result with an external subject label. A bound
registry's label MUST be its registry ID, and the label of a registry the validator checked outside
the packet MUST distinguish its source. A validator MUST NOT let a subject label replace or
manufacture the registry document's own identity.

An implementation MUST expose a registry result through its public checking APIs, machine-readable
command output, validation reports, and structured exceptions in the same
[Part 02 §9.5](02_core_logical_schemas.md#ew-registry-result-serialization) representation, without
reducing it to a Boolean or an invalid-finding list. An implementation MAY render a result
differently for a person. Part 02 §9.5 keeps diagnostic `detail` out of conformance, equality, and
ordering.

<a id="ew-packet-amendment" data-spec-anchor="canonical"></a>
## 15. Amendment

An amendment publishes a new version of an existing packet. This section binds under every profile.
[Part 00 §7.3](00_architecture.md#ew-later-physical-profiles) has each profile say how it realizes
an amendment, and [Part 03 §9](03_portable_physical_profile.md#ew-portable-amendment) does so for
the portable profile.

<a id="ew-packet-version-scope" data-spec-anchor="alias"></a>
<a id="ew-amendment-definition" data-spec-anchor="canonical"></a>
### 15.1 What an amendment is

An **amendment** produces a new version of an existing packet. A writer performing one MUST NOT
modify the bytes of any resource a superseded manifest names, and MUST set a `packet_version` that
sorts strictly after the superseded one, compared as a semantic version, and has the superseded
one's major version ([Part 04 §3](04_packet_catalog.md#ew-packet-identifiers)). The amended manifest MUST carry
`replaces` exactly as the superseded manifest does, or omit it where that manifest omits it. It MUST
carry `created_at` exactly as the superseded manifest does, so that the member records when the
amended packet was first built and its validation block records when it was last validated; no
checker verifies this.

`packet_version` versions the bundle. A writer MUST NOT increment it for a rewrite of a table's
rows.

An amendment **writes** a resource that the amended manifest names and the superseded manifest does
not name at the same `uri`. A resource an amendment writes is realized by its profile;
[Part 03 §9](03_portable_physical_profile.md#ew-portable-amendment) has the portable profile write
it as a new file.

A build whose recipe gives `[packet].amends` (§3.1) is an **amending build**. It performs an
amendment of the packet at the root the build writes, and it is bound as an amendment wherever this
part binds a build and an amendment differently. `amends` is the `packet_version` of the packet's
current manifest. An amending build binds each registry its recipe names, and each registry the
packet's current manifest binds under an ID for which the recipe names none, unless that registry
is an extension registry that has no required singleton and declares none of the amended
manifest's resources ([Part 04 §8](04_packet_catalog.md#ew-packet-registry-bindings)). Its writer
MUST report each registry it leaves out this way, naming its ID, which no checker verifies. The
amended manifest keeps the packet's `description` unless `[packet].description` gives one. §§3.3, 3.5, 3.6, 4.3, 7,
8 and 12 state where an amending build differs from a build of a new packet.

<a id="ew-amendment-scope" data-spec-anchor="canonical"></a>
### 15.2 What an amendment may change

A writer performing an amendment MAY make, and MUST NOT make, these changes:

| change | |
|---|---|
| Add a resource the superseded manifest does not name, other than a canonical table | MAY |
| Add to a canonical table, whether or not the superseded manifest names it, rows each forming, under at least one of the table's group lists, a group the superseded version does not hold ([Part 02 §2.8](02_core_logical_schemas.md#ew-amendment-groups)) | MAY |
| Replace a `core.preferred_runs` row with a row of the same primary key | MAY |
| Remove or replace an analysis, compatibility-projection or documentation resource | MAY — Part 06 makes analysis resources disposable |
| Change or remove any other row of a canonical table | MUST NOT |
| Change a canonical resource that is not a table, or remove a canonical resource | MUST NOT |
| Change `packet_id`, `profile_id`, the standard versions, the major version of `packet_version`, or `replaces` | MUST NOT |

A table's group lists are those its declaration carries in the registry the amended manifest binds.
Every added row forms a new group under at least one of them, so a group a table declares under its
only list, such as a session's trials or a curation's units, never grows: nothing in a packet
records which derived results read which rows. A group a held row describes is held before it has
rows, so a stream the packet holds gains no events and a unit it holds no observation intervals,
even where the packet holds none. Under a table's other lists an added row may join a held group, as
a new registration's coordinates join each held unit's under `core.unit_coordinates`' first list.

The asymmetry is the design: an amendment **extends** what a packet says and does not revise it. A
packet whose canonical data was wrong is therefore corrected by a replacement naming it
([Part 04 §3](04_packet_catalog.md#ew-packet-identifiers)), which MAY keep its `packet_id` at a greater major version. A
correction is a replacement, not an edit and not an amendment.

A preference is the one row an amendment may replace. Replacing one changes no row a run produced,
and the superseded version keeps the replaced row. An amendment removes no preference, so an
alternative §12 resolved stays resolved.

A writer performing an amendment that writes a canonical table other than `core.processing_runs`,
`core.source_files` and `core.processing_run_inputs` MUST derive again from the amended packet, or
remove, every analysis and compatibility-projection resource whose `derived_from` chain
([Part 04 §7](04_packet_catalog.md#ew-resource-lineage)) reaches that table. The three provenance
tables are exempt because their rows record what ran, not what was measured.

A row of a canonical table is compared over the columns its declaration declares in the registry
the amended manifest binds, as §15.6 compares rows, so an amendment that removes a column that
declaration does not declare (§3.5) changes no row. An amendment that writes a canonical table only
to remove such a column writes that table, and the duty above to derive again or remove holds as
for any other written table.

<a id="ew-superseded-manifest-retention" data-spec-anchor="canonical"></a>
### 15.3 Superseded manifests

A packet retains every manifest its amendments superseded, and no manifest of a packet its
manifest's `replaces` names. A writer retaining a superseded manifest MUST retain its exact bytes,
so that an item naming that version is confirmed from the retained copy; no checker verifies this.
Retaining them lets a later cleanup distinguish a file an old version
named from a file nothing ever named. A retained manifest keeps its own `created_at` and its own
validation record, which a writer performing an amendment MUST NOT rewrite.

Where an amendment binds a different registry document, the packet retains the superseded copy at
the path the superseded manifest records. A writer MUST refuse an amendment that would bind,
anywhere in the packet's current and retained manifests, two different digests under the same
registry ID and version, because that version would then be ambiguous within one packet.

<a id="ew-incremental-revalidation" data-spec-anchor="canonical"></a>
### 15.4 Scope of revalidation

A writer performing an amendment MUST validate the whole packet, not only what it added. What is
bounded is the *work*, not the verdict: the resources an amendment did not write are immutable, so
their verdict is determined rather than assumed, and re-establishing it costs nothing.

A writer performing an amendment MUST establish the physical order of the resources it writes, and a
validator MUST NOT require it to re-establish that order for any other packet-owned resource.

A validator MUST derive a complete input set from the layer that owns each check. A generated
Tier 1 check takes its inputs from the registry declarations that generated it: the attached
resource, both ends of a foreign key, and every specialization or discriminator branch it reads.
A Tier 2 check takes its inputs from the parsed base-resource set Part 11 §3 requires static
validation to return. A §5.3 shim check declares its inputs explicitly.

A validator MUST re-run a check when it is attached to a resource the amendment writes or any
member of its input set was written. A Tier 2 dependency MUST NOT be inferred by searching query
text: an alias, common table expression, literal, or comment that resembles a resource does not
create one. The session-inventory shim declares the packet manifest and `core.sessions`; installing
a manifest writes the manifest input for this purpose. A shim without a complete declaration MUST
run rather than be skipped.

A validator **MUST make that test over-inclusive where it is uncertain**. Matching a resource name
inside a string literal or a comment re-runs a check that did not need it, which costs time; failing
to match one costs correctness. A validator that cannot show an input is immutable MUST run the
check: skipping a check whose inputs *could* have changed stays forbidden.

<a id="ew-packet-cleanup" data-spec-anchor="canonical"></a>
### 15.5 Cleanup

Cleanup is a separate operation. A writer SHOULD offer it over a committed packet, since nothing
else removes what an amendment leaves behind; a writer that performs no amendment leaves nothing
for it to remove. A writer performing cleanup MUST remove orphans before superseded
manifests: expiring a manifest first would make an orphan indistinguishable from a stray,
permanently.

A writer MUST NOT remove a stray, which the packet's profile defines. A packet may carry files this
specification does not govern, and cleanup that deletes the ungoverned is a data-loss bug wearing an
operation's name. A writer performing cleanup MUST NOT remove anything unless it was asked to
remove, and MUST otherwise report what it would remove. No checker verifies a writer's cleanup.

A writer performing an amendment **MUST NOT** delete anything as part of amending, other than a
staging area as §2 permits and the paths §6 lets it remove when it acts on a promotion record. A
file that no manifest version names any longer MAY be deleted, but by cleanup, as a separate
operation — which is what keeps an amendment's failure from having removed something.

A packet MAY declare its own retention, and a writer SHOULD emit one: how many superseded manifests
to keep, and an optional age beyond which one may be dropped. Both are **floors** — a manifest is
expired only when both permit it — and both default to one kept version and no age limit, because a
packet is archival where a table is operational.

<a id="ew-amendment-comparison" data-spec-anchor="canonical"></a>
### 15.6 Comparison with the superseded version

A validator given a packet that retains a superseded manifest, and a writer validating an amendment
under §15.4, MUST compare the current version with the superseded version whose `packet_version`,
compared as a semantic version (§15.1), immediately precedes the current one, and MUST report each
of these at `error`:

| check | finding |
|---|---|
| `amendment.identity_changed` | the two manifests differ in `packet_id`, `profile_id`, `semantic_standard_version`, `logical_standard_version`, the major version of `packet_version`, or `replaces`, where an absent member differs from any present one and two arrays differ unless they hold equal items in the same order |
| `amendment.resource_changed` | a canonical resource the superseded manifest names that the current manifest does not name, or names at another `uri` where the resource is not a table |
| `amendment.row_changed` | a row of a canonical table both manifests name and the amendment wrote, which the superseded version holds and the current version does not hold unchanged |
| `amendment.group_grown` | a row of a canonical table the amendment wrote, which the current version holds and the superseded version does not, where the table declares no group list, or where under every group list the superseded version holds the row's group ([Part 02 §2.8](02_core_logical_schemas.md#ew-amendment-groups)) |
| `amendment.derived_resource_stale` | an analysis or compatibility-projection resource both manifests name at the same `uri`, whose `derived_from` chain in either manifest reaches a canonical table the amendment wrote other than the three provenance tables |

A table's rows are compared as a multiset over the columns the amended manifest's registry declares,
matched by name: an `optional` column a file omits holds null under
[Part 02 §6.3](02_core_logical_schemas.md#ew-absence), and values compare as
[Part 11 §5](11_tier_2_rule_language.md#ew-tier-2-deterministic-semantics) compares them, a null
equal to a null. Neither `amendment.row_changed` nor `amendment.group_grown` reports a replaced
preference: a `core.preferred_runs` row of the superseded version and the current version's row
with the same primary key. Group lists are those of §15.2. A validator attributes each finding
under §9.5.

Where the superseded version cannot be read, the comparison is an evaluation the packet requires
that did not complete (§§9.4 and 9.5), and not a finding. A packet that retains no superseded
manifest has nothing to compare. Each earlier version was compared with its own predecessor by the
writer that amended it, and retention may since have removed its files, so a validator compares
only this pair.

<a id="ew-validation-normative-references" data-spec-anchor="canonical"></a>
## 16. Normative references

The application column states the extent to which this part invokes each external authority:

| reference | candidate edition | application |
|---|---|---|
| [TOML v1.0.0](https://toml.io/en/v1.0.0) | exact | a session recipe's syntax and decoded values (§3.1) |
| [The Unicode Standard, Version 15.0.0](https://www.unicode.org/versions/Unicode15.0.0/) | exact | canonical caseless matching of payload names, Section 3.13, definition D145 (§5.3) |
