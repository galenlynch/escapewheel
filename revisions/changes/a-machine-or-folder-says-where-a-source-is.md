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
| **Decision clauses** | §3.1; §3.2 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Problem

An external resource entry can name a `source`, a body of data such as one session's raw
recording, and give its `uri` relative to wherever that source is. Part 04 §5.5 has a **source
resolution document**, conventionally `sources.json`, map each source name to an absolute URI or an
absolute path. A reader tries the documents its caller supplies, in order, and then the `sources.json`
at the packet root, which the writer writes naming where it read each source. The design is meant
to let the same packet find its data at a different place on each machine without being rebuilt.

It does that only for a caller who passes a document every time. Three arrangements it is meant
for fail:

- **A machine holds the data at its own path**, such as a cluster mount of a bucket. Nothing lets
  the machine state that once, so every notebook, script and tool carries the path or an argument
  naming a document.
- **A folder of packets shares mirrors.** Each packet's default has to be edited, or a document
  passed each time; no document can serve the folder.
- **A packet travels with its data**, as a bundle copied to a laptop. The default still names the
  original store, so a reader reads from there, or reports the source unresolved while offline,
  with the copy beside it. No document can say where a source is relative to itself, because the
  schema admits only absolute locations.

This change adds two places a reader looks, a folder above the packet and a variable naming
documents, and lets a document locate a source relative to itself. What a resolution document
means, that one is never a packet resource, that an unresolved source is a fact rather than a
defect, and how a resolved source is verified against its recorded digest are unchanged.

## 2. Evidence

Observations are of the tree at the commit this document is based on.

- `escapewheel_reader.open_packet` takes resolution documents as its `sources` argument, and
  `resolve_sources` (`escapewheel-reader/src/escapewheel_reader/location.py`) keeps the first
  location each name is given. Neither the reader's nor the validator's command line accepts a
  resolution document, so from the command line only the packet's default is ever consulted.
- The reader also takes `rewrite`, a URI-prefix substitution applied to every resource. It is the
  mechanism source names were introduced to replace, and it survives because nothing else lets a
  caller redirect a packet whose default is wrong.
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
- **A per-machine document in the platform's configuration folder.** Rutter has one. The folder
  differs by operating system and by library, so a specification naming it would bind every
  reader to one library's convention; the variable can list a machine-wide document instead.
- **Dot segments, so the packet's own default can reach data beside the packet.** Part 03 §4 keeps
  `.` and `..` out of every relative reference, and on an object store they have no meaning except
  a lexical one this specification would have to define. A document in a folder above both the
  packet and its data reaches the data with downward paths alone.
- **Search above the packet on an object store too.** Each level is a request for a prefix nothing
  names, made by every reader that opens the packet; on a filesystem a level costs one lookup.

## 3. Decision

Two subsections replace parts of Part 04 §5.5: where a reader looks, and what a document's `uri` may
be.

### 3.1 Where a reader looks for a source

A reader MUST resolve a `source` through the first of these documents that names it, and report it
unresolved where none does:

1. each resolution document its caller supplies, in the order supplied;
2. where the packet root is a filesystem path rather than a URI with a scheme, the file
   `sources.json` in each directory above the packet root, the nearest first, up to the
   filesystem's root;
3. each file named by the environment variable `ESCAPEWHEEL_SOURCES`, in the order named, which
   lists filesystem paths separated by the platform's path-list separator, `:` on POSIX systems and
   `;` on Windows, an empty entry naming nothing; and
4. `sources.json` at the packet root.

A document absent from a place in the second to fourth items is skipped. A reader MUST NOT resolve a
source through a document it cannot read, one that fails the schema where the reader validates
it, or one whose `sources_standard_version` it does not know, and MUST report that it did not use
that document. A reader MUST NOT look for a resolution document anywhere else, and MUST NOT search
above a packet root that is a URI with a scheme.

The packet's own default comes last so that a folder's or a machine's document overrides the
locations the writer recorded. A folder's document comes before the variable's because it is the
more specific: a bundle's document names its copies even on a machine whose variable names the
original store.

### 3.2 A document's location may be relative to the document

A resolution document entry's `uri` MAY be a relative reference in the form of
Part 03 §4, and is otherwise an absolute URI
or an absolute path, as now. A reader MUST resolve a relative `uri` by appending its decoded names,
in order, to the directory or prefix holding the document, as Part 03 §4 resolves a relative
reference against a packet root. A relative `uri` in a document that is not stored at a location
names no location, and a reader MUST report a source it would resolve through one as unresolved.

`artifacts/sources.schema.json` admits the relative form, and its `$id` becomes
`https://escapewheel.org/schemas/sources/0.2.0`. Its `sources_standard_version` admits
`escapewheel-sources-v0.2` and `escapewheel-sources-v0.1`, and a relative `uri` only at v0.2, so
that a reader knowing only v0.1 refuses a document that may hold a relative location rather than
misreading it. A reader that knows v0.2 MUST also read a v0.1 document, whose locations are all
absolute. A writer MUST write v0.2.

## 4. Questions

1. Does the search above the packet root extend to an object store?
   **Answered 2026-10-06:** No. It covers a packet root that is a filesystem path, which is where a
   bundle and a project folder live, and makes no request for an object-store prefix that nothing
   names.
2. Where does the packet's own default rank?
   **Answered 2026-10-06:** Last, after the folder documents and the variable, as rutter ranks a
   configuration's own value, so a mirror stated anywhere else overrides what the writer recorded.
3. Does the specification name a per-machine document in the platform's configuration folder?
   **Answered 2026-10-06:** No. `ESCAPEWHEEL_SOURCES` can list one, and a folder's location differs
   by operating system and library.

## 5. Consequence

No packet changes and no registry changes. A packet whose default names its sources resolves as it
does now on a machine with no variable set and no `sources.json` above it. Every document written
at `escapewheel-sources-v0.1`, a packet's default among them, still resolves. A reader that knows
only v0.1 refuses a v0.2 document, so a packet written after the change shows that reader its
sources as unresolved until the reader is updated.

A `sources.json` placed above a packet now changes where that packet's sources resolve, which is
the point of the change and also a way for a stray document to redirect a read. Verification
against the recorded digests is what catches a redirect to the wrong bytes, and is unchanged.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged: no concept's meaning moves. | None required. |
| logical prose and registry | Unchanged: a source is not a logical resource. | None required. |
| physical profiles | Unchanged: Part 03 §4's relative-reference form is cited, not changed. | None required. |
| packet manifest and JSON Schemas | Part 04 §5.5's resolution order and the schema's `uri` pattern, `$id` and version constant change under §§3.1 and 3.2. | The schema and `spec/tools` checks. |
| validation and import | Unchanged: structural validation still needs no resolution document. | None required. |
| extensions | Unchanged. | None required. |
| reader, writer, validator, adapters | The reader resolves in the new order, reads `ESCAPEWHEEL_SOURCES`, searches above a filesystem packet root, resolves a relative location against its document, and reports which document resolved each source and each document it did not use. The reader's and validator's command lines accept resolution documents. The writer writes the new version. | The reader, validator and writer suites. |
| conformance fixtures and tests | §6's cases. | Reader tests. |
| revision process and tooling | The ledger places §§3.1 and 3.2. | `ledger.py`, `evidence.py`. |
| generated publications and developer documentation | The combined specification regenerates. The reader's documentation describes where it looks. | `verify.py`. |

## 6. Conformance and implementation evidence

These cases distinguish the new rules from the current ones:

- a packet whose default names a store, under a folder whose `sources.json` names a local copy,
  resolves to the copy;
- the same packet with `ESCAPEWHEEL_SOURCES` naming a document that names a third location resolves
  to the folder's copy, and without the folder's document to the variable's location;
- a caller-supplied document outranks all three;
- a `sources.json` above a packet root on an object store is not read;
- a folder document whose `uri` is relative resolves against that folder, and a source resolved
  through it opens with its recorded digest verified;
- a document of an unknown version, or one that cannot be read, is not used and is reported, and
  the next place is tried; and
- a v0.1 document resolves its sources, a v0.1 document holding a relative `uri` fails the
  schema, and the writer's default is written at v0.2.
