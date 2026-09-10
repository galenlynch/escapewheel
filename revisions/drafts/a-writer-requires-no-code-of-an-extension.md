# A Writer Requires No Code of an Extension

| | |
|---|---|
| **Status** | Draft |
| **Amends** | `09` §5 (adds the contract an extension is held to); `05` §3.4 (what a build may require of a source that is an extension) |
| **Depends on** | R17 §2 (an extension is a registry document in `02`'s format), R17 §4 (an extension's verdict is separate), R63 §2.1 (an adapter declares `PRODUCES`), R53 §2.5 (a writer mints every assigned identifier), R79 §2.2 (a packet obligation and an importer obligation are reported apart) |
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
nothing may depend on.

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

## 3. Decision

### 3.1 A writer requires no code of an extension

A writer **MUST** be able to build a packet carrying an extension's tables given only the
extension's registry document and its rows as files. A writer **MUST NOT** require an extension to
be installed, importable, or resolvable in the writer's own environment.

A writer **MAY** accept an extension that ships code — an adapter registered under an entry-point
group, or a registry document loaded from an installed distribution — and **MUST NOT** treat either
as the ordinary case, which is what `09` §5.1's "needs no code" turns from a possibility into a
promise.

### 3.2 What an extension delivers

An extension delivers a registry document in `02`'s format (R17 §2) and, per table it declares, rows
as Parquet. Where a raw source needs converting first, a recipe names a **command**: an argument
list run in the source's own root, not a shell line, so an extension isolates its dependencies
however it likes and a build states no opinion about how.

Rows arrive carrying identifiers as the **names** their source used. A writer numbers them (R53
§2.5), so an extension neither knows nor needs the packet's numbering, and two extensions naming one
unit differently is a defect the writer resolves rather than one they must coordinate over.

### 3.3 A build reports an extension's failure as the extension's

A command that exits non-zero **MUST** fail the build, and a build **MUST** report which extension's
command failed rather than reporting the resource that went missing. R17 §4 keeps an extension's
validation verdict separate from core's for the same reason, and R79 §2.2 keeps a packet obligation
apart from an importer's: a finding that names the wrong party sends someone to the wrong artifact.

### 3.4 An extension may validate its own tables

An extension **MAY** validate its own tables before returning them, against its own registry
document and on the same terms a validator applies to core (R17 §4). Nothing about the boundary
prevents it: the validator is a distribution an extension may depend on exactly as it depends on
Parquet, and doing so in the extension's own environment is what the boundary makes safe.

A build **MUST NOT** rely on an extension having done so. Its own validation runs over every staged
resource whatever produced it, which is what `05` makes commit mean.

## 4. What this does not change

- **An extension is still a registry document.** R17 §2 is untouched; this part says how the
  document and its rows reach a build, not what either contains.
- **No packet is invalidated and no table changes.** This binds a writer and a build, so what
  changes is what an implementation may demand before it will write one.

## 5. Consequence

`09` §5 gains the contract as new subsections and `05` §3.4 gains the requirement that a command's
failure be reported against the extension. No table, column, reference, rule or vocabulary changes,
and neither packaged packet is rebuilt for this part.

The reference implementation already satisfies it and gains one report: a source of kind `tables`
reads files after running a command, resolves an extension registry from a path or an installed
distribution, and requires neither. What it does not do today is name the extension when a command
fails, which §3.3 requires.

Nothing is measured as changing, because §2.2 measures that every extension table in both packets
already arrives this way. What the part buys is that it must keep doing so.

## 6. Open

- **What an extension may assume about a rebuild.** R75 §2 wants two builds of one recipe to produce
  one packet, and a command is an argument list a build does not otherwise constrain — so an
  extension whose command is not deterministic breaks that guarantee without breaking any clause
  here. Whether determinism is an extension's obligation or a recipe author's is unsettled, and
  neither packaged session exercises it: both commands read a fixed file and write a fixed table.
