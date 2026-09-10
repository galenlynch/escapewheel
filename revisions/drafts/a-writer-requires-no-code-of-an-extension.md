# A Writer Requires No Code of an Extension

| | |
|---|---|
| **Status** | Draft |
| **Amends** | `09` §5 (adds the contract an extension is held to); `05` §3.4 (what a build may require of a source that is an extension, and what it owes when that source's command fails) |
| **Depends on** | R17 §2 (an extension is a registry document in `02`'s format), R17 §4 (an extension's verdict is separate), R63 §2.1 (an adapter declares `PRODUCES`), R53 §2.5 (a writer mints every assigned identifier), R79 §2.2 (a packet obligation and an importer obligation are reported apart), R51 §2.2 (a record optional to produce and useful when present), R3 §3.0 (duplication must buy otherwise-unavailable access) |
| **Profile** | all |

Normative, except §2, which is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

`09` §5.1 says an extension needs no code: a registry document names its tables, Parquet files hold
their rows, and neither imports anything of the reference implementation. That states what an
extension may get away with. It does not state what a **writer** may require, and the difference is
the whole of an extension's independence — a writer free to demand code makes "needs no code" a
courtesy rather than a contract.

This part makes the boundary the requirement: a build reaches an extension through files and, where
a raw source needs converting, a subprocess. Everything more coupled becomes an optimisation that
nothing may depend on. It also states what crosses back, because a boundary that carries an exit
status and nothing else makes every failure behind it look the same.

Measured on the four extension registries this repository carries — `aind_opto`, `aind_unit_qc`,
`dynamic_foraging` and `vr_foraging` — and on the two packaged sessions **`ecephys_776259`** (twelve
probes, 6,781 sorted units, recorded 2025-04-09) and **`ecephys_786867`** (ten probes, 4,505 units,
recorded 2025-09-25).

## 2. Background

Informative.

### 2.1 The contract is stated in pieces

Four parts each hold one piece and none holds the shape. R17 §2 makes an extension a registry
document and `09` §5.2 namespaces it. `09` §5.3 has a packet declare it in the catalog. `05` §3.4
has a source adapter declare `PRODUCES` before any I/O (R63 §2.1). `09` §5.1 observes that no code
is needed.

What no part says is what a build may **require**. An implementation that resolved an extension only
through an installed distribution would contradict no clause, and every packet it wrote would
conform.

### 2.2 Every extension table in both packets crosses a boundary

Both recipes supply all six extension tables — `dynamic_foraging.trials`, `.blocks`, `.sessions` and
`aind_unit_qc.metrics`, `.waveform_metrics`, `.synchrony` — through a source of kind `tables`,
reading Parquet that a `command` produced first. **No distribution registers an extension registry
under the entry-point group at all.**

So the decoupled path carries everything and the coupled path carries nothing. A rule written the
other way round would describe no build that has ever run here.

### 2.3 A shared process is a shared dependency closure

An extension that runs inside the writer resolves its dependencies against the writer's environment.
Two extensions pinning incompatible versions of one library make that environment unsolvable, and
neither extension is wrong — the conflict is a property of the pair. The cost lands on whoever is
building a packet, who wanted one of them and gets neither.

Solving it out of process costs almost nothing here, because R53 §2.5 already has the writer mint
every assigned identifier: an extension writes `session_id` as `"ecephys_776259"` and never learns
the integer. It cannot need the writer's objects, because the numbers it would need do not exist
until after it has finished.

### 2.4 A command's output arrives unattributed

Every source but this one tells the build what it did with what it found — **67 notes** in
`ecephys_776259`'s build and **49** in `ecephys_786867`'s, recording a probe with no original
timestamps, a video with no timing file, a sorter stamping no UTC offset. The `tables` source
supplying **six of forty tables** contributes **one** of them, and that one says only that the
command ran.

The command's own account is not missing. It is unattributable: a subprocess inherits the build's
streams, so `extract.py`'s output lands between the build's own lines with no timestamp, no source
name, and ahead of the note recording the run.

```
[  45.7s] tables -> dynamic_foraging.trials, dynamic_foraging.blocks, ...
450 trials -> 19 blocks
  blocks.parquet        19 rows x  8 cols     3.1 KB
  qc_metrics.parquet  4505 rows x 24 cols   495.9 KB
  … four more
[  46.3s]   note: ran 'python extract.py' in /mnt/Data/786867-packet
```

Six of those lines restate what a build already reads from the Parquet footer at `05` Stage 1
without opening a row. The one carrying a fact nothing else holds is the first: 450 trials became
19 blocks, a relation between the command's inputs and its outputs that no artifact in the packet
records.

What a failing command tells the build is less again. A command that cannot start, one that exits
non-zero, and one that exits zero having written nothing are a recipe's defect and an extension's
twice over; a build tells the first from the second by the kind of error the operating system
raised, and reports the third as `no file at the declared path`, naming the resource rather than
whatever was supposed to produce it. The non-zero case arrives as an exit status alone, its
diagnosis having gone to a stream nobody kept.

## 3. Decision

### 3.1 A writer requires no code of an extension

A writer **MUST** be able to build a packet carrying an extension's tables given only the
extension's registry document and its rows as files. A writer **MUST NOT** require an extension to
be installed, importable, or resolvable in the writer's own environment.

A writer **MAY** accept an extension that ships code — an adapter registered under an entry-point
group, or a registry document loaded from an installed distribution — and **MUST NOT** treat either
as the ordinary case, which is what `09` §5.1's "needs no code" turns from a possibility into a
promise.

### 3.2 An extension delivers a registry document and rows as files

An extension delivers a registry document in `02`'s format (R17 §2) and, per table it declares, rows
as Parquet. Where a raw source needs converting first, a recipe names a **command**: an argument
list run in the source's own root, not a shell line, so an extension isolates its dependencies
however it likes and a build states no opinion about how.

How the document is produced is the extension's business — generated from a schema definition, from
a spreadsheet, or typed — but an extension **MUST NOT** derive it from the rows it delivers for the
packet being built. A declaration derived from one packet's data cannot disagree with that data, so
it declares nothing, and two packets whose extensions each derived one are two relations rather than
the one R86 §2.1 presents.

`aind_unit_qc.waveform_metrics` measures the difference. It declares **13** columns; the extraction
in both packaged sessions delivers **10**, and both packets carry 13, with `half_width`,
`peak_to_valley` and `peak_trough_ratio` null in all 6,781 rows of one and all 4,505 of the other.
A document derived from either file would declare 10 and assert that this extension **has** no
`half_width` — where the hand-written one says that this pipeline did not compute one, which is a
fact about the run rather than about the extension. R2 §5's three presence states are what carry
that distinction, and deriving the document discards them.

The document therefore reaches a build through the recipe rather than through the command: a build
loads the documents a recipe names before any source runs, because it resolves each source's owned
resources against them before it performs any I/O (R63 §2.1).

Rows arrive carrying identifiers as the **names** their source used, and a writer numbers them
(R53 §2.5), so an extension neither knows nor needs the packet's numbering; two extensions naming
one unit differently is a defect the writer resolves rather than one they must coordinate over.

### 3.3 A build reports a failed command against the source that ran it

A command that exits non-zero **MUST** fail the build, and a build **MUST** name the source whose
command failed together with the resources that source owns, rather than reporting the first
resource it then finds missing. R17 §4 keeps an extension's validation verdict separate from core's
for the same reason, and R79 §2.2 keeps a packet obligation apart from an importer's: a finding that
names the wrong party sends someone to the wrong artifact.

A command belongs to a source, and a source is not an extension. Both packaged recipes give
one `tables` source a single `command`, and it produces **six tables across two extensions** —
`dynamic_foraging.trials`, `.blocks`, `.sessions` and `aind_unit_qc.metrics`, `.waveform_metrics`,
`.synchrony` — so a build naming the extension would pick one of the two and be wrong about the
other half of the tables. Which extension came up short is a fact about the outputs, which §3.6
lets an extension state; which command failed is a fact the build holds already.

### 3.4 A build keeps what a command wrote to its streams

A build **MUST** capture a command's standard output and standard error and **MUST** report them
with a failure of that command. Where the command succeeds, a build **SHOULD** keep them readable
afterwards.

This does not require holding the output in memory. A command may run for minutes and its progress is
worth watching while it does, so a build writes the streams to a file and reports that file and its
last lines. What the requirement forbids is the arrangement §2.4 measures, where a diagnosis is
printed to a stream nobody kept and the failure is reported as an exit status.

Nothing here is asked of the extension. An extension that prints why it stopped is already
behaving well, and what is missing is custody of what it printed, which only the build can hold.

### 3.5 An extension may validate its own tables

An extension **MAY** validate its own tables before returning them, against its own registry
document and on the same terms a validator applies to core (R17 §4). Nothing about the boundary
prevents it: the validator is a distribution an extension may depend on exactly as it depends on
Parquet, and doing so in the extension's own environment is what the boundary makes safe.

A build **MUST NOT** rely on an extension having done so. Its own validation runs over every staged
resource whatever produced it, which is what `05` makes commit mean.

### 3.6 An extension may state what a build cannot derive

An extension **MAY** write a report of its run at a path the recipe names, and a build **MUST**
report what one contains where it is present. A build **MUST NOT** require one, and **MUST NOT**
fail a build on a report's contents alone: a validator judges the tables (R17 §4), and an
extension's account of its own inputs says how they came to be rather than whether they conform.

A report carries what a build cannot derive, and a build **SHOULD** ignore what it can. Rows per
table, which tables exist, and whether their schemas conform are each established without asking —
from the Parquet footer at `05` Stage 1, from the recipe, and by validation — so a report restating
them is R3 §3.0's duplication that buys no otherwise-unavailable access, which §2.4 measures two
lines of. What no artifact holds is what the command **read**, what it **skipped and why**, and
whether a table that is short is legitimately short.

A report is JSON, and small enough that writing one is not a project. An optional `problems` array
carries an entry per finding, each with a `level` of `error`, `warning` or `info` — R2 §7.3's
levels, so a build reports an extension's findings on the terms it reports a rule's — a `message`,
and optionally the `resource` the finding concerns. An optional `read` array names what the command
consumed. A build **MUST** report every problem it is given and **MUST NOT** refuse a report for
carrying keys it does not recognise, which is what lets an extension say more than this without
waiting for a revision to permit it.

A file rather than the streams §3.4 keeps, because those carry output written for a person: every
command in both packaged recipes prints for a human, so a build parsing them would be reading a
person's report as a machine's. A path the recipe names is opt-in by construction and collides with
nothing the command already prints.

Optional to produce and useful when present is R51 §2.2's shape for `store_digest`, adopted for the
same reason. Every artifact an extension must produce before its tables are accepted is a reason
not to write an extension, and `09` §5.1's "needs no code" exists to keep that gradient flat.

## 4. What this does not change

- **An extension is still a registry document.** R17 §2 is untouched; this part says how the
  document and its rows reach a build, not what either contains.
- **No packet is invalidated and no table changes.** This binds a writer and a build, so what
  changes is what an implementation may demand before it will write one.

## 5. Consequence

`09` §5 gains the contract as new subsections, and `05` §3.4 gains what a build owes when a source's
command fails. No table, column, reference, rule or vocabulary changes, and neither packaged packet
is rebuilt for this part.

The reference implementation satisfies §3.1 and §3.2 already — a source of kind `tables` reads files
after running a command, resolves an extension registry from a path or an installed distribution,
and requires neither — and owes three things. It names the missing resource rather than the source
when a command fails (§3.3); it keeps nothing of what a command wrote (§3.4); and it reads no report
(§3.6). The first two are changes to one adapter. The third is a recipe field and a reader for it,
and neither packaged recipe would set it until an extension writes one.

No packet changes, because §2.2 measures that every extension table already arrives across the
boundary. What §3.1 buys is that it must keep doing so, and what §2.4 measures is what crossing it
costs to debug meanwhile: one note in sixty-seven for six of the packet's forty tables.

## 6. Open

- **What an extension may assume about a rebuild.** R75 §2.1 requires two builds of one recipe over
  the same source bytes to produce the same rows and the same assigned identifiers, and a command is
  an argument list a build does not otherwise constrain — so an extension whose command is not
  deterministic breaks that guarantee without breaking any clause here. Whether determinism is an
  extension's obligation or a recipe author's is unsettled, and neither packaged session exercises
  it: both commands read a fixed file and write a fixed table. §3.6's report is where an extension
  would record the inputs that make the question answerable, which is an argument for the field it
  is not an argument for requiring one.
