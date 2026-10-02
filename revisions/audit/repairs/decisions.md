# Decisions the ledger repair waits on

The audit of `revisions/applied.toml` asked, for each accepted Decision clause recorded as
`applied`, whether the section the ledger names still states the rule. Its record is
[applied-targets.md](../applied-targets.md). A critical reading of the unrepaired classes then
sorted each rule into one that can be entered as written, one that is not owed, and one that needs
a choice. This file lists every choice, with what each option changes, so that each can be
answered without opening the repair files.

Entries are cited by class letter and number: C5 is entry 5 of
[C-indicative-sections.md](C-indicative-sections.md), D5 of
[D-needs-a-choice.md](D-needs-a-choice.md), E2 of [E-disputed.md](E-disputed.md), and G1 the first
entry of [G-process-and-dispositions.md](G-process-and-dispositions.md). Each entry there carries
the clause's words, the readings, the candidate text and the evidence.

"Fix" means the ordinary workflow: the accepted clause already decided the rule, so no
implementation that conformed to the decision behaves differently. "Revision" means the change
alters what a conforming implementation does or what an incorporated artifact carries, so it goes
through the revision process and needs its own acceptance.

## Answered on 2026-10-02

Every decision took its preferred option. The eighth was left open on a first pass, since the
reference engine does not meet the rounding rule it restores, and took its preferred option the
same day once its entry stated the options again with what was measured.

| decision | answer | entered by |
|---:|---|---|
| 1 | §1 lists the first paragraph of §14.4 as binding every implementation | `b5696685` |
| 2 | the keyword is restored and the loader checks a path-valued registry from its bytes | `b5696685`, `6dc476a9` |
| 3 | every writer command that rejects a registry offers that registry's result | `ba589b18` |
| 4 | the label rule binds a validator's report | `b5696685` |
| 5 | the eleven further §14 sentences are repaired with the entries | `b5696685` |
| 6 | one unchecked label under the §14 heading | `b5696685` |
| 7 | one §1 sentence gives Part 11 §§2 to 8 their force | `b5696685` |
| 8 | Part 11 §4 states the rounding rule, and the validator converts a decimal to an approximate domain through its text | `8e85aced`, `f3891eb1` |
| 9 | the validator interpolates `PERCENTILE_CONT` in binary64 | `0e0256b4` |
| 10 | Part 11 §3 is reworded | `b5696685` |
| 11 | the style guide states both drafting rules | `5f558363` |
| 12 | a writer MUST name a media asset's device where its source states one | `b5696685` |
| 13 | a reader exposes a resource's content class and lineage policy | `b5696685` |
| 14 | Part 02 §9.2 recommends that a registry document carry `$schema` first | `b5696685` |
| 15 | the reading of a null changes what a consumer concludes, so it is proposed as a revision | draft `a-null-producing-run-on-an-array-says-the-packet-names-none.md` |
| 16 | nothing is owed: the ledger note on R53 §2.3.1 already records it | — |
| 17 | proposed | draft `a-unit-is-identified-outside-its-packet-by-its-name.md` |
| 18 | proposed | draft `a-recipe-accepts-a-discarded-value-by-naming-its-column.md` |
| 19 | proposed | draft `core-declares-a-clocks-transform-in-typed-columns-alone.md` |
| 20 | the draft was accepted as R157 | `bb3cae24` |
| 21 | the guide states both sentences | `5f558363` |

All four were promoted and are drafts in `revisions/drafts/`. `e60b54e0` added the ledger notes for the rules the commits above entered,
and `8e85aced` carries its own.

## Applied on 2026-10-02 without a decision

- **Twelve reworded restorations**: D4, D7, D8, D10, D11, D13, D15, E4, E6, E16 and C22 in Parts
  01, 02, 03, 04 and 11, and E12 in the revision guide.
- **Ten labels** on requirements restored on 2026-10-01 that no check observes.
- **Ledger targets**: 132 sections added and 43 dropped, as the second reading of the targets
  confirmed ([applied-target-pointers.md](../applied-target-pointers.md)). Three confirmed
  additions name a guide section with no anchor and cannot be recorded.
- **Dispositions**: R15 §3, R79 §2.3, R107 §3.1, R148 §3.4, R151 §3.2 and R112 §3.1 are
  `superseded`; R22 §4, R27 §3, R30 §3.1, R41 §2.3 and R3 §3.4 are `registry`, each with a guarded
  pointer.
- **Ledger notes** on the fifteen disputed clauses the reading found not owed (E1, E3, E5, E7 to
  E11, E13 to E15, E17, E19 to E21), on the tool-enforced rules G3 to G6, and on each restored
  clause.

Thirteen of the 25 reworded restorations are held. Twelve belong to Part 05 §14 (C1, C3, C4, C8,
C9, C10, C11, C13, C14, C16, C17 and E18), which is repaired in one change after decisions 1 to 6:
a keyworded sentence beside an indicative one reads as making the second optional. D9 is held by
decision 14, where the two readings of its clause disagree.

## Part 05 §14, the registry boundary

R127 decided each rule of §14 with a keyword, and the incorporating commit wrote §§14.1, 14.4,
14.5 and 14.6 in the indicative. No sentence elsewhere gives those statements a keyword's force.
The repair is one sentence per rule, for the whole section, in one fix.

### 1. Part 05 §1 says §14.4 binds a writer; three of its rules bind every implementation

- **Entries:** C5, C6, C7 (R127 §3.5).
- **Context:** §14.4's first paragraph covers publishing or releasing a registry, generating
  registry-derived checks, and checking a registry for an extension author. None of those is a
  writer's act, and Part 05 §1 lists §14.4 under "a writer" and says the part binds no checker.
- **Options:**
  1. Preferred. Keep "An implementation" as the subject and change §1's closing sentence to
     "§§14.1, 14.2 and 14.6 and the first paragraph of §14.4 every implementation". A fix; it
     alters an index sentence whose words R146 §3.1 set.
  2. Move the three sentences to §14.2, which §1 already assigns to every implementation. A fix;
     R127 §3.5 then sits in two subsections.
  3. Restore in §14.4 and leave §1. A fix; §1 then misstates the section.
  4. Move the author-check rule to Part 02 §9.4 as a checker rule. A revision.
- **Consequence:** no registry, implementation or corpus change under options 1 to 3.

### 2. A path-valued extension registry is checked through the mapping entry point

- **Entry:** C2 (R127 §3.3).
- **Context:** the clause has an implementation that owns the source bytes use the byte entry
  point. `load_checked` in `escapewheel_writer/extensions.py` decodes a registry that a
  distribution registers as a file path and checks the decoded mapping.
- **Options:**
  1. Preferred. Restore the keyword and fix the loader in the same change, with a test for a
     repeated member. A fix plus a small implementation fix.
  2. Restore the keyword and leave the loader as a recorded deviation in `TODO.md`.
  3. Leave the sentence indicative; the ledger entry then records a rule R127 decided as
     described only.
- **Consequence:** option 1 changes one writer function and no packet.

### 3. `escapewheel import` gives no machine-readable result for a rejected extension registry

- **Entry:** C12 (R127 §3.5).
- **Context:** the clause has a command-line tool offer machine-readable output containing the
  rejected registry's result. `import` prints a state word, and `--registry-result` writes the
  core registry's result alone. `extension check --result` does write the result.
- **Options:**
  1. Preferred. Every writer command that rejects a registry offers that registry's result, and
     `import` is fixed to write the result of whichever registry stopped the build. A fix plus an
     implementation fix.
  2. The clause's looser reading: the writer's command-line tool offers it somewhere, which
     `extension check --result` meets today. A fix, with no code change; a build that fails on an
     extension gives automation a state word.
  3. Leave the sentence indicative.

### 4. The label rule binds a validator's report, or every exposed result

- **Entry:** C15 (R127 §3.7, R130 §3.9).
- **Context:** a report pairs each registry result with a label naming the registry evaluated.
  The result schema is closed and has no label member, and `extension check --result` and
  `import --registry-result` write a bare result.
- **Options:**
  1. Preferred. A validator's report carries the label. A fix; the reference validator complies.
  2. Every implementation that exposes a result. A revision: Part 02 §9.5 needs a wrapper or a
     label beside the file, and both commands change.
  3. Keyword only R130's sentence on a bound registry's label and leave the pairing rule
     indicative.

### 5. Eleven further §14 sentences take the same repair

- **Entries:** the table in C-indicative-sections.md, "The third reading of each section as a
  whole".
- **Context:** the 17 class C entries do not cover §14. Thirteen further sentences state without
  a keyword what R127, R130 or R146 decided with one. Eleven take a keyword or a capitalised MAY.
  One stays indicative because R146 §3.7 decided its words that way. One, "The result schema
  begins at version 0.1.0; this boundary and reporting change does not by itself change…",
  records one decision's effect at the time and is a candidate for removal.
- **Options:**
  1. Preferred. Repair the eleven in the same change as the entries, and remove the history
     sentence with a ledger note. A fix.
  2. Repair only the 17 entries and E18; eleven decided rules stay beside keyworded neighbours.
- **Open within option 1:** one reader gives "Only a `valid` context directs generation or
  execution of registry-derived packet checks" (§14.5) a keyword with the validator as subject;
  the other holds that the clause has no keyword there and that C1, C5, C8 and C14 carry the
  force. Preferred: leave it indicative.

### 6. One unchecked label under the §14 heading, or one per subsection

- **Context:** no check observes any requirement of §14, and a label on each sentence would add
  about twenty.
- **Options:**
  1. Preferred. One sentence under the §14 heading: no checker verifies a requirement of this
     section.
  2. One sentence closing each of §14.1, §14.2 and §14.4, the subsections whose rules bind an
     implementation.

## Part 11, the rule language

Part 11 §§2 to 4 define a language in the indicative, as R125 itself does for much of them and as
R149 did when it added `CHARACTER_LENGTH`. The force comes from §1: "A validator claiming support
for this language MUST support the identified contract as a whole". A keyword on the five class C
entries alone would add actorless requirements and weaken 31 neighbouring sentences by contrast.

### 7. One §1 sentence gives §§2 to 8 their force

- **Entries:** C18, C20, and the Part 11 section of C-indicative-sections.md.
- **Candidate text:** "The contract is every statement of §§2–8, whether or not it carries a
  keyword: those sections define the language in the indicative, and a validator claiming support
  MUST give a rule the meaning they define."
- **Options:**
  1. Preferred. Add the sentence as a fix, and keyword none of the five entries.
  2. Add it by a short revision, on the view that only a keyworded sentence binds today and the
     sentence therefore changes force.
  3. Keyword sentence by sentence: the five entries and the 18 uncovered sentences where R125 or
     R149 has a keyword.
- **Consequence:** none for the reference validator beyond the two defects in decisions 8 and 9.

### 8. Restore the rounding rule the reference engine does not meet

- **Entry:** C21 (R125 §3.4).
- **Status:** answered with option 1 on 2026-10-02, after a first pass that day left it open.
- **Context:** "every exact-to-approximate conversion MUST use round-to-nearest, ties-to-even" is
  missing from Part 11 §4, not merely unkeyworded. §4 states that rounding for an explicit cast to
  `DOUBLE PRECISION`, so the missing sentence adds only the implicit conversion of §5, where an
  exact value combined with an approximate one converts with no rounding named.
- **The rule is the correct one.** Round to nearest, ties to even, is the IEEE 754 correctly
  rounded conversion and the only rule that gives one result for each value; ISO SQL leaves the
  rounding implementation-defined. DuckDB 1.5.5 departs from it by rounding twice, which is an
  accuracy defect of one unit in the last place and no rule a part could state instead.
- **Where DuckDB 1.5.5 departs,** as measured before the answer, converting to
  `DOUBLE PRECISION`:
  - `INTEGER` and `BIGINT` values convert correctly, as do `DECIMAL(38,0)` values from 0 to 2^64.
  - Above 2^64 the errors cluster by magnitude: 245 of 1,500 values of 65 bits, 6 of 1,500 of 70
    bits, 77 of 1,500 of 120 bits, and none from 80 to 110 bits. Mixed widths gave the 72 of
    3,000 first recorded.
  - A decimal literal of 15 or fewer significant digits converts correctly. Of 1,000 literals
    each with every significant digit after the point, 52 of 16 digits, 271 of 17, 260 of 18 and
    248 of 19 were wrong, each by one unit in the last place; some 25-digit literals were wrong
    by two.
  - A conversion through text, `CAST(CAST(x AS VARCHAR) AS DOUBLE)`, was correct in every case
    tried, so a lowering can meet the rule.
  - No shipped rule converts a `DECIMAL` above 2^64 or writes a literal of 16 or more digits.
- **As entered.** Part 11 §4 states the rule after its common-type rules. The validator converts
  through its text every `DECIMAL` value, decimal literal and integer literal beyond `BIGINT`
  that a rule converts to `REAL` or `DOUBLE PRECISION`, whether by an explicit cast, a
  comparison, an arithmetic operator, `BETWEEN`, `IN`, `COALESCE`, `CASE`, a set operation or
  the ordering value of `PERCENTILE_CONT`. It leaves `INTEGER` and `BIGINT` values to the engine.
  A rule in which it cannot place a conversion is reported incomplete under Part 11 §8 and is not
  run. Eight vectors in `conformance/rule-language/vectors.json` fail on the engine's own
  conversion and pass on the query the validator gives it.
- **Remeasured on the query the validator gives the engine,** DuckDB 1.5.5, each value added to
  a zero of the target domain and compared with the correctly rounded value. No result was wrong
  in any population below; the counts are the engine's own conversion of the same values.
  - `INTEGER` and `BIGINT` to either domain: none of 1,500 each.
  - `DECIMAL(38,0)` to `DOUBLE PRECISION`, 1,500 values of each bit length: none of 53, 60 or 64
    bits, 220 of 65, 8 of 70, none of 80, 90, 100 or 110, 92 of 120 and 1 of 126. Of 3,000 values
    with a bit length drawn uniformly from 1 to 126, 22.
  - Negative `DECIMAL(38,0)` to `DOUBLE PRECISION`, 1,500 each: none of 40 or 53 bits, 373 of 54,
    383 of 55, 183 of 56, 57 of 58, 8 of 60, 3 of 62, 1 of 63, none of 64, 238 of 65, 9 of 70,
    none of 100 and 102 of 120. The engine's conversion is therefore correct from -2^53 to 2^64
    and not from 0 alone.
  - `DECIMAL(38,0)` to `REAL`, the non-negative values of the eleven bit lengths above: none.
  - An integer literal beyond `BIGINT`, which the engine holds in a 128-bit integer domain, to
    `DOUBLE PRECISION`, 1,500 each: 263 of 65 bits, 1 of 70, none of 100, 83 of 120 and 3 of 126.
  - A decimal literal to `DOUBLE PRECISION`, 1,000 of each digit count. With every digit after
    the point: none of 15 digits, 57 of 16, 286 of 17, 250 of 18, 287 of 19, 584 of 25, where
    the largest error was two units in the last place, 305 of 30 and none of 38. With one digit
    before the point: none of 15, 3 of 16, 63 of 17, 67 of 18, 48 of 19, 71 of 25, 88 of 30 and
    56 of 38. With the point placed uniformly: none of 16, 8 of 17, 16 of 18, 11 of 19, 15 of
    25, 5 of 30 and 6 of 38.
  - A decimal literal to `REAL`, 1,000 of each digit count with one digit before the point: none
    of 5 digits, 43 of 8, 52 of 10, 52 of 15, 60 of 16 and 55 to 78 from 17 to 38. A literal of
    15 or fewer digits therefore converts correctly to `DOUBLE PRECISION` only.
- **Shipped rules.** The validator changes the query of three of the 139: the ordering value and
  the compared gap of `core.clock_anchors.gap_within_bound`, and the literals `1.0` and `0.5` of
  `core.sessions.alignment_bound_at_least_default` and
  `aind_unit_qc.metrics.amplitude_cutoff_is_bounded`. The engine converts those literals
  correctly, so an outcome can differ only for a gap between two anchors below -2^53 or above
  2^64 ticks.
- **The defect exists either way.** The explicit-cast sentence already requires the rounding, and
  `TODO.md` records that the reference validator does not meet it.
- **Options:**
  1. Preferred. Restore "Every exact-to-approximate conversion rounds to nearest, ties to even.",
     add a conformance vector, and fix the validator by lowering. A fix plus an implementation
     fix; no shipped rule changes outcome.
  2. Restore it and make a long non-zero-scale literal invalid where it converts to an
     approximate type. A revision with a new language identifier.
  3. Do not restore; two validators may then differ on a comparison between an exact and an
     approximate value.

### 9. `PERCENTILE_CONT` returns a decimal median where the part gives `DOUBLE PRECISION`

- **Entry:** C18 (R125 §3.2).
- **Context:** the shipped rule `core.clock_anchors.gap_within_bound` takes the median of
  `DECIMAL(38,0)` gaps. For gaps of 1, 2, 3 and 5 ticks the engine returns 2 and the rule reports
  the gap of 5; the binary64 median of 2.5 reports nothing.
- **Options:**
  1. Preferred. The validator converts the ordering value to binary64 before interpolating, with
     vectors over a `DECIMAL(38,0)` and a `REAL` input. An implementation fix; the corpus is
     rerun, since a finding can change where a median falls between two integers.
  2. The rule casts `gap` to `DOUBLE PRECISION` itself. The registry text and version change, and
     the validator still departs for any other such rule.
  3. Part 11 keeps a decimal ordering domain. A revision and a new language identifier.

### 10. Part 11 §3 says a table exposes "exactly" its declared columns

- **Entry:** C19 (R125 §3.3).
- **Context:** Part 02 §10.2 and the reference validator do not expose an `optional` column a
  packet's table omits, and §10.2 keeps a rule from naming one.
- **Options:**
  1. Preferred. Reword: "Each visible table exposes its registry-declared columns under §4 and no
     others; an `optional` column the packet's table omits is not exposed, and Part 02 §10.2 keeps
     a rule from naming one." A fix; no valid rule can bind such a column.
  2. Leave the sentence and note in the ledger that it is a definition.
  3. Make "exactly" true by supplying a typed null column. A revision, since §10.2's reason for
     its prohibition then fails.

## Single sentences

### 11. R111 §3.3's two drafting rules have no owner

- **Entries:** D1, D2; E10 covers the same paragraph.
- **Context:** the clause requires a requirement stating a property of an artifact to name the
  part it constrains and to use an active verb. Part 00 §2.4 states only that a requirement binds
  an actor or states an artifact property. About a dozen requirements in Parts 00, 02, 03 and 11
  are agentless passives today.
- **Options:**
  1. Preferred. `spec/CONTRIBUTING.md` §4 states both rules, replacing "A conformance predicate
     may instead name the artifact being tested", and the ledger note says the style guide carries
     them. A fix; an accepted MUST then lives as editorial guidance, since `ledger.py` cannot name
     the style guide as a target.
  2. Part 00 §2.4 states them with a keyword, labelled unchecked, and the passives are rewritten
     in the same change. A fix, unless a rewrite has to choose which actor a passive binds.

### 12. A media asset's device: the clause says MUST, the part says SHOULD

- **Entry:** D5 (R102 §3.2).
- **Context:** Part 01 §3.18 has said SHOULD since R102's own incorporation. The registry
  description says MUST and MUST NOT. The reference video adapter complies either way.
- **Options:**
  1. Preferred. "A writer MUST name the device that recorded a media asset where its source
     states one, and MUST NOT infer it from a file name. No checker verifies either." A fix that
     raises the part's current force, so it needs a yes.
  2. Keep SHOULD and add only the MUST NOT on inferring from a file name. Lowering the first half
     on purpose needs a revision amending R102 §3.2.
  3. Leave it; a registry description then owns an actor obligation, which Part 00 §2.2 excludes.

### 13. A reader exposes a resource's content class and lineage policy

- **Entry:** D6 (R128 §3.7).
- **Context:** the clause has a reader expose the resolved policy and content class without a
  validation receipt. Part 05 §14.3 keeps the receipt half. The duty to expose has been "may" in
  Part 02 §2.7 since incorporation. The reference reader exposes both.
- **Options:**
  1. Preferred. Part 04 §10's reader paragraph gains "Where a resource's declaration resolves, a
     reader MUST expose that declaration's content class and lineage policy with the resource. …
     No checker verifies this.", and Part 02 §2.7 points there. A fix that raises "may" to MUST,
     so it needs a yes.
  2. The same sentence in place in Part 02 §2.7.
  3. Keep "may", reading the clause as constraining only how. Should be confirmed by a revision.

### 14. Whether a registry document should carry `$schema` first

- **Entries:** D9, G "Clauses recorded as applied" 6 (R57 §2.1).
- **Context:** R57 §2.1 says a writer SHOULD emit `$schema` first. R126 §3.2 then required
  `$schema` on every registry document, and the ordering reached no part. All five registry
  documents in the tree begin with it. The two readings disagree.
- **Options:**
  1. Restore: "A registry document SHOULD carry `$schema` as its first member, so that the head
     of the file shows which meta-schema governs it; member order carries no other meaning, and
     no checker verifies it." A fix; the ledger entry stays `applied`.
  2. Record the clause as `superseded` by R126 and carry no ordering rule. One reading holds this
     is a ledger change only; the other that R126 did not replace the ordering, so retiring it
     needs a revision.
- **Preferred:** option 1. It costs one sentence, every document complies, and it avoids resting
  a `superseded` entry on an inference about R126.

### 15. The description of `processing_run_id` on the two array-asset tables is false

- **Entry:** D4, "The choice".
- **Context:** the description says "Null means it was acquired rather than computed". The
  reference LFP and waveform arrays are computed and carry null, and R130 §3.7 lets a
  materialization record no run.
- **Options:**
  1. Preferred. Reword the description in `spec/source` so that null also covers an array whose
     run the packet does not record, and regenerate. It changes what a consumer may conclude from
     a null: say whether that is a fix or a revision.
  2. Leave it.
  3. Require a run for every computed array. A revision, with new writer behaviour and a rebuild.

### 16. A carried identifier's name column

- **Entry:** E11 (R53 §2.3.1, by way of R111 §3.5).
- **Context:** R53 forbade a name column beside a carried identifier. R126 §3.6 restated the name
  rules with a prohibition only for an assigned identifier a table does not own, and Part 02 §8.2
  now says "A carried identifier likewise gets no corresponding name column" in the indicative.
  No registry declares such a column. The ledger note on R53 §2.3.1 records this, which was the
  preferred option, so nothing is owed unless one of these is wanted:
  1. Reword to "needs no corresponding name column", making the non-rule explicit. A fix.
  2. Extend `registry.identity.name` to refuse the column. A revision with a new invariant.

## Changes that need a revision

Each has a proposal in `revisions/proposals/`, named in the table above; decision 20 closed with R157.

### 17. The relation a consumer uses for a unit outside its packet

- **Entries:** D12, D14 (R81 §2.5, R123 §3.1).
- **Context:** the prohibition on carrying `unit_id` outside its packet is restored (D13). The
  positive rule names `(sorting_run_id, local_unit_label)`, which includes a packet-assigned
  number, omits the curation, can be null or tied under R149, and disagrees with the registry's
  statement that `unit_name` is the only bridge between packets. It stays unkeyworded.
- **Preferred:** a revision chooses among `unit_name`, `(sorting_run_name, curation_name,
  local_unit_label)` or the pair, adds a uniqueness rule if the relation needs one, and gives Part
  02 §12.9's interval sentence the same form.

### 18. `[overrides]` does not resolve a discarded fact

- **Entry:** D16 (R108 §3.3).
- **Context:** the clause has an `[overrides]` entry silence the discarded-fact refusal.
  `refuse_a_discarded_fact` never reads `[overrides]`, its message names that resolution, and the
  `block.field` key the recipe schema admits cannot name a column of `core.probes`.
- **Options:**
  1. Preferred. A revision completes the rule with a `resource.column` key, as `[encoding]`
     uses, and exempts such an entry from the idle-override report.
  2. A revision withdraws the resolution and corrects the message; a case where each source
     holds a column the other lacks then has no resolution.

### 19. `core.clocks.transform_to_parent` is still declared

- **Entry:** D17 (R3 §3.4).
- **Context:** R3 replaced the column with `transform_slope` and `transform_offset`, and it was
  never removed. No part, package or corpus packet uses it. The ledger now records the clause as
  `registry` with the note that the column remains.
- **Options:**
  1. Preferred. A short revision removes the column and advances the core `registry_version`.
  2. A revision keeps the column and gives it a meaning, against R3 and R99.

### 20. R3 §7.1's byte-order sentence

- **Entry:** E2.
- **Context:** "arrays MUST be little-endian" contradicts Part 03 §6.4's writer permission and
  was never in a part. The open draft `the-reader-floor-bounds-an-arrays-byte-order.md` withdraws
  it in terms.
- **Decision:** none new. Accepting that draft closes the entry; its freshness gate is rerun
  first, since Part 03 §6.4 gained a sentence on 2026-10-01.

## The revision guide

### 21. Two sentences on rules the process tools enforce

- **Entries:** G1, G2 (R120 §3.2, R120 §3.4).
- **Candidate text:** in guide §2, "`stages.py` rejects an absent or unknown domain or change
  form wherever the field applies, and accepts the legacy default only for an accepted record
  below R120." In guide §8.4, "A section of this guide that an `Amends` target, ledger
  destination, evidence owner, or citation names carries an anchor of the same canonical form."
- **Context:** both describe what a tool already enforces, so neither changes the process. They
  are held because the guide is the process owner.
- **Options:** enter both as a `docs` fix (preferred), or leave the guide as it is.
