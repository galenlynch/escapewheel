# Refactor before the v0.2 release

A mid-level audit of the four packages, the repository scripts and the specification tooling ran
on 2026-10-01 against commit `f30864e`. This document records what the audit found, the rules the
refactor applies, and the work in the order it will be done. It tracks implementation work only:
it changes no packet contract, and where an item turns out to need a specification or process
change, that item goes through `revisions/` and is marked so here.

Tick an item when its commit lands. Figures below were measured at `f30864e` and are not
maintained; the tick marks are.

## 1. What the audit found

The package boundaries hold. Imports run reader ← validator ← writer ← aind and form no cycle. The
problems are below that level, and the same four recur in every package and in the tooling.

**Errors have no taxonomy.** The validator and the writer define no base exception class. The
reader defines `PacketError`, and 5 of its 17 exception classes derive from `ValueError` instead.
A caller that needs to tell two failures apart reads the message: `match=` appears 58 times in the
reader's tests, 110 times in the writer's and 12 times in aind's. Ten of those tests match text
that another package wrote.

**Shared vocabularies are declared nowhere.** Check IDs, finding levels, verdicts, validation
states and resource IDs are string literals wherever they are used. The validator emits 71
distinct literal check IDs and declares none of them; the writer, the corpus and the integration
tests compare against the same literals. No package defines a `Protocol`, an enumeration or a
`TypedDict`.

**The adapter contract exists by convention.** A build reads about fifteen members of a source
adapter by `getattr` or `hasattr`, and the writer's `CONTRIBUTING.md` names three. The adapters
disagree about empty tables, about whether `offers()` is derived, and about how rows stream.

**The declared public surface differs from the one in use.** A package's `__all__`, its `api.rst`
and the names other packages import are three different sets. The aind package overrides five
underscore-private methods of `NWBSource`, calls two more and imports the private helper `_clean`.

Several modules also hold more than one job, and §7 lists them. Size is the smaller problem: the
splits are moves once the four problems above are settled, and they are hard before that.

## 2. Settled decisions

| subject | decision |
|---|---|
| scope | All five stages land before the release. |
| error root | The reader defines `EscapewheelError`. `PacketError`, `ValidatorError` and `WriterError` derive from it, and the shared command line catches it. A refusal before a build exits with status 2 and a refused commit with status 1, as now. |
| old import paths | Dropped. Only the two documented tiers of §6 remain importable by another package, and no module re-exports a moved name for compatibility. |
| adapter contract | `into()` is deleted, since no build calls it. `SessionSource.offers()` is derived from its records like the others. The five `NWBSource` hooks that aind overrides become public names. |
| check IDs and the specification | The specification need not name every check ID. The validator declares every ID in one table, which records for each whether a part names it, and a test compares that flag with the parts. |
| ledger fidelity | A check that an applied clause's text is still present goes through `revisions/` as a process proposal; §9 describes the preferred form. |
| fixture spelling | Test fixtures write `validator_name` as `escapewheel_validator`, as the writer and Part 08 do. |
| resource-ID constants | One hand-kept module in the reader names the resource IDs that code refers to, and a test checks each against the registry. |

## 3. Rules the refactor applies

### 3.1 Errors

- Every exception a package raises on purpose derives from that package's base class. A class
  keeps a built-in second base (`ValueError`, `KeyError`, `LookupError`, `FileExistsError`) where
  a caller already catches the built-in.
- Where a caller or a test now reads a message to learn a fact, the exception carries that fact as
  an attribute: a resource ID, a reason code, a row position, a list of problems.
- No package catches or asserts on another package's message text. A test of package A that
  expects package B to refuse asserts B's exception class and attributes.
- Within a package, a test asserts on a code or an attribute where one exists. Matching message
  text remains acceptable only for wording a person reads and no code depends on.
- A command-line entry point lets no deliberate refusal escape as a traceback.

### 3.2 Coupling between packages

- A package imports from another package only names in that package's two documented tiers (§6).
- No package imports, overrides, patches or reads an underscore-prefixed name of another package.
- A literal that two packages must agree on has one definition, in the lowest package that uses
  it, and the others import it.

### 3.3 Specification citations in code

The four packages carry about 1,235 section citations in `src`: 189 in the reader, 214 in the
validator, 752 in the writer and 80 in aind. In the auditors' samples of 40 per package, between a
quarter and a half cited general background or repeated a citation already made in the same
function or class.

- Cite a section once, at the function, class or constant whose behaviour that one rule fixes.
- A helper, a delegate or a later line of the same definition does not repeat the citation.
- A message cites a section only where its reader can act on that section.
- No test matches on a citation.
- A citation names the current part and section, never the revision that introduced the rule, and
  carries no history.

`revisions/check_citations.py` and `revisions/repoint.py` keep passing throughout.

### 3.4 Each step

Each step is one commit that leaves its package's suite and `verify.py` passing. A step preserves
behaviour unless this document says otherwise. A move and a behaviour change never share a commit.

## 4. Defects the audit found

These are wrong today whatever the shape of the code. Each is fixed in the stage named.

- [x] `escapewheel import` exits with a traceback on most build failures. Its call to `build`
      handles only `RegistryRejected`, so `RecipeError`, `SourceDefect`, `PayloadRefused` and
      `NotCommitted` escape, and the shared entry point catches only the reader's `PacketError`.
      Stage 1.
- [x] `UnsupportedEncoding` is not a `SourceDefect`, and only the NWB adapter and aind's unit-QC
      adapter catch it, so the sorter, waveform and LFP adapters fail with a traceback. Stage 1.
- [x] The validator builds the check ID `packet.registry.<reason>` from the free-text `reason` of
      the reader's `RegistryUnavailable`. Stage 1.
- [ ] An adapter served out of process loses its compensations. The build reads `compensations`
      from the source object, and the delivery module never carries the attribute across.
      Stage 2; if the delivery report needs a new key, that part is a specification change.
- [x] Three fixture builders write `validator_name` as `escapewheel_validate`. Stage 2.
- [x] The validator's test registry declares `core.trials`, which the core registry does not
      have. Stage 5.
- [ ] `BATCH_ROWS` has three definitions and two values in the writer. Stage 2.
- [ ] The ledger checks that an applied clause's target exists and never that its text is there,
      and nothing reads a superseded entry's `by`. §9.

## 5. Stage 1: errors

### 5.1 Reader

- [x] Add `EscapewheelError` and make `PacketError` derive from it.
- [x] Move every exception class into `errors.py` and under `PacketError`: `NotAligned`,
      `Unanchored`, `StaleSupport`, `ClockMismatch` and `PhysicalProfileError` keep `ValueError`
      as a second base.
- [x] Group them: `ManifestError` (with a `SourcesError` beneath it), `RegistryUnavailable`,
      `ResourceError` over the four resource errors with `resource_id` and `source` attributes,
      and `Refused` over the errors that decline an operation the packet does not support.
- [x] Give `RegistryUnavailable.reason` a closed set of values that the validator's check IDs are
      declared from.
- [x] Give `UnresolvableAxis` a reason code. It is raised at 20 sites, for causes that tests tell
      apart by text.
- [x] Replace the deliberate `LookupError` and `KeyError` raises with `NotDeclared(PacketError,
      LookupError)`.

### 5.2 Validator

- [x] Add `ValidatorError`; `StoreUnreachable`, `ResourceMissing` and `OrderViolation` derive from
      it and gain attributes (`uri`, `key`; `resource_id`, `row`, `kind`).
- [x] Replace the built-in raises that escape `validate` (an unreadable replaced packet, an
      unknown digest algorithm) with named classes.
- [x] `RegistryRejected` and `RuleProfileError` live in the checkers copied from `spec/tools`, so
      they change at that source or stay as they are.

### 5.3 Writer and adapters

- [x] Add `WriterError`; every class the writer defines derives from it.
- [x] Split `RecipeError` by cause: an unsound recipe (carrying its problems), an unknown source
      kind, a source-order error, an unfilled term, a missing materializer, strict-mode notes, an
      unreadable recipe file.
- [x] Give `Problem` a `code`, and `PayloadRefused` its problems as a list.
- [x] Give `SourceDefect` `where` and `code`, and make `UnsupportedEncoding` a `SourceDefect`.
- [x] Give adapter notes a code, so a test asserts a code where it now matches note text.
- [x] Name the built-in raises tests tell apart by text: an undeclared resource, an occupied
      packet path, a usage error.
- [x] The command line catches `EscapewheelError` once and prints the refusal.

### 5.4 Tests

- [ ] Convert every cross-package `match=` to a class and attribute assertion.
- [ ] Convert in-package `match=` where a code or attribute now exists.

## 6. Stages 2 and 3: vocabularies and the public surface

### 6.1 Declared vocabularies (stage 2)

- [x] Validator: one table of check IDs, each with its default level, its scope and whether a
      part names it; one function per templated family (`<resource>.physical_order`,
      `<resource>.<column>.outside_reserved_set` and the like). `Report.add` takes an entry. At
      `f30864e`, 30 of the 71 literal IDs appear in no part.
- [ ] Validator: a `Level` enumeration, and constants for verdicts and evaluation statuses. The
      writer compares against them where it now compares against `"valid"`.
- [x] Settle `source.absolute_uri` against the three `sources.*` IDs: one prefix.
- [x] Reader: the resource-ID module of §2, the packet file names, and the profile ID, each
      defined once.
- [ ] Writer: a `SourceAdapter` protocol and one capability protocol for each optional member
      (streaming, staged arrays, referenced arrays and media, payloads, compensations). The build
      is typed against them and stops reading attributes by name. One policy for empty tables and
      a derived `offers()`. One streaming surface.
- [ ] Writer: the delivery module uses the protocol-name constants the declaration module already
      defines.
- [ ] Shared helpers defined once: `semver`, the provenance resource list, identifier quoting, the
      tables a registry declares, the manifest-entry builder, the adapter lookup with its
      unknown-kind refusal.

### 6.2 Two documented tiers (stage 3)

Each package has a user tier, exported from `__init__` and documented in `api.rst`, and a support
tier of named submodules that a downstream package may import. Every other name is private, every
module declares `__all__`, and `api.rst` lists exactly the two tiers.

| package | user tier | support tier |
|---|---|---|
| reader | opening a packet and a dataset; table, array and spike access; clocks and alignment; the exception classes | the functions the validator and writer use today from `clocks`, `ordering`, `profile`, `registries`, `uri` and `location`, and a `PacketLike` protocol for functions that take a packet |
| validator | `validate`, `check_packet_manifest`, `Report`, `Finding`, the evaluation types, the check-ID table, `Level`, the registry checks and schemas | `verify_order` and `OrderViolation`, `adjacency_settles_uniqueness`, the amendment group names, the store listing and digest functions |
| writer | `build`, `Recipe`, `PacketWriter`, `verify`, `prune`, `materializers`, one function that runs a recipe through to a commit, the exception classes | `escapewheel_writer.adapter`: the protocols, `SourceDefect`, `Clock` and its helpers, the staged and referenced bindings, `Payload`, the protocol names, `SourceStore`, `serve`, and the `NWBSource` extension points |
| aind | its adapters, by entry point | none |

- [x] Reader: decide the delegate policy for `Packet` methods that mirror free functions, then
      make `__all__`, `api.rst` and the imports agree.
- [ ] Validator: likewise; remove the names that are public by accident.
- [ ] Writer: add `escapewheel_writer.adapter`; publish the `NWBSource` class tables and the five
      hooks that aind overrides, with the two accessors and the `clean` helper it calls; delete
      `into()`.
- [ ] aind and `conformance/`: import only from the tiers.
- [ ] Tests: stop importing private names across modules, or move the test beside the module
      whose private name it needs.

## 7. Stage 4: splits

Each split is a move. It follows stages 1 to 3 because the moves are simple once errors,
constants and the surface have homes.

| module | lines | becomes |
|---|---:|---|
| validator `validator.py` | 2,868 | `report`, `registry_types`, `declarations`, `rules`, a `shim` subpackage (`time_origin`, `floors`, `owned`, `ordering`, `arrays`, `tables`, `external`), and `validator` holding `validate` and the manifest and amendment entry points |
| writer `writer.py` | 2,184 | `layout`, `promotion`, `bindings`, `staging`, `documents`, `numbering`, and `writer` holding `PacketWriter` with a `Declarations` and an `Attachments` collaborator |
| writer `session.py` | 1,437 | `facts`, `alignment`, `provenance`, `sourcing`, and `session` holding `build` and `Context` |
| writer `recipe.py` | 1,431 | `secrets`, `kinds`, `recipe_check`, and `recipe` holding the model |
| writer `delivery.py` | 911 | `serving` and `reading` |
| writer `scripts/cli.py` | 701 | one parser function for each subcommand |
| writer `sources/nwb.py` | 1,252 | a `nwb` subpackage: names, file access, devices, electrodes, signals, events, and the source class |
| writer `sources/sorter.py` | 956 | `analyzer` (shared with the waveform and unit-QC adapters), `sorter_labels`, `sorter` |
| writer `sources/sync.py` | 772 | `sync_checks` (pure array functions) and `sync` |
| aind `session.py` | 745 | `calibrations` and `session` |
| reader `packet.py` | 749 | `duck` (the DuckDB surface) and `packet`; source resolution moves to `location` |

Known obstacles:

- The validator's tests and the writer's patch `validator.listing`, which three of the new
  modules would call. The listing function becomes a parameter or one patch point.
- `amendment.py` imports `_DDL` from `validator` inside a function to avoid a cycle;
  `registry_types` ends the cycle.
- `_run_checks` takes a `finalize` flag because a session check runs between the Tier 1 checks
  and the record that the core registry completed. `Report` gains an explicit completion call.
- `amending.py` and `writer.py` import each other lazily; `promotion` ends that cycle.
- `PacketWriter._tables` is read by the session module and mutated in place when a catalog row is
  bound. It gets a narrow accessor before `Attachments` is extracted.
- The `NWBSource` hooks are methods of one class. The subpackage either composes the method
  groups as mixins or passes the source to functions.

## 8. Stage 5: structural changes

- [ ] Writer: `commit` and `_amend` are one pipeline written twice (staging, notes and hooks,
      materialize and restage, refusal, promotion claim, publish). Make the URI base a staging
      parameter in place of the `_amending` flag, then express both as the same phases. This is
      the riskiest item and lands alone.
- [ ] Writer: `build` and the import command repeat the same preparation. One path.
- [ ] Validator: `Finding` gains `resource` and `column`, summary findings carry their counts as
      data, and the row cap has one value. The report's JSON gains members; Part 05 §9.1 requires
      a level, a check and a message and forbids none of this.
- [ ] Validator: one options object for the verification modes, so the API derives `external`
      from the other modes as the command line does.
- [ ] Validator: `validate` becomes four phase calls over one context object.
- [x] Reader: functions that take a packet are typed against `PacketLike`, and the six memo
      caches they reach by `getattr` become one public memo.
- [ ] Tests: split `test_validation.py` (2,336 lines), `test_writer.py` (1,530) and
      `test_recipe.py` (1,194) along the new modules.
- [ ] Tests: one shared packet-fixture helper for the reader's and validator's suites, with its
      small registry derived from the real one; one `nwbfixture` for the writer and aind.
- [x] Corpus: `fixtures/build.py` (2,312 lines) is held together by the module globals `KEYS` and
      `SPECS`. Replace them with an object, declare each packet once as a record that carries its
      expected finding, then split the module.

## 9. Specification tooling

- [ ] `spec/tools/checkers/registry_document.py` (1,863 lines) is copied into the validator.
      Delete its uncalled legacy interface, register each invariant with its ID, its dependence on
      core and its universe, then split it into a result model, the invariants, the rule and unit
      phases and the entry points. Each new file needs a line in the copy map.
- [x] One shared module for what the tools each reimplement: parts by number, fence-aware headings
      and anchors, the citation grammar, metadata rows, JSON Pointer, tracked files, the tables a
      registry declares, region replacement, and one reporter.
- [x] `check.py` is a script that exits on import. It becomes functions under a `main`, and it
      meta-validates the two schemas it skips.
- [x] The Part 03 generated regions and `spec/informative/tables.md` have no `--check` of their
      own; only the verifier's whole-tree comparison catches a stale one. Give each a check.
- [x] Generators raise an error class and `main` converts it, in place of `SystemExit` raised
      inside importable functions.
- [x] `framework.py`: move its expected-value data out and cut `defects` by phase.
- [x] `verify.py`: one stage record type and one spelling of the interpreter. `--quick` runs no
      package suite; either it gains a marked fast subset or its documentation says so.
- [x] Two verifier stages execute every shipped rule over empty tables. Keep one.
- [x] Ledger, as a process proposal. Preferred form: `headings.toml` locks a
      whitespace-normalized digest of each section an applied clause lands in, and a changed
      digest prints those clauses for re-reading before it is relocked. The ledger has 830
      clauses, of which 501 are applied. The same proposal covers validating a superseded
      entry's `by` and removing the ratchet that rewrites `applied.toml`.

## 10. Order of work

1. Stage 1 in dependency order: reader, validator, writer and adapters, then the tests.
2. Stage 2: validator vocabularies, reader constants, the adapter protocols.
3. Stage 3, one package at a time, lowest first.
4. Stage 4. The validator and writer splits are independent of each other.
5. Stage 5 and the tooling items of §9. The ledger proposal can be written at any point.

The citation rule of §3.3 is applied to a module when that module is moved or rewritten, and in
one closing pass over whatever was not touched.

## 11. Choices made during the work

Section 2 settles the decisions taken before the work began. This section records each choice the
plan left open, as it was made.

### 11.1 Reader errors

- `Refused` groups nine classes: `NoTimeOrigin`, `AmbiguousRun`, `UnresolvableChannelIndex`,
  `UnresolvableAxis`, `MultiSessionUnresolved`, `NotAligned`, `Unanchored`, `ClockMismatch` and
  `StaleSupport`. Each declines a question the packet's readable data cannot answer one way.
  `PhysicalProfileError` stays directly under `PacketError`, since it reports a fault in the
  bundled descriptor and none in a packet.
- `ResourceError.resource_id` and `ResourceError.source` are optional. A source that cannot be
  resolved is raised below the point where the resource is known, and the resource reader fills
  in `resource_id` before the error leaves it.
- `RegistryFault` is a string enumeration of four members. Acquiring a registry fails as
  `MISSING`, `UNREADABLE` or `DIGEST`, and the validator maps those three to their check IDs in
  one table. `INVALID` reports acquired bytes that are not a JSON object; the validator never
  receives it, because it checks the bytes itself.
- `AxisFault` has sixteen members for the twenty raise sites of `UnresolvableAxis`. Sites that
  report the same fault in two places share a member: a missing catalog row, an absent label
  table, a bad coordinate array, and an incomplete origin form.
- `NotDeclared` replaces twelve raises: a stream of an event type, a run for a scope, a clock's
  tick rate, a table's support, the discriminator lookups, and a reference between two tables,
  which was a `ResourceNotFoundError` naming no resource. It is no `KeyError`, so a caller that
  caught `KeyError` from `aligned_spikes`, `preferred_run` or `observed_seconds` catches
  `LookupError` or `NotDeclared` instead; no package in the repository did.
- `Dataset.table` raises `ResourceNotFoundError` with `resource_id` where no packet holds the
  resource, as `Packet.resource` does, in place of a `KeyError`.
- `escapewheel_writer.materialize` no longer exports `NotAligned`. The reader's `errors` module
  is its one home, as §2 drops old import paths.

### 11.2 The ledger proposal

The proposal is `revisions/proposals/the-ledger-locks-the-text-an-applied-clause-lands-in.md`. It
departs from §9's preferred form in one place and settles three points §9 left open.

- The lock is a file of its own beside the ledger under `revisions/`, and `headings.toml` does not
  hold it. The specification tree is checked from a copy of itself alone, the ledger that says
  which sections carry clauses lies outside that copy, and eight applied targets land in the
  revision guide.
- A section's digest covers its subsections, since a citation of the section number names that
  extent. Ten sections that carry clauses have subsections.
- The digest leaves out generated regions as well as collapsing whitespace. Seven sections that
  carry clauses enclose a region a generator rewrites.
- A clause that strikes a requirement and has no successor is disposed `applied` at the section it
  struck from. One entry, R107 §3.5, is recorded `superseded` with no `by` today.

Writing the tool waits on the proposal's promotion and acceptance.

### 11.3 Validator errors

- `StoreUnreachable.key` is None where the failure concerns everything under the URI, such as a
  listing or an unknown scheme, and the member's key where one member was being read.
  `read_member` fills `key` in on an error raised below it.
- `OrderViolation.kind` is an `OrderFault`, a string enumeration of two members, `DESCENT` and
  `REPEAT`. `row` is an index into the stream, and the message prints the row's position.
  `resource_id` is None from `verify_order`, which is not told the table; the writer sets it on
  the exception it catches, in place of raising a second one with the table prepended.
- `UnknownAlgorithm` and `ReplacedPacketUnreadable` keep `ValueError` and `FileNotFoundError` as
  second bases, since callers and tests caught those. `FormatCheckUnavailable` keeps no built-in
  base, because no caller catches `RuntimeError`.
- `_Unmappable` moves under `ValidatorError`, keeps its private name and drops `ValueError`. It
  is raised and caught inside the time-origin check and never leaves `validate`.
- `RegistryRejected` and `RuleProfileError` stay as they are, in the modules copied from the
  specification's tree. The taxonomy test reads the exempt modules from the copy map.
- `generate()` keeps its `TypeError` for an argument that is no checked context: it guards a
  programming error and refuses no input.
- `escapewheel validate` catches `EscapewheelError` once, prints the refusal to standard error
  and exits with status 1. A `--replaced` path holding no readable manifest exits with status 2,
  the status the command already returns where that path is absent; an unparsable manifest there
  used to leave as a traceback.
- The validator's findings still print a row's index where `OrderViolation` now prints its
  position. The findings change to positions with the check-ID table of §6.1.

### 11.4 The verifier

- Every stage is a `Stage` record naming the uv project whose environment runs it, so the
  interpreter has one spelling. `--quick` runs no package suite and its documentation says so; it
  gains no fast subset.
- A stage declares whether it writes tracked files. The four that do run first, alone and in
  order, and the rest run together, bounded by `--jobs`. This is outside the plan of §9 and was
  asked for to shorten a run.

### 11.5 Reader constants

- The resource-ID module is `escapewheel_reader.resource_ids`. It holds the 43 core-registry IDs
  that source code in the four packages spells as a literal, and no others. A constant's name is
  its ID upper-cased with each dot an underscore, which a test enforces.
- An extension's resource IDs stay with the package that carries the extension.
- The reader bundles no registry, so the test of the constants reads the registry from the
  specification's tree and is skipped where that tree is absent. A second test fails where any
  other reader module spells a named ID as a whole literal.
- The reader's per-module aliases for resource IDs are deleted. `CHANNELS` and `RUNS` each meant a
  different table in two modules.
- The packet's file names stay in the modules that read them: `MANIFEST_FILENAME` in `manifest`,
  `SOURCES_FILENAME` and `SOURCES_VERSION` in `location`, and `ZARR_METADATA_FILENAMES` in
  `resources`, which was the private `_ZARR_METADATA`. No layout module is added.
- `MANIFESTS_DIRNAME` is defined in the reader although only the validator and the writer use it,
  so that both import one definition from a package below them.
- `PROFILE_ID` is defined in `profile`, and a test checks it against the bundled descriptor.
- The validator, the writer and the adapters still spell these literals. Their conversion goes
  with each package's stage 2.

### 11.6 The corpus

- A packet is declared once, as a `Packet` record in `fixtures/corpus_packets/` that carries its
  build function, its expected finding, the checks it must not draw, and whether it is validated
  with checksums. `fixtures/build.py` writes each record and `fixtures/corpus.py` judges each.
- `corpus.py` keeps `EXPECTED` as a literal, because `revisions/evidence.py` and `tools/facts.py`
  read it from that file's syntax tree without importing it. `corpus.py` exits 1 before judging
  anything where the literal and the records disagree. Removing the literal means changing those
  two tools to import the records, which is not done here.
- The module globals `KEYS` and `SPECS` are replaced by a `Numbering` object that each build
  creates for its own packet.
- The package holds the record, four helper modules (registry, numbering, writing, arrays), the
  valid session's rows in `session.py`, and one module for each subject's packets. `build.py`
  re-exports `PACKETS`, `VALID` and `content` for the callers that load it by path.
- `fixtures/packets/` is ignored, so the verifier's candidate-state check does not see a change
  to the corpus. The split was checked by comparing a digest of every written file before and
  after: identical, apart from the `validator_name` lines the first commit corrected.

Found and left as they were, since each changes what the corpus asserts or is outside the split:

- Four of the six packets expected to draw a warning are not marked `conforming`, so the corpus
  does not check that they pass: `spike_outside_window`, `wide_anchor_gap`, `two_primaries` and
  `outside_table_floor`.
- `tone_in_place_of_its_own` expects an extension's check and names no `registry`, so the
  per-registry verdicts are not checked for it.
- `fixtures/README.md`'s table of variants is incomplete and stale in places.
- `writing.sql_name` is defined and never called.

### 11.7 Validator vocabularies

- The validator's vocabularies are four string enumerations in `vocabulary.py`: `Level`,
  `Verdict`, `EvaluationStatus` and `RegistryState`. A member equals the string a report's JSON
  carries, so a caller comparing against the string is unaffected. A test refuses a vocabulary
  string written anywhere else in the package, except in the copied checkers and for one phase
  state in `manifest.py`.
- The check-ID table is the module `check_table`, since `checks` is the name the generator and
  the runner give a list of checks. It holds 101 entries: 83 fixed IDs, each a constant named
  after its ID, and 18 templated families, each a template with one function that builds an ID
  from its parts. 52 of the 101 are named by no part.
- An entry records its ID, its default level, its scope and whether a numbered part names it.
  Scope is one of `packet`, `registry`, `resource` and `column`, and says what one finding of the
  check names.
- `Report.add` takes an entry and reports at the entry's level. A check whose level depends on
  what was found passes `entry.at(level)`: the reader-floor finding, `kind_declared`, and a Tier 1
  check that could not run.
- A generated check, a manifest issue and an amendment finding carry an entry in place of an ID
  string. `Finding.check` stays a string, so a report and its JSON are unchanged.
- A Tier 2 rule's ID is declared by its registry, and the ID of a registry result's outcome by
  the registry contract. Both reach a report as entries built by `rule` and `registry_outcome`,
  carry no named flag, and are outside the table.
- `Report.add` still accepts a level and an ID string in an entry's place, because the writer
  reports `verify.unreachable` and `verify.recorded` that way. The form goes when the writer
  declares its own entries.
- An entry is named where a numbered part writes its ID standing alone, joined to no longer ID. A
  family is named where a part writes its template under any placeholder names, or one ID the
  template admits; `registry.determined_by.resolves` therefore does not name
  `<resource_id>.determined_by`. The test reads `spec/parts` and is skipped where the
  specification's tree is not beside the package.
- The ordering scan's findings under `<resource>.physical_order`, `<resource>.primary_key_unique`
  and `<resource>.determined_by` name a row by its position. No corpus expectation or tracked file
  held such a row. An `axis_index`, `position_index` or `channel_index` in an axis finding is a
  stored value and prints as stored.
- The one prefix is `sources.`: `source.absolute_uri` becomes `sources.absolute_uri`. That renames
  one ID where `source.` would rename three, and it matches the resolution document's name. No
  part, corpus expectation or other package names any of the four.

Found and left as it was, since REFACTOR.md lists no such change:

- The ordering scan raises `KeyError` where a table repeats a primary key and a sort column
  declared `determined_by` that key is constant in the file. The scan drops the constant column
  from its batches and the `determined_by` comparison still reads it.

### 11.8 Reader tiers, split and memo

The reader's row of §7's table is done: `packet.py` is `duck` and `packet`, and source resolution
is in `location`.

- `Packet` has no method that mirrors a free function. Nine of the 28 functions taking a packet
  had a delegate and no rule said which; no package outside the reader's own tests called one;
  and removing them removes `packet`'s import of `access` and `clocks`. A test fails where a
  `Packet` method shares a name with an exported function.
- A name is public only through an `__all__`. The user tier is `escapewheel_reader.__all__`, and
  the support tier is every name in a submodule's `__all__` that `__init__` does not export. A
  bare name left out of `__all__` is for the reader's own modules and an underscore name for its
  own module, so no name gained an underscore. A module exports only names it defines.
- `api.rst` lists the user tier by subject, the support tier as `module.name` entries with
  `resource_ids` listed whole, and one page for each module with a public name.
  `tests/test_surface.py` holds `api.rst` against the `__all__`s in both directions.
- `duck`'s functions take the packet root and the declared table resources, so `duck` does not
  import `packet`. `Packet.duckdb` and `Packet.sql` keep their signatures. One guard serves the
  packet and the dataset, each passing the sentence its own refusal ends with.
- `PacketLike` is a protocol in `escapewheel_reader.protocols` listing the members the free
  functions use and no others. A test holds that every module-level function with a `packet`
  parameter is annotated with it.
- The six caches are one dataclass, `protocols.Memo`, with a field for each function, exposed as
  `Packet.memo` and declared by `PacketLike`. What is kept and for how long is as before.
  `with_declarations` gives the rebound packet a shallow copy of the memo.
- The functions reach the memo through `Memo.of(packet)`, which gives an object with no `memo` an
  empty one that is then discarded. Stand-ins with no memo exist in the reader's tests and in the
  validator's time-origin test; once each carries a memo, `Memo.of` becomes `packet.memo`.
- The citation rule of §3.3 was applied to `packet`, `duck`, the moved source resolution and the
  functions rewritten for the memo. The reader's other modules wait for the closing pass.
  `access.events` keeps its revision citation, which `revisions/repoint.py` exempts by file.

Found and left as they were:

- Part 04 §5.5 cites "Immutability (§5.1)", and immutability is stated in Part 03 §8.1. A
  specification part is not edited here.
- The ledger places three clauses at Part 01 §2.2 and §2.4 whose rules read today in Part 01
  §2.3 and §2.6. The ledger is not edited here.
- `declared_bound` treats a sessions table with no `alignment_bound` column as unreadable, so it
  returns the default bound and reads again on every call.
- `ordering.overridden` is used only by its own test, and the validator's tests patch the private
  `ordering._overrides`.

### 11.9 Writer and adapter errors

- Every exception class of the writer is defined in `escapewheel_writer.errors` and derives from
  `WriterError`. `escapewheel_writer.sources.defect` is removed, and no old import path remains.
  A test in the writer and in aind refuses a built-in exception raised from the package's source.
- `RecipeFault` is a string enumeration and `Problem` carries one as a required third field,
  `code`. A fault reported from two places shares a member. `declaration.refusals` returns pairs
  of a fault and a message.
- `RecipeError` has seven subclasses: `RecipeUnreadable` (still a `ValueError`), `RecipeUnsound`,
  `UnknownSourceKind`, `SourcesNotOrdered`, `TermUnfilled`, `MaterializerNotFound` and
  `NotesUnderStrict`. The first two carry `path` and a list of `Problem`. A refusal a build makes
  is a `RecipeUnsound`; a wrapped `ReplacementRefused` or `AmendmentRefused` is chained as its
  cause. `AmendmentRefused` has no codes and is wrapped as one problem.
- `PayloadRefused.problems` is a list of `PayloadProblem`, each with a `PayloadFault` code and a
  message, and `PayloadRefused.source` names the source.
- `SourceDefect(message, *, code=None, where=None)` keeps its one-argument form, so an adapter
  released apart from the writer raises it unchanged. The writer's codes are `SourceFault`, and
  aind declares its own `AindFault`. A test in each package refuses a defect raised with no code.
- `UnsupportedEncoding` is a `SourceDefect`. The NWB adapter still notes a pickled optional column
  where it noted one, and aind's unit-QC adapter still skips a pickled metric column.
- A failed delivery raises `DeliveryFailed`, a `SourceDefect` carrying each failure as a
  `SourceDefect` in `failures`.
- A note is a `Note`, a `str` subclass with a `code`, in `escapewheel_writer.notes` beside
  `NoteCode`; aind declares `AindNote`. `notes` stays a list of strings, and plain text is a note
  whose code is None. A code does not cross an out-of-process delivery, whose report carries a
  level, a message and a resource; a relayed note is `NoteCode.REPORTED`. Carrying the code across
  would add a key to the delivery report, which is a specification change.
- The built-in raises became nine classes, each keeping the built-in it was as a second base:
  `UsageError` (with a `UsageFault` code), `UndeclaredResource`, `PacketOccupied`,
  `UnknownCompensation`, `CompensationsInvalid`, `DeclarationUnreadable`, `FixedOffsetZone`,
  `OutOfRange` and `TickOverflow`. `UndeclaredResource` and `UnknownCompensation` stay `KeyError`
  and print their message without the quotes a `KeyError` adds.
- The shared entry point catches `EscapewheelError` where it caught `PacketError`, prints the
  refusal and returns 1. `escapewheel import` returns 2 for any `EscapewheelError` raised before
  the commit begins and 1 for one raised by the commit; a source that streams its rows is read
  during the commit, so its defect there returns 1. A missing recipe file is still an `OSError`.
- Where a test's point is a subject or a count no attribute carries, it selects by code and keeps
  a substring for that subject or count.

Left for §5.4 and stage 3: the new names are not yet exported from the writer's `__init__` or
listed in its `api.rst`, and these `match=` assertions remain: `NaiveTimestamp` and `NotCommitted`
in `test_writer.py`, two on the reader's `NotAligned`, two on the validator's `OrderViolation`,
and those on `AmendmentRefused`, `NonFinite`, `ExtensionNotFound`, `Collided` and
`PromotionRecordUnreadable`, whose classes carry no attribute for the fact matched.

### 11.10 Specification tooling

- The shared module is `spec/tools/specdoc.py`. It imports only the standard library, so a script
  under `revisions/` or `tools/` imports it after putting `spec/tools` on its path. The scripts
  under `revisions/` were edited to use it; no record, ledger entry or evidence file was.
- A shared helper takes the directory it reads as an argument, so the patch points the process
  tests use still work.
- Duplicated helpers that differed keep each caller's behaviour through a parameter:
  `part_citation(gap)` takes the separator, `metadata` keeps the last of a repeated row and
  `metadata_value` the first, and `tracked_files(..., whole_names=False)` splits on whitespace as
  five callers did. Nothing was unified where callers disagreed.
- `resolve_pointer` is the ledger's resolver, and `ScalarError` carries the token so the evidence
  checker keeps its own wording.
- A generator raises `specdoc.GenerationError` and the ledger `LedgerError`; each entry point
  prints the message and exits 1, as the former `SystemExit` did. `tools/facts.py` still raises
  `SystemExit` at two sites.
- `spec/tools/check.py` runs from seven functions under `main`, with its output unchanged. The
  registry result schema and the physical profile schema are meta-validated by a raising call
  with no report line.
- The two new comparisons, of Part 03's generated regions and of the rendered listing, are checks
  of the existing structural-checks stage, and `build.py --check` and `render.py --check` call the
  same functions. No stage was added.
- The framework checker's expected values are in `spec/tools/framework_data.py`, and `defects`
  concatenates fourteen phase functions in the former order.
- The shipped rules execute over empty tables in one stage; the rule-language probe keeps their
  static check and binding.
- The probes under `conformance/` keep their own reporters and table projections, since they run
  in the package environments. The copied checkers keep theirs.

Found and left as they were:

- No heading enumeration skips fenced code, so a numbered heading inside a fence would count as a
  section. No part has one.
- Five callers split the tracked-file listing on whitespace, which breaks on a name holding a
  space. No tracked name has one.
- In a fresh checkout the quick verifier fails once at the process tooling tests, because the
  ignored `fixtures/packets/` does not exist until the corpus stage has written it.

### 11.11 Validator constants and the test registry

- The validator takes every core resource ID, the manifest file name, the manifests directory
  name and the Zarr metadata file names from the reader's constants, and a test fails on a whole
  string literal in the package's own source that equals one. The copied checkers are outside the
  rule. Its own `MANIFEST_FILENAME` is removed.
- No test literal was converted: each is a fixture's row, manifest or registry text.
- The validator reads a prefix holding both Zarr metadata documents as version 2 and the reader
  reads it as version 3. Left as found, since aligning them changes behaviour this plan does not
  list.
- The validator's test registry declares `core.intervals` where it declared `core.trials`, with
  the same simplified shape, so each test checks what it checked. A test holds that the fixture
  declares only resources the core registry declares. Individual tests still add declarations
  core lacks; the shared fixture of §8 is the place for those.

### 11.12 Reader citations and the shared helpers' home

- Every reader module and test cites a rule once, at the definition that implements it. Where one
  section governs a whole module, the module docstring carries the citation and its members do
  not repeat it. The copied descriptor checker keeps its citations.
- An exception class cites the rule it refuses under, and the message raising it does not. A
  message keeps a citation only where it tells its reader what to declare: the three run
  messages, which cite Part 05 §12.
- A revision citation became the part that states the rule. Where the revision's clause is
  rationale only, the sentence states the rule with no citation. `access.events` keeps the one
  revision citation `revisions/repoint.py` exempts.
- `registries.declared_tables` is the one definition of the tables a registry document declares.
  It skips what an unchecked document omits, and `strict=True` raises `KeyError` instead, which
  is what the copies in the writer, the validator's generator and the fixtures do.
- A shared helper lives in the lowest package that uses it. `semver`, the provenance resource
  list and the escaping `quoted` therefore stay in the validator, which the writer imports, and
  the reader gains none of them. The manifest-entry builder and the adapter lookup are the
  writer's.
- The reader's `sql.quote` does not escape an embedded quotation mark and the validator's
  `quoted` does. Left as two functions, since making one of them changes behaviour this plan
  does not list.
- `ordering.overridden` is removed; `stored_order` is the module's one public name.
- The docstring of every function typed against `PacketLike` names `PacketLike`.

Found and left as they were:

- Part 01 §3.9 does not state the estimator used past a terminal anchor, though the ledger places
  its clause there. Part 01 §3.9 also has a consumer report ticks it cannot map, and
  `clocks.on_clock` drops them as `analysis.spike_events` does under Part 06 §4.
- The reader's contributing guide and design notes still ask for and carry revision citations.
- The validator's tests patch the reader's private `ordering._overrides`.
