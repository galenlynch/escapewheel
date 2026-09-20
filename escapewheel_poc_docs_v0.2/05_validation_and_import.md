# Part 05 — Validation and Import

Normative.

## 1. Core principle

**Validation is importation.** Copying bytes into a packet directory is staging, not import.

A resource is imported when it has been discovered, extracted to staging, normalized to the logical schemas, validated, committed, and recorded in the catalog with its provenance.

A staged resource MUST NOT appear in the catalog as a committed canonical resource. Nothing becomes core data before it has passed the validators that apply to it.

## 2. Pipeline

| stage | action |
|---|---|
| 1 | discover what each source offers |
| 2 | extract candidate resources to staging |
| 3 | normalize to the logical schemas |
| 4 | validate the staged resources |
| 5 | commit |
| 6 | record provenance |
| 7 | materialize analysis resources |

A writer MUST NOT combine parsing, normalization, validation, and writing into one opaque step. A source adapter returns records; it MUST NOT write files.

## 3. The session recipe

### 3.1 Purpose

One source is rarely sufficient: integer sample indices come from a sorter, task structure and registration from an exported file, and session identity from acquisition metadata. The unit of work is therefore a **recipe** naming several sources, not a single input file.

A recipe declares, for one packet:

- each source: its kind, its root, and its options;
- which resources each source supplies;
- the clocks the packet declares, and their parents;
- what to materialize;
- session facts no source carries.

A recipe MAY declare a fact a source it reads also states; §3.6 says which of the two the packet gets. `core.subjects` is not a resource the recipe supplies unconditionally: a source that states a subject MAY own it, arbitrated as any other resource two sources can produce, and the recipe's `[subject]` block supplies the table only where no source owns it.

### 3.2 The recipe is the provenance record

A writer MUST record the recipe in the import run's parameters, and its digest as the run's `code_uri`. A committed packet therefore states what produced it.

### 3.3 Ownership

Each source declares its resources as `owns` or `contributes`.

| declaration | meaning |
|---|---|
| `owns` | this source is solely responsible; records another source emits for the resource are discarded |
| `contributes` | this source adds rows alongside others |

`contributes` exists because some resources genuinely have several suppliers. Without the distinction, the last adapter to run wins silently.

A recipe MUST NOT declare `owns` for a resource that more than one of its sources produces rows for, unless it declares a preference between them. Exclusivity is for a resource one source is responsible for; where two sources each hold part, `owns` discards the part the owner does not hold, and no check sees it because the resource is claimed.

A preference is declared in the recipe, in a table keyed by resource, each entry naming the source that owns it and the reason that source knows more. A build MUST apply a declared preference and MUST NOT hold a preference of its own for any resource a recipe does not name: a built-in winner is one no recipe can see, and a recipe that has not heard of a new contest is better refused than silently arbitrated.

A preference MUST NOT name a resource only one source produces. Such an entry arbitrates nothing and exempts a report that will never be due, so it is a claim no build tests, and it goes stale the moment the second producer stops producing.

### 3.4 What a source can produce

Every source adapter MUST declare the set of resource identifiers it can supply. It is static: a property of the adapter, readable with nothing open, and distinct from what a particular source root happens to hold.

An adapter declares five such facts, all read before any source is opened: the resources it can supply, the recipe fields it can state (§3.6), the values a build must supply it (Part 03 §11.2), the options it reads and can run without (Part 03 §11.2), and the kinds whose output it reads, which is what orders a build. An adapter a build cannot import publishes them as the declaration document Part 03 §11.5 specifies, where they are `produces`, `states`, `needs`, `accepts` and `consumes`; what an implementation calls them in code is Part 07 §4's.

A build MUST read a source entry that declares no `owns` as owning every resource its adapter declares it can supply and no other source owns. **A recipe states what it narrows; silence means the whole.**

Where two sources default to the same resource and no preference is declared, a build MUST refuse the recipe naming both.

A build MUST report rows a source produced for a resource another source owns, except where the recipe declares a preference between them. That another source claims it is not the exemption: a preference says two sources offer the same rows and names the one that knows more, and without one they are producing different rows. The neighbouring case, a resource *no* source claims, is reported as a warning before a byte is read.

A build MUST refuse where a preference discards a value another source stated: where a passed-over source's row holds a non-null value in a column the preferred source's row leaves null, or does not produce at all. Where a preferred source produces no rows for the resource and another does, that is the rule's limiting case. The comparison is over declared columns and not over `metadata`, which §8 of Part 02 makes schemaless by design, so two sources filling it differently is not a difference a build can weigh. That refusal is what makes the exemption above sound: the exemption rests on the loser's copy being redundant, and a preference is declared before either source is opened.

A build MUST NOT compose a row from more than one source. The merged row would be a fact no source stated. A recipe resolves the refusal by naming the fact in `[overrides]` with its reason, by preferring the other source, or by correcting the source that states less.

A build MUST also be able to determine, for each source a recipe names and without opening it, which recipe fields that source can **state**, and MUST refuse a recipe naming a source it cannot determine that for. What an implementation calls that declaration in code is Part 07 §4's, and the key it takes in a declaration document is Part 03 §11.5's.

### 3.5 Checking a recipe

A build MUST check a recipe against the registry before it opens any source. A build MUST refuse:

- a resource owned by more than one source;
- an owned resource the registry does not define;
- an owned table whose **required** foreign key targets a table nothing supplies;
- a clock declared twice, referenced but absent, or parented to nothing;
- a required source option that is not set.

A build MUST also refuse, on the same terms and before any source is opened:

- an adapter declaring a value Part 03 §11.2 resolves to neither a term nor a recipe option;
- an adapter declaring a term that list carries and this recipe cannot fill, naming the term and the source;
- an adapter declaring no protocol of a group the profile names, or one it does not name;
- a declaration whose resources include one no loaded registry declares;
- a declaration whose stated fields include one no recipe block carries;
- a source entry setting an option the adapter names in neither `needs` nor `accepts`, naming the source and the option;
- a declaration whose accepted options include a term, or one its `needs` also names.

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

### 3.7 When a source runs a command

A command that exits non-zero MUST fail the build, and a build MUST name the source whose command failed together with the resources that source owns, rather than reporting the first resource it then finds missing. A command belongs to a source and a source is not an extension: one command may produce tables of several extensions, so a finding naming one of them would be wrong about the rest.

A recipe MUST carry a command as an argument list, and a build MUST NOT derive one by splitting a string. A parse is a quoting convention the recipe never declared: POSIX rules applied on every host eat a backslash everywhere, so `C:\Python\python.exe` becomes `C:Pythonpython.exe` and fails as a missing executable rather than as a malformed command. A list needs no convention, because the host's own process interface takes one.

Where the command is one a build reaches a source through (Part 03 §11.2), the build MUST write what it supplies that source to the command's standard input and MUST close the stream when it has, without waiting for the command to exit, and MUST read what the command produces while it writes. A command that converts a raw source before it is read is not one of these and is supplied nothing. A pipe holds tens of kilobytes and a supplied object may be far larger, so a build that wrote one whole before reading rows would wait on an adapter that was waiting on it.

A build MUST capture a command's standard output and standard error, and MUST report them with a failure of that command. Where the command succeeds, a build SHOULD keep them readable afterwards. Where the recipe puts rows on standard output (Part 03 §11.1), a build MUST NOT report standard output as a diagnosis, and standard error is where a command that also emits data prints one. Holding them in memory is not what this asks: a command may run for minutes and its progress is worth watching while it does, so a build writes the streams to a file and reports that file and its last lines.

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

### 3.9 Whether a source runs in the writer's process

A build MUST deliver a source whose adapter declares a protocol out of process unless the recipe declares that it runs in the writer's, and a writer MUST NOT run such a source in process where the recipe does not say so. An adapter the build ships with declares none (Part 03 §11.1), so in process is its only route and a recipe naming one declares nothing: a build MUST NOT require a declaration where it offers no choice.

The recipe declares it because the recipe author chose the environment. One process resolves one dependency closure, so whether a given set of adapters installs together is a fact about one machine on one day rather than a property of any adapter, and the person assembling the recipe is the only party who can find out and the one who carries it when the answer changes.

What the opt-in buys is a saved transfer and what it costs is a solvable environment. A build that cannot import an adapter the recipe opted in MUST refuse, naming the source and the import that failed, before any source is opened.

## 4. Stages 1 to 3

### 4.1 Discover

For each source, report what it offers per resource, and how many rows. Discovery MUST NOT write to the packet.

### 4.2 Extract

Copy or stream candidate resources into a staging area under the packet root. A writer MUST stream a table whose row count is large rather than materializing it as host objects.

### 4.3 Normalize

Map source objects onto the logical schemas: assign identifiers packet-wide before any table is written, apply the declared sort, and coerce types to the registry's.

Normalization MUST be deterministic in the recipe. Two runs of the same recipe over the same sources produce the same packet.

An interval is closed (01 §2.3). A writer MUST convert a source whose intervals are half-open — `[start, stop)` — which is a subtraction on the stop bound. A writer MUST NOT carry a half-open bound through unchanged.

An adapter compensating for a known defect in its source MUST declare the compensation, and a writer MUST record every compensation applied in the import run's parameters. Choosing not to correct a known defect is equally a compensation and is declared as a pass-through.

### 4.4 When a source's delivery is complete

What a build expects of a source is the set of resources it owns, settled from `owns` and what the adapter declares before any I/O (§3.4). A run succeeded when every resource in that set arrived and the process exited clean.

A resource an adapter owns and has nothing for MUST arrive empty rather than not arriving (Part 03 §11.3). That is what makes the test usable: a build reads a resource that did not arrive as the run having failed, and never as the source having had nothing to say.

A non-zero exit is a failure whatever arrived. A build MUST report one as a failure even where every resource is present, because an adapter saying it failed is not overruled by its own output, and a command dying between two resources delivers the first one complete and valid.

A build MUST report a delivery it cannot parse as a failure where the command exited zero, naming what was short. What no protocol catches is a short table from a run that exits zero: where an adapter declares a row count a build MUST check it, and an adapter that cannot know its size before it sends declares none, which a build MUST read as unknown rather than as zero.

A build MUST report everything the protocol it used carries about a failure — standard error for `files-v0.1` and `stream-v0.1`, and the error's message together with its detail for `flight-v0.1`, where a failing adapter writes nothing to standard error because the diagnosis travels on the connection it was asked over. A build SHOULD try every resource it was waiting for and report every failure together rather than stopping at the first: the answer a person wants is which resources did not arrive, not which one did not arrive first.

## 5. Stage 4: Validate

### 5.1 Tier 1

Generated from structure (Part 02 §10.1): required-column non-null, primary-key uniqueness, foreign-key anti-joins, closed-vocabulary membership.

### 5.2 Tier 2

Declared per table as SQL returning offending rows, or as an expanded template (Part 02 §10.2).

### 5.3 The shim

A validator MUST check physical order, file presence, Parquet types, Zarr rank and codecs, and checksums outside SQL. A query cannot observe them, so such a check written as SQL fails silently rather than loudly.

A claim that crosses from the manifest to a table belongs here for the same reason. A resource's `processing_run_id` lives in the manifest, which no query sees, so the check that it names a run present in `core.processing_runs` is the shim's and not a foreign key.

### 5.4 Extensions

Each extension registry present is validated on the same terms as core, and its verdict is reported separately. A validator MUST NOT attribute a core failure to an extension, and MUST NOT let an extension failure invalidate core.

## 6. Stage 5: Commit

Commit MUST be atomic with respect to a concurrent reader:

1. write the staged resources;
2. validate them;
3. move resources into their final paths;
4. **publish** the packet catalog at `packet.json`, last and atomically.

A reader MUST observe either the previously committed catalog or the newly published one, and MUST
NOT observe a catalog naming a resource that is not yet in place. Every packet-owned
resource the catalog names MUST already be at its final location and MUST have passed validation
before it is published.

The publication mechanism is the profile's. A filesystem profile MAY publish by atomic rename
within one directory; an object-store profile MAY publish by a single-object write. A writer MUST
NOT be required to perform an atomic **directory** rename, which no object store
offers and which the packet layout does not need — the catalog is one object.

Where the store offers a conditional write, a writer publishing a new version SHOULD use it, so
two writers cannot silently overwrite one another's head. Where it offers none, a writer MUST NOT
claim it detected a conflict it could not detect.

A commit that finds an error MUST NOT write a manifest at the packet root, and SHOULD leave staging in place for inspection.

## 7. Stage 6: Provenance

Record `core.source_files` for the inputs, one `core.processing_runs` row for the import, and `core.processing_run_inputs` linking them. The run declares its `scope` and `scope_kind`.

## 8. Stage 7: Materialize

Materialization runs inside the import: core is staged, the staged packet is opened, derived resources are computed from it, and everything is validated together before anything is promoted.

Deriving into an already-committed packet is an amendment (03 §9.1), not part of an import.

## 9. Reporting

### 9.1 Findings

A finding declares a level, the check that produced it, and a message. Where a check is a query, the offending rows are the finding.

| level | meaning |
|---|---|
| `error` | the packet does not conform |
| `warning` | conformant, but likely not intended |
| `info` | recorded, not judged |

### 9.2 Error policy

An import MUST refuse to commit on any error.

A validator MUST NOT downgrade an error to make a packet pass. An advisory rule MUST NOT be an error (Part 02 §10.2), so enabling advisory checks cannot change whether a packet previously passed.

### 9.3 Comparison against a prior packet

Where an import replaces an existing packet, it SHOULD report every resource the prior catalog declared that the new one does not. This is a warning: narrowing is legitimate, and no other check sees a resource that is simply absent.

## 10. Two conformance classes

A report says which of two claims it is making.

**Packet conformance** is a property of the bytes. It is evaluated on a packet regardless of how the packet was produced, and it is what `validate` reports. Provenance is SHOULD within it: a packet carrying none is conforming.

**Writer conformance** is a property of a process. A writer conforms when it satisfies this part, which includes recording provenance for the import activity and the inputs it read. A packet is not judged by it.

A validator MUST report packet conformance, and MUST NOT report a packet as non-conforming for an obligation that binds only a writer. Where it also checks writer obligations — a build-time run inside `import`, which has the process in hand — it MUST report the two separately, as it already does for core and extension verdicts.

An analysis resource is where the two meet: `processing_run_id` is MUST for one, and that is a packet obligation rather than a writer's, because a derived resource naming no run is unreproducible whoever built it.

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

A recorded `sha256` therefore says what a packet's bytes **are**, not what a second build would
produce. Two conforming builds of one dataset may record different digests for the same rows.

## 12. Alternatives are resolved before a commit

Where two or more `core.processing_runs` rows share `(session_id, activity_type, scope_kind, scope)`, the packet **MUST** carry a `core.preferred_runs` row naming one of them, and a writer **MUST** refuse to commit one that does not. Where an activity has more than one run in a session, every one of those runs **MUST** declare `scope` and `scope_kind` — without a scope the runs cannot be grouped, so an ambiguity cannot be found rather than not existing.

Both are checked at `error` level. A consumer MUST NOT silently choose; on a conforming packet that case is unreachable. A consumer that meets an unresolved alternative is holding a packet that failed validation and reports that. Nothing here forbids a packet holding two sortings of one probe or two curations of one sorting; what it requires is that the packet says which is current.
