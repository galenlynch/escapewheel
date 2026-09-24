# An Adapter Declares Its Whole Contract and Delivers Only Where a Build Points It

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `cf0d686ee169a201849c0a0113d1c86982c9fb30` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 03 §§11, 11.1, 11.2, and 11.5; Part 04 §5.5; Part 05 §§2 and 3.5; Part 07 §4; `registry/adapter.schema.json`; `registry/sources.schema.json` |
| **Depends on** | [R80 §§2.2–2.4](../accepted/R80-a-source-resolution-document-locates-an-external-resource.md#2-decision); [R115 §§3.1, 3.3, 3.6, and 3.12](../accepted/R115-a-build-reaches-a-source-through-declarations.md#3-decision); [R117 §3.1](../accepted/R117-an-adapter-delivers-an-array-by-writing-it.md#3-decision); [R119 §3.4](../accepted/R119-an-adapter-declares-the-options-it-accepts.md#3-decision); [R133 §3.2](../accepted/R133-a-build-decides-ownership-only-from-the-recipe-and-adapter-declarations.md#3-decision) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5 |

Section 3 is normative. Sections 1, 2, and 4–7 are informative.

Normative keywords follow BCP 14.

## 1. Scope

A build reads what an adapter declares before it opens any source.
[Part 03 §11.5](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-adapter-declaration-document)
names the eight members of the declaration document an adapter publishes where a build cannot
import it, and
[Part 05 §3.5](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-recipe-check) lists
what a build refuses a declaration for. The document's schema is published but not incorporated,
and it requires four of the eight members. The prose gives two omissions a meaning and leaves the
other two without one. The reference writer checks a declaration's shape and refusals only where a
recipe names a document, so a class declaration escapes both, and it runs an independently released
adapter in process without the protocol Part 03 §11.1 requires it to declare. That section has an
adapter declare at least one protocol while the document holds only one, and nothing checks the
protocol a recipe names against the adapter's.

[Part 04 §5.5](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-source-resolution) has the
same gap for the source resolution document a reader follows. Its schema is published and not
incorporated, and the accepted rule that a reader refuses a document version it does not know
reached the prose only as a reference to that schema.

[Part 05 §2](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-import-pipeline) says a
source adapter returns records and writes no files.
[Part 03 §11](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-reaching-a-source)
has an adapter write a packet-owned array, a `files-v0.1` delivery, and a report into locations a
build supplies. Neither part says who owns those locations, so an adapter author cannot tell which
writes a build relies on.

This revision makes every declaration member required, lets `protocols` name every protocol an
adapter supports, and incorporates the declaration schema, so a build checks a class and a document
alike. It has a build reach an adapter by a protocol the adapter declares. It incorporates the
resolution schema, leaves validating a resolution document to the reader, and restores the version
rule. It replaces the no-write sentence with a rule saying where an adapter delivers and that the build owns those
locations. The rule governs only a delivery, so a cache of source bytes stays an implementation
matter that a later revision may still govern.

The change is structural because it replaces rules inside existing sections: Part 03 §11.5's
single `protocol`, its readings of an absent member, and its reference to a published schema; Part
03 §11.2's rule that declaring the protocol asks for its terms; Part 04 §5.5's reference to a
published schema; Part 05 §2's no-write sentence; and the descriptions of an adapter as returning
only records in Part 03 §11 and Part 07 §4. Appended sections would leave each contradicting its
replacement.

### 1.1 Structural crosswalk

Commit `18c6ba6` gave Part 03 §11.5, Part 05 §3.5, and Part 07 §4 their canonical anchors. Commit
`23e12d0` added `ew-reaching-a-source` to Part 03 §11, `ew-source-resolution` to Part 04 §5.5, and
`ew-import-pipeline` to Part 05 §2, and commit `cf0d686` added `ew-protocol-groups` to Part 03
§11.1 and `ew-build-supplied-values` to Part 03 §11.2. None changed anything else. No section is
added, moved, or retired.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| [Part 03 §11](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-reaching-a-source), an adapter reads one source and returns records | extend in place | same section | an adapter delivers through the channels and locations the profile names, listed there | §3.4 |
| [Part 03 §11.1](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-protocol-groups), an adapter declares and supports at least one protocol | extend in place | same section | out of process, a build reaches an adapter by the protocol its recipe entry names, which the adapter must declare, or else by any the adapter declares; in process, by none | §3.5 |
| [Part 03 §11.2](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-build-supplied-values), declaring the protocol asks for its terms | replace in place | same section | a build supplies the terms of the protocol it reaches the adapter by | §3.5 |
| [Part 03 §11.5](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-adapter-declaration-document), a shape published as a schema; a single `protocol`; readings of a document without `accepts` or `contributes` | replace in place | same section | the schema is incorporated, every member is required, `protocols` names a set, and a class is checked as the document holding its facts, which only an adapter a build ships may leave without a protocol | §§3.1, 3.2 |
| [Part 04 §5.5](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-source-resolution), a shape published as a schema | replace in place | same section | the schema is incorporated, a writer writes a conforming document, a reader may validate one, and a reader does not resolve through an unknown version | §3.3 |
| [Part 05 §2](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-import-pipeline), a source adapter returns records and writes no files | replace in place | same section | an adapter delivers only where a build points it, and the build owns those locations | §3.4 |
| [Part 05 §3.5](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-recipe-check), the declaration refusals | extend in place | same section | adds the refusal of a declaration failing its schema, in either form, and of a recipe naming a protocol its adapter does not declare | §§3.2, 3.5 |
| [Part 07 §4](../../escapewheel_poc_docs_v0.2/07_reference_implementation.md#ew-reference-object-model), an adapter's return type is records; an adapter names its protocol by a constant | revise the informative text | same section | rows are returned as records; an array and a report are written where the build points; an independently released adapter names its protocols by constants | §§3.1, 3.4 |

## 2. Background

Section 2 is informative. Every observation was reproduced at `63aa520` or a later commit up to the
recorded baseline, all sharing one code: the commits between them change only revision documents,
status records, and five canonical anchors. Probes ran in the writer's environment against `registry/logical_schemas.json`, using throwaway
recipes, adapter classes, and documents under a scratch directory.

### 2.1 The adapter declaration schema admits an incomplete document

`registry/adapter.schema.json` requires `kind`, `protocol`, `produces`, and `needs`, and closes the
object. A document carrying only those four validates with no error. Part 03 §11.5 says only that
the document's shape "is published as" the schema; under
[Part 00 §2.2](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-authority-by-concern), an
artifact acquires authority only where a numbered part expressly incorporates it.

Part 03 §11.5 reads a document without `accepts` as accepting no option beyond what it needs, and
one without `contributes` as declaring none. An absent `states` has no stated meaning, yet
[Part 05 §3.4](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-source-declarations)
requires a build to refuse a source whose stated fields it cannot determine, so the writer refuses
a document without `states` that the schema admits. An absent `consumes` becomes an empty list in
the writer's `declared()`.

`registry/adapter.example.json` carries all eight members, and no other declaration document is
tracked. The schema's `$schema` description binds a build with an uppercase keyword and cites Part
04 §5.4, which is about prefix resources; the `accepts` and `contributes` descriptions restate the
two readings of an absent member.

### 2.2 An adapter class escapes the declaration refusals

A class registered as kind `bogus` with `PRODUCES = {"core.tirals"}` and `ACCEPTS = ("root",)`
was checked by `Recipe.check`. Its errors named the undeclared resource through the ownership check
and nothing about `accepts`. The same facts rendered by `declaration.of` and passed to
`declaration.refusals` produced two refusals: `produces core.tirals, which no loaded registry
declares` and `accepts root, which is a term a build fills rather than an option a recipe sets`.
`Recipe._declaration_problems` skips every source without a `[source.delivery]` block, which is
every built-in adapter and every adapter registered through the `escapewheel.sources` entry-point
group.

Part 03 §11.5 already makes a class and a document one declaration, so the refusals bind a class
today and the writer's omission is a defect under the current rule. What the current rule lacks is
a shape check for a class, which has no JSON to validate until it is rendered.

No adapter class in the writer or the AIND package states a protocol. `escapewheel declare` takes
one as an argument, defaulting to `stream-v0.1`, and `declaration.of` writes whatever it is given.
A recipe running the AIND package's `session` adapter, which the `escapewheel.sources` group
registers, with `in_process = true` drew no protocol refusal from `Recipe.check`. Part 03 §11.1
requires an adapter released independently of a build to declare a protocol and a build to refuse
one that declares none, and says the in-process opt-in does not change what an adapter supports, so
this too is a defect under the current rule. An adapter a build ships need not declare a protocol,
so the document holding a built-in class's facts lacks a member the schema requires.

`sources.discovered()` loads each registered class and checks nothing about its declarations.
`escapewheel declare` renders a class with `declaration.of` and writes the result without
validating it; only the AIND package's tests check its generated documents against the schema.
`session.build`'s docstring says the recipe is "assumed already checked; `Recipe.check` is the
caller's job", and its body does not call it. The command line calls `Recipe.check` first, so the
gap is open to a caller of the Python function, which is the route an orchestrator takes. Part 05
§3.5 already requires a build to check a recipe before it opens any source.

### 2.3 An adapter declares one protocol where the profile has it declare a set

Part 03 §11.1, from
[R115 §3.3](../accepted/R115-a-build-reaches-a-source-through-declarations.md#3-decision), has an
adapter released independently of a build "declare and support at least one protocol in a group".
[R115 §3.12](../accepted/R115-a-build-reaches-a-source-through-declarations.md#3-decision) put
`protocol` among the document's keys, and the schema makes it a string, so a document names one.
The writer's `escapewheel deliver` serves any adapter class over each of the group's three
protocols, so an AIND adapter supports three and its document can state one.

A recipe's `[source.delivery]` block also carries a `protocol` (Part 05 §3.1). The writer reaches an
adapter by the recipe's protocol where the block names one and by the document's otherwise, and
compares neither with the other: a recipe naming `flight-v0.1` for the built-in `nwb` adapter,
whose generated document names `stream-v0.1`, drew no refusal from `Recipe.check`, and the build
would have reached the adapter by `flight-v0.1`. Part 03 §11.2 has a build supply "whichever terms
its adapter's protocol requires", on the ground that "declaring the protocol is what asks for it",
which presumes one.

### 2.4 The reader never applies the source resolution schema

Part 04 §5.5 says the source resolution document's shape "is published as"
`https://escapewheel.org/schemas/sources/0.1.0`. The reader vendors `sources.schema.json` and
exports `sources_schema()`, and `read_sources` checks only `sources_standard_version`. A document
whose entry carries `url` instead of `uri` and an extra top-level member raises `KeyError: 'uri'`
from `read_sources`; the schema reports all three defects. The reader reads the packet root's
`sources.json` inside a suppression of every exception, so a malformed one resolves nothing and
says nothing. The writer writes `sources.json` at commit without validating it.

[R80 §2.2](../accepted/R80-a-source-resolution-document-locates-an-external-resource.md#2-decision)
has a reader refuse a `sources_standard_version` it does not know rather than read the document as
if it did. The applied-clause ledger records that clause at Part 04 §5.5 through the schema, whose
`const` carries it, so a reader that does not validate has no stated version rule.

The schema restricts a source name to `^[A-Za-z0-9][A-Za-z0-9._:@+-]*$` and 512 characters. The
manifest schema's `source` is any string, and R80 §2.1 makes a source name opaque, so a packet can
carry a source that no conforming resolution document can name.

A registry is the precedent for leaving validation to a reader.
[Part 02 §2.7](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-resource-provenance-policy)
lets a reader expose resolved facts without validating the registry. Validating a resolution
document is cheap where validating a registry is not, but whether a reader validates changes only
how clearly it reports a malformed document, and never whether a packet is valid.

### 2.5 Part 05 §2 contradicts the delivery routes

Part 05 §2 closes on the rule that a source adapter returns records and writes no files. It
predates R115 and R117, which introduced the delivery routes; neither lists Part 05 §2 among the
sections it amends, and R117 §3.1 says that no adapter but one delivering an array writes anything.
The routes an adapter writes through are:

| location | supplied as | written by |
|---|---|---|
| a packet-owned array | `array_location` (Part 03 §11.2) | the adapter, as Zarr v3 (Part 03 §11.3) |
| a `files-v0.1` delivery | `delivery_root` | the adapter, as Parquet |
| a report | `report_path`, at the path the recipe names (Part 09 §5.8) | the adapter, under `files-v0.1` and `stream-v0.1` |
| a `flight-v0.1` socket | `socket` | the adapter binds it |

Part 03 §11 says an adapter "reads one source and returns records", and Part 07 §4 says an
adapter's return type is records, not a path, before describing an adapter that writes an array.
The writer's `sources/__init__.py` docstring says an adapter never writes.

The writer creates the other three locations under a workspace beside the packet,
`<out>.deliveries`, and removes it when it commits, so cleanup already belongs to the build; no part
says so. After a refusal the workspace stays, and the next build reuses it with
`mkdir(exist_ok=True)` and clears nothing. Under `files-v0.1`, `_read_files` reads every Parquet file under
`delivery_root`, so a rerun whose adapter no longer writes a resource reads the file an earlier run
left as that resource's delivery. This is from reading the code; it was not reproduced.

One write takes no supplied location. An adapter reading a remote store keeps fetched objects in a
cache, found from `ESCAPEWHEEL_SOURCE_CACHE` or else under `TMPDIR`. The cache holds source bytes
and nothing a build reads as a delivery. Governing it would mean defining at least its location and
lifetime, and its layout wherever adapters share one.

### 2.6 The writer's array delivery drifts from Part 03 §11.3

[Part 03 §11.3](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-referenced-resource-delivery)
has an adapter name each packet-owned array's directory by its catalog row's `resource_id` and a
build bind bytes to rows one-to-one. The writer names the directory by `array_asset_id` and writes a
`_resources.json` beside the arrays, which no part mentions and no schema checks; the build reads
the binding from that file. Bringing the writer to the current rule needs no specification change
and belongs with this implementation.

### 2.7 Alternatives

Keeping the four required members and defining each omission leaves a schema that cannot tell a
deliberate empty list from a forgotten key. Exempting `contributes` from the required members buys
nothing, since the regeneration that adds `states`, `accepts`, and `consumes` adds it too, and
leaves one member whose omission still needs a stated meaning. Leaving both schemas published and
unincorporated keeps a build checking a shape that governs nothing. Checking a registered class at
discovery would refuse a package before any recipe names it, so a broken package would stop a build
that never uses it. Requiring a reader to refuse a malformed resolution document would make a
broken optional `sources.json` stop a packet from opening, including its tables that need no
source. Deleting Part 05 §2's sentence without a replacement removes the contradiction and still
leaves an adapter author unable to tell where a build reads a delivery. Requiring a build to remove
its locations after a refusal would discard what a person diagnosing the refusal reads, and once a
build supplies each location empty, a location kept after a refusal cannot reach a later build.

Requiring every importable declaration to carry a protocol would withdraw Part 03 §11.1's exemption
for an adapter a build ships, and would check a fact that does not apply: running such an adapter in
process is what spares its rows a protocol. Checking a class on its other members and leaving the
writer's protocol gap to a later change would leave the adapters §2.2 names escaping one refusal
Part 03 §11.1 already requires.

Keeping a single `protocol` would have an adapter supporting three protocols state one, and would
leave the protocol a recipe names nothing to be checked against. Keeping the name `protocol` for an
array would name a set in the singular. Requiring a recipe to name a protocol wherever an adapter
declares several would add a line to a recipe for a choice no packet byte depends on, since a build
supports every protocol of the group and the rows are the same whichever carries them.

### 2.8 Feasibility and overlap

No other proposal or draft is open. The writer resolves a declaration through one function,
`declared`, whether it comes from a class or a document, and `declaration.of` renders a class as a
document once it is given a protocol, so checking a class as its document reuses the existing path
wherever the class states its protocols. A built-in class states none, so its check omits that
member alone. An independently released class needs a way to state its protocols, which the
writer's adapter classes do not yet have, and the AIND package's three adapters must use it. The
writer already chooses one protocol per source when it parses a recipe, and supplies the terms of
that protocol alone, and none for a source it runs in process. The writer's suite has 592 tests,
the AIND package's 67, and the reader's 228, all passing at the recorded baseline, and the full
repository verifier passed its 35 stages at `63aa520`.

## 3. Decision

Five subsections complete and incorporate an adapter's declaration document, check an adapter's
declaration alike whether it is a class or a document, incorporate the source resolution
document's schema while leaving its validation to the reader, say where an adapter delivers, and
say which protocol a build reaches an adapter by.

### 3.1 An adapter's declaration document states every member

Part 03 §11.5 incorporates `registry/adapter.schema.json`, whose `$id` is
`https://escapewheel.org/schemas/adapter/0.1.0`, as the exact shape of an adapter's declaration
document. The schema owns member names, JSON types, required members, closure, and patterns; the
prose owns what each member means and every refusal. The schema's descriptions are informative.

An adapter's declaration document MUST carry all eight members: `kind`, `protocols`, `produces`,
`contributes`, `states`, `needs`, `accepts`, and `consumes`. Each member listing names is an array.
`protocols` names every protocol the adapter supports, at least one and none twice; in any other
member, an empty array declares none. The schema requires all eight.

### 3.2 A build checks an adapter's class and document alike

A build MUST refuse an adapter's declaration that fails the schema §3.1 incorporates, naming where
it fails, before it opens any source. A build MUST check an importable declaration as the document
holding the same facts, so a class and a document are refused for the same defects under the same
terms. The one exception is `protocols`, which an importable declaration of an adapter a build ships
may omit, as Part 03 §11.1 lets it; the exception does not reach an adapter released independently
of a build, even where a recipe runs it in process.

### 3.3 A source resolution document has an incorporated shape a reader need not check

Part 04 §5.5 incorporates `registry/sources.schema.json`, whose `$id` is
`https://escapewheel.org/schemas/sources/0.1.0`, as the exact shape of a source resolution
document. The schema owns member names, JSON types, required members, closure, patterns, and the
version constant; the prose owns what each member means. The schema's descriptions are
informative. A source name is any string an external resource entry's `source` can hold.

A writer that writes a resolution document MUST write one that satisfies the schema. A reader MAY
validate a resolution document against the schema, and need not. A reader MUST NOT resolve a source
through a document whose `sources_standard_version` it does not know.

### 3.4 An adapter delivers only where a build points it

An adapter MUST deliver only through the channels and locations a build supplies it, and a
build MUST read a delivery from nowhere else. A build owns each location it chooses for a delivery:
it MUST supply the location empty, and MUST remove what remains of it once the build commits. An
adapter MUST NOT rely on a location outliving the build. This rule governs a delivery and nothing
else an adapter writes.

For the portable profile, Part 03 §11 names the routes:

- rows, returned in process where a recipe opts the adapter in, or across the protocol a build
  reaches the adapter by (§3.5), with a `flight-v0.1` adapter serving them at `socket`;
- a packet-owned array, written into `array_location`;
- a `files-v0.1` delivery, written into `delivery_root`; and
- a report, written at the `report_path` the recipe names (Part 09 §5.8).

### 3.5 A build reaches an adapter by a protocol the adapter declares

A build reaching out of process (Part 05 §3.9) an adapter that declares its protocols MUST reach it
by one of them: the protocol the recipe entry names, or any the adapter declares where the entry
names none. A build MUST refuse a recipe entry naming a protocol its adapter does not declare,
naming the source and the protocol, before it opens any source. A recipe opting an adapter into the
writer's process has the build reach it by no protocol, whatever the adapter declares.

An adapter a build ships need declare no protocol, and neither rule above reaches it: a build may
run it in process or serve it over any protocol of the group (Part 03 §11.1).

A build MUST supply the terms of the protocol it reaches an adapter by, and no other protocol's
(Part 03 §11.2); in process it supplies no protocol's terms.

## 4. What this does not change

An adapter's rows still reach a build as records whichever route delivers them, and a dense array
still crosses as bytes under `array_location`. A packet remains valid whatever resolution
documents exist, and structural validation still needs none.

## 5. Consequence

Packet bytes are unchanged, and no packet is rebuilt. An adapter's declaration document omitting a
member is refused until it states that member; the tracked example complies, and a generated document
complies by construction. A third party's hand-written document must be updated. An importable
declaration the writer now accepts with an undeclared resource, a term in `accepts`, or a malformed
name is refused at the recipe check. An independently released adapter that a recipe runs in
process and that declares no protocol is refused at the recipe check, as Part 03 §11.1 already
requires; the AIND package's three adapters declare all three protocols of the group. Every
declaration document replaces `protocol` with `protocols`, which a generated document does by
construction. A recipe naming a protocol its adapter does not declare is refused, and a build
supplies the terms of the one protocol it reaches an adapter by. A resolution document is refused
by no conforming reader merely for failing the schema, and a document a conforming writer writes always satisfies it. A
source name that the schema now refuses becomes resolvable. The schema `$id` versions stay until
release identifiers are assigned.

No accepted clause is superseded whole. R119 §3.4's reading of a document without `accepts` and
R133 §3.2's reading of one without `contributes` are replaced by §3.1; the rest of each clause
stands, and their ledger notes record the change. R115 §3.12's `protocol` key is replaced by §3.1's
`protocols`, R115 §3.1's rule that declaring the protocol asks for its terms by §3.5, and R115
§3.3's requirement of at least one protocol stands and gains the build's choice among them. R117 §3.1's sentence that no other adapter writes
anything is replaced by §3.4, and its rule for arrays stands. R115 §3.6 keeps an adapter's interface
records, and §3.4 leaves that intact for rows. R80 §2.2's version rule gains a stated owner in Part
04 §5.5.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. No scientific meaning changes. | None required. |
| logical prose and registry | Unchanged. Neither declares an adapter or a resolution document. | None required. |
| physical profiles | Part 03 §11 lists the delivery routes; §11.1 says which declared protocol a build reaches an adapter by; §11.2 supplies the terms of that protocol; §11.5 incorporates `registry/adapter.schema.json`, names `protocols`, requires every member, drops its readings of an absent `accepts` or `contributes`, and checks a class as its document, exempting only a built-in class from `protocols`. The schema replaces `protocol` with `protocols`, an array of at least one protocol name with no repeats, lists all eight members under `required`, its `$schema` description drops the keyword and the wrong citation, and its `accepts` and `contributes` descriptions drop the absent-member readings. | `evidence/R<N>.json` names the anchors; `registry/check.py` validates the example document, and a document missing a member or carrying an empty `protocols` fails. |
| packet manifest and JSON Schemas | Part 04 §5.5 incorporates `registry/sources.schema.json`, lets a reader choose whether to validate, and states the version rule. The schema drops its source-name pattern and length limit, and its `$schema` description drops the keyword. The manifest and delivery schemas are unchanged. | `registry/check.py` validates the example and a name with a space. |
| validation and import | Part 05 §2 states where an adapter delivers and that the build owns those locations; §3.5 adds the refusals of a declaration failing its schema and of a recipe naming a protocol its adapter does not declare. | The writer tests below. |
| extensions | Registry content unchanged. The AIND package's three adapters declare all three protocols of the group, and its generated documents gain any missing members and carry `protocols`. | The AIND suite validates its generated documents against the schema. |
| reader, writer, validator, adapters | The reader already resolves nothing through a document of unknown version. It validates a caller-supplied document, refusing one that fails with where it fails, and keeps treating a packet root `sources.json` it cannot read as resolving nothing. The writer lets an adapter class state its protocols by the constants it exports, checks a class declaration as its document at the recipe check, refuses there an adapter another distribution registers that states no protocol and a recipe protocol its adapter does not declare, renders a class's own protocols in `escapewheel declare`'s output and takes a repeatable `--protocol` only for a class stating none, validates `escapewheel declare`'s output and the `sources.json` it writes, runs the recipe check inside `session.build`, empties each delivery location before it supplies it, names array directories by `resource_id`, and binds arrays by catalog row without `_resources.json`. The validator is unchanged. | Reader and writer tests below. |
| conformance fixtures and tests | Packet fixtures are unchanged, because a validator reads neither document. Writer tests cover a document missing each member, a document of empty arrays, a class with an undeclared resource, a term in `accepts`, or a malformed name refused at the recipe check, an adapter another distribution registers that states no protocol refused at the recipe check while a built-in one passes, a document with an empty or repeating `protocols` refused, a recipe naming a protocol its adapter does not declare refused, a recipe naming none reaching the adapter by one it declares with only that protocol's terms supplied, the same adapter run in process with no protocol's terms supplied, `escapewheel declare` output passing the schema, `session.build` refusing a recipe that fails the check, a `sources.json` the writer writes passing the schema, array directories named by `resource_id`, a delivery location supplied empty after a refused run left files in it, and the workspace removed after a commit. Reader tests cover a caller-supplied document failing the schema, one of an unknown version, and a packet root document of an unknown version. | `escapewheel-writer`, `escapewheel-reader`, and `escapewheel-aind` suites. |
| revision process and tooling | Ordinary ledger and evidence records. The notes of R119 §3.4, R133 §3.2, R117 §3.1, R115 §§3.1, 3.3, and 3.12, and R80 §2.2 are rewritten, and R115 §§3.1 and 3.3 target Part 03 §§11.2 and 11.1 by anchor. | `ledger.py` and `evidence.py`. |
| generated publications and developer documentation | The combined specification and heading index regenerate. The writer and reader READMEs, `registry/README.md`'s incorporation column, the writer's `sources/__init__.py` docstring, and the repository TODO's schema-audit item are updated. | `verify.py`. |

## 6. Conformance and implementation evidence

Each clause is `applied`, each by its canonical anchor: §3.1 at Part 03 §11.5 and Part 07 §4; §3.2
at Part 03 §11.5 and Part 05 §3.5; §3.3 at Part 04 §5.5; §3.4 at Part 05 §2, Part 03 §11, and Part
07 §4; and §3.5 at Part 03 §§11.1 and 11.2 and Part 05 §3.5.

The negative cases distinguish the new rule from the current one:

- an adapter's declaration document omitting `states`, `accepts`, `consumes`, or `contributes` is
  refused, naming the member, where the schema now admits it;
- a document carrying a single `protocol` is refused, where the schema now requires it;
- a recipe naming `flight-v0.1` for an adapter whose document declares only `stream-v0.1` is
  refused, naming the source and the protocol, where the writer now reaches the adapter by
  `flight-v0.1`;
- a class declaring an undeclared resource, a term in `accepts`, or a `produces` entry that fails
  the schema's pattern is refused at the recipe check, where the writer now passes it;
- an adapter another distribution registers, run in process and declaring no protocol, is refused
  at the recipe check, naming the group, where the writer now passes it;
- `session.build` refuses a recipe that fails the check, where it now builds from it;
- a `files-v0.1` adapter that writes its Parquet outside `delivery_root` delivers nothing, and the
  build reports its resources as not arriving; and
- a rerun after a refused build, whose adapter no longer writes a resource, reads no file an earlier
  run left under `delivery_root`, where the writer now reads it as that resource's delivery.

The positive cases are a document of all eight members whose arrays other than `protocols` are
empty, which is accepted; a document declaring all three protocols, whose recipe entry names none
and which a build reaches by one of them, supplying only that protocol's terms; the same adapter
opted into the writer's process, which a build reaches by none and supplies no protocol's terms; a
built-in adapter declaring no protocol, which passes the recipe check; and a resolution document naming a source
whose name carries a space, which now satisfies the schema.
A document whose `protocols` is empty or names a protocol twice is refused, as the current schema
refuses any member it does not know. Two reader cases hold the restored and optional rules without
distinguishing them from current behavior: a resolution document of an unknown version resolves no source, and a caller-supplied
document failing the schema is refused by the reference reader, naming where it fails.

## 7. Open

A build-supplied location for an adapter's source cache is deferred. §3.4 does not forbid a write
outside a delivery location, so a later revision can add a cache location without amending it; that
revision would settle the location's lifetime, which would outlast a build, and how an adapter
declares an optional term, since Part 03 §11.5 lets it name a term only in `needs`.
