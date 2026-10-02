# Class A: sentences absent from the parts

Each rule below is decided by an accepted revision and stated by no part. A third reading then tried to show each restoration to be a mistake: whether a later revision changed the rule, whether the text contradicts or exceeds anything, whether it names an actor who can comply, whether a check observes it, whether it sits in the part that owns it, and whether the reference implementation and the corpus comply. The rules below passed. "Text to enter" is that reading's wording; where it differs from the text first proposed, both are shown.

27 rules, ordered by part and section: Part 01 (9), Part 02 (3), Part 03 (2), Part 04 (6), Part 05 (4), Part 12 (3).

All of these were entered on 2026-10-01, one commit per part from `96c0bbcd` to `ef5190df`, and each clause's ledger entry carries a `restored 2026-10-01` note. The audit record, [applied-targets.md](../applied-targets.md), lists where the entered text departs from "Text to enter".

## Part 01

### 1. R38 §2.3 at Part 01 §2.3 (Observation)

- **The revision decides:** a clock's own interval is not derived from what it recorded either: it is the extent of the acquisition
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** A clock's own interval is not derived from what was timed on it either: it is the extent of the acquisition, so for a sample clock whose origin is sample 0 of a recording it runs from tick 0 to the last sample's index, one less than the recording's length.
- **Placement:** Part 01 §2.3 (Observation), appended to the second paragraph, after the sentence ending 'but MUST NOT assert a window derived from its own timestamps.'
- **Observed by a check:** yes, or the sentence binds nothing.
- **Text first proposed, set aside:** A clock's own interval is not derived from what it recorded either: it is the extent of the acquisition, so for a sample clock whose origin is sample 0 of a recording, `start_tick` is 0 and `stop_tick` is the last sample's index, one less than the recording's length.
- **Evaluation:** Restore it in Part 01 §2.3 in the indicative, reworded to name no column and to say 'what was timed on it'. The reference writer already complies and already cites this section for the rule; note that the reference clock's window is the span of the sync train, which R38 §4 treats as that clock's acquisition extent.
- **By lens:**
  - *Still decided:* R38 §2.3's third paragraph, with R45 §2.3 replacing only its example ('the last sample's index, one less than the recording's length'). R98 §2.1 relies on it, R39/R146 §3.3 build the time origin on the windows, and none withdraws it. The v0.2 compilation (4ce6f09c) condensed R38 into Part 01 §2.3 and never carried this sentence; no crosswalk drops it.
  - *Contradiction:* None with the parts or registry: Part 02 §12.5 requires a window, the registry describes `start_tick`/`stop_tick` as first and last tick observed, Part 01 §3.13.1 already uses 'the recording's extent'. One awkward neighbour: Part 02 §12.5 admits several intervals for an acquisition paused and resumed, so 'the extent of the acquisition' has to be read per stretch. No open draft touches observation.
  - *Exceeds the clause:* The proposal keeps the clause's indicative and R45's closed example, and adds nothing. It inherits the clause's phrase 'what it recorded', which a clock does not do; Part 01's own phrase is 'anything timed by a clock'.
  - *Actor:* No keyword and no actor, as in the clause: it defines what a clock's interval is, which is Part 01's kind of statement. It therefore binds nothing under Part 00 §2.5; turning it into a writer MUST NOT would exceed the clause.
  - *Checks:* No check can tell an extent from a hull of the data (a window taken from the data only makes the `within_observation` rules vacuous). As an indicative definition it needs no unchecked label.
  - *Placement:* Part 01 §2.3 (Observation) is right; the ledger's '§2.2' is the pre-R146 number. The reference writer already cites 'Part 01 §2.3' for exactly this rule. The proposed text names `start_tick` and `stop_tick`; Part 01 should say it without columns, as §2.2 and §3.9 say 'tick 0 is sample 0'.
  - *Implementation and corpus:* Complies. escapewheel-writer sources/sorter.py `SorterSource.observation_intervals` writes [0, length - 1] from the recording length, not from the spikes; escapewheel-aind session.py `watched` uses the declared acquisition window, 'never the extent of the events'; sources/sync.py `SyncSource.observation_intervals` uses the span of the sync train for the reference clock, which R38 §4 itself names as that clock's window. fixtures/corpus_packets/session.py states fixed windows. No packet changes verdict and no validator check is needed.
  - *Wording:* Replace 'what it recorded' and the two column names. Corrected sentence below; it must directly follow the MUST NOT sentence so that 'either' has its antecedent.

### 2. R6 §2 at Part 01 §3.9 (ew-clock-concept)

- **The revision decides:** where present, the wall-clock time of any tick is `tick_zero_utc + t_tick / effective_tick_rate`, using `tick_rate_hz` or `tick_rate_num / tick_rate_den`
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** Where a clock binds its tick 0 to a wall-clock instant, the wall-clock time of a tick on that clock is that instant plus the tick divided by the clock's declared tick rate, in seconds.
- **Placement:** Part 01 §3.9 (ew-clock-concept), as a sentence in the paragraph beginning 'A clock's tick-zero binding and a session's start time are **independent and MUST NOT be conflated**', placed first in that paragraph
- **Observed by a check:** yes, or the sentence binds nothing.
- **Text first proposed, set aside:** Where a clock binds its tick 0 to a wall-clock instant, the wall-clock time of a tick on that clock is that instant plus the tick divided by the clock's declared tick rate (in Part 02's terms, `tick_zero_utc + t_tick / rate`, the rate being `tick_rate_hz` or `tick_rate_num / tick_rate_den`).
- **Evaluation:** Restore the definition without the parenthetical naming Part 02 columns. The reference writer's `tick_at` already inverts exactly this arithmetic.
- **By lens:**
  - *Still decided:* R6 §2 defines the wall-clock time of a tick. R27 §6.2 constrains only how a derived binding is anchored, and R39 §3 says the column 'stays what R6 made it'. The binding bullet was restored on 2026-09-04 (02c66576) with a citation to R6 §2 in place of the formula; R121 then removed revision citations, which is how the definition was lost. No revision withdraws it.
  - *Contradiction:* None. It parallels Part 01 §2.2's derivation of seconds and agrees with the bullet it follows ('the only route from a packet's ticks to real time') and with 'tick-zero binding and a session's start time are independent'. It settles that the time is taken on the tick's own clock at its declared rate, which is what R6 decided. No draft touches it.
  - *Exceeds the clause:* The semantic sentence does not. The parenthetical does: it restates the definition in Part 02's columns (`tick_zero_utc`, `t_tick`, `tick_rate_hz`, `tick_rate_num / tick_rate_den`) inside Part 01. 'The clock's declared tick rate' already covers both rate forms, since Part 02 §12.4 has exactly one present.
  - *Actor:* A definition with no keyword and no actor, as in R6, stating what a binding means. Determinate.
  - *Checks:* Not a requirement, so no label. Nothing checks a consumer's wall-clock arithmetic.
  - *Placement:* Part 01 §3.9 owns the clock's meaning and already holds the binding bullet. The column form belongs to Part 02 and the registry description ('Wall-clock instant of tick 0 on this clock') already carries it, so the parenthetical would be a second statement in the wrong part (R146 §2.3).
  - *Implementation and corpus:* Consistent. escapewheel-writer clock.py `Clock.tick_at` is the inverse (`round(elapsed * tick_rate_num / tick_rate_den)` from `tick_zero_utc`), and escapewheel-aind session.py derives windows through it. The reader offers no wall-clock conversion. No packet or check changes.
  - *Wording:* Drop the parenthetical and say the quotient is in seconds, as §2.2 does for derived seconds.

### 3. R27 §5.3 at Part 01 §3.9 (ew-clock-concept)

- **The revision decides:** between two anchors separated by at most 2m (m the clock's median anchor interval) the mapping is linear interpolation on the bracketing pair
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** A clock's **median anchor interval** is the median interval between its consecutive anchors, in ticks on that clock. Between two anchors separated by at most two median anchor intervals, the mapping onto the parent clock is linear interpolation on the bracketing pair.
- **Placement:** Part 01 §3.9 (ew-clock-concept), as a new paragraph immediately before the paragraph beginning 'Alignment beyond the terminal anchors is defined only while'
- **Observed by a check:** yes, or the sentence binds nothing.
- **Text first proposed, set aside:** Let m be the median interval between consecutive anchors of a clock, in ticks on that clock. Between two anchors separated by at most 2m, the mapping is linear interpolation on the bracketing pair; inside a gap wider than 2m it is undefined further than m from every anchor.
- **Evaluation:** Restore the definition of the median anchor interval and of interpolation only; leave out the proposed second half about wider gaps. That half is a separate clause, and the reference `align` scales the interior limit with the recorded `alignment_bound`, so stating it is a behaviour question for a decision, not a text fix.
- **By lens:**
  - *Still decided:* R27 §5.3's first clause defines interpolation between anchors; R37 §4 ('No change to interpolation') and R40 §3 keep it. R99 moved the alignment record into columns and R145 §3.3 moved the record sentences to Part 02 §12.6; neither touches the map's form. The v0.2 compilation carried the rule only as '(R37 §3, R40 §2)' and R121 removed such citations, so the loss was not a decision.
  - *Contradiction:* The first half contradicts nothing: the registry messages for `core.clock_anchors.monotonic` and `gap_within_bound` presuppose it, and Part 02 §12.6 says the map is exact at every anchor. The second half ('inside a gap wider than 2m it is undefined further than m from every anchor') conflicts with the reference implementation and sits awkwardly beside Part 02 §12.6, where the session's recorded bound replaces 'one median anchor interval': The reference `align` (escapewheel-reader clocks.py) marks a tick defined when it is within `bound * m` of an anchor on either side, so at a recorded `alignment_bound` above one it defines ticks inside a gap wider than 2m that R27 §5.3 and R37 §3.3 ('the clause on gaps is unchanged') leave undefined.
  - *Exceeds the clause:* The first half is the clause. The second half is a different clause of R27 §5.3 (its third bullet, as R37 §3.3 left it) and is not this finding's rule; the first reader says to drop it if tracked separately.
  - *Actor:* A definition in the indicative with no actor, as in R27. Determinate, except that neither R27 nor the proposal says how a fractional interpolated tick is rounded (the reference uses `np.rint`).
  - *Checks:* Not a requirement. The validator's origin check (Part 05 §5.3, shim/time_origin.py) maps through anchors and so presupposes this definition, which no part currently gives it.
  - *Placement:* Part 01 §3.9 owns the clock and already uses 'median anchor interval' without defining it; the registry's `alignment_bound` description cites Part 01 §3.9 for the term. Defining the term there is better than introducing a bare symbol m.
  - *Implementation and corpus:* First half: complies. `align` interpolates with `np.interp` on the bracketing pair and a gap of at most 2m is within one median interval of an anchor everywhere, so it is defined at any bound of one or more. Second half: does not comply at a bound above one, as stated under contradiction. The reader's test `test_the_middle_of_a_wide_gap_is_undefined` states the design ('one threshold both ways'). The corpus variant `wide_anchor_gap` expects only the registry warning, which does not depend on the map's form, so no verdict changes either way.
  - *Wording:* Define the term the section already uses instead of 'Let m be'; name the parent clock as the mapping's target.

### 4. R27 §5.3 at Part 01 §3.9 (ew-clock-concept)

- **The revision decides:** beyond the terminal anchors a consumer MUST use the rate fitted over the clock's full anchor sequence and MUST NOT extend the terminal segment's slope
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** A consumer MUST NOT extend the terminal segment's slope.
- **Placement:** Part 01 §3.9 (ew-clock-concept), in the new mapping paragraph before 'Alignment beyond the terminal anchors is defined only while', directly after finding 31's formula sentence
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** Beyond the terminal anchors a consumer computing the mapping MUST use the rate fitted over the clock's full anchor sequence, and MUST NOT extend the terminal segment's slope.
- **Evaluation:** Restore the prohibition as its own sentence and let finding 31's sentence carry 'fitted over the clock's full anchor sequence', so the estimator is stated once. The reference `align` already complies.
- **By lens:**
  - *Still decided:* R27 §5.3's second bullet, kept and completed by R37 §3.1 ('R27 §5.3 already says ... this states the offset the rate is applied from') and by R40 §3 ('the globally fitted rate, applied from the terminal anchor'). R99, R145 and R146 reword Part 01 §3.9 without touching the estimator. Lost in the v0.2 compilation, which cited the revisions instead of stating it.
  - *Contradiction:* Not with §3.9, which already speaks of 'the estimator's error' without saying what the estimator is. It sharpens a tension already in Part 01: §2.3's rationale says 'outside the first and last anchor the mapping is undefined', which §3.9 already qualifies. Part 05 §5.3's 'a writer's estimator may fit anchors the writer does not record' is compatible: a consumer fits the recorded sequence.
  - *Exceeds the clause:* No added force. But restored beside finding 31 it states the same obligation twice in one section ('MUST use the rate fitted over the clock's full anchor sequence' here, 'rate is fitted over that clock's anchors' there), in two wordings of different strength.
  - *Actor:* A consumer computing the mapping; R146 §2.3 says the consumer rules of this section 'state what a converted value means and stay'. It prescribes an estimator, but the estimator is the interoperability outcome: reader and writer must place the same ticks. How the rate is fitted (least squares in the reference) is left open, as in the clause.
  - *Checks:* No validator observes a consumer; always compliable; consumer rules in Part 01 carry no label. The writer's use of the same estimator is observed indirectly by `time.origin_not_earliest` within one tick.
  - *Placement:* Part 01 §3.9, with the rest of the mapping's definition. No other part states it.
  - *Implementation and corpus:* Complies. escapewheel-reader clocks.py `align` recomputes both ends as `parent_tick + rint(slope * offset)` with `slope` from `rate`, a fit over the whole anchor sequence, and does not extend the terminal segment; `extrapolation_error` measures the same estimator. The writer and the validator's time_origin shim call `align`.
  - *Wording:* Fold the 'full anchor sequence' into finding 31's formula sentence and keep from this finding only the prohibition, so the section states the estimator once.

### 5. R27 §5.3 at Part 01 §3.9 (ew-clock-concept)

- **The revision decides:** the bound applies per edge of the parent chain, each edge against its own m
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** Where a tick is mapped through a chain of parent clocks, how far each clock's mapping reaches is counted in that clock's own median anchor interval.
- **Placement:** Part 01 §3.9 (ew-clock-concept), appended to the paragraph beginning 'A writer reaching past one median anchor interval MUST measure its error'
- **Observed by a check:** yes, or the sentence binds nothing.
- **Text first proposed, set aside:** The bound applies per edge of the parent chain: each clock's mapping to its parent is evaluated against that clock's own median anchor interval.
- **Evaluation:** Restore the per-edge reading in Part 01 §3.9 only, worded as the unit each edge's reach is counted in, so it cannot be read as a per-edge recorded bound. The validator's origin check already walks the chain this way.
- **By lens:**
  - *Still decided:* R27 §5.3's fourth bullet. R37 §3.3 changed what bounds the mapping and kept the one-median-interval default; R99 §3.1 records one multiple per session ('One session declares one bound') and does not say whose median it multiplies; no revision withdraws the per-edge reading.
  - *Contradiction:* None, provided it is not read as a per-edge recorded bound, which R99 declined. Part 02 §12.6 and the registry give `alignment_bound` in median anchor intervals and cite Part 01 §3.9 for the unit, and Part 05 §5.3 maps 'through the anchors or transform of every clock on the path'; both need this sentence to be determinate with clocks of different anchor density.
  - *Exceeds the clause:* No. The clause's rationale (an edge at 1 Hz and one every 30 s) is left out, correctly.
  - *Actor:* A definition with no keyword, as in the clause. Determinate.
  - *Checks:* Not a requirement. The validator's origin check applies it and would disagree with a writer that used one median for the whole chain.
  - *Placement:* Part 01 §3.9, next to the definition of the median anchor interval (finding 18); Part 02 §12.6 owns the recorded value and cites Part 01 §3.9 for what the unit means, so stating it there as well would be a second owner.
  - *Implementation and corpus:* Complies. `align` takes `median(diff(anchor_t)) * bound` from the anchors of the clock being mapped, and the validator's `_onto`/`_step` (shim/time_origin.py) calls it once per edge of the parent chain with the session's bound. The reader's `mapped` carries a tick across one edge only. Both AIND packets parent every clock directly to the reference (R146 §2.8), so no shipped packet's verdict depends on it.
  - *Wording:* 'The bound' is not yet a term of Part 01 §3.9, which speaks of a tolerance and of 'reaching past one median anchor interval'; and 'evaluated against' is vague. State it as what bounds each edge.

### 6. R37 §3.1 at Part 01 §3.9 (ew-clock-concept)

- **The revision decides:** beyond the terminal anchors a consumer MUST compute parent(t) = parent(a) + rate * (t - a), with `a` the nearest terminal anchor and `rate` fitted over that clock's anchors
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** Beyond the terminal anchors a consumer MUST compute the mapping as `parent(t) = parent(a) + rate * (t - a)`, where `a` is the nearest terminal anchor and `rate` is fitted over the clock's full anchor sequence.
- **Placement:** Part 01 §3.9 (ew-clock-concept), opening a new paragraph immediately before 'Alignment beyond the terminal anchors is defined only while', after finding 18's definition paragraph
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** Beyond the terminal anchors a consumer MUST compute the mapping as `parent(t) = parent(a) + rate * (t - a)`, where `a` is the nearest terminal anchor and `rate` is fitted over that clock's anchors.
- **Evaluation:** Restore the formula once, with 'fitted over the clock's full anchor sequence' so it also carries R27 §5.3's wording, then follow it with the two prohibitions of findings 19 and 32. The reference `align` already computes exactly this.
- **By lens:**
  - *Still decided:* R37 §3.1 states the estimator with MUST; R40 §3 keeps it ('No change to the estimator'), R39 §4 and R101 cite it as current, and R99, R145 and R146 leave it alone. `git log -S` shows the formula never reached a part: the compilation wrote 'the estimator's error ... (R37 §3, R40 §2)'.
  - *Contradiction:* None with §3.9 or Part 02 §12.6. Same pre-existing tension as finding 19 with Part 01 §2.3's 'outside the first and last anchor the mapping is undefined'. The bound that limits how far this formula may be applied stays in the next paragraph and Part 02 §12.6.
  - *Exceeds the clause:* The proposal's 'fitted over that clock's anchors' is weaker than what stands decided: R27 §5.3 says 'the clock's full anchor sequence' and R40 §3 'the globally fitted rate', while R37 §3.1 also reports a rate fitted over the nearest 30 anchors. The restored sentence should say the full sequence.
  - *Actor:* A consumer, as decided. The formula is the outcome (which parent tick), not a method beyond it; the fit itself is left open. A writer and a validator also map, and bind only through their own rules (Part 06 §4, Part 05 §5.3).
  - *Checks:* No validator observes a consumer; always compliable; no label, as for the section's other consumer rules.
  - *Placement:* Part 01 §3.9; no other owner. The formula names no column.
  - *Implementation and corpus:* Complies: `align` computes `anchor_p[end] + rint(slope * (tick - anchor_t[end]))` from the nearest terminal anchor with the globally fitted slope, and its comment says the fit's intercept is not used. escapewheel-reader tests/test_clocks.py `test_extrapolation_starts_at_the_terminal_anchor` and `test_extrapolation_uses_the_fitted_rate_not_the_last_segment` pin it.
  - *Wording:* State the rate as fitted over the clock's full anchor sequence, which also absorbs finding 19's first half.

### 7. R37 §3.1 at Part 01 §3.9 (ew-clock-concept)

- **The revision decides:** a consumer MUST NOT use the intercept of a fit over the whole anchor sequence
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** A consumer MUST NOT use the intercept of a fit over the whole anchor sequence.
- **Placement:** Part 01 §3.9 (ew-clock-concept), in the new mapping paragraph, after finding 31's formula sentence and finding 19's prohibition
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Evaluation:** Restore as written, immediately after the formula sentence of finding 31; it must not go in without that sentence. The reference implementation already complies.
- **By lens:**
  - *Still decided:* R37 §3.1's second sentence, kept by R40 §3; R39 §4 still contrasts the terminal-anchored estimator with the intercept-based one. Never reached a part; no revision withdraws it.
  - *Contradiction:* None found in Parts 01, 02, 05 and 06 or the registry (no occurrence of 'intercept'; `transform_offset` belongs to the linear-transform model, which a clock with anchors may not also declare).
  - *Exceeds the clause:* No. Word for word the clause.
  - *Actor:* A consumer; it can tell whether it used the fit's intercept. It forbids one estimator, which is the defined harmful case (a constant offset of hundreds of microseconds at the session's ends).
  - *Checks:* No validator observes a consumer; always compliable; no label, as for its neighbours.
  - *Placement:* Part 01 §3.9, directly after the formula of finding 31, without which it has no meaning.
  - *Implementation and corpus:* Complies: `align` discards the intercept `rate` returns (`slope, _ = rate(...)`).
  - *Wording:* Fine as written once it follows finding 31's sentence.

### 8. R70 §2.2 at Part 01 §3.18 (ew-media-asset-concept)

- **The revision decides:** a writer MUST declare neither rate column where it wrote no pts
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** A writer that carries none for an asset MUST NOT declare a rate for it, and no checker verifies this.
- **Placement:** Part 01 §3.18 (ew-media-asset-concept), the paragraph beginning 'The asset declares the **rate** those timestamps count at', as a new sentence after 'A writer that carries presentation timestamps MUST declare it and MUST NOT declare half of it.'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** A writer that carries presentation timestamps MUST declare it and MUST NOT declare half of it; a writer that carries none for an asset MUST NOT declare a rate for that asset.
- **Evaluation:** Restore the second half as its own sentence carrying the unchecked label, since no rule reports a rate without timestamps. The only shipped adapter that writes a rate already complies; making it checked would be a registry rule and a revision.
- **By lens:**
  - *Still decided:* R70 §2.2 binds a writer both ways. R102 only lists the columns; no revision withdraws 'MUST declare neither'. The phrase never reached a part.
  - *Contradiction:* None in the parts or registry. The registry checks the other half (`pts_rate_declared_where_frames_carry_pts`) and the pair (`pts_rate_pair_complete`); a rate without timestamps passes all three rules, which is silence and not a contrary declaration. The amendment rules (Part 05 §15) do not make the rule harder to meet: an asset's row cannot change in an amendment either way.
  - *Exceeds the clause:* No. 'A writer that carries none for an asset MUST NOT declare a rate for that asset' is the clause's second half; the first half is already in the part and is repeated unchanged in the proposal.
  - *Actor:* A writer, which knows whether it wrote timestamps for the asset. Determinate.
  - *Checks:* No registry rule, schema or validator check reports a rate on an asset whose frames carry no presentation timestamp, though a Tier 2 anti-join could; adding one is a registry change and needs its own revision. A writer can always comply and the sentence is scoped to one asset, so it is acceptable only with the unchecked label, which Part 01 already uses ('and no checker verifies this').
  - *Placement:* Part 01 §3.18's rate paragraph already holds the first half; the second belongs beside it.
  - *Implementation and corpus:* Complies. escapewheel-aind video.py `VideoSource.media_assets` adds `_pts_rate` only where a timing file exists, which is exactly when `_frames` writes timestamps; no other adapter writes either. No corpus packet declares a rate, so no packet changes verdict.
  - *Wording:* Keep the existing sentence and add one after it with the label.

### 9. R105 §3.4 at Part 01 §3.24 (ew-coordinate-frame-concept)

- **The revision decides:** an axis's `unit` MUST be declared
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** A writer MUST declare each axis's unit, which it knows because it wrote the values. No checker verifies this.
- **Placement:** Part 01 §3.24 (ew-coordinate-frame-concept), as a new paragraph after the paragraph 'A frame has as many axes as it has: two for a shank, five for a rendering space.'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** A writer MUST declare each axis's unit.
- **Evaluation:** Restore the writer obligation in Part 01 §3.24 with the unchecked label, as prose and not as a bullet under the frame. Every shipped adapter and fixture already states a unit; requiring it in the registry would be a separate revision.
- **By lens:**
  - *Still decided:* R105 §3.4: '`unit` MUST be declared, and a writer knows it by construction'. R131 lists the column among unit columns and R150 groups the table; neither changes the obligation. R146 revised Part 01 §3.24 for 'one row per axis' and the struck columns only. R105 §3.2 declared the column nullable in the same revision, so nullability is not a later retreat.
  - *Contradiction:* Sits beside two weaker statements without contradicting them: Part 01 §2.5 ('A measured quantity SHOULD declare its unit') is the general rule this one tightens for an axis, and the registry's `nullable` presence means a null unit passes validation while its writer did not conform, the shape Part 02 §12.5 already has. Part 02 §12.7's `unit_from` resolution and Part 01 §3.8's 'Each value's unit is the axis's' rely on it.
  - *Exceeds the clause:* No in force. As a bullet under the frame ('MUST declare each axis's unit') it would read as a property of the packet, which no check reports and the registry's presence denies; naming the writer, as the proposal does, keeps it to what was decided.
  - *Actor:* A writer, which wrote the values and so knows their unit; a dimensionless or conventional axis has a UCUM annotation code, so it can always comply. Determinate.
  - *Checks:* Nothing observes it: the column is nullable, the table's one rule checks axis names, and R131's check covers only non-null values. Acceptable only labelled as unchecked. Making it checked means `presence: required` or a rule, a registry change that needs a revision.
  - *Placement:* Part 01 §3.24 holds the sibling rules of R105 §3.4 (the axis name verbatim, direction left undeclared); Part 02 §12.7 is the other credible home, but it states the representation and cites Part 01 for meaning, so §3.24 is right and the sentence names no column.
  - *Implementation and corpus:* Complies. escapewheel-writer sources/nwb/electrodes.py `coordinate_frame_axes` writes `COORDINATE_UNIT` ('um') on every axis row and fixtures/corpus_packets/session.py states 'um' on all five; both AIND packets carry `um` on every axis (R131 §2.2). No packet changes verdict and no validator check is added.
  - *Wording:* Give the reason in the same sentence and add the label; place it as prose after the list, not as a list item.

## Part 02

### 10. R91 §3.3 at Part 02 §8.6 (ew-free-form-metadata)

- **The revision decides:** a writer MUST NOT put a mark in core.events.metadata
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** A writer MUST NOT put a mark, a value an event carries beyond its tick (Part 01 §3.12), in `core.events.metadata`. No checker verifies this.
- **Placement:** Part 02 §8.6 (ew-free-form-metadata), as its own paragraph after the paragraph beginning 'No rule checks either half and none is added.'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** A writer MUST NOT put a mark, a value an event carries beyond its tick, in `core.events.metadata`, which no rule reads and no filter can use.
- **Evaluation:** Restore the prohibition in Part 02 §8.6, after the 'No rule checks either half' paragraph, with the unchecked label and without the reason clause, which is as true of the permitted `core.events.payload` as of `metadata`. The reference adapters already comply, and the ledger target should move from Part 01 §3.12 to Part 02 §8.6.
- **By lens:**
  - *Still decided:* Read R91 §§2.4 and 3.3 and R97, accepted later, which wrote Part 02 §8.6 and treats the prohibition as standing in its §4 ('forbids a writer putting a mark in `core.events.metadata`') and §6. R94 and R146 touch the columns without withdrawing it; R146 only bars the column name from Part 01.
  - *Contradiction:* It limits §8.6's 'A writer MAY fill `metadata` on every row of a table that declares it' for one table, and the registry still declares `core.events.metadata`, whose fixed description ('What the source stated about this row that the standard does not model') would otherwise invite a mark; that is the reason the sentence is needed, not a conflict. The proposal's reason clause, 'which no rule reads and no filter can use', is equally true of `core.events.payload`, the home R91 kept for a per-event value, so beside the surviving `payload` it reads as a reason against the permitted column too.
  - *Exceeds the clause:* Force and actor match the clause. The gloss 'a value an event carries beyond its tick' is not in R91 §3.3, but it is Part 01 §3.12's own phrase ('What a stream's events carry beyond a tick') and R91 §2.4's sense of a mark, so it defines the term without widening the rule.
  - *Actor:* A writer, before the keyword, and it can always comply: the value goes to the table the stream's `detail_kind` names, to `payload`, or nowhere. 'Mark' must be defined where it is first used normatively (spec/CONTRIBUTING.md §5); the parts use it only in Part 01 §3.12's indicative sentence.
  - *Checks:* Unchecked and uncheckable: §8.6 already says the content of `metadata` is schemaless and that its obligations bind the writer alone. The sentence must carry its own label, because §8.6's 'No rule checks either half' refers to the two halves of the paragraph before it.
  - *Placement:* Part 02, since Part 01 §2.2 names no column. §8.6 is acceptable as the section holding every writer rule for `metadata`, though the rule concerns one table and Part 02 §12 is where table-specific rules live; §12 has no event subsection and adding one is more than a sentence. Place it after the 'No rule checks either half' paragraph, not before, so that paragraph still counts two halves. The ledger entry for R91 §3.3 should name Part 02 §8.6, not Part 01 §3.12.
  - *Implementation and corpus:* Complies. The only adapter writing `core.events` is escapewheel-writer sources/nwb/events.py `events`, which puts a varying per-event value in `payload` and never sets `metadata` on an event row (its `metadata` writes are on `core.event_streams` and interval rows). No validator check is possible or needed, and no corpus packet is affected.
  - *Wording:* Cite Part 01 §3.12 for the gloss, drop the reason clause that applies equally to `payload`, and add the unchecked label.

### 11. R8 §3 at Part 02 §9.3 (ew-registry-vocabularies)

- **The revision decides:** the three values carry declared meanings: `succeeded` completed with usable outputs, `failed` did not complete, `partial` completed for some inputs only so committed outputs are incomplete
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** `core.processing_runs.status` says whether the run completed: `succeeded`, it completed and its outputs are usable; `failed`, it did not complete; `partial`, it completed for some inputs only, so its committed outputs are incomplete.
- **Placement:** Part 02 §9.3 (ew-registry-vocabularies), after the table of the four closed columns and the sentence 'A scorer's own `label` is open, because aggregating over scorers is incompatible with one closed set.'
- **Observed by a check:** yes, or the sentence binds nothing.
- **Evaluation:** Restore as written: the registry description already cites Part 02 §9.3 for these meanings, and the sentence is a definition that binds no one and matches what the reference writer records. Placing it after the scorer sentence keeps that sentence next to the table rows it comments on.
- **By lens:**
  - *Still decided:* Read R8 §3 and the later revisions naming the column (R26, R41, R101, R106, R107). R101 rewrote the registry description to 'with the meanings R8 §3 declares' (8fded7a4) and it now reads 'with the meanings Part 02 §9.3 declares', so later work assumes the meanings are stated; R107 §3.1 says 'the registry has no field for the meaning of its own enum'. The meanings never reached a part (`git log -S'completed for some inputs'` finds only R8 and the audit).
  - *Contradiction:* None. `core.processing_runs.no_failed_runs` (error) agrees with `failed`, and Part 05 §§7 and 12 and Part 06 §5 say nothing of status. Part 05 §4.4's 'A run succeeded when every resource in that set arrived and the process exited clean' uses 'run' for a build's execution of a source's command, a different thing from a `core.processing_runs` row; the code-font value keeps the two apart.
  - *Exceeds the clause:* The three meanings are R8 §3's own words. R8's rider on `failed` ('its outputs MUST NOT be committed') is left out and is carried, more strictly, by the registry rule, so the proposal drops no force that a part needs.
  - *Actor:* A definition of three values, in the indicative, binding no actor; that is the right form for a meaning, as §9.3's own table of `closed`, `open` and `free` is.
  - *Checks:* Not a requirement, so nothing needs checking; the value set is checked by the closed vocabulary's `enum` and `failed` by the error rule. Whether a writer chose the right value among the three is not decidable from a packet, and the sentence does not claim it is.
  - *Placement:* Part 02 §9.3 is R8 §3's ledger target and the section the registry description cites, so the sentence makes that citation true without touching the incorporated registry. Part 01 §3.20 could hold a column-free version, but that would leave the registry's citation dangling and split the vocabulary from its meanings.
  - *Implementation and corpus:* Consistent with the code: provenance.py `import_run` and materialize.py write `succeeded`, and sources/sorter.py writes `failed` where the sorter log has an error and `succeeded` otherwise; nothing writes `partial`. No packet, fixture or validator check changes.
  - *Wording:* Reads acceptably after the closed-column table. 'Usable' is R8's word and is loose, but tightening it would be a new decision.

### 12. R37 §3.2 at Part 02 §12.6 (ew-clock-alignment-record)

- **The revision decides:** a writer SHOULD test each terminal anchor by predicting it from a fit over its neighbours and comparing the residual with the distribution of the same residual over that clock's interior anchors
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** The terminal-anchor test predicts a clock's first and its last anchor from a fit over that anchor's neighbours and compares the residual with the distribution of the same residual over the clock's interior anchors. A writer SHOULD run it on each clock whose anchors it writes; a clock with too few anchors to give that distribution cannot be tested.
- **Placement:** Part 02 §12.6 (ew-clock-alignment-record), opening the paragraph that now begins '`core.clocks.withheld_first_anchor` and `withheld_last_anchor` record the terminal-anchor test'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** A writer SHOULD test each terminal anchor by predicting it from a fit over its neighbours and comparing the residual against the distribution of the same residual over that clock's interior anchors.
- **Evaluation:** Restore in §12.6 as a definition followed by the SHOULD, since the registry already cites that section for a test no part defines. Expect one follow-up in the writer: a clock too short to test is recorded `false` where the three states call for null.
- **By lens:**
  - *Still decided:* Yes. R99 §3.2 ('A writer running the test MUST record both') and R39 refer to R37 §3.2's test by name and none redefines it; R40 and R145 §2.6 touch the tolerance and the measurement, not the test. The definition was never in a part (`git log -S'terminal-anchor'` shows the name arriving with R99's incorporation, fa39d961, without it).
  - *Contradiction:* None. The registry descriptions of `core.clocks.withheld_first_anchor` and `withheld_last_anchor` cite 'Part 02 §12.6's terminal-anchor test', and §12.6 uses the name without saying what the test is, so the definition closes a reference that currently resolves to nothing. Part 01 §3.9's tolerance and Part 05 §5.3's one-tick allowance ('a writer's estimator may fit anchors the writer does not record') are consistent with it.
  - *Exceeds the clause:* Force stays SHOULD. R37's measurements and its sentence on why the test uses the clock's own spread are rationale and stay out (R121). The corrected text adds the limit that a clock without interior anchors cannot be tested, which the clause leaves implicit; it is the departure reason spec/CONTRIBUTING.md §4 wants a SHOULD to show.
  - *Actor:* A writer. The sentence prescribes a method, which §4 discourages, but here the method is the meaning of two stored columns, so interoperability needs it. It stays loose on the fit, the number of neighbours and the cut on the distribution, so `true` from two writers is not strictly comparable; the clause decided no more than that.
  - *Checks:* No check sees how a test was run; the null or non-null state of the two columns shows only whether the writer says it ran. As a SHOULD it needs no unchecked label, and the neighbouring 'a writer running it MUST record both' keeps its registry rule `core.clocks.withheld_needs_anchors`.
  - *Placement:* Part 02 §12.6, because the registry cites that section for the test and spec/CONTRIBUTING.md §7 has a citation point at the section that states the rule. Part 05 §4.3 would be the home for a writer's procedure under R146's reasoning, but moving it there would leave the registry descriptions citing the wrong section, and changing them is a registry change, not a text fix.
  - *Implementation and corpus:* Complies where it runs: `suspect_terminals` in escapewheel-writer/src/escapewheel_writer/sources/sync_checks.py predicts each terminal from 30 neighbours and compares against the 99th percentile of the same residual at interior positions. Two things the definition makes visible: a clock with too few anchors returns (False, False) and `declare_withheld` then records `false`, 'tested and kept', for a clock on which no comparison was made; and the NWB source's `signal_anchors` runs no test, which a SHOULD permits and null records. No fixture or validator change.
  - *Wording:* State the definition as its own sentence so the name used by the registry and by the next sentence has a referent, then the recommendation. 'Comparing against' and the British 'neighbours' are fine beside the part's mixed spelling.

## Part 03

### 13. R129 §3.1 at Part 03 §1 (ew-portable-profile-scope)

- **The revision decides:** the generic checker MUST require every listed anchor to resolve uniquely in Part 03 to the clause that defines the entry's meaning
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** Each descriptor interface and variant lists `anchors`, which the schema requires to be a nonempty array of distinct canonical `ew-` identifiers. Each anchor MUST name a section of this part that defines the entry's meaning, and the generic cross-member checker MUST refuse a descriptor any of whose anchors does not resolve exactly once in this part. No checker verifies that the section an anchor names defines the entry's meaning.
- **Placement:** Part 03 §1 (ew-portable-profile-scope), as a new paragraph after the paragraph ending 'the generic cross-member checker MUST refuse it on any other interface.'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** Each descriptor interface and variant carries a nonempty `anchors` array of distinct canonical `ew-` identifiers, and the generic cross-member checker MUST require every listed anchor to resolve uniquely in this part to the clause that defines the entry's meaning.
- **Evaluation:** Restore it in Part 03 §1, but split the checkable half (each anchor resolves exactly once in this part, which spec/tools/check.py already enforces) from the uncheckable half (the section defines the entry's meaning), label the latter unchecked, and leave the array's shape to the schema. No behaviour changes; note that the reader's first-use check runs the checker without Part 03's text and that no negative test of an unresolved anchor exists.
- **By lens:**
  - *Still decided:* Yes. R137, R144, R154 and R155 were searched for 'anchor': R154 §3.1 adds `ew-overriding-orders` to the Parquet interface's anchors and R144 moved no listed anchor to Part 12; none restates or withdraws the resolution rule. R129's incorporation (cbfbccf3) wrote only 'The descriptor owns the profile's ... anchors' and R129's crosswalk row for Part 03 §1 ('expand in place') records no decision to drop it.
  - *Contradiction:* None in the parts: Part 02 §9.4 states the parallel rule for the registry-contract descriptor only, and Part 00 §2.3 makes an incorporated artifact that violates its governing prose an inconsistent candidate. It sits beside Part 03 §1's 'A conforming distributed copy MUST pass ... the generic cross-member checker at a packaging or equivalent conformance boundary', so a distributed copy's check then needs Part 03's text; the open byte-order draft also revises a sentence of §1 (the schema identifier) and its baseline would need refreshing after any edit to §1.
  - *Exceeds the clause:* The proposed first half ('carries a nonempty `anchors` array of distinct canonical `ew-` identifiers') restates in prose a shape that physical_profile.schema.json `$defs.anchors` already owns (required on `interface` and `variant`, minItems 1, uniqueItems, `^ew-` pattern); the clause gave that to the descriptor, not to the checker. The second half matches the clause word for word.
  - *Actor:* 'the generic cross-member checker' is Part 03 §1's existing name for the Part 00 §2.4 checker of a physical-profile descriptor, so the actor is valid. It can tell whether an anchor resolves exactly once; it cannot tell whether the section 'defines the entry's meaning', so that half is not an outcome the named actor can determine.
  - *Checks:* Unique resolution is checked: spec/tools/checkers/descriptor.py `check_physical_profile` counts `<a id=...>` matches when given `part_text`, and spec/tools/check.py `profile_checks` passes Part 03. 'To the clause that defines the entry's meaning' is observed by no check; the descriptor's author can always comply and the sentence is scoped to listed anchors, so it must be labelled unchecked. No test feeds the checker an unresolved or duplicated anchor (spec/tools/tests/test_descriptor.py never passes `part_text`), though R129 §6 named that case.
  - *Placement:* Part 03 §1 is right: it already holds the descriptor's other cross-member rule ('the generic cross-member checker MUST refuse it on any other interface') and Part 00 §2.4 names Part 03 §1 as the contract of this checker. No other part states it; Part 02 §9.4's sentence governs a different descriptor, so no second owner arises.
  - *Implementation and corpus:* Complies at the conformance boundary: spec/tools/check.py `profile_checks` runs the anchor check, all five listed anchors resolve once in Part 03, and tools/copies.py holds the packages' copies byte-identical. The reader's first-use check (escapewheel-reader profile.py `physical_profile`) calls the same checker without `part_text` and so skips anchors; that is acceptable only if the tree's run is the packaging boundary, which the restored sentence makes worth saying in review. No packet or corpus case is affected.
  - *Wording:* 'resolve uniquely ... to the clause that defines the entry's meaning' joins a checkable outcome to an uncheckable one in one MUST; split them, attribute the array's shape to the schema, and match the neighbouring 'MUST refuse' phrasing.

### 14. R129 §3.5 at Part 03 §2 (ew-portable-profile-technologies)

- **The revision decides:** an implementation MAY support additional upstream features without changing the descriptor or packet
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** A reader MAY expose the logical values of a resource that uses a valid feature outside its interface's floor, and doing so changes neither the descriptor nor the packet.
- **Placement:** Part 03 §2 (ew-portable-profile-technologies), at the end of the last paragraph, after the sentence ending 'nor decides packet conformance.'
- **Observed by a check:** yes, or the sentence binds nothing.
- **Text first proposed, set aside:** An implementation MAY support additional upstream features without changing the descriptor or packet.
- **Evaluation:** Restore the permission in Part 03 §2 but name the reader: with 'An implementation' the sentence would also read as letting a packet writer exceed the Parquet floor that §5.5 makes a writer ceiling. The reference reader already decodes outside-floor arrays, so nothing changes.
- **By lens:**
  - *Still decided:* Yes. R137 depends on R129 §3.5 and says 'No accepted clause is superseded'; its §3.5 gives an outside-floor resource a finding at `warning` or `info` and never `error`, which presupposes readers that support more than the floor. The open byte-order draft says a conforming reader 'need no longer decode' a big-endian v2 array, which also keeps the permission. Incorporation cbfbccf3 omitted the sentence and R129's crosswalk records no decision to drop it.
  - *Contradiction:* As written, 'An implementation MAY support additional upstream features' placed after 'reader_and_packet_writer also bounds packet-owned writer output' can be read to let a packet writer emit beyond the Parquet floor, against Part 03 §5.5 ('A packet writer MUST keep every written table within that same floor'). In R129 §3.5 the sentence sat in a paragraph about reading features absent from a floor; the bare sentence loses that scope.
  - *Exceeds the clause:* The words equal the clause's, but the destination widens their reach because Part 00 §2.4 makes 'implementation' every actor alike, the writer included. Naming the reader restores the scope the clause's paragraph gave it and adds nothing.
  - *Actor:* 'An implementation' is the right subject only where a rule binds every actor alike (Part 00 §2.4); this one concerns what a reader decodes. spec/CONTRIBUTING.md §4 allows a MAY only for a permission otherwise uncertain: it is, because §6.4 says the floors admit 'exactly' their entries and §2 says a floor 'states what every conforming reader supports', which can be read as a closed set.
  - *Checks:* A permission; nothing to check and nothing a check could contradict. No label is needed.
  - *Placement:* Part 03 §2's floor paragraph owns what a floor means for a reader, and no other part grants the permission: Part 03 §6.1 and Part 05 §14.3 only say a reader fails the one resource it lacks support for, and §6.4's MAY is the writer's. No second owner.
  - *Implementation and corpus:* Already the reference behaviour: `ArrayResource.open` in escapewheel-reader resources.py decodes whatever zarr-python can, `within_reader_floor` documents 'this reader may decode it, and a conforming one need not', and tests/test_resources.py `test_a_decodable_array_outside_the_floor_still_reads` exercises it. No packet, corpus case or validator check changes.
  - *Wording:* Replace 'An implementation' with 'A reader', say what is supported (a valid feature outside the floor), and keep the clause's point that neither the descriptor nor the packet changes.

## Part 04

### 15. R14 §2.3.2 at Part 04 §5.1 (Declaration)

- **The revision decides:** a writer SHOULD prefer to own core tables where their size permits
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** A writer SHOULD therefore own a core table unless its size prevents it.
- **Placement:** Part 04 §5.1 (Declaration), directly after 'its validation rules cannot run at all while it is unreachable.'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** A writer SHOULD prefer to own core tables where their size permits.
- **Evaluation:** The recommendation still stands and nothing contradicts it, but 'SHOULD prefer' is a disposition rather than an observable outcome. Restore it as 'A writer SHOULD therefore own a core table unless its size prevents it.'; the reference writer already owns every table.
- **By lens:**
  - *Still decided:* Yes. R14 §2.3.2 ends with the SHOULD; R36 §3 and R42 only note that no packet externalises a table, and R63, R128, R129, R133 and R143 do not withdraw it. The portable descriptor still gives the Parquet interface 'packet and external ownership' (Part 03 §5.5 generated text), so an external table remains possible and the recommendation is not moot. The sentence was never in a part: `git log -S'prefer to own core'` over the parts is empty, and the v0.2 compilation 4ce6f09c kept the reason and dropped the SHOULD without a revision.
  - *Contradiction:* None. Part 04 §5.1's 'Referencing is expected for large resources' is the other side of the same trade and the size condition reconciles them; Part 00 §7.2, Part 03 §§5.5 and 8, Part 12 §5 and the two open drafts that touch external resources (credentials, sidecars) say nothing about which tables a packet owns.
  - *Exceeds the clause:* The proposed sentence is the clause's own words minus the examples (`core.spike_events`, `core.media_frames`), so it adds nothing. 'core' is the clause's scope and should stay; widening to extension tables would exceed it.
  - *Actor:* A writer is named and can comply. 'SHOULD prefer to own' states a disposition, not an outcome: a writer that externalises every core table can still claim it preferred otherwise, which spec/CONTRIBUTING.md §4 asks a requirement not to allow. State the outcome (own the table) and the reason for departing (size).
  - *Checks:* No check can observe it: 'where size permits' is not decidable from a packet, and no Part 04 §10 check or validator finding concerns an external table. A writer can always comply and the sentence is scoped to core tables, so it is acceptable as an unchecked SHOULD whose reason for departure is in the sentence; the project's 'No checker verifies this' label is used on MUSTs and is optional here.
  - *Placement:* Part 04 §5.1 holds the reason sentence and §5.2 already binds a writer, so the destination is right. Part 05 has no section on choosing packet ownership (its `owns` is a source's claim on a resource), and no other part states the rule, so there is no second owner.
  - *Implementation and corpus:* Complies. The writer owns every table: `escapewheel_writer/documents.py` builds an external entry only for an `ExternalArray` or `ExternalMedia` (lfp.py `external_arrays`, escapewheel_aind/video.py `external_media`) and opaque references; no code path externalises a table. No manifest under `conformance/` declares `external: true`. No validator check is needed.
  - *Wording:* Replace 'SHOULD prefer to own core tables where their size permits' with an outcome and add 'therefore' so it reads as the consequence of the cost sentence before it.

### 16. R36 §2.3 at Part 04 §5.3 (ew-external-resource-verification)

- **The revision decides:** a validator offering level 3 MUST offer 3a and MAY offer 3b
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** A validator that offers any of levels 3a to 3c MUST offer level 3a and MAY offer level 3c.
- **Placement:** Part 04 §5.3 (ew-external-resource-verification), after 'Levels 3a to 3c run only in a requested mode.'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** A validator offering level 3 MUST offer 3a and MAY offer 3b and 3c.
- **Evaluation:** Restore the MUST, but name the levels the part defines and drop the invented permission for 3b, which no revision decided. Settle finding 12 (whether offering the external levels is itself mandatory under R14 §2.3.2) in the same edit, since the conditional wording reads as answering it.
- **By lens:**
  - *Still decided:* The MUST half stands: R36 §2.3 says a validator offering level 3 MUST offer 3a, and R51 §2.3 ('the three levels stay separate flags') and R136 §3.5 change how levels are reached, not which are offered. R36's '3b' is today's 3c. R14 §2.3.2's unconditional 'A validator MUST offer a separate, explicitly requested mode' is the audit's finding 12, left as a judgement; R36's conditional wording is what this sentence restores.
  - *Contradiction:* None in the parts: 'offer' appears in no sentence about verification, and Part 04 §5.3 says only that levels 3a to 3c run in a requested mode. The conditional form does not contradict R14's unconditional MUST but reads as if offering the external levels were optional, which is the point finding 12 left open; the two should be settled in one edit.
  - *Exceeds the clause:* Yes. 'MAY offer 3b and 3c' grants a permission for the store-digest level (today's 3b) that no clause decided: R36 predates it and R51 §2.3 defines it without saying whether a validator must offer it. Only 'MAY offer 3c' is R36's.
  - *Actor:* A validator, before the keyword, with an outcome a test can observe (which modes it exposes).
  - *Checks:* No packet check or corpus case observes which modes a validator offers; it is a property of the validator, testable in its own suite, and a validator can always comply. It is scoped to a validator that offers an external level.
  - *Placement:* Part 04 §5.3 defines the levels and already carries validator obligations; Part 05 §5 cites it. No other part states which levels are offered.
  - *Implementation and corpus:* Complies: `escapewheel_validator/scripts/cli.py` offers `--external` (3a), `--store-digests` (3b) and `--checksums` (3c), and `verification.py` `Verification.resolves_external` makes 3b and 3c imply 3a. No packet is affected.
  - *Wording:* The part defines no 'level 3', only rows 3a, 3b and 3c, so 'A validator offering level 3' names an undefined term. Say 'any of levels 3a to 3c'.

### 17. R52 §2.3 at Part 04 §5.3 (ew-external-resource-verification)

- **The revision decides:** A disagreement on a packet-owned resource's digest is reported as an error, not a warning
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** A validator MUST report at `error` each packet-owned resource whose recorded `digest` it finds does not hold.
- **Placement:** Part 04 §5.3 (ew-external-resource-verification), after 'Level 3b remains the comparison of recorded store digests (§5.4).'
- **Observed by a check:** yes, or the sentence binds nothing.
- **Text first proposed, set aside:** A validator that finds a packet-owned resource's recorded `digest` does not hold MUST report the disagreement as an error, not a warning.
- **Evaluation:** The error level is still decided and the reference validator already reports `owned.digest` at error. Restore it in the parts' own form and without 'not a warning', which would imply something about external mismatches that no part states.
- **By lens:**
  - *Still decided:* Yes. R52 §2.3 fixes the level with a keyword. R136 §3.5 restates how a recorded digest is established and the report's route, and sets levels only for a missing digest and a member list that disagrees with its entry; R132's verdict composition and R137's finding levels do not touch it. R52's second paragraph (count owned resources recording no digest) has lapsed, since R136 §3.4 requires a digest of every owned resource.
  - *Contradiction:* None. Part 05 §9.1 makes `error` 'the packet does not conform', Part 03 §8.1 makes owned bytes immutable and says the promise 'is verified rather than assumed', and Part 05 §9.5's third bullet already attributes 'any other finding about one resource entry, or the resource it locates' to the declaring registry, so the finding needs no new attribution rule. 'not a warning' invites the inference that an external mismatch is a warning, which no part says and the reference validator does not do.
  - *Exceeds the clause:* No added force. Drop 'not a warning', which is the clause's emphasis rather than a second rule. The clause's condition is that the mode was asked for; 'whose recorded `digest` it finds does not hold' keeps that, since a validator finds it only at level 2.
  - *Actor:* A validator, before the keyword, with an observable outcome (the level of a reported finding).
  - *Checks:* Observable: the reference validator reports `owned.digest` at error (`check_table.py` OWNED_DIGEST, `shim/owned.py` `check_owned_digests`) and tests/test_shim_owned.py and test_opaque.py assert the level. The check ID is not named by any part; naming it is a revision's business, not this fix's.
  - *Placement:* Two homes are credible. Part 04 §5.3 defines level 2 and already holds the report obligations for it; Part 05 §5.3 is where finding levels and check IDs for the shim's checks are stated and it lists 'checksums' without a level. Part 04 §5.3 keeps the level and its outcome under one owner and is the ledger target; Part 03 §10, the other ledger target, only cites §5.3. No part states the level today, so no second owner arises.
  - *Implementation and corpus:* Complies: `check_owned_digests` reports a disagreement at error and `owned.verified` at info. No conformance packet has a digest that fails. No new check is needed.
  - *Wording:* Use the parts' form 'MUST report at `error`' (Part 05 §5.3) and name what is reported.

### 18. R80 §2.1 at Part 04 §5.5 (ew-source-resolution)

- **The revision decides:** a source name SHOULD be unique beyond the packet, so one resolution document serves many packets
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** A writer SHOULD choose a source name that is unique beyond the packet, naming the same body of data wherever it is used, so that one resolution document serves many packets.
- **Placement:** Part 04 §5.5 (ew-source-resolution), after 'A source name is any string an external resource entry's `source` can hold.'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** A source name is opaque to this specification. A writer SHOULD choose one that is unique beyond the packet, so that one resolution document serves many packets.
- **Evaluation:** Restore the SHOULD without the extra opacity sentence, which the R134 sentence before it already covers. Add a short gloss so 'unique beyond the packet' cannot be read as 'different in every packet'; no check can observe the rule.
- **By lens:**
  - *Still decided:* Yes. R80 §2.1 has the SHOULD and R80 §5 lists how a name stays unique as open, not withdrawn. R134 §3.3 widened which strings a name may be (the schema's pattern was dropped) and says nothing about how one is chosen. The sentence was never in a part.
  - *Contradiction:* None. Part 04 §5.5's 'A source name is any string an external resource entry's `source` can hold' and the schema's informative description ('A name is opaque') sit beside it without conflict.
  - *Exceeds the clause:* The proposal also restores 'A source name is opaque to this specification', which is not the finding's rule and repeats, in other words, the R134 sentence it would follow. Restore the SHOULD alone.
  - *Actor:* A writer chooses the name (through its adapter). 'unique beyond the packet' can be misread as 'different from the names other packets use', which is the opposite of the purpose: one name must mean one body of data in every packet that uses it. The reason clause makes the intended reading recoverable; a short gloss makes it determinate.
  - *Checks:* No check can observe it: uniqueness across packets is not decidable from one packet, and R80 §5 says the format cannot enforce it. A writer cannot always know every other name in use, which is why it is a SHOULD; it is scoped to source names.
  - *Placement:* Part 04 §5.5, after the sentence that says what a source name is. No other part or schema recommends it.
  - *Implementation and corpus:* Unobservable in code: `PacketWriter.declare_source` takes any name, and no shipped adapter names a source (tests use `raw_nwb` and `cams`). No packet is affected.
  - *Wording:* Name the writer, keep the clause's 'unique beyond the packet' and its reason, and add the gloss. If the gloss is judged more than a fix may add, the sentence without 'naming the same body of data wherever it is used,' is the clause verbatim.

### 19. R80 §2.2 at Part 04 §5.5 (ew-source-resolution)

- **The revision decides:** a reader MUST NOT dereference the document's $schema
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** A resolution document's `$schema`, where present, names its meta-schema by `$id`: it is identity, not a fetch instruction, and a reader MUST NOT dereference it.
- **Placement:** Part 04 §5.5 (ew-source-resolution), in the paragraph beginning 'A writer that writes a resolution document MUST write one that satisfies the schema.', after 'A reader MAY validate a resolution document against the schema, and need not.'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Evaluation:** Safe as written: R134 moved the keyword out of an informative description without withdrawing the rule, the sentence matches Part 02 §9.2's practice, and the reference reader validates against its bundled schema. No check can observe it, as with §5.5's other reader obligations.
- **By lens:**
  - *Still decided:* Yes. R80 §2.2's field table binds a reader. R134's consequence table has the schema's `$schema` description drop its keyword and R134 §3.3 makes the descriptions informative, but R134 says 'No accepted clause is superseded whole', lists what it replaces without this rule, and gives a prose owner only to the version rule; R134 §2.4 discusses only that rule. So the keyword left the description by a decision about descriptions, and the rule was left without an owner rather than withdrawn.
  - *Contradiction:* None. Part 04 §5.5's 'A reader MAY validate a resolution document against the schema' means the incorporated schema, which a reader holds locally. Part 02 §9.2 states the same prohibition for a checker and registry identifiers and Part 02 §9.3 for authority URIs, so the sentence matches the parts' practice. The schema's informative description ('a reader neither dereferences nor requires it') agrees.
  - *Exceeds the clause:* No: it restores the dereference half of the clause's sentence. The other half ('MUST NOT require it') was judged carried by the schema not requiring `$schema`; note that a reader need not apply the schema (R134 §3.3), so nothing in prose stops a reader demanding the member. That is outside this finding and could be restored in the same sentence if wanted.
  - *Actor:* A reader, before the keyword, with a determinate outcome (no fetch of the named URI).
  - *Checks:* No packet check, schema or corpus case can observe a reader's fetch; a reader's own suite can. A reader can always comply and the sentence is scoped to one member of one document. It needs the 'unchecked' treatment the project gives such a MUST; note that §5.5's other reader obligations carry no label, and this one is unchecked in the same way they are.
  - *Placement:* Part 04 §5.5 owns the resolution document and, since R134, 'what each member means'; it currently says nothing about `$schema`. Part 02 §9.2 binds a checker selecting registry schemas, a different actor and document, so no second owner.
  - *Implementation and corpus:* Complies: `escapewheel_reader/location.py` `read_sources` and `check_sources` validate against the bundled `schemas/sources.schema.json` and never read the document's `$schema`; the writer's `sources_document` writes the `$id` there as identity. No packet is affected and no validator check is needed.
  - *Wording:* 'meta-schema' is the parts' term for the schema a document names in `$schema` (Part 02 §9.2), and the sentence reads cleanly in the paragraph on validating a resolution document. No change.

### 20. R80 §2.3 at Part 04 §5.5 (ew-source-resolution)

- **The revision decides:** a reader MUST NOT infer that the packet vouches for what the default document says
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** The packet's recorded digests do not cover the default, and a reader MUST NOT infer that the packet vouches for what it says. No checker verifies this.
- **Placement:** Part 04 §5.5 (ew-source-resolution), after 'A writer SHOULD write that default.' (or after finding 58's sentence)
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** The default is not a packet resource: the packet's recorded digests do not cover it, and a reader MUST NOT infer that the packet vouches for what it says.
- **Evaluation:** Restore the prohibition without the clause that repeats 'MUST NOT be a packet resource', and label it as unchecked. Keep R80's actor, a reader; moving it to a consumer, which Part 00 §2.4 and R111 would favour for an inference, is a revision's change and not a fix.
- **By lens:**
  - *Still decided:* Yes. R80 §2.3 binds a reader and no later revision cites or withdraws it; R111 §3.5 assigned actors only to sentences then in the parts, and this one never was. R136 renamed R52's checksums as the entries' recorded `digest`.
  - *Contradiction:* None. Part 04 §5.5 already has 'A resolution document MUST NOT be a packet resource', so the proposal's 'The default is not a packet resource:' repeats a keyword rule two paragraphs up in the indicative; drop it. 'the packet's recorded digests do not cover it' is entailed by §4.3 (a digest is recorded on a resource entry) and is what R80 §2.3 says MUST be stated; it is finding 59's content, which the audit left as a judgement, and it is harmless as the lead-in to the keyword clause.
  - *Exceeds the clause:* The keyword clause is the clause's. Including the digests clause adopts one reading of finding 59; say so in the ledger note rather than restore it silently.
  - *Actor:* The clause names a reader. Under Part 00 §2.4 a reader is bound by what it returns and a consumer by what it concludes, and R111 §3.3 gives 'a consumer MUST NOT infer ...' as the model for such a rule, as the neighbouring 'A consumer MUST NOT read resolution through a different document ...' was assigned by R111 §3.5. Changing the actor is what R111 did by revision, so a fix keeps 'a reader', which R80 chose and which can comply (it presents nothing from the default as verified by the packet).
  - *Checks:* No check can observe an inference; R111 §3.3 permits exactly this form. A reader can always comply and the sentence is scoped to the default at the packet root, so it must carry the label the parts use ('No checker verifies this.').
  - *Placement:* Part 04 §5.5, after the sentence about the default. Nothing else in the parts or artifacts says what the default is evidence of ('vouch' occurs nowhere).
  - *Implementation and corpus:* Unobservable in code and not violated: `escapewheel_reader/location.py` `resolve_sources` consults the root `sources.json` after the caller's documents and attaches no verification claim to it. No packet is affected.
  - *Wording:* Drop the repeated first clause and add the label.

## Part 05

### 21. R87 §2.3 at Part 05 §3.5 (ew-recipe-check)

- **The revision decides:** a field an override covers is reported as information, so the log lists every place the recipe corrects a source
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** A build MUST report as **information**, before it opens any source, a field the recipe declares that some listed source states and an override covers, so that its reports list every field in which the recipe supersedes a source. No checker verifies this.
- **Placement:** Part 05 §3.5 (ew-recipe-check), as a new paragraph at the end of the section, after the sentence beginning 'A warning is not an error because narrowing is legitimate'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** A build MUST report as information, before it opens any source, a field the recipe declares that some listed source states and an override covers, so that the log lists every place the recipe corrects a source. ('`Recipe.check`' becomes 'a build' and '`STATES` names' becomes 'states', as §3.5 already words the warning.)
- **Evaluation:** Restore it: the clause is still decided, the reference writer already emits and tests the report, and nothing else states it. Enter the reworded sentence at the end of §3.5 without the proposal's editorial parenthesis and without the undefined term 'the log'.
- **By lens:**
  - *Still decided:* Read R87 in full and every later accepted revision naming `[overrides]` (R108 §3.3, R133 §3.3's recipe schema row, R150's amending-build refusal) plus R146's crosswalk rows for Part 05 §§3.4-3.7; none withdraws or rewords the information report. R87's own accepting commit 9a858fea wrote only the warning bullet into §3.5, so the loss is an incorporation omission and not a later decision.
  - *Contradiction:* None in Part 05 §§3.5-3.6, Part 12 §§7 and 9, the recipe schema or the open drafts. Two things sit beside it: §3.6's 'silences the report' means the difference report of that section, and R108 gave `[overrides]` a second use (a preferred source over a displaced one, Part 05 §3.4) that this report does not list because it covers only fields the recipe declares; an amending build refuses any `[overrides]` member, so the report cannot arise there.
  - *Exceeds the clause:* Force, timing ('before any source is opened') and condition match the clause word for word once `Recipe.check` is read as a build and `STATES` as 'states'. The trailing parenthesis in the proposed text is a note to the editor and must not enter the part.
  - *Actor:* A build (Part 00 §2.4, binding the writer) can always comply: the recipe, the adapters' declarations and the overrides table are all in hand before any source is opened, and the outcome is a line in what the build reports. It prescribes no method.
  - *Checks:* No registry rule, schema, validator check or corpus case can observe a build's reports; the packet records the recipe (Part 05 §3.2) but not the log. It is a writer-conformance obligation under Part 05 §10 like every other bullet of §3.5, the build can always comply and the sentence is scoped to declared-and-stated fields, so it is acceptable but must be labelled as unchecked.
  - *Placement:* Part 05 §3.5 owns the pre-I/O recipe check and already states the warning half of the same clause; no other part states the information half, so no second owner arises. It must follow the sentence 'A warning is not an error because narrowing is legitimate', which belongs to the warning list, rather than split the list from that sentence.
  - *Implementation and corpus:* The reference writer complies: `_declared_fact_problems` in escapewheel-writer/src/escapewheel_writer/recipe_check.py appends `RecipeFault.OVERRIDE_APPLIED` at `Level.INFO` for a declared, stated and overridden field, and `test_an_override_is_recorded_rather_than_warned` in escapewheel-writer/tests/test_recipe_check.py asserts it, citing Part 05 §3.5. No packet or fixture changes and no validator check is needed.
  - *Wording:* Drop the parenthesis; bold **information** to match 'as a **warning**'; Part 05 never defines 'the log', so say what the build's reports list; 'supersedes' is §3.6's verb for an override where 'corrects' presumes the source is wrong, which a stale override is not. The neighbouring build obligations carry no unchecked label, so the reviewer may prefer to settle labelling for §3.5 as a whole.

### 22. R129 §3.7 at Part 05 §14.3 (ew-reader-registry-independence)

- **The revision decides:** the failing reader MUST identify the missing support
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** Where the resource uses a format version or feature the reader does not support, the reader MUST identify that version or feature in the failure. No checker verifies this.
- **Placement:** Part 05 §14.3 (ew-reader-registry-independence), last paragraph, after the sentence ending 'fails that resource alone where it lacks support'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** Where a reader fails a resource for lack of support, it MUST identify the missing support.
- **Evaluation:** Restore it as a third sentence of §14.3's last paragraph, scoped to an unsupported format version or feature as the clause was, and labelled as unchecked. The reference reader meets it for an undecodable Zarr codec and relies on the library's message elsewhere, which is worth a test but is not a reason to withhold the sentence.
- **By lens:**
  - *Still decided:* Read R129 §3.7, R137 (a feature outside a floor is a resource finding; its §4 keeps 'a reader still fails only the resource it cannot decode'), R146 §3.7 and its crosswalk rows moving Part 04 §5.3's last paragraph to Part 05 §14.3, and R154. R129's own incorporating commit cbfbccf3 wrote the paragraph without the identification duty, R146 §3.7 fixes the paragraph's two sentences verbatim without mentioning it, and no revision withdraws it.
  - *Contradiction:* None: a further sentence leaves R146 §3.7's two quoted sentences intact. It sits beside §14.3's second paragraph ('local failure or partial-access behavior is not defined here'), which concerns an unusable declaration and not an unsupported representation, and beside Part 03 §6.1's actorless 'MUST fail that resource specifically'; the open byte-order draft leaves Part 03 §6.1 unchanged and says nothing of what a failure names.
  - *Exceeds the clause:* The proposed 'for lack of support' is wider than the clause, whose condition is a representation using 'a format version or feature the reader does not support'; lack of support also covers an optional dependency that is not installed or a store backend that is missing. The reworded text restores the clause's condition.
  - *Actor:* A reader is named and is bound by what it returns; the outcome is that the failure names the version or feature. It can always comply, because the preceding sentence has it inspect the resource's metadata before exposing values, so it holds what the resource uses and knows what it supports.
  - *Checks:* No registry rule, schema, validator check or corpus case observes a reader's failure; conformance/zarr-probe measures what readers decode and is a probe, not a check. The reader can always comply and the sentence is scoped to an unsupported version or feature, so it is acceptable and must be labelled as unchecked, in the words R146 §3.7 uses.
  - *Placement:* Part 05 §14.3 is where R146 put the reader's per-resource failure and is the only statement covering tables as well as arrays, so the duty belongs with it. Part 03 §6.1 holds the forceful 'fail that resource specifically' but only within the array version section and without an actor, so it is a weaker home and gains no second version from this sentence.
  - *Implementation and corpus:* The reference reader complies for the tested case: `array` in escapewheel-reader/src/escapewheel_reader/resources.py raises `UnsupportedCodecError` carrying the resource ID, Zarr's message naming the codec and whether the array is outside the floor, asserted by test_resources.py with `match="example.unimplemented"`. For any other unsupported feature, an unsupported Parquet compression in `table` for instance, it passes on the library's own exception, which normally names the feature but is not wrapped or tested, so full compliance is not demonstrated; no packet or validator check is affected.
  - *Wording:* 'The missing support' is vague and 'it' has no near antecedent after the paragraph's last sentence. Name the reader, restate the clause's condition, and say where the identification appears.

### 23. R32 §4 at Part 05 §15.1 (ew-amendment-definition)

- **The revision decides:** `created_at` is the packet's creation and MUST be preserved by an amendment; `validation.validated_at` is replaced
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** It MUST carry `created_at` exactly as the superseded manifest does, so that the member records when the amended packet was first built and its validation block records when it was last validated; no checker verifies this.
- **Placement:** Part 05 §15.1 (ew-amendment-definition), first paragraph, after the sentence 'The amended manifest MUST carry `replaces` exactly as the superseded manifest does, or omit it where that manifest omits it.'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** `created_at` is the packet's creation: the amended manifest MUST carry the superseded manifest's `created_at` unchanged. Its validation block records the latest run and is replaced.
- **Evaluation:** Restore the carry-over of `created_at` in §15.1, worded as a property of the amended manifest and labelled unchecked; the reference writer and every amended fixture already comply. Leave Part 04 §3 alone and do not assert 'the packet's creation', which a replacement keeping its `packet_id` would falsify.
- **By lens:**
  - *Still decided:* Read R32 §4, R61, R75 (cites `created_at` only as a reason builds are not byte-identical), R130 (format only), R146 §3.2 ('retained with its own `created_at`', the retained copy's bytes), R150 and R153 §3.5. None gives `created_at` another meaning or lists it as something an amendment sets; git pickaxe shows the rule was never in a part.
  - *Contradiction:* None in the parts, manifest.schema.json (type and format only) or drafts. Part 05 §15.3's 'keeps its own `created_at`' stays true though every version in one amendment line then shares the value, and Part 05 §11's deterministic-build mode that pins `created_at` is unaffected.
  - *Exceeds the clause:* The proposed 'is the packet's creation' is the clause's phrase, but since R153 a replacement may keep its `packet_id` at a greater major version and is a new build with a new `created_at`, so 'the packet's creation' now claims more than holds. The carry-over across an amendment is all the clause still decides.
  - *Actor:* Stated as a property of the amended manifest, the form §15.1's `replaces` sentence uses and CONTRIBUTING §4 allows; the writer performing the amendment holds the superseded manifest and can always comply and tell.
  - *Checks:* No check observes it: `amendment.identity_changed` does not compare `created_at`, and no corpus case differs in it. It is acceptable as scoped to an amendment and always compliable, and must carry 'no checker verifies this' as §15.3 does; adding the comparison to §15.6 would be a revision, not a fix.
  - *Placement:* Part 05 §15.1 owns what the amended manifest carries. Do not add a definition of the member to Part 04 §3: its generated table is format only, and a meaning stated there as well would be a second owner.
  - *Implementation and corpus:* Complies. publication.py `Amendment._candidate` and verify.py `verify` copy the superseded manifest and never reset `created_at`; `promote` writes a fresh validation block. test_amending.py asserts equality with the retained manifest, prune.py `_stamp` measures age from `validated_at` first, and all ten fixtures/packets/amended_* share one `created_at` across versions.
  - *Wording:* Drop 'is the packet's creation' as a bare definition and the detached second sentence; model the sentence on the `replaces` one and label it unchecked. If finding 25's closed list is adopted, this sentence becomes an instance of it and only its explanatory half is needed.

### 24. R61 §2.1 at Part 05 §15.5 (ew-packet-cleanup)

- **The revision decides:** A conforming implementation SHOULD offer cleanup over a committed packet
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** A writer SHOULD offer it over a committed packet, since nothing else removes what an amendment leaves behind; a writer that performs no amendment leaves nothing for it to remove.
- **Placement:** Part 05 §15.5 (ew-packet-cleanup), first paragraph, directly after the sentence 'Cleanup is a separate operation.'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** A writer SHOULD offer cleanup over a committed packet.
- **Evaluation:** Restore the SHOULD in §15.5 with its reason stated, as CONTRIBUTING §4 requires of a SHOULD; the reference writer already offers `prune`. The section still never defines an orphan, which this sentence leans on.
- **By lens:**
  - *Still decided:* Read R61 in full, R62, R111 §3.5 (the stray clause binds a writer, 'cleanup being a mutation of a packet'), R135 §3.5 and R146 §3.2 and its crosswalk row for Part 03's former section 9.5. None withdraws the recommendation; the v0.2 compilation (4ce6f09c) wrote only 'Cleanup is a separate operation' and R146 moved that unchanged. R61 §5's open questions (remote packets, reporting strays) do not bear on it.
  - *Contradiction:* None found in Part 05 §§10, 11 and 15, Part 03 §9, Part 07's command list or the drafts. Part 05 §11's acceptance criteria do not list cleanup, which is consistent with a SHOULD.
  - *Exceeds the clause:* The proposed text keeps the clause's force and object. Mapping 'a conforming implementation' to 'a writer' follows R111 §3.5 and adds no actor; narrowing it to writers that amend would drop scope and is not proposed.
  - *Actor:* A writer can comply and tell. But CONTRIBUTING §4 requires a SHOULD to state, or make evident, why an implementation might depart, and the bare sentence does not: the evident case is a writer that performs no amendment, whose packets hold no orphan and no superseded manifest.
  - *Checks:* No check observes whether a writer offers an operation, and a validator is forbidden to judge a packet by a writer-only obligation (Part 05 §10). As a SHOULD it needs no unchecked label; Part 05 §13.4's 'A reader SHOULD offer' and §11's 'A writer MAY offer' are the precedent for stating a capability.
  - *Placement:* Part 05 §15.5 (ew-packet-cleanup) owns cleanup and Part 05 §1 binds a writer to §15. No other part states it. Note that §15.5 uses 'orphan' without defining it (R61 §2.1's definition is not in any part), so the sentence should say what the operation removes or rely on a separate restoration of that definition.
  - *Implementation and corpus:* Complies: escapewheel-writer prune.py `prune` and the `escapewheel prune` command in scripts/cli.py, listed in informative Part 07. No packet or fixture is affected and no validator check is needed.
  - *Wording:* Give the reason, without history, and attach it to the section's opening so 'Cleanup is a separate operation' is not left as a fragment beside it.

## Part 12

### 25. R115 §3.3 at Part 12 §3 (ew-protocol-groups)

- **The revision decides:** a writer MUST NOT require any adapter to be importable in its own environment
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** A build MUST NOT require an adapter to be importable in the writer's environment, except one its recipe opts into the writer's process (Part 05 §3.9), and MUST be able to reach an adapter that is not.
- **Placement:** Part 12 §3 (ew-protocol-groups), as the opening sentence of the paragraph beginning 'An adapter **released independently of a build** MUST declare and support at least one protocol in a group'
- **Observed by a check:** yes, or the sentence binds nothing.
- **Text first proposed, set aside:** A writer MUST NOT require any adapter to be importable in its own environment, and a build MUST be able to reach one that is not.
- **Evaluation:** Restore it in Part 12 §3, where §7's 'which this part forbids requiring' already points, but bind a build and name Part 05 §3.9's opt-in as the exception, since the clause's bare 'any adapter' reads as contradicting the refusal of an opted-in adapter that will not import. The reference writer already complies and writer tests cover it, so this is a text fix.
- **By lens:**
  - *Still decided:* Read R115 §3.3 and §3.5, R116, R117, R119, R133, R134 §§3.2 and 3.5, R144 and R146. None withdraws the prohibition; R144's crosswalk deliberately reworded Part 03's former section 11.5's 'which this section forbids requiring' to 'which this part forbids requiring', so the later record still treats the rule as stated in Part 12. The incorporating commit 092707be never carried the sentence (Part 03 §11 as first written has the §11.5 back-reference and no prohibition), so the loss is an incorporation omission and not a later decision.
  - *Contradiction:* Taken literally, 'MUST NOT require any adapter to be importable' sits against Part 05 §3.9, which has a build refuse where it cannot import an adapter the recipe opted in, and has a build run a shipped adapter that declares no protocol in process. R115 held both, but the part should not: the restored sentence needs the opt-in named as the exception. No conflict found with Part 12 §7 (document for an adapter a build cannot import), Part 09 §5.6 or the open drafts (grepped revisions/drafts for importable, Part 12 and protocol).
  - *Exceeds the clause:* The proposed text is the clause's sentence word for word, so it adds nothing; it drops only the context R115 §3.5 gave it. The second half ('a build MUST be able to reach one that is not') is the clause's and is already entailed by Part 12 §3 (a build supports every protocol) and §7 (a build reads the declaration document), so it is a summary in the owning part and not a new duty.
  - *Actor:* 'A writer' and 'a build' are both Part 00 §2.4 terms and the outcome is observable: a recipe naming an adapter the writer's environment cannot import, with a delivery command and a declaration document, builds. Part 12 §1 says the part's rules bind a build and the adapters it reaches, so 'a build' is the actor that fits the destination; 'its own environment' needs 'the writer's' once the subject is a build.
  - *Checks:* Checked by the writer suite: test_recipe_check.py::test_ownership_defaults_from_a_document_for_a_kind_that_cannot_be_imported and the test_delivery.py cases that fetch from script adapters of unregistered kinds. No validator or corpus case can see it, since a packet does not record how its adapters were reached.
  - *Placement:* Part 12 §3 is right: Part 12 §7 already cites 'this part' as the place that forbids it, and R144 worded that citation on purpose. Part 05 §3.9 is the only other credible home (it holds the opt-in exception and is profile-independent, as R115's 'Profile: all' was), but putting it there would falsify §7's 'this part'; cite §3.9 from the restored sentence instead.
  - *Implementation and corpus:* Complies. escapewheel_writer/recipe_check.py::_declaration_problems reads a declaration document where kinds.importable(kind) is false and refuses only a delivered kind that names no document (NO_DECLARATION, which is Part 12 §7's rule); reading.fetch runs the recipe's command over any protocol with nothing imported. No packet or fixture changes, and no new validator check is needed.
  - *Wording:* 'in its own environment' is ambiguous after the actor change, and 'any adapter' overstates beside Part 05 §3.9. No retired term or moved citation.

### 26. R115 §3.9 at Part 12 §3 (ew-protocol-groups)

- **The revision decides:** a profile MUST NOT make using that implementation a condition of conformance, and a build MUST NOT refuse an adapter that speaks a protocol without it
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** Nothing in this profile makes using an implementation a writer ships a condition of an adapter's conformance, and a build MUST NOT refuse an adapter for speaking a protocol without one.
- **Placement:** Part 12 §3 (ew-protocol-groups), appended to the paragraph beginning 'A build reaching out of process an adapter that declares its protocols MUST reach it by one of them'
- **Observed by a check:** yes, or the sentence binds nothing.
- **Text first proposed, set aside:** This profile MUST NOT make using that implementation a condition of conformance, and a build MUST NOT refuse an adapter that speaks a protocol without it.
- **Evaluation:** Restore the build's prohibition in Part 12 §3, worded so it does not lean on finding 103's sentence and so the profile half is a statement rather than a MUST on a non-actor. The reference writer complies and one hand-written stream adapter in the writer suite already exercises it; add ew-protocol-groups to the ledger targets of R115 §3.9.
- **By lens:**
  - *Still decided:* Read R115 §3.9 in full and R116, R117, R119, R134, R144 and R146; none touches the prohibition. The ledger note from the accepting commit 092707be treats it as implied by the protocol group, so it was never written into a part rather than removed from one.
  - *Contradiction:* None found in Part 12 §§3, 4, 7 and 8, Part 05 §§3.5 and 3.9 (the refusal lists name no such ground) or Part 09 §§5.6 and 5.7. Part 07 §4 says an independently released adapter 'declares its protocols by naming constants the implementation exports rather than strings it spells'; that is informative and describes the reference convention, but it reads as the opposite expectation and should be glanced at when the sentence goes in.
  - *Exceeds the clause:* The proposed text matches the clause's two prohibitions. Its 'that implementation' depends on finding 103's sentence being present, which is not settled, so the sentence must stand without it.
  - *Actor:* The build half names a Part 00 §2.4 actor and an observable outcome (an adapter speaking a protocol with its own code is not refused for that). The profile half binds 'this profile', which is not an actor and which the part itself is: it is the specification constraining its own text. Part 12 §3 has the same form already ('A profile MUST NOT change what a named protocol means'), but CONTRIBUTING §4 wants an actor before the keyword, so state the profile half as a fact about the profile.
  - *Checks:* The build half is observable by a writer test and is exercised: test_delivery.py::test_an_adapter_still_ending_the_sentinel_is_not_cut_off drives a `stream-v0.1` script adapter written against bare pyarrow and the build accepts it; nothing does the same for `files-v0.1` or `flight-v0.1`, whose tests use the writer's own serving module. The profile half is a statement about the part's own text and has nothing to check.
  - *Placement:* Part 12 §3 owns which adapters a build refuses over a protocol, and no other part states this rule (Part 09 §5.6 is about an extension's code). The ledger's targets for R115 §3.9 (Part 12 §8 and Part 07 §4) do not include §3 and need it added.
  - *Implementation and corpus:* Complies: escapewheel_writer/reading.py (_read_files, _read_stream, _read_flight) reads the wire format and has no check of what produced it, and recipe_check.py's refusals key on declarations only. No packet, fixture or validator check is affected.
  - *Wording:* 'that implementation' has no antecedent unless finding 103 is restored, and 'condition of conformance' with a MUST on 'this profile' is actorless. Corrected sentence given in final_text.

### 27. R115 §3.11 at Part 12 §9 (ew-adapter-run-report)

- **The revision decides:** a build MUST ignore `app_metadata` on `FlightInfo`, which carries no finding
- **The part now says:** nothing; the sentence is absent.
- **Text to enter:** No finding travels in a listing. `flight-v0.1` gives no meaning to the `app_metadata` field of a `FlightInfo`, the entry `ListFlights` returns for each resource, and a build MUST ignore that field.
- **Placement:** Part 12 §9 (ew-adapter-run-report), as a new paragraph after the one beginning 'Which channel carries a report is the protocol's'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** `flight-v0.1` names no meaning for the `app_metadata` field of a `FlightInfo`, and a build MUST ignore it.
- **Evaluation:** Restore it in Part 12 §9 with a clause tying `FlightInfo` to the `ListFlights` listing the part already names; it stands apart from findings 96 and 97. The reference build already ignores the field, but nothing tests that, so add a writer test with the fix or label the sentence as unverified.
- **By lens:**
  - *Still decided:* No later revision touches it (read R116, R117 §3.2 on the `resources` descriptor, R134, R144, R146; `app_metadata` and `FlightInfo` occur in no other accepted revision and in no part's history). The incorporating commit 092707be left it out without a note. Unlike `extra_info`, the field is not among the things R115 §6 flags as unverified across languages: it is a member of the Flight message itself.
  - *Contradiction:* None found. Part 05 §4.4's 'report everything the protocol it used carries about a failure' concerns a failure, and a listing is not one; Part 05 §4.4's row-count check and §4.1's discovery use the listing's schema and row count, not this field; Part 12 §9's 'MUST report every problem it is given' is about a report. Part 12 §3 forbids changing what a named protocol means, which agrees with fixing that `flight-v0.1` gives the field none. No open draft uses the field.
  - *Exceeds the clause:* The proposed text matches the clause: no meaning named, and a build MUST ignore it. It drops the clause's reason ('which leaves the field to a later version of the protocol'), which is rationale and, under §3, would be a new member of the group rather than a later version; dropping it loses nothing.
  - *Actor:* 'A build' is a Part 00 §2.4 term, it can always comply, and the outcome is determinate: what a build stages, refuses and reports is the same whatever the field holds.
  - *Checks:* No existing check observes a violation: no writer test serves a listing carrying `app_metadata`, and a validator or corpus case cannot see a build's handling of a listing. A writer test could (an adapter putting an error-level entry there, the build reporting nothing of it). Until one exists the sentence is unchecked and should say so or gain the test with the fix; a build always complies by not reading the field.
  - *Placement:* Part 12 §9 is the better of the two offered homes, because the rule is about where a finding may travel and §9 already says which channel carries a report under `flight-v0.1`. Part 12 §3's table has no room for it, and §8 mentions `ListFlights` only for the rendezvous. Place it after the paragraph beginning 'Which channel carries a report is the protocol's', which does not depend on findings 96 and 97.
  - *Implementation and corpus:* Complies: escapewheel_writer/reading.py::_read_flight takes only `info.descriptor.path` from each listing entry and never reads `app_metadata`, and serving.py sets none. No packet, fixture or validator check changes.
  - *Wording:* The parts have not introduced `FlightInfo`: Part 12 §8 names `ListFlights` and §3 speaks of 'one descriptor per resource'. The sentence needs the few words that tie the message to the listing; no retired term or moved citation otherwise.
