# Class A: sentences absent from the parts

Each rule below is decided by an accepted revision and stated by no part. Restoring it contradicts nothing a part or a later revision says.

35 rules, ordered by part and section: Part 01 (9), Part 02 (6), Part 03 (3), Part 04 (6), Part 05 (4), Part 12 (7).

Nothing here has been applied. The audit record is [applied-targets.md](../applied-targets.md).

## Part 01

### 1. R38 §2.3 at Part 01 §2.3

- **The revision decides:** a clock's own interval is not derived from what it recorded either: it is the extent of the acquisition
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A clock's own interval is not derived from what it recorded either: it is the extent of the acquisition, so for a sample clock whose origin is sample 0 of a recording, `start_tick` is 0 and `stop_tick` is the last sample's index, one less than the recording's length.
- **Placement:** Part 01 §2.3
- **Risk:** None found. The example must take R45 §2.3's closed form, not R38's original 'the recording's length'. The clause has no capitalized keyword, so the indicative restores it fully; the ledger target §2.2 is now Time basis and the observation rules sit in §2.3.
- **Second reading:** The sentence is a rule about what a writer records as a clock's own window, stated in the indicative in R38 §2.3; R45 §2.3 amends only its example (`stop_tick` is 'the last sample's index, one less than the recording's length') and R98 §2.1 relies on it ('taken from the extent of the recording it counts and explicitly not from the spikes, which is what R38 §2.3 requires of a window'). Part 01 §2.3's MUST NOT binds 'Anything timed by a clock', not the clock; Part 02 §12.5 requires a window without saying what it spans; the registry describes the columns as 'First tick observed' and 'Last tick observed', which a window taken from the first and last recorded timestamp also satisfies. Searched Parts 01, 02, 05 and the registry for 'acquisition', 'extent', 'derived', 'recording'. Part 01 §3.13.1 uses 'the recording's extent' as a rate's fallback denominator without tying the clock's window to it.

### 2. R6 §2 at Part 01 §3.9 (Clock)

- **The revision decides:** where present, the wall-clock time of any tick is `tick_zero_utc + t_tick / effective_tick_rate`, using `tick_rate_hz` or `tick_rate_num / tick_rate_den`
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** Where a clock binds its tick 0 to a wall-clock instant, the wall-clock time of a tick on that clock is that instant plus the tick divided by the clock's declared tick rate (in Part 02's terms, `tick_zero_utc + t_tick / rate`, the rate being `tick_rate_hz` or `tick_rate_num / tick_rate_den`).
- **Placement:** Part 01 §3.9 (Clock), at the tick-zero bullet; the column-level form belongs beside Part 02 §12.4
- **Risk:** None found. It parallels Part 01 §2.2's derivation of seconds and uses only declared values. R6's 'effective_tick_rate' is not a term of the parts; since Part 02 §12.4 now requires exactly one rate form, 'the clock's declared tick rate' says the same.
- **Second reading:** R6 §2 defines what a tick-zero binding yields: `tick_zero_utc + t_tick / effective_tick_rate`, at the clock's own declared rate. No part states it. Part 01 §3.9 says a clock 'MAY bind its tick 0 to a wall-clock instant, which is the only route from a packet's ticks to real time' and stops there; Part 01 §2.2 defines only seconds from the session origin on the reference clock; Part 02 §12.4 to §12.6 and the registry (`tick_zero_utc`: 'Wall-clock instant of tick 0 on this clock') give the column and no computation. The formula is a definition and carries no keyword in R6 either, but it settles a real choice (the tick's own clock at its declared rate, not a path through the parent chain), so it is not mere rationale. No later revision withdraws it: R39 §3 says 'No withdrawal of `tick_zero_utc`. It stays optional and stays what R6 made it', and R27 amends only how a derived value is anchored.

### 3. R27 §5.3 at Part 01 §3.9 (Clock)

- **The revision decides:** between two anchors separated by at most 2m (m the clock's median anchor interval) the mapping is linear interpolation on the bracketing pair
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** Let m be the median interval between consecutive anchors of a clock, in ticks on that clock. Between two anchors separated by at most 2m, the mapping is linear interpolation on the bracketing pair; inside a gap wider than 2m it is undefined further than m from every anchor.
- **Placement:** Part 01 §3.9 (Clock), before 'Alignment beyond the terminal anchors'
- **Risk:** None found. It agrees with the registry rule `gap_within_bound`, with Part 02 §12.6's 'exact at every anchor', and with Part 01 §2.3's remark that outside the first and last anchor the mapping is undefined. The second half of the restore text is R27 §5.3's third clause as R37 §3.3 left it for gaps ('a gap wider than 2m leaves its middle undefined'); drop it if that clause is tracked separately.
- **Second reading:** R27 §5.3's first clause defines the mapping between anchors. No part defines it. Part 01 §3.9 says a clock 'MUST declare either a linear transform or anchor points' and then speaks only of alignment 'beyond the terminal anchors'; Part 02 §12.6 says 'the map is exact at every anchor' without saying what it is between them; Part 05 §5.3 maps 'through the anchors or transform of every clock on the path'. The registry keeps two traces, the messages of `core.clock_anchors.monotonic` ('so interpolation is undefined') and `core.clock_anchors.gap_within_bound` ('an anchor gap exceeds twice the median, leaving ticks the mapping does not define'), which presuppose the definition and do not state it. It is a definition and carries no keyword in R27, but it is what a consumer computes, not rationale. Later revisions keep it: R37 §4 'No change to interpolation. Between anchors no more than 2m apart the rule is unchanged', and R40 §3 keeps the undefined middle of a wider gap. R145, which restated the measurement clauses of Part 01 §3.9, did not touch it.

### 4. R27 §5.3 at Part 01 §3.9 (Clock)

- **The revision decides:** beyond the terminal anchors a consumer MUST use the rate fitted over the clock's full anchor sequence and MUST NOT extend the terminal segment's slope
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** Beyond the terminal anchors a consumer computing the mapping MUST use the rate fitted over the clock's full anchor sequence, and MUST NOT extend the terminal segment's slope.
- **Placement:** Part 01 §3.9 (Clock), at 'Alignment beyond the terminal anchors'
- **Risk:** No contradiction; the part already presupposes an estimator. R37 §3.1 completes the rule and should be restored with it, or the sentence is under-determined: the rate is applied from the nearest terminal anchor (parent(t) = parent(a) + rate * (t - a)) and a consumer MUST NOT use the intercept of a fit over the whole sequence. Part 05 §5.3 allows one tick of slack 'because a writer's estimator may fit anchors the writer does not record', which is consistent.
- **Second reading:** R27 §5.3's second clause puts two capitals on a consumer mapping past the ends. Part 01 §3.9 refers to 'the estimator's error' and never says what the estimator is; no part mentions a fitted rate, a slope to be avoided, or the terminal segment (searches of spec/parts for 'fitted', 'slope', 'estimator', 'extrapolat' find only that phrase, `transform_slope`, and Part 06 §4's writer-side omission). Later revisions keep and sharpen the rule and none withdraws it: R37 §3.1 'R27 §5.3 already says "MUST use the rate fitted over the clock's full anchor sequence"; this states the offset the rate is applied from', and R40 §3 'No change to the estimator. R37 §3.1 stands: the globally fitted rate, applied from the terminal anchor.' The ledger records both R27 §5.3 and R37 §3.1 as applied at Part 01 §3.9, where neither is stated.

### 5. R27 §5.3 at Part 01 §3.9 (Clock)

- **The revision decides:** the bound applies per edge of the parent chain, each edge against its own m
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** The bound applies per edge of the parent chain: each clock's mapping to its parent is evaluated against that clock's own median anchor interval.
- **Placement:** Part 01 §3.9 (Clock); Part 02 §12.6 would carry the same point for `alignment_bound`
- **Risk:** No contradiction with R99 §3.1: the session records one multiple, and the restored sentence says each edge applies it to its own median. It must not be worded as a per-edge recorded bound, which R99 declined ('One session declares one bound').
- **Second reading:** R27 §5.3's fourth clause says the bound is evaluated edge by edge, each against that edge's own median anchor interval. The parts state the bound as a number of median anchor intervals and never say whose: Part 01 §3.9 'A writer reaching past one median anchor interval MUST measure its error'; Part 02 §12.6 '`core.sessions.alignment_bound` holds how far past its anchors the writer mapped, in median anchor intervals ... one session declares one bound'; the registry's unit `{median_anchor_interval}`; Part 05 §5.3 'through the anchors or transform of every clock on the path ... within the alignment bound'. With several anchored clocks of different anchor density, one session-level number is ambiguous without the per-edge reading. Later revisions changed what bounds the mapping (R37 §3.3 error rather than distance, R40 §2.1 the tolerance) and where the bound is recorded (R99 §3.1, one per session) but none says against which median it is taken, and R37 §3.3 keeps R27's one-median-interval default, so the clause still governs.

### 6. R37 §3.1 at Part 01 §3.9

- **The revision decides:** beyond the terminal anchors a consumer MUST compute parent(t) = parent(a) + rate * (t - a), with `a` the nearest terminal anchor and `rate` fitted over that clock's anchors
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** Beyond the terminal anchors a consumer MUST compute the mapping as `parent(t) = parent(a) + rate * (t - a)`, where `a` is the nearest terminal anchor and `rate` is fitted over that clock's anchors.
- **Placement:** Part 01 §3.9
- **Risk:** No contradiction with a later revision. Part 01 §2.3's rationale says 'outside the first and last anchor the mapping is undefined', which already sits beside §3.9's defined-within-tolerance sentence; restoring the estimator does not add to that tension. The parts also never state R13 §3's linear interpolation between anchors, so the restored sentence will be the only statement of the map's form unless that is restored with it.
- **Second reading:** R37 §3.1 states the estimator with MUST. R40 §3 keeps it ('No change to the estimator. R37 §3.1 stands: the globally fitted rate, applied from the terminal anchor'); R39 §4 and R101 cite it as current; R99 moves the alignment record into columns and R145/R146 reword Part 01 §3.9 without touching the estimator. Searched spec/parts and the registry for 'terminal anchor', 'estimator', 'fitted', 'rate', 'nearest', 'extrapolat', 'interpolat', 'intercept': Part 01 §3.9 says alignment past the terminal anchors is defined 'only while the estimator's error stays within tolerance' and Part 05 §5.3 mentions 'a writer's estimator', and no part or artifact says what the estimator computes. git log -S'nearest terminal anchor' finds only the commit that added R37, so the sentence never reached a part.

### 7. R37 §3.1 at Part 01 §3.9

- **The revision decides:** a consumer MUST NOT use the intercept of a fit over the whole anchor sequence
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A consumer MUST NOT use the intercept of a fit over the whole anchor sequence.
- **Placement:** Part 01 §3.9
- **Risk:** None found; it belongs directly after the estimator sentence of finding 31 and has no meaning without it.
- **Second reading:** R37 §3.1's second MUST NOT, standing with the estimator of finding 31 and kept by R40 §3. Searched spec/parts and spec/artifacts for 'intercept', 'whole sequence', 'fit over': no occurrence. No later revision withdraws it; R39 §4 still contrasts 'R37 §3.1's terminal-anchored estimator and the intercept-based one'.

### 8. R70 §2.2 at Part 01 §3.18 (Media asset)

- **The revision decides:** a writer MUST declare neither rate column where it wrote no pts
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A writer that carries presentation timestamps MUST declare it and MUST NOT declare half of it; a writer that carries none for an asset MUST NOT declare a rate for that asset.
- **Placement:** Part 01 §3.18 (Media asset), the rate paragraph
- **Risk:** Contradicts nothing in a part or later revision. No registry rule checks it (a rate on an asset whose frames carry no pts passes all three core.media_assets rules), so the restored MUST NOT is unchecked unless a rule is added, which is a registry change needing its own revision.
- **Second reading:** R70 §2.2 binds a writer both ways: declare both columns where it wrote pts, and 'MUST declare neither where it did not'. Part 01 §3.18 states only the first half ('A writer that carries presentation timestamps MUST declare it and MUST NOT declare half of it'). The registry's three rules on core.media_assets (pts_rate_pair_complete, pts_rate_declared_where_frames_carry_pts, pts_rate_positive) do not report a rate on an asset whose frames carry no pts, and the column descriptions say nothing of it. The phrase 'declare neither' has never been in a part (git log -S finds it only in revisions/). No later accepted revision cites R70 §2.2 or touches pts_rate beyond listing the columns (R102).

### 9. R105 §3.4 at Part 01 §3.24 (ew-coordinate-frame-concept)

- **The revision decides:** an axis's `unit` MUST be declared
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A writer MUST declare each axis's unit.
- **Placement:** Part 01 §3.24 (ew-coordinate-frame-concept), in the list of what a frame declares
- **Risk:** No contradiction with a later revision, but the column is `nullable` in the registry and in R105 §3.2's table, so the restored MUST is a writer obligation no validator checks and should say so. With it restored, a null `unit` means a writer broke the rule, which is what makes Part 02 §12.7's `unit_from` resolution always succeed. Under R131 the value must be a UCUM code.
- **Second reading:** R105 §3.4, 'What a writer records about an axis', says '`unit` **MUST** be declared, and a writer knows it by construction'. No part requires a writer to fill an axis's unit: Part 01 §3.24's list requires a name and each axis with the source's own name, and nothing about a unit; Part 01 §3.8 says only 'Each value's unit is the axis's'; Part 02 §12.7 says `axis_value` declares `unit_from` of core.coordinate_frame_axes.unit; Part 02 §8.4's SHOULD is about a column declaring `unit` or `unit_from` in the registry, not about a row's value. The registry declares the column nullable, as R105 §3.2's own table does, so presence does not carry it, and the registry has no Tier 2 rule on it. R131 lists the column among unit columns and R150 groups the table; neither withdraws the obligation. Not refuted.

## Part 02

### 10. R88 §2.4 at Part 02 §7.1 (ew-session-scope)

- **The revision decides:** every dependent row (a sorting run, a curation version, a coordinate, a run input) references the copy of the run for its own session
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A run whose results reach several sessions is recorded once per session, and every dependent row (a sorting run, a curation version, a coordinate, a run input) references the copy for its own session.
- **Placement:** Part 02 §7.1 (ew-session-scope), or a sentence of Part 02 §12 that §12.3's 'as for any row whose results reach more than one session' can cite; the ledger target §12.3 is the calibration section and holds only the derived case
- **Risk:** The clause carries no keyword, so restoring it in the indicative restores its own force; adding MUST would be a new decision. No registry rule checks that a dependent row's run belongs to the row's session apart from core.preferred_runs.run_in_session, so the statement is unchecked. Nothing in a part or later revision contradicts it.
- **Second reading:** R88 §2.4 decides, in the indicative under its Decision heading, that 'A run whose results reach several sessions is recorded once per session, and every dependent row — a sorting run, a curation version, a coordinate, a run input — references the copy for its own session.' No part states it for processing runs. Part 02 §12.3 applies the pattern to calibrations and points at a general rule ('recorded once per session, as for any row whose results reach more than one session') that no part states. Part 02 §7.1 (session scope) does not supply it: every registry reference to `core.processing_runs` is on `processing_run_id` alone (sorting_runs, curation_versions, electrode_coordinates, unit_coordinates, event_streams, array_assets, processing_run_inputs), so none is a session-preserving edge, and only `core.preferred_runs.run_in_session` compares a run's session with the referencing row's. Part 01 §3.20 and Part 05 §7 say nothing of a run spanning sessions. The clause's one capitalised sentence (copies MUST NOT share a `processing_run_name`) is carried by Part 02 §8.2's uniqueness of an assigned identifier's name. No later revision cites R88 §2.4 except R89, which relies on it.

### 11. R91 §3.3 at Part 02 §8.6 (ew-free-form-metadata)

- **The revision decides:** a writer MUST NOT put a mark in core.events.metadata
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A writer MUST NOT put a mark, a value an event carries beyond its tick, in `core.events.metadata`, which no rule reads and no filter can use.
- **Placement:** Part 02 §8.6 (ew-free-form-metadata), with the other writer rules for `metadata`; the ledger target Part 01 §3.12 cannot name the column since R146
- **Risk:** No contradiction: `core.events.payload` remains the per-event home R91 §3.3 kept, and §8.6 already says no rule checks what a writer puts in `metadata`, so this joins obligations that bind the writer unchecked. If it is placed in Part 01 §3.12 instead it must be worded without the column name.
- **Second reading:** R91 §3.3: 'A writer MUST NOT put a mark in `core.events.metadata`, which no rule reads and no filter can use.' No part states it. 'mark' occurs in the parts only in Part 01 §3.12's indicative sentence. Part 02 §8.6's writer rules for `metadata` forbid a key that duplicates or contradicts a column and say indicatively that 'A fact required to interpret the data belongs in a column, never in a key'; a mark has no core column to duplicate, so those do not reach it. The registry's `metadata` description is the fixed sentence of §8.6. R97 §4 and §6, accepted later, restate the prohibition as standing ('R91 §3.3 having forbidden `core.events.metadata` as its substitute'). No revision withdraws it.

### 12. R8 §3 at Part 02 §9.3 (ew-registry-vocabularies)

- **The revision decides:** the three values carry declared meanings: `succeeded` completed with usable outputs, `failed` did not complete, `partial` completed for some inputs only so committed outputs are incomplete
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** `core.processing_runs.status` says whether the run completed: `succeeded`, it completed and its outputs are usable; `failed`, it did not complete; `partial`, it completed for some inputs only, so its committed outputs are incomplete.
- **Placement:** Part 02 §9.3 (ew-registry-vocabularies), after the table of closed columns
- **Risk:** None found; the registry description already assumes the sentence is there. R8's rider on `failed` ('its outputs MUST NOT be committed') is carried by the error rule `core.processing_runs.no_failed_runs` and need not be repeated. Part 05 §4.4's 'A run succeeded when every resource in that set arrived' is about a build's delivery from a source, a different use of the word.
- **Second reading:** R8 §3 gives each permitted value a meaning. Part 02 §9.3 lists only the values ('`core.processing_runs.status` | `succeeded`, `failed`, `partial`'), and Part 01 §3.20 says nothing of status. The registry's description of the column points at a statement that does not exist: 'Whether the run completed, with the meanings Part 02 §9.3 declares.' R107 (which struck prose restating a declaration) removed the values from the description and did not move the meanings anywhere. Only `failed` leaves a trace, through the registry rule `core.processing_runs.no_failed_runs` ('a failed run is recorded in a committed packet'); `succeeded` and `partial` are defined nowhere. R26, R41, R101 and R106 cite the vocabulary without changing it.

### 13. R101 §3.9 at Part 02 §9.3 (ew-registry-vocabularies)

- **The revision decides:** a writer MUST map the source's spelling onto one of the four values
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A writer MUST map the source's spelling of a subject's sex onto one of the four values of `core.subjects.sex`.
- **Placement:** Part 02 §9.3 (ew-registry-vocabularies), after the table of closed columns
- **Risk:** No contradiction. Part 01 §3.4 keeps sex at SHOULD, so the restored sentence should be read as governing how a stated sex is written, not whether one is declared. The companion rule of the same clause (null where the source states it unknown, states none, or describes a preparation that has none) survives only as the registry description, in the indicative; no validator can check either, so the sentence wants the usual 'no checker verifies this' label.
- **Second reading:** R101 §3.9 states it with a keyword ('A writer **MUST** map the source's spelling onto one of the four'). No part states a writer obligation for the closed `sex` column: Part 02 §9.3 has only the closed-set row ('a validator MUST reject a value outside it') and the four values; the registry description of core.subjects.sex states only when the column is null; Part 01 §3.4 says a subject 'SHOULD declare species, sex, and date of birth'. Part 02 §9.3's writer rules cover reserved sets and open columns with an authority, and R140 §3.1 confines the spelling rule to open columns and says a closed `enum` 'spells every value it admits', which withdraws nothing here. The closed set does make `Male` unwritable in a passing packet, so what is lost is the obligation to project a stated sex onto the set rather than drop it to null. Not refuted.

### 14. R37 §3.2 at Part 02 §12.6 (ew-clock-alignment-record)

- **The revision decides:** a writer MUST NOT emit an anchor whose parent tick it has reason to believe is misplaced
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A writer MUST NOT emit an anchor whose parent tick it has reason to believe is misplaced.
- **Placement:** Part 02 §12.6 (ew-clock-alignment-record)
- **Risk:** None found. The second half of R37 §3.2's sentence (record the withheld count in the run's parameters) must not be restored: R99 §3.2 replaced it with `withheld_first_anchor` and `withheld_last_anchor`, which Part 02 §12.6 states.
- **Second reading:** R37 §3.2's MUST NOT. Its companion ('MUST record any anchor it withheld') was moved to columns by R99 §3.2, which records 'the outcome of R37 §3.2's terminal-anchor test' and so presupposes the prohibition instead of replacing it; R37 §4 says 'A dropped anchor is simply absent'. Part 02 §12.6 describes the three recorded states ('true is one it withheld') and binds only 'a writer running it MUST record both'. Searched spec/parts and the registry for 'misplaced', 'withh', 'reason to believe', 'trust', 'emit': no part forbids writing an anchor the writer distrusts. No later revision withdraws it.

### 15. R37 §3.2 at Part 02 §12.6 (ew-clock-alignment-record)

- **The revision decides:** a writer SHOULD test each terminal anchor by predicting it from a fit over its neighbours and comparing the residual with the distribution of the same residual over that clock's interior anchors
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A writer SHOULD test each terminal anchor by predicting it from a fit over its neighbours and comparing the residual against the distribution of the same residual over that clock's interior anchors.
- **Placement:** Part 02 §12.6 (ew-clock-alignment-record)
- **Risk:** None found. The registry already cites Part 02 §12.6 as the owner of the test, so the definition closes a dangling reference. R37 §3.2's measurements and its reason for a spread-based test are rationale and need not return.
- **Second reading:** R37 §3.2's SHOULD defines the terminal-anchor test. R99 §3.2 ('A writer running the test MUST record both') and the registry descriptions of `core.clocks.withheld_first_anchor` and `withheld_last_anchor` ('Part 02 §12.6's terminal-anchor test') refer to the test by name, and Part 02 §12.6 neither says what the test is nor recommends running it. Searched spec/parts and the registry for 'residual', 'neighbour', 'neighbor', 'interior', 'predict', 'terminal': nothing. No later revision withdraws or redefines the test.

## Part 03

### 16. R129 §3.1 at Part 03 §1 (ew-portable-profile-scope)

- **The revision decides:** the generic checker MUST require every listed anchor to resolve uniquely in Part 03 to the clause that defines the entry's meaning
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** Each descriptor interface and variant carries a nonempty `anchors` array of distinct canonical `ew-` identifiers, and the generic cross-member checker MUST require every listed anchor to resolve uniquely in this part to the clause that defines the entry's meaning.
- **Placement:** Part 03 §1 (ew-portable-profile-scope)
- **Risk:** None found: all five anchors the incorporated descriptor lists (ew-table-encoding, ew-overriding-orders, ew-parquet-reader-floor, ew-array-version, ew-array-codecs) resolve once each in Part 03, and R144's move of the adapter interface to Part 12 took none of them.
- **Second reading:** R129 §3.1 has the MUST. Part 03 mentions anchors once ('The descriptor owns the profile's … anchors') and states no resolution rule; physical_profile.schema.json $defs.anchors checks only a nonempty duplicate-free array of `ew-` identifiers; and the like sentence in Part 02 §9.4 ('Every anchor MUST resolve uniquely in the numbered specification') is about the registry-contract descriptor alone. No later revision (R137, R144, R154, R155 searched for 'anchor') withdraws or restates it; R154 §3.1 adds the anchor ew-overriding-orders and assumes it resolves. The reference checker passes Part 03's text to check_physical_profile, so the rule is implemented but unstated.

### 17. R129 §3.5 at Part 03 §2 (ew-portable-profile-technologies)

- **The revision decides:** an implementation MAY support additional upstream features without changing the descriptor or packet
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** An implementation MAY support additional upstream features without changing the descriptor or packet.
- **Placement:** Part 03 §2 (ew-portable-profile-technologies), last paragraph
- **Risk:** No contradiction. It is a permission that nothing in the parts forbids, so its absence changes no conformance outcome; what is lost is the explicit statement that extra support needs no descriptor or packet change. Part 00 §2.4 reserves 'implementation' for rules binding every actor alike, which fits here; 'A reader' would also serve.
- **Second reading:** R129 §3.5: 'An implementation MAY support additional upstream features without changing the descriptor or packet.' No part states the permission. Part 03 §2 says a feature outside a reader-only floor 'is outside the portability guarantee', §6.1 has 'Lack of implementation support for one selected resource MUST fail that resource specifically', §6.4 gives a writer leave to use any codec, and Part 05 §14.3 has a reader fail a resource 'where it lacks support'; these presuppose that support beyond the floor varies but none grants it. Searched 'MAY (support|read|decode|expose)', 'beyond', 'minimum', 'optional', 'additional' in Parts 00, 03, 04 and 05. No later revision withdraws it (R137 depends on §3.5 and supersedes nothing).

### 18. R129 §3.9 at Part 03 §2 (ew-portable-profile-technologies)

- **The revision decides:** a specialized implementation MAY expose members, objects, bytes, parsing, rendering, or other representation-aware operations without changing the resource's logical kind or the reader floor
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A specialized implementation MAY expose members, objects, bytes, parsing, rendering, or other representation-aware operations without changing the resource's logical kind or the reader floor.
- **Placement:** Part 03 §2 (ew-portable-profile-technologies), after the generic-reader sentence
- **Risk:** No contradiction. It is a permission nothing in the parts forbids, so its absence changes no conformance outcome; what it adds is that such operations leave the logical kind and the floor unchanged. The part says 'reader floor' where the clause says 'portable reader floor'.
- **Second reading:** R129 §3.9: 'A specialized implementation MAY expose members, objects, bytes, parsing, rendering, or other representation-aware operations without changing the resource's logical kind or the portable reader floor.' No part states it. Part 03 §2 says only what a generic reader need not do; Part 02 §2.3 that generic code is not required to parse a payload; Part 09 §5.1 that physical-profile support determines how a payload is read; Part 09 §5.6 that generic physical support for every opaque payload is not granted. R143 and R144 add opaque delivery and storage rules and no reader permission. Searched 'specialized', 'specialised', 'representation', 'render', 'decoder', 'MAY expose'.

## Part 04

### 19. R14 §2.3.2 at Part 04 §5.1 (Declaration)

- **The revision decides:** a writer SHOULD prefer to own core tables where their size permits
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A writer SHOULD prefer to own core tables where their size permits.
- **Placement:** Part 04 §5.1 (Declaration), after 'its validation rules cannot run at all while it is unreachable'
- **Risk:** None found. 'Referencing is expected for large resources' in the same paragraph is the other side of the same trade and is bounded by 'where their size permits'.
- **Second reading:** R14 §2.3.2 ends with a recommendation to a writer, and the reason for it. Part 04 §5.1 keeps the reason ('Externalizing a table costs more than externalizing an array: its validation rules cannot run at all while it is unreachable') and drops the SHOULD. No part recommends owning core tables: searches of spec/parts for 'prefer', 'own core', 'externaliz' and for a writer SHOULD on ownership find only that sentence. No later revision withdraws it: R36 §3 and R42 only note that no packet yet externalises a table. The passage sits in Part 04 §5.1, not in the ledger target §5.3.

### 20. R36 §2.3 at Part 04 §5.3 (ew-external-resource-verification)

- **The revision decides:** a validator offering level 3 MUST offer 3a and MAY offer 3b
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A validator offering level 3 MUST offer 3a and MAY offer 3b and 3c.
- **Placement:** Part 04 §5.3 (ew-external-resource-verification)
- **Risk:** Renamed terms: R36's '3b' (the digest) is the part's 3c since R51 §2.3 added the store-digest level as 3b; R51 does not say whether 3b is optional, and 'MAY offer 3b' follows only from its being conditional on a recorded `store_digest`, so that half is an adaptation to confirm. Nothing in the part contradicts the sentence.
- **Second reading:** The sentence is a keyword rule in R36 §2.3. R51 §2.3 inserts the store-digest level between the two and renumbers R36's 3b as today's 3c without touching which levels a validator offers; R136 §3.5 changes how 3c is established, not whether it is offered. Searched spec/parts for 'offer', 'requested', 'asked': Part 04 §5.3 says only that 'Levels 3a to 3c run only in a requested mode', and no part says which level a validator that verifies external resources must provide. R14 §2.3.2's stronger 'A validator MUST offer a separate, explicitly requested mode' is not in a part either.

### 21. R52 §2.3 at Part 04 §5.3 (ew-external-resource-verification)

- **The revision decides:** A disagreement on a packet-owned resource's digest is reported as an error, not a warning
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A validator that finds a packet-owned resource's recorded `digest` does not hold MUST report the disagreement as an error, not a warning.
- **Placement:** Part 04 §5.3 (ew-external-resource-verification)
- **Risk:** None found; it agrees with Part 03 §8.1 (owned bytes are immutable) and with Part 05 §9.1's meaning of `error`. Renamed terms: R52's `checksums=True` and 'R15 §4 level 3b' are the part's level 2, and `sha256` is `digest` since R136. R52 §2.3's second paragraph (count the owned resources that record no digest) has lapsed, because R136 §3.4 requires a digest of every packet-owned resource. No check ID exists for this finding, which a restoration may want to name.
- **Second reading:** R52 §2.3 fixes the level with a keyword ('report a disagreement as an **error** — not a warning'). R136 §3.5 restates how a recorded digest is established and what the report says of the route, and §5 says only that R52 §2.3's ledger entry gains a note; it sets the level of a missing digest (`packet.resource.digest_missing`, error) and of a member list that disagrees with the entry's digest (`packet.resource.member_digest`), not of owned bytes that disagree with their recorded digest. Part 04 §5.3 defines level 2 as 'packet-owned resources' recorded digests hold' and names no finding or level for when one does not; Part 05 §5.3 lists 'checksums' among the shim's checks without a level; Part 05 §9.1 defines `error` generally. Searched Parts 03, 04, 05 for digest or checksum beside error, warning, mismatch, 'does not hold', 'disagree'. The level is therefore left to inference.

### 22. R80 §2.1 at Part 04 §5.5 (ew-source-resolution)

- **The revision decides:** a source name SHOULD be unique beyond the packet, so one resolution document serves many packets
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A source name is opaque to this specification. A writer SHOULD choose one that is unique beyond the packet, so that one resolution document serves many packets.
- **Placement:** Part 04 §5.5 (ew-source-resolution), after 'A source name is any string an external resource entry's `source` can hold.'
- **Risk:** No contradiction: R134 §3.3 widened which strings a name may be, not how it is chosen. Uniqueness beyond a packet cannot be checked from a packet, so the SHOULD is unchecked.
- **Second reading:** R80 §2.1: 'A source name is opaque to this specification. It SHOULD be unique beyond the packet, so that one resolution document serves many packets'. Part 04 §5.5 says only 'A source name is any string an external resource entry's `source` can hold' (R134 §3.3, which removed the schema's name pattern and says nothing of uniqueness). sources.schema.json's description of `sources` repeats opacity only, and is informative. Nothing in Part 03 §4, Part 04 §4.1, Part 12 or the manifest schema recommends uniqueness across packets. No later revision cites or withdraws the sentence.

### 23. R80 §2.2 at Part 04 §5.5 (ew-source-resolution)

- **The revision decides:** a reader MUST NOT dereference the document's $schema
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A resolution document's `$schema`, where present, names its meta-schema by `$id`: it is identity, not a fetch instruction, and a reader MUST NOT dereference it.
- **Placement:** Part 04 §5.5 (ew-source-resolution), the paragraph on validating a resolution document
- **Risk:** No contradiction: a reader MAY validate against the incorporated schema, which it holds locally. R134 removed the keyword from the schema description on purpose (descriptions are informative), but nothing suggests it meant to withdraw the rule; the prose owner it gave the neighbouring version rule is what this one lacks.
- **Second reading:** R80 §2.2's field table binds a reader: `$schema` is 'Identity, not a fetch instruction: a reader MUST NOT dereference it and MUST NOT require it'. Until R134 the rule lived in sources.schema.json's `$schema` description; R134's consequence table has that description drop the keyword and R134 §3.3 makes the schema's descriptions informative, while giving a prose owner only to the version rule ('R80 §2.2's version rule gains a stated owner in Part 04 §5.5') and stating 'No accepted clause is superseded whole'. So the dereference prohibition stands and has no normative statement: Part 04 §5.5 never mentions `$schema`; Part 02 §9.2's prohibition binds a checker selecting registry schemas and contracts, Part 02 §9.3's a validator and an authority URI, and Part 04 §5.3's 'Structural validation MUST NOT reach the network' binds validation, not a reader resolving a source. The 'MUST NOT require it' half is carried: the incorporated schema does not require `$schema`.

### 24. R80 §2.3 at Part 04 §5.5 (ew-source-resolution)

- **The revision decides:** a reader MUST NOT infer that the packet vouches for what the default document says
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** The default is not a packet resource: the packet's recorded digests do not cover it, and a reader MUST NOT infer that the packet vouches for what it says.
- **Placement:** Part 04 §5.5 (ew-source-resolution), after 'A writer SHOULD write that default.'
- **Risk:** No contradiction. The first half states the consequence finding 59 concerns ('R52's checksums' are now the entries' recorded `digest`, R136). The prohibition binds a reader's inference and no check can observe it.
- **Second reading:** R80 §2.3 binds a reader: 'a reader MUST NOT infer that the packet vouches for what it says', of the default `sources.json`. Part 04 §5.5 has no such sentence. Its nearest rules are different: a resolution document is not a packet resource and immutability does not reach it; a consumer MUST NOT read resolution through a different document as invalidating a recorded digest; a reader that finds a mismatch reports it. None tells a reader what the default at the packet root is evidence of. 'vouch' appears nowhere in spec/parts or spec/artifacts, and no later revision cites or withdraws the sentence.

## Part 05

### 25. R87 §2.3 at Part 05 §3.5 (ew-recipe-check)

- **The revision decides:** a field an override covers is reported as information, so the log lists every place the recipe corrects a source
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A build MUST report as information, before it opens any source, a field the recipe declares that some listed source states and an override covers, so that the log lists every place the recipe corrects a source. ('`Recipe.check`' becomes 'a build' and '`STATES` names' becomes 'states', as §3.5 already words the warning.)
- **Placement:** Part 05 §3.5 (ew-recipe-check), after the warning list
- **Risk:** No contradiction: §3.6's 'silences the report' is the report of a difference, and an amending build refuses any `[overrides]` member, so the information report cannot arise there. The omission looks like compression at incorporation (9a858fea).
- **Second reading:** R87 §2.3 requires the recipe check to report, before any source is opened, 'every field the recipe declares that some listed source's `STATES` names', the uncovered ones as a warning and 'a field an override covers ... as information, so the log lists every place the recipe corrects a source'. Part 05 §3.5 (ew-recipe-check) keeps only the warning ('a field the recipe declares that some listed source states and no override covers'). Part 05 §3.6 has a build report an override only where the source agrees or no source states the field (R87 §2.5), which is the build-time report of a stale override, not the check-time listing of every covered field; its 'silences the report' refers to §2.1's difference report. `Recipe.check` and `STATES` are reference-implementation names, but §3.5 already restates the clause's other half as a build obligation, so the sentence is a rule and not an implementation note. No later revision cites R87 §2.3 or removes the information report (R108, R115, R119, R133 and R150 touch §§3.4-3.6 for other matters), and the reference writer's recipe.py still documents an `info` level for 'an override it will apply (Part 05 §3.5)'.

### 26. R129 §3.7 at Part 05 §14.3 (ew-reader-registry-independence)

- **The revision decides:** the failing reader MUST identify the missing support
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** Where a reader fails a resource for lack of support, it MUST identify the missing support.
- **Placement:** Part 05 §14.3 (ew-reader-registry-independence), after the last sentence
- **Risk:** No contradiction. R146 §3.7 quotes the paragraph's two sentences verbatim, so the duty is best added as a further sentence rather than by rewording those two. No part says how the support is identified and no checker can observe it, so it is an unchecked reader obligation.
- **Second reading:** R129 §3.7: 'the reader MUST fail that resource specifically and identify the missing support.' The first half is in Part 03 §6.1 ('MUST fail that resource specifically') and Part 05 §14.3 ('fails that resource alone where it lacks support'); the duty to identify what support is missing is in no part and never was (git log -S'identify the missing support' over the parts is empty). R146 §3.7 fixes the wording of the two sentences of Part 05 §14.3's last paragraph but neither states nor withdraws the identification duty, and R146 does not cite R129. Searched 'missing support', 'lacks support', 'identify', 'naming' near reader failure in Parts 03, 04 and 05; Part 04 §10's reader rule names a registry ID on a binding failure, which is a different failure.

### 27. R32 §4 at Part 05 §15.1 (ew-amendment-definition)

- **The revision decides:** `created_at` is the packet's creation and MUST be preserved by an amendment; `validation.validated_at` is replaced
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** `created_at` is the packet's creation: the amended manifest MUST carry the superseded manifest's `created_at` unchanged. Its validation block records the latest run and is replaced.
- **Placement:** Part 05 §15.1 (ew-amendment-definition), with the carry-over rule; the member's meaning could instead sit in Part 04 §3
- **Risk:** No contradiction. Part 05 §15.3's 'keeps its own `created_at`' reads slightly oddly once every version of a packet shares one creation time, but remains true. A replacement (Part 04 §3) is a different packet version line and is not bound by this. No checker compares `created_at` across versions, so the sentence would be an unchecked MUST unless `amendment.identity_changed` is extended, which is a separate decision.
- **Second reading:** R32 §4 says of the amended manifest that `created_at` is the packet's creation and MUST be preserved, while `validation.validated_at` is replaced. No part says what `created_at` means or what an amendment does with it. Part 04 §3 lists the member with its format only; Part 05 §11 mentions it as a reason builds are not byte-identical; Part 05 §15.3 ('A retained manifest keeps its own `created_at` and its own validation record, which a writer performing an amendment MUST NOT rewrite') is about the retained copy's bytes, the rule R146 §3.2 restates, and says nothing of the new manifest. The two rules are different and compatible. No later revision withdraws R32's: R61 supersedes R32 §4 only for retention. The reference writer still implements it (`escapewheel-writer/tests/test_amending.py` asserts the amended `created_at` equals the retained manifest's), so the rule is live and unstated. `amendment.identity_changed` does not compare `created_at`.

### 28. R61 §2.1 at Part 05 §15.5 (ew-packet-cleanup)

- **The revision decides:** A conforming implementation SHOULD offer cleanup over a committed packet
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A writer SHOULD offer cleanup over a committed packet.
- **Placement:** Part 05 §15.5 (ew-packet-cleanup)
- **Risk:** None found. Renamed term: R61's 'a conforming implementation' is 'a writer' under R111 §3.5 and Part 00 §2.4. The rest of R61 §2.1's lead sentence (the order, the stray) is already stated in the section.
- **Second reading:** R61 §2.1 opens with a keyword recommendation. R111 §3.5 assigns cleanup to the writer ('cleanup being a mutation of a packet whatever it is called'), R135 §3.5 narrows what a stray is, and R146 §3.2 moves the order and the stray protection to Part 05 §15.5 with a named actor; none withdraws the recommendation to offer the operation. Part 05 §15.5 says 'Cleanup is a separate operation' and binds only 'a writer performing cleanup'; Part 05 §11's acceptance criteria do not mention it; informative Part 07 lists the reference implementation's `prune`. Searched spec/parts for 'cleanup', 'prune', 'offer'.

## Part 12

### 29. R115 §3.3 at Part 12 §3 (ew-protocol-groups)

- **The revision decides:** a writer MUST NOT require any adapter to be importable in its own environment
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A writer MUST NOT require any adapter to be importable in its own environment, and a build MUST be able to reach one that is not.
- **Placement:** Part 12 §3 (ew-protocol-groups), ahead of the sentence on an adapter released independently of a build
- **Risk:** No contradiction found. It supplies the rule Part 12 §7 already cites ('which this part forbids requiring'). It must be read beside Part 05 §3.9, which has a build refuse where it cannot import an adapter the recipe opted into the writer's process, and R134 §3.5, which runs a shipped adapter that declares no protocol in process; both were compatible with the sentence in R115 itself (§3.5), since the opt-in is the recipe's and a shipped adapter is importable by construction.
- **Second reading:** R115 §3.3 opens 'A writer **MUST NOT** require any adapter to be importable in its own environment, and a build **MUST** be able to reach one that is not.' No part carries the prohibition. `git log -S'importable in its own'` finds it only in drafts, never in a part, so it was not incorporated at acceptance and nothing later removed it; R116, R117, R119, R133, R134 and R144 do not withdraw it. Part 12 §7 refers to it as though it were stated ('by importing the adapter — which this part forbids requiring'), but no sentence of Part 12 forbids it, so that reference dangles. The nearest statements only imply it: Part 12 §3 has a build support every protocol, Part 12 §7 has a build read the document of an adapter it cannot import, and Part 05 §3.9 has a build deliver out of process a source whose adapter declares a protocol. Part 09 §5.6's 'MUST NOT require the extension itself to be installed, importable, or resolvable' binds for an extension, not an adapter.

### 30. R115 §3.9 at Part 12 §3 (ew-protocol-groups)

- **The revision decides:** a writer SHOULD ship an implementation of each protocol its profile names, covering both ends, and whoever speaks one MAY use it rather than write their own
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A writer SHOULD ship an implementation of each protocol this profile names, covering both ends, and whoever speaks one — an adapter, or an extension delivering its rows over the same protocols — MAY use it rather than write their own.
- **Placement:** Part 12 §3 (ew-protocol-groups), as a closing paragraph; the ledger targets Part 12 §8 (ew-reaching-a-running-adapter), whose subject is the rendezvous
- **Risk:** None found. Part 07 §4 already describes the reference implementation doing so. Restore together with finding 104, which keeps the shipped implementation optional.
- **Second reading:** R115 §3.9: 'A writer **SHOULD** ship an implementation of each protocol its profile names, covering both ends, and **whoever speaks one MAY use it** rather than write their own'. No normative part states it. Part 12 §3 obliges a build to support every protocol, which is one end and a MUST about support; Part 12 §8, the ledger's target, carries only the retry rendezvous; Part 07 §4 (informative) says an independently released adapter names 'constants the implementation exports', which presupposes a shipped implementation without recommending one. `git log -S'SHOULD ship'` finds nothing in any part. The ledger note concedes the rule is 'Part 03's former section 11.1's group plus this', not a sentence. No later revision withdraws it.

### 31. R115 §3.9 at Part 12 §3 (ew-protocol-groups)

- **The revision decides:** a profile MUST NOT make using that implementation a condition of conformance, and a build MUST NOT refuse an adapter that speaks a protocol without it
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** This profile MUST NOT make using that implementation a condition of conformance, and a build MUST NOT refuse an adapter that speaks a protocol without it.
- **Placement:** Part 12 §3 (ew-protocol-groups), with finding 103's sentence
- **Risk:** None found. 'A profile' becomes 'this profile' because Part 12 is the profile's own part; no term is renamed.
- **Second reading:** R115 §3.9: 'A profile **MUST NOT** make using it a condition of conformance, and a build **MUST NOT** refuse an adapter that speaks a protocol without it.' No part states either prohibition. Part 12 §3 defines what a build must support and what it must refuse, and nowhere forbids a refusal on this ground; Part 09 §5.6 forbids requiring an extension's code, not requiring the writer's protocol implementation of an adapter. `git log -S'condition of conformance'` finds the phrase only in the draft and the ledger note. No later revision withdraws it.

### 32. R115 §3.7 at Part 12 §5 (ew-referenced-resource-delivery)

- **The revision decides:** a writer SHOULD report what resolving those names cost, as a figure of its own rather than as a comparison
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A writer SHOULD report what resolving those names cost, as a figure of its own rather than as a comparison: a build that received rows out of process never staged them the other way and has no baseline to subtract.
- **Placement:** Part 12 §5 (ew-referenced-resource-delivery), after the sentence on identifiers crossing as names
- **Risk:** None found. Part 12 otherwise names 'a build' where R115 says 'a writer'; the two are the same actor's roles and the clause's own word is 'writer'.
- **Second reading:** R115 §3.7: 'A writer **SHOULD** report what resolving those names cost, as a figure of its own rather than as a comparison'. No part states it. Part 12 §5 (ew-referenced-resource-delivery) carries the clause's first rule ('An adapter MUST hand over identifiers as the names its source used and never as numbers') and nothing on reporting the cost; Part 05 §4.3, Part 09 §5.7 and every 'SHOULD report' in Parts 01-05 and 12 concern other subjects. `git log -S'resolving those names'` finds the sentence in drafts only. R109 §3.2, which the clause extends to adapters, has no such recommendation, so it restates nothing. No later revision withdraws it.

### 33. R115 §3.11 at Part 12 §9 (ew-adapter-run-report)

- **The revision decides:** an adapter MAY attach one `problems` entry to a failing `flight-v0.1` call in the error's `extra_info`
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** Under `flight-v0.1` an adapter MAY attach one `problems` entry to a failing call, in the error's detail.
- **Placement:** Part 12 §9 (ew-adapter-run-report), after the paragraph on which channel carries a report
- **Risk:** No contradiction. `extra_info` is the name one Arrow binding gives the field, which may be why the parts say 'detail'; the restored text should keep the parts' word and say how the entry is encoded (R115 measured a JSON entry of 125 bytes). The parts specify `flight-v0.1` thinly (Part 12 §§3, 8, 9), so this sentence would be more specific than its surroundings. It should be restored together with finding 97, which is what makes the entry optional for a build.
- **Second reading:** R115 §3.11 says 'An adapter MAY attach one finding to the failing call': a Flight error carrying one `problems` entry in `extra_info`. No part grants it. Part 12 §3's table says a `flight-v0.1` failure's diagnosis travels on 'the error's message and detail', and Part 05 §4.4 has a build report 'everything the protocol it used carries about a failure'; neither says the detail may hold a `problems` entry, and Part 12 §9 defines `problems` only as a member of the report. `extra_info` has never appeared under spec/ (git log -S finds no commit), and among accepted revisions only R115 uses it; R116, R134, R144 and R146 do not withdraw it. The permission is one that would otherwise be uncertain, since nothing else tells a build that the detail has a shape. Renamed term: the parts call `extra_info` the error's 'detail'. Not refuted.

### 34. R115 §3.11 at Part 12 §9 (ew-adapter-run-report)

- **The revision decides:** a build MUST NOT refuse a failure whose `extra_info` it cannot parse, and reports the message alone
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A build MUST NOT refuse a failure whose detail it cannot parse, and reports the message alone.
- **Placement:** Part 12 §9 (ew-adapter-run-report), with finding 96's sentence
- **Risk:** No contradiction, but it has meaning only once finding 96's permission is stated, since until then the parts give the detail no structure to parse. 'Refuse a failure' is R115's wording for treating the unparseable detail as a further error; the restored sentence would be clearer as 'MUST NOT fail on' it, parallel to §9's rule for a report. Its second half ('reports the message alone') has no keyword in the clause.
- **Second reading:** R115 §3.11 says 'A build **MUST NOT** refuse a failure whose `extra_info` it cannot parse, and reports the message alone'. No part states it: Part 05 §4.4's only unparseable case is a delivery ('A build MUST report a delivery it cannot parse as a failure'), Part 12 §9's tolerance rule is for a report ('MUST NOT refuse a report for carrying keys it does not recognise'), and Part 12 §3 says only that the diagnosis is the error's message and detail. Neither term has appeared under spec/, and no later revision withdraws the rule. It is not entailed by 'A build MUST report everything the protocol it used carries', which says nothing of a detail that fails to parse. Renamed term: `extra_info` is the error's 'detail' in the parts. Not refuted.

### 35. R115 §3.11 at Part 12 §9 (ew-adapter-run-report)

- **The revision decides:** a build MUST ignore `app_metadata` on `FlightInfo`, which carries no finding
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** `flight-v0.1` names no meaning for the `app_metadata` field of a `FlightInfo`, and a build MUST ignore it.
- **Placement:** Part 12 §9 (ew-adapter-run-report), with findings 96 and 97; or Part 12 §3's `flight-v0.1` row
- **Risk:** No contradiction. The parts never describe the listing a build asks a `flight-v0.1` adapter for (Part 12 §8 mentions `ListFlights` once; Part 05 §4.4 mentions a declared row count), so the sentence needs a line of context about that listing to land on, or it names a field of a message the part has not introduced.
- **Second reading:** R115 §3.11 says 'A build **MUST** ignore `app_metadata`, which leaves the field to a later version of the protocol'. Neither `app_metadata` nor `FlightInfo` occurs under spec/ and neither ever has (git log -S finds no commit); among accepted revisions only R115 names them, and R116, R134, R144 and R146 do not withdraw the rule. Part 12 §3 says a protocol's meaning is fixed by its name and version, but nothing tells a build what to do with a field the protocol gives no meaning, and Part 05 §4.4's 'report everything the protocol it used carries about a failure' could be read to reach it. Not refuted.
