# Drafts

A draft is candidate normative text for a problem whose scope and intended direction have already
been settled. Exploratory work belongs in `../proposals/`; start a draft from
`../templates/draft.md`.

A draft has no number. It gets one only after acceptance is authorized, taken from the end of the
accepted range, so the numbered space reads in the order revisions were **applied**
rather than the order they were written. Nothing outside this directory may cite a draft by number,
because it has none, and a draft does not change the authoritative generated v0.2 specification.

Why: an `R<N>` is permanent once accepted — `applied.toml` keys on it, `build.py` stamps it into
every column's `since`, the registry's `derived_from` lists it, and the compiled spec cites it. A
number assigned at drafting time forces the application order to match the drafting order, and
renumbering later would break all four.

A draft cites another draft by its file name in backticks. At acceptance those citations become
`R<N> §<x>`, which is a step in the acceptance sequence in `../CONTRIBUTING.md`.

## Application order

Dependencies run downward, so a draft may depend on the ones above it and on nothing below.

| order | draft | words | appraisal | placement |
|---:|---|---:|---|---|
| 1 | [`define-specification-artifacts-and-normative-ownership`](define-specification-artifacts-and-normative-ownership.md) | 4,085 | Revise before acceptance; R120 now assigns process ownership, structural reorganization, and one-way ledger traceability, but P0.2 has not disposed the historical and misplaced maintenance material | After P0.2 is accepted and incorporated, revise this draft's exact structural landing, traceability plan, appraisal baseline, and complete crosswalk. |

The last to leave was `allow-controlled-specification-reorganization`, accepted as **R120** on
2026-09-18 at 4,227 words. It makes this guide the owner of material revision procedure, establishes
process and specification decision domains, permits controlled structural reorganization through a
crosswalk and stable anchors, and changes the clause ledger to one-way current-owner traceability.
It changes no packet requirement or numbered-part body; P0.2 retains the separate cleanup of
historical and misplaced maintenance material.

The last to leave was `an-adapter-declares-the-options-it-accepts`, accepted as **R119** on
2026-09-15 at 2,172 words: an adapter declares in `accepts` the options it can run without, where
declaring one in `needs` makes a recipe carry it — which left 28 of the ten adapters' options
undeclarable and so unchecked, 10 of them set by the two packaged recipes. Its appraisal found the
new refusal breaking every declaration document written against R115, since none carries the key and
§3.2 refuses a recipe setting an option for an adapter that names none; §5 states that break and
accepts it, because scoping the refusal would make it inert on the adapter it exists for. The
appraisal also found `R63 §2.2` cited for a cost that section removes rather than imposes, which is
R63 §2.1's.

A draft withdrawn before acceptance is **deleted rather than numbered**, since the `R<N>` space
records what bound something and a draft never did. Git holds the document, and whatever the
appraisal found goes wherever the work went. `a-build-supplies-the-electrode-identifiers-it-assigned`
went that way on 2026-09-12 at commit `aa230d7`: it proposed a ninth term for Part 03 §11.2's supply
vocabulary, and the appraisal found the boundary already carried the value, `PacketWriter._preassign`
resolving a name to an assigned number packet-wide before any table is built (Part 05 §8). What the
adapters needed was to compose the name the owning adapter composes, which deleted the mapping
instead of declaring it — recorded in `TODO.md` §2.

The last to leave was `a-columns-encoding-follows-declared-order-and-counted-repetition`, accepted
as **R118** on 2026-09-15 at 2,744 words: Part 03 §5.5's tick, leading-identifier and float rules
became four rules over declared order and counted repetition, which leave 15 columns needing an
exception across the two packaged sessions where R110's leave 193. Its appraisal found the obvious
alternative unargued, writing each column three ways and keeping the smallest, and two clauses
carrying the reference writer into the profile. Building both sessions with `--sample 2000` to close
its last open measurement found the writer choosing a streamed table's encodings from the batch as
delivered rather than as written.

Before it, `an-adapter-delivers-an-array-by-writing-it`, accepted as **R117** on
2026-09-14 at 2,246 words: a packet-owned array crosses by being written to the location a build
supplies and read back, since every field of its manifest entry is recoverable from the array and
its name; a referenced one crosses as a resource document under the delivery's own reserved
identifier. Two forms were rejected on the way, both recorded in its §3.2 — the run's report, which
Part 09 §5.8 makes optional where a catalog cannot be, and a document beside the delivery, which
needed a term, an action and a rule about arriving that the delivery already gives.

Before it, `a-build-supplies-a-source-on-standard-input`, accepted as **R116** on
2026-09-14 at 1,283 words: the object a build supplies crosses on standard input, because the
argument list it crossed by caps one argument at 131,072 bytes on Linux and a whole command line at
32,767 characters on Windows, where the NWB adapter's object for one real session is 322,799.

Before it, `a-build-reaches-a-source-through-declarations`, accepted as **R115** on
2026-09-11 at 12,038 words. It was two drafts merged — a writer requiring no knowledge of a
particular source, and an adapter's rows crossing a process boundary — split at 3,801 words for
length and unacceptable apart, since each carried a mechanism the other's rules stood on. The
split also hid a contradiction between them for a day.
