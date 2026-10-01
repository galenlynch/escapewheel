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

- [ ] `escapewheel import` exits with a traceback on most build failures. Its call to `build`
      handles only `RegistryRejected`, so `RecipeError`, `SourceDefect`, `PayloadRefused` and
      `NotCommitted` escape, and the shared entry point catches only the reader's `PacketError`.
      Stage 1.
- [ ] `UnsupportedEncoding` is not a `SourceDefect`, and only the NWB adapter and aind's unit-QC
      adapter catch it, so the sorter, waveform and LFP adapters fail with a traceback. Stage 1.
- [x] The validator builds the check ID `packet.registry.<reason>` from the free-text `reason` of
      the reader's `RegistryUnavailable`. Stage 1.
- [ ] An adapter served out of process loses its compensations. The build reads `compensations`
      from the source object, and the delivery module never carries the attribute across.
      Stage 2; if the delivery report needs a new key, that part is a specification change.
- [ ] Three fixture builders write `validator_name` as `escapewheel_validate`. Stage 2.
- [ ] The validator's test registry declares `core.trials`, which the core registry does not
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

- [ ] Add `ValidatorError`; `StoreUnreachable`, `ResourceMissing` and `OrderViolation` derive from
      it and gain attributes (`uri`, `key`; `resource_id`, `row`, `kind`).
- [ ] Replace the built-in raises that escape `validate` (an unreadable replaced packet, an
      unknown digest algorithm) with named classes.
- [ ] `RegistryRejected` and `RuleProfileError` live in the checkers copied from `spec/tools`, so
      they change at that source or stay as they are.

### 5.3 Writer and adapters

- [ ] Add `WriterError`; every class the writer defines derives from it.
- [ ] Split `RecipeError` by cause: an unsound recipe (carrying its problems), an unknown source
      kind, a source-order error, an unfilled term, a missing materializer, strict-mode notes, an
      unreadable recipe file.
- [ ] Give `Problem` a `code`, and `PayloadRefused` its problems as a list.
- [ ] Give `SourceDefect` `where` and `code`, and make `UnsupportedEncoding` a `SourceDefect`.
- [ ] Give adapter notes a code, so a test asserts a code where it now matches note text.
- [ ] Name the built-in raises tests tell apart by text: an undeclared resource, an occupied
      packet path, a usage error.
- [ ] The command line catches `EscapewheelError` once and prints the refusal.

### 5.4 Tests

- [ ] Convert every cross-package `match=` to a class and attribute assertion.
- [ ] Convert in-package `match=` where a code or attribute now exists.

## 6. Stages 2 and 3: vocabularies and the public surface

### 6.1 Declared vocabularies (stage 2)

- [ ] Validator: one table of check IDs, each with its default level, its scope and whether a
      part names it; one function per templated family (`<resource>.physical_order`,
      `<resource>.<column>.outside_reserved_set` and the like). `Report.add` takes an entry. At
      `f30864e`, 30 of the 71 literal IDs appear in no part.
- [ ] Validator: a `Level` enumeration, and constants for verdicts and evaluation statuses. The
      writer compares against them where it now compares against `"valid"`.
- [ ] Settle `source.absolute_uri` against the three `sources.*` IDs: one prefix.
- [ ] Reader: the resource-ID module of §2, the packet file names, and the profile ID, each
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

- [ ] Reader: decide the delegate policy for `Packet` methods that mirror free functions, then
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
- [ ] Reader: functions that take a packet are typed against `PacketLike`, and the six memo
      caches they reach by `getattr` become one public memo.
- [ ] Tests: split `test_validation.py` (2,336 lines), `test_writer.py` (1,530) and
      `test_recipe.py` (1,194) along the new modules.
- [ ] Tests: one shared packet-fixture helper for the reader's and validator's suites, with its
      small registry derived from the real one; one `nwbfixture` for the writer and aind.
- [ ] Corpus: `fixtures/build.py` (2,312 lines) is held together by the module globals `KEYS` and
      `SPECS`. Replace them with an object, declare each packet once as a record that carries its
      expected finding, then split the module.

## 9. Specification tooling

- [ ] `spec/tools/checkers/registry_document.py` (1,863 lines) is copied into the validator.
      Delete its uncalled legacy interface, register each invariant with its ID, its dependence on
      core and its universe, then split it into a result model, the invariants, the rule and unit
      phases and the entry points. Each new file needs a line in the copy map.
- [ ] One shared module for what the tools each reimplement: parts by number, fence-aware headings
      and anchors, the citation grammar, metadata rows, JSON Pointer, tracked files, the tables a
      registry declares, region replacement, and one reporter.
- [ ] `check.py` is a script that exits on import. It becomes functions under a `main`, and it
      meta-validates the two schemas it skips.
- [ ] The Part 03 generated regions and `spec/informative/tables.md` have no `--check` of their
      own; only the verifier's whole-tree comparison catches a stale one. Give each a check.
- [ ] Generators raise an error class and `main` converts it, in place of `SystemExit` raised
      inside importable functions.
- [ ] `framework.py`: move its expected-value data out and cut `defects` by phase.
- [ ] `verify.py`: one stage record type and one spelling of the interpreter. `--quick` runs no
      package suite; either it gains a marked fast subset or its documentation says so.
- [ ] Two verifier stages execute every shipped rule over empty tables. Keep one.
- [ ] Ledger, as a process proposal. Preferred form: `headings.toml` locks a
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
