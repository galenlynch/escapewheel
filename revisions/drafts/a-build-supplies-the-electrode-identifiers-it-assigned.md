# A Build Supplies the Electrode Identifiers It Assigned

| | |
|---|---|
| **Status** | Draft |
| **Amends** | Part 03 §11.2 (`electrodes` joins the closed supply vocabulary, which source's rows fill it, and what a build refuses where a key is null); Part 03 §11.3 (an identifier a build supplied crosses back as a number, and an adapter reports a supplied identifier it cannot resolve) |
| **Depends on** | R115 §3.1 (the closed supply vocabulary, its resolution order, and a build refusing a term it cannot fill), R115 §3.7 (an identifier crosses the boundary as a name, because an assigned number does not exist until a writer mints it), R53 §2.3.1 (an assigned identifier's owner carries its name), R53 §2.5 (a writer assigns identifiers when it commits), R81 §1.2 (a source's own label repeats, so the key is a pair), R83 §1.1 (an index resolved against a list nobody wrote down), R83 §2.3 (a consumer reports an index it cannot resolve rather than resolving it against the wrong list) |
| **Profile** | all |

Normative, except §1 and §4, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

### 1.1 Two adapters need an electrode map no term carries

Part 03 §11.2 lists what a build passes an adapter: eight terms, each naming one value and the form
it takes, so that an adapter and a build written by different people pass the same thing. A name an
adapter declares resolves against that list first and the recipe's options second, and a build
refuses a recipe where it resolves to neither (R115 §3.1).

Two adapters need a ninth. Both the LFP adapter and the waveform adapter must reach the
`electrode_id` a build assigned to a contact their own source describes, and no existing term or
option carries it: an option is a literal the recipe writes down, and this value does not exist until
another source has run and the writer has numbered what it delivered (R53 §2.5). So a build reading
either declaration refuses every recipe naming either adapter, and the two resources those adapters
own cannot be produced at all.

What the mapping carries, measured on the two packaged sessions: `core.unit_electrodes` at
**171,280** and **114,945** rows, and `core.array_channels` at **1,152** and **960**. Every one of
those rows names an electrode the adapter reached through the mapping and could reach no other way.

### 1.2 The electrode label repeats across probes

`core.electrodes.local_electrode_label` is the source's own name for a contact, and it is not unique
within a session: **1,920 distinct labels over 4,608 electrodes on 12 probes**, and **1,920 over
3,840 on 10 probes**. Beside the probe's own name it is unique in both — **4,608 of 4,608** and
**3,840 of 3,840** distinct `(probe_name, local_electrode_label)` pairs, with no null label in
either — so the key is a pair of names the source states, as a sorter's unit label needs its run for
the same reason: R81 §1.2 measured 810 distinct labels over 6,781 `(unit_id, sorting_run_id)` pairs
across 12 runs.

Both halves are declared nullable, so a source may state neither, and §2.1 refuses such a source
rather than falling back to something weaker.

### 1.3 A row position cannot cross the boundary

What both adapters hold is not a label but an index. The NWB names the contacts of an electrical
series and of a waveform group by their position in its own electrode table, so the value the array
hands an adapter is a row number in a file that adapter has open.

Passing that number to the build instead would make a delivery's row order load-bearing. A build's
only statement of a source's row positions is the order the rows arrived in, and Part 03 §11.3 makes
the declared sort the build's, so nothing states or checks the order a delivery comes in; an adapter
reordering what it hands over would leave every index naming a different contact, with no artifact
disagreeing. R83 §1.1 measures what that costs: an index resolved against a list nobody wrote down
named the wrong electrode for **5,071 of 6,781 units**, and was caught only because **609** of them
landed outside the unit's own channel support, the other 4,462 keeping a plausible wrong contact.

Resolving that index against the file it indexes is a different act, and one the adapter holding the
file can perform: the names it resolves to are facts the source states, and those cross.

### 1.4 An unresolved identifier disappears without a finding

An electrode the mapping does not carry is handled two ways in the reference implementation, neither
of them visible. `core.array_channels.electrode_id` is nullable, so the LFP adapter writes a null and
the row validates. `core.unit_electrodes.electrode_id` is required, so the waveform adapter drops the
row. That same waveform adapter reports an unmatched **unit** — `units: n NWB row(s) match no unit or
are all zero; skipped` — and says nothing at all about an unmatched electrode. §1.3's measurement is
what an unreported miss costs, so the term needs a rule about missing as much as it needs a shape.

## 2. Decision

### 2.1 `electrodes` is a term of the supply vocabulary

Part 03 §11.2's table gains a row:

| term | what a build passes |
|---|---|
| `electrodes` | one record per electrode: its probe's name, the source's label for the contact, and the identifier assigned |

A build **MUST** fill it from the rows of the source that owns `core.electrodes`, taking each probe's
name from `core.probes.probe_name` (R53 §2.3.1) and each contact's from
`core.electrodes.local_electrode_label`. A build **MUST** refuse a recipe where that source leaves
either null in any row it delivers, naming the source and the column: R115 §3.1 already refuses a
term a recipe cannot fill, and a mapping half of whose keys are null is that term rather than a
shorter one.

Keying the term on a row position is rejected for §1.3's reason, and carrying that position as a
column of `core.electrodes` fails the same way while costing a column in every packet: the position
describes a file the packet exists to replace, and no consumer resolves anything through it.

**Opening the vocabulary is rejected, because an unreserved term has no filler.** The open half
already exists: a name outside the list resolves against the recipe's options, filled by whatever the
recipe carries. What is left over is a value computed mid-build from another source's rows, and no
recipe can write one down, so a build meeting an unreserved name can only refuse — which is what it
does today. Reserving a term buys a **pinned form** rather than a filler: `first_samples` is a recipe
option in the reference implementation and Part 03 §11.2 reserved it anyway, to fix the record shape
two implementations have to agree on. An open supply vocabulary is a set of names with no agreed
shapes, under which a third-party adapter and a build it never saw each pass something reasonable and
neither is wrong.

### 2.2 A supplied identifier crosses back as a number

Part 03 §11.3 requires an adapter to hand over identifiers as the names its source used and never as
numbers, because a writer mints every assigned identifier packet-wide and the numbers do not exist
until it has (R115 §3.7, R53 §2.5). That reason holds for an identifier the adapter learned from its
source and fails for one the build handed it, which exists already.

So an adapter **MUST** hand over an identifier it learned from its source as that source's name, and
**MAY** hand over an identifier a build supplied it as the number it was given. Without the second
half the term buys nothing: `core.unit_electrodes.electrode_id` is required and the adapter has no
name to put there. Returning the pair for the build to resolve is the alternative, and it costs two
string columns over the 288,337 rows of §1.1 and a resolution per row, to move a lookup the adapter
can already perform — and it would retire `units` by the same argument, which R115 §3.1 settled the
other way.

### 2.3 An adapter reports a supplied identifier it cannot resolve

An adapter meeting a pair the supplied records do not carry **MUST** report it and **MUST NOT** write
a null or drop the row in silence. Where it writes a report the finding is a `problems` entry
(Part 09 §5.8); in the build's own process it is a note of the delivery, and a build **MUST** report
what it is given either way. This is R83 §2.3's rule for an unresolvable channel index, on an
identifier a build supplied rather than on a column a packet carries.

The empty case needs no rule. R115 §3.1 already has a build refuse a recipe where a term cannot be
filled and forbids passing one absent or empty, so an adapter declaring `electrodes` is never handed
nothing; what remains is a mapping that is present and short.

## 3. What this does not change

- **No table, column, reference, rule or vocabulary of the registry.** §1.1 counts rows of
  `core.unit_electrodes` and `core.array_channels`, and §2.1 reads `core.probes.probe_name` and
  `core.electrodes.local_electrode_label` as they stand and adds nothing to either table.
- **No packet is invalidated**, and neither packaged session is rebuilt. The rows those two adapters
  produced are the rows they produce under this revision; what changes is how the value reaches them
  and what happens when it misses.

## 4. Consequence

The supply vocabulary goes from eight terms to nine, and `electrodes` is the second of them to carry
assigned identifiers keyed by names a source states, after `units`. Those two are one family, and
parameterizing it is declined here because the pair is resource-specific: `units` keys on a sorting
run's device and the sorter's label for the unit, `electrodes` on a probe's name and the source's
label for the contact, so a parameterized term must name its key columns and an adapter's declaration
stops being a list of names. Two instances is where R55 §2.1 named the mechanism it found under
`scope_kind` and `interval_kind`, so what defers this one is the key and not the count.

Growth is bounded by what flows **into** an adapter rather than by how many adapters there are. Of
the fifteen fields the reference implementation's build context holds, five ever cross into an
adapter — the session's name, the reference clock, the clocks declared so far, the unit mapping and
this electrode mapping — while the other ten are things adapters produce and the build consumes. Ten
adapters draw on those five.

Nothing rebuilds. The two adapters declare the term and resolve their own source's row positions
against its electrode table, the two `spec.kind` branches that pass the mapping today are replaced by
the declaration, and §1.4's silent misses become findings.
