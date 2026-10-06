# A machine or a folder says where a source is

| | |
|---|---|
| **Status** | **Ready** |
| **Opened** | 2026-10-06 |
| **Based on** | `fcc03a5164a894f684c0f53ffd66054c351a13dd` |
| **Change form** | ordinary |
| **Amends** | Part 04 §5.5; `artifacts/sources.schema.json` |
| **Depends on** | None |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Problem

An external resource entry can name a `source`, a body of data such as one session's raw recording,
and give its `uri` relative to wherever that source is. Part 04 §5.5 has a **source resolution
document**, conventionally `sources.json`, map each source name to an absolute URI or an absolute
path. A reader tries the documents its caller supplies, in order, and then the `sources.json` at the
packet root, which the writer writes naming where it read each source. The design is meant to let
the same packet find its data at a different place on each machine without being rebuilt.

It does that only for a caller who passes a document every time, and only for entries that name a
source. Three arrangements it is meant for fail:

- **A machine holds a whole store at its own path**, such as a cluster or Code Ocean mount of a
  bucket. Nothing lets the machine state that once, so every notebook, script and tool carries the
  path or an argument naming a document. A document naming sources would need one entry for every
  source anyone might open, and could not reach an entry whose `uri` is absolute.
- **A folder of packets shares mirrors.** Each packet's default has to be edited, or a document
  passed each time; no document can serve the folder.
- **A packet travels with its data**, as a bundle copied to a laptop. The default still names the
  original store, so a reader reads from there, or reports the source unresolved while offline,
  with the copy beside it. No document can say where a source is relative to itself, because the
  schema admits only absolute locations.

This change adds three places a reader looks: the folders above the packet, a variable naming
documents, and a reader's own per-user machine document. It also lets a document state a **mirror**,
one location prefix standing for another, and lets a document locate a source or a mirror relative
to itself. What a resolution document means, that one is never a packet resource, that an unresolved
source is a fact rather than a defect, and how a resolved source is verified against its recorded
digest are unchanged.

## 2. Evidence

Observations are of the tree at the commit this document is based on.

- `escapewheel_reader.open_packet` takes resolution documents as its `sources` argument, and
  `resolve_sources` (`escapewheel-reader/src/escapewheel_reader/location.py`) keeps the first
  location each name is given. Neither the reader's nor the validator's command line accepts a
  resolution document, so from the command line only the packet's default is ever consulted.
- The reader also takes `rewrite`, a URI-prefix substitution applied to every resource, the longest
  prefix winning. It survives because nothing else lets a caller redirect an entry that names no
  source, and it lives in the caller's code, so each caller restates it.
- Most external entries name no source. The AIND video adapter
  (`escapewheel-aind/src/escapewheel_aind/video.py`) and the writer's LFP source
  (`escapewheel-writer/src/escapewheel_writer/sources/lfp.py`) write an absolute `uri` and no
  `source`; only the sidecar source passes one through.
- `artifacts/sources.schema.json` restricts an entry's `uri` to the pattern
  `^([A-Za-z][A-Za-z0-9+.-]+:|/)`: a URI with a scheme, or an absolute path.
- Part 04 §5.5 already asks a writer to choose a source name "unique beyond the packet, so that one
  resolution document serves many packets". No place a reader looks today serves more than one
  packet unless a caller passes it.

A neighbouring tool solves the same problem. `aind-rutter` locates each named input folder of a
configuration through, in order: a command-line override, paths files the command is given and
those its `RUTTER_PATHS` variable lists, a `rutter.paths.yml` in the configuration's folder or any
folder above it, the machine's own paths file, and last the configuration's own value. A path in a
paths file is relative to that file's folder, and its bundle command writes one at the top of a
bundle naming the copies by relative path. The arrangement transfers except for one property:
rutter's published inputs never change, so it never re-checks one it has cached, whereas a source
here can change and is verified against the packet's recorded digests.

Alternatives:

- **Keep caller-supplied documents only.** Every consumer carries locations in its own code, which
  is what source names were meant to end.
- **Names alone, without mirrors.** A machine mount covers every source in a store, so its document
  would list each one and go stale as sources are added, and it still could not reach an entry
  whose `uri` is absolute.
- **The variable alone, without a machine document.** A Jupyter kernel started from a launcher, a
  desktop application or a scheduled job often does not inherit the shell's environment, so the
  machine's statement is lost exactly where notebooks run.
- **A machine document at a path the specification names for each platform.** Two readers on one
  machine would find the same file, which the variable already achieves, at the cost of binding the
  specification to platform conventions that differ by library and change over time.
- **Fall through to the next document where a location is missing.** A reader would probe the
  filesystem or store for each candidate, so where a read lands would depend on what happened to be
  reachable, and a partial copy would silently mix with the original.
- **Dot segments, so the packet's own default can reach data beside the packet.** Part 03 §4 keeps
  `.` and `..` out of every relative reference, and on an object store they have no meaning except
  a lexical one this specification would have to define. A document in a folder above both the
  packet and its data reaches the data with downward paths alone.
- **Search above the packet on an object store too.** Each level is a request for a prefix nothing
  names, made by every reader that opens the packet; on a filesystem a level costs one lookup.

## 3. Decision

Three subsections replace parts of Part 04 §5.5: where a reader looks, how a location resolves
through what it finds, and what a document's locations may be relative to.

### 3.1 Where a reader looks for a resolution document

A reader MUST rank resolution documents in this order:

1. each resolution document its caller supplies, in the order supplied;
2. where the packet root is a filesystem path rather than a URI with a scheme, the file
   `sources.json` in each directory above the packet root, the nearest first, up to the
   filesystem's root;
3. each file named by the environment variable `ESCAPEWHEEL_SOURCES`, in the order named, which
   lists filesystem paths separated by the platform's path-list separator, `:` on POSIX systems and
   `;` on Windows, an empty entry naming nothing;
4. the reader's **machine document**, where it has one; and
5. `sources.json` at the packet root.

A reader MAY have a machine document, a per-user file at a location the reader chooses, and where it
has one MUST document that location, which no checker verifies. A document absent from a place in
the second to fifth items is skipped. A reader MUST NOT use a document it cannot read, one that
fails the schema where the reader validates it, or one whose `sources_standard_version` it does not
know, and MUST report that it did not use that document. A reader MUST NOT look for a resolution
document anywhere else, and MUST NOT search above a packet root that is a URI with a scheme.

The packet's own default comes last so that a document stated anywhere else overrides the locations
the writer recorded. A folder's document comes before the variable's and the machine's because it
is the more specific: a bundle's document names its copies even on a machine that mirrors the
original store.

### 3.2 A location resolves through the first document that speaks to it

A reader MUST resolve a `source` through the first ranked document whose `sources` names it, and
report it unresolved where none does.

A resolution document MAY carry `mirrors`, which maps a **mirror prefix**, an absolute URI or an
absolute path ending in `/`, to an entry whose `uri` is the directory or prefix standing for it.
Once a reader has an external resource's absolute location, whether from the entry's own `uri` or
from its source's location, it MUST apply the first ranked document holding a mirror prefix that
begins the location, and within that document the longest such prefix. The reader replaces the
prefix by the mirror's location, appending the names that follow the prefix, decoded where the
location is a URI, as Part 03 §4 appends a relative reference's names. A reader MUST apply mirrors
once, not to the location a mirror produced, and a location that no mirror prefix begins stands.

A reader MUST NOT test whether a location exists in order to choose among documents or mirrors,
which no checker verifies. A reader MUST report, for each external resource, the document through
which its source resolved and the document whose mirror it applied, where either did.

### 3.3 A document's locations may be relative to the document

A `uri` in a resolution document's `sources` or `mirrors` MAY be a relative reference in the form
of Part 03 §4, and a mirror's `uri` MAY also be empty; it is otherwise an absolute URI or an
absolute path. A reader MUST resolve a relative `uri` by appending its decoded names, in order, to
the directory or prefix holding the document, as Part 03 §4 resolves a relative reference against
a packet root, and an empty `uri` names that directory or prefix itself. A relative or empty `uri`
in a document that is not stored at a location names no location, and a reader MUST report a source
it would resolve through one as unresolved, and MUST NOT apply a mirror holding one.

`artifacts/sources.schema.json` admits `mirrors` and the relative and empty forms, and its `$id`
becomes `https://escapewheel.org/schemas/sources/0.2.0`. A document carries `sources`, `mirrors` or
both. Its `sources_standard_version` admits `escapewheel-sources-v0.2` and
`escapewheel-sources-v0.1`, and `mirrors` and a relative `uri` only at v0.2, so that a reader
knowing only v0.1 refuses a document it would misread. A reader that knows v0.2 MUST also read a
v0.1 document, whose locations are all absolute and which states no mirror. A writer MUST write
v0.2.

## 4. Questions

1. Does the search above the packet root extend to an object store?
   **Answered 2026-10-06:** No. It covers a packet root that is a filesystem path, which is where a
   bundle and a project folder live, and makes no request for an object-store prefix that nothing
   names.
2. Where does the packet's own default rank?
   **Answered 2026-10-06:** Last, after the folder documents, the variable and the machine
   document, as rutter ranks a configuration's own value, so a location stated anywhere else
   overrides what the writer recorded.
3. Does the specification name where a per-machine document is?
   **Answered 2026-10-06:** No. A reader may have one, ranked after the variable, at a location its
   documentation states. Where a configuration file belongs is a platform convention, and differs
   on macOS between libraries; `ESCAPEWHEEL_SOURCES` is the portable way to point every reader at
   one file.
4. Does a mirror reach an entry that names no source?
   **Answered 2026-10-06:** Yes. A mirror applies to an external resource's absolute location
   however the reader came by it, so a machine mount redirects every entry in the store with one
   line.

## 5. Consequence

No packet changes and no registry changes. A packet resolves as it does now on a machine with no
variable set, no machine document and no `sources.json` above it. Every document written at
`escapewheel-sources-v0.1`, a packet's default among them, still resolves. A reader that knows only
v0.1 refuses a v0.2 document, so a packet written after the change shows that reader its sources as
unresolved until the reader is updated.

A machine states a mount once, as one mirror in a document `ESCAPEWHEEL_SOURCES` names, or in a
reader's machine document where the variable does not reach that reader's process. A bundle states
its copies in a `sources.json` at its top, by source name or, where it keeps the store's layout, by
a mirror whose `uri` is empty; a mirror prefix naming one asset's directory redirects that asset
alone, so a partial copy sends what it lacks to the next document's mirror.

A `sources.json` above a packet or a machine document now changes where that packet's resources
resolve, which is the point of the change and also a way for a stray document to redirect a read.
Verification against the recorded digests catches a redirect to the wrong bytes only where a digest
was recorded, and many external entries carry none: a video records its size at most, and a Zarr v2
store often has no store digest. The report of which document and mirror placed each resource is
what lets a reader see a redirect it did not intend.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged: no concept's meaning moves. | None required. |
| logical prose and registry | Unchanged: a source is not a logical resource. | None required. |
| physical profiles | Unchanged: Part 03 §4's relative-reference form is cited, not changed. | None required. |
| packet manifest and JSON Schemas | Part 04 §5.5's resolution order, the schema's `mirrors` member, `uri` pattern, `$id` and version constant change under §§3.1 to 3.3. | The schema and `spec/tools` checks. |
| validation and import | Unchanged: structural validation still needs no resolution document. | None required. |
| extensions | Unchanged. | None required. |
| reader, writer, validator, adapters | The reader ranks documents in the new order, documents where its machine document is, applies mirrors, resolves a relative location against its document, and reports the document and mirror that placed each resource and each document it did not use. The reader's `rewrite` becomes a caller-supplied mirror. The reader's and validator's command lines accept resolution documents. The writer writes the new version. | The reader, validator and writer suites. |
| conformance fixtures and tests | §6's cases. | Reader tests. |
| revision process and tooling | The ledger places §§3.1 to 3.3. | `ledger.py`, `evidence.py`. |
| generated publications and developer documentation | The combined specification regenerates. The reader's documentation describes where it looks and how a mirror applies. | `verify.py`. |

## 6. Conformance and implementation evidence

These cases distinguish the new rules from the current ones:

- a packet whose default names a store, under a folder whose `sources.json` names a local copy,
  resolves to the copy;
- the same packet, with the reader's machine document and a document named by `ESCAPEWHEEL_SOURCES`
  each naming a different location, resolves to the folder's copy, without the folder's document to
  the variable's location, and without both to the machine document's;
- a caller-supplied document outranks all three;
- a `sources.json` above a packet root on an object store is not read;
- a machine document whose only member is a mirror redirects an entry with an absolute `uri` and an
  entry resolved through the packet's default, and leaves a location it does not begin unchanged;
- of two mirror prefixes in one document, the longer applies; a lower-ranked document's mirror does
  not apply where a higher-ranked one's does; and a mirror's result is not mirrored again;
- a bundle's mirror of the store's prefix with an empty `uri` resolves against the bundle's folder;
- a bundle's mirror of one asset's directory resolves that asset against the bundle's folder, and
  another asset falls to the machine document's mirror;
- a location reached through a mirror is reported with the document holding that mirror, and a
  source resolved through a relative `uri` opens with its recorded digest verified;
- a document of an unknown version, or one that cannot be read, is not used and is reported, and
  the next place is tried; and
- a v0.1 document resolves its sources, a v0.1 document holding a relative `uri` or `mirrors` fails
  the schema, and the writer's default is written at v0.2.
