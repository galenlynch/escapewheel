# Audit of the ledger's applied targets

The clause ledger, `revisions/applied.toml`, records where each `applied` Decision clause of an
accepted revision is now stated. The ledger check resolves each target and reads no text inside it,
so a clause can be recorded at a section that does not state it. This audit reads every applied
target against its section once. It adds no field to the ledger and no check to the tools: a finding
is repaired where it lies, in the part or in the ledger entry.

Each table lists what the audit found at commit `072f3d8b`. The 56 class A and B rules were restored
on 2026-10-01 and the two class F rules were noted in the ledger; nothing else below has been
repaired. Every other class has since had a critical reading, summarised under
"The remaining classes after a critical reading".

## Method

Each applied clause is split into its rules, and each rule is given one status:

| status | meaning |
|---|---|
| stated | a target of the clause states the rule with the same force and scope |
| stated elsewhere | a part states it, in a section the ledger does not name for the clause |
| weakened | a part states it with different force or narrower scope, and no later revision accounts for the difference |
| changed by a later revision | a later accepted revision replaced, withdrew or amended the rule |
| registry | the registry carries the rule as an exact declaration |
| missing | no part states it and no later revision accounts for its absence |

A first reader gave every rule a status and quoted the passage it relied on; each quote was then
found verbatim in the parts by a script. A second reader took every `weakened` and `missing` rule
and tried to refute it: as rationale and no rule, as changed by a later revision, as stated in other
words, or as carried by an incorporated artifact. A rule the second reader could not refute is
*confirmed*. Where two careful readings of the clause disagree, the rule is *disputed*. A keyword
binds only in capitals (Part 00 §2.5), so a normative part that restates a MUST in the indicative
has weakened it. Parts 07 and 10 are informative and cannot weaken a rule.

## Result of the full reading, 2026-10-01

The 501 applied clauses hold 2,634 rules.

| first reading | rules |
|---|---:|
| stated | 1,887 |
| stated elsewhere | 217 |
| changed by a later revision | 211 |
| registry | 125 |
| weakened | 113 |
| missing | 77 |
| not a rule | 4 |

The second reading took the 190 weakened and missing rules.

| second reading | rules |
|---|---:|
| confirmed | 111 |
| disputed | 21 |
| stated after all | 20 |
| not a rule | 18 |
| carried by an incorporated artifact or a process tool | 13 |
| changed by a later revision | 7 |

The 111 confirmed rules come from 73 clauses of 44 revisions: 48 from revisions below R100, 20 from
R100 to R124, 42 from R125 to R129, and 1 from R130 onward.

## Confirmed rules the parts no longer state

Each row is one rule of an accepted revision that no part states with the revision's force. The
class says what kind of repair the rule needs.

| class | rules | meaning |
|---|---:|---|
| A | 27 | The sentence is absent, and restoring it survived a third reading. |
| B | 29 | The sentence is present with a weaker keyword, no keyword, or a narrower scope, and restoring its force survived a third reading. |
| C | 22 | The sentence is present in the indicative, in a section that states every rule in the indicative: Part 05 §14.1 to Part 05 §14.6 (17 rules) and Part 11 §2 to Part 11 §4 (5 rules). |
| D | 31 | Restoring the revision's words would meet a later text, an unanswered question, a rule no named actor can follow, or behaviour the reference implementation does not have. |
| F | 2 | Other sentences already carry the rule with force, so the part should not state it again. |

The 72 rules first classed A or B had a third reading, which tried to show each restoration to be a
mistake. It tested whether a later revision changed the rule, whether the text contradicts or
exceeds anything, whether it names an actor who can comply, whether a check observes it, whether it
sits in the part that owns it, and whether the reference implementation and the corpus comply. Ten
restorations passed as first worded and 46 passed with different wording, actor, scope or placement.
Fourteen were referred to class D and two to class F. Classes C and D have had no third reading.

Of the 56 class A and B rules, 32 are requirements no check observes, 28 of them a MUST or
MUST NOT; each binds a named actor who can comply.

### The class A and B restorations

The 56 rules were entered one commit per part, `96c0bbcd` (Parts 00 and 01), `09f65ce4` (Part 02),
`f2362e21` (Parts 03 and 06), `5ee501c1` (Part 04), `da6d491d` (Part 05) and `ef5190df` (Part 12),
with `bccc6b75` adding one label. Each clause's ledger entry carries a `restored 2026-10-01` note,
and eight entries gained or changed a target for the section the sentence landed in: R38 §2.3,
R91 §3.3, R128 §3.4, R14 §2.3.2, R128 §3.8, R32 §4, R115 §3.1 and R115 §3.9.

The entered text is the third reading's, with these departures:

- R37 §3.1 and R27 §5.3: the extrapolation formula and the two prohibitions form one paragraph of
  Part 01 §3.9.
- R70 §2.2: the sentence closes the rate paragraph of Part 01 §3.18, so the consumer permission
  before it keeps its antecedent.
- R22 §3: the two label obligations share one closing sentence saying no checker verifies either.
- R37 §3.2: the recommendation to run the terminal-anchor test states the clause's reason.
- R80 §2.1: the source-name recommendation is the clause's own words, without the added gloss.
- R128 §3.8 in Part 12 §5: the sentence after it names the document as what the schema shapes.
- R115 §3.11 and R80 §2.2: each carries an unchecked label the third reading's text lacked.

A requirement a writer, a build or a reader cannot be observed to meet says that no checker
verifies it. Ten restored requirements no check observes carry no such sentence, as the third
reading advised: seven consumer prohibitions in Part 01 (R45 §2.1, R85 §2.3, R27 §5.3, R37 §3.1
twice, R68 §2.5, R69 §2.2), where no consumer rule of the part is labelled; R122 §3.8 in Part 00
§2.1, a property of the specification; and the two validator rules of R36 §2.3 in Part 04 §5.3,
which a validator's own suite can test. Four more are recommendations (R37 §3.2, R14 §2.3.2,
R80 §2.1 and R61 §2.1), which take no label.

The third reading named work the restorations leave open: a writer test that a build ignores a
listing's `app_metadata` (R115 §3.11) and a reader test that a failure names the unsupported
version or feature (R129 §3.7); the writer recording `false` on a clock too short for the
terminal-anchor test, where null is called for (R37 §3.2); and whether Part 02 §9.4's
document-level precedence sentence takes a keyword beside the restored phase rule (R126 §3.3).
Each open draft's freshness gate reads sections these commits changed and is rerun before
acceptance.

The `repairs/` directory beside this file holds one file per class, with each rule's current text,
the text to enter, its placement and the evaluation, and a file for the disputed rules. The class D
table below covers the 17 rules first classed D; `repairs/D2-referred-from-A-and-B.md` states the
choice for each of the 14 referred later.

### What each class D rule meets

| clause | section | what restoring it meets |
|---|---|---|
| R3 §3.0 | Part 02 §5.2 | The clause keys a child table on the parent's key plus the value. Three core child tables are keyed on a position or a qualifier instead. |
| R3 §3.4 | the core registry | The clause replaced `core.clocks.transform_to_parent` with typed columns, and the registry still declares the replaced column. Removing it changes the registry and its version. |
| R57 §2.1 | Part 02 §9.2 | A writer SHOULD emit `$schema` first. A checker now decodes the whole document before it reads the key, so the recommendation serves only a person reading the head of the file. |
| R81 §2.5 (2 rules) | Part 02 §12.1 | A consumer relates a unit outside the packet by `(sorting_run_id, local_unit_label)`, and `sorting_run_id` is itself packet-assigned. R123 §3.1 states the prohibition in safer words. |
| R123 §3.1 | Part 02 §12.1 | The same relation: where labels tie or are null it does not identify every unit. |
| R91 §3.3 | Part 01 §3.12 | A stream whose events carry marks MUST name a table through `detail_kind`, and the same clause keeps `core.events.payload` as a home for a per-event value. |
| R102 §3.1 | Part 01 §3.17 | An array a run produced MUST name that run, and a packet that records no provenance is conforming. |
| R102 §3.2 | Part 01 §3.18 | A writer MUST name the device where its source states one. The part says SHOULD, "as an array asset does", and the array-asset rule is a SHOULD. |
| R107 §3.4 | Part 02 §9.3 | `tables.md` MUST render every declaration a column carries. The file is an informative projection, so the MUST binds no actor the specification names. |
| R108 §3.3 | Part 05 §3.4 | An `[overrides]` entry naming a fact MUST silence the discarded-fact refusal. The part does not say how an entry keyed by block and field names a discarded column. |
| R111 §3.3 (2 rules) | Part 00 §2.4 | Two drafting rules bind whoever writes the specification, who is none of its five actors. |
| R126 §3.9 | Part 02 §9.4 | A checker without the exact domain MUST report the phase as unsupported, and Part 02 assigns no outcome identifier for a missing domain. |
| R128 §3.7 | Part 02 §2.7 | A reader MUST expose the resolved policy and content class, and later texts have a reader fail the operation where the declaration does not resolve. |
| R129 §3.1 | Part 03 §1 | A generic checker MUST NOT embed this profile's identifiers: a rule about how a checker is built, which no test of one profile observes. |
| R147 §3.3 | Part 02 §8.3 | The lead-in governs six generated checks whose own clauses differ in force, so one MUST over the table raises three of them. |

### The confirmed rules

| clause | section | found | class | rule as the revision states it |
|---|---|---|---|---|
| R2 §5 | the core registry | weakened | D | a reader MUST tolerate an absent `optional` column |
| R3 §3.0 | Part 02 §5.2 | weakened | D | multiplicity rule: a field that is zero or more X MUST be a child table keyed on the parent's primary key plus the value; never a list, a delimited string or JSON |
| R3 §3.4 | the core registry | missing | D | `core.clocks.transform_to_parent` is replaced by the typed columns |
| R3 §5.1 | Part 03 §6.2 | weakened | B | readers MUST NOT assume their language presents axes in declared order; a column-major binding enumerates them in reverse |
| R6 §2 | Part 01 §3.9 | missing | A | where present, the wall-clock time of any tick is `tick_zero_utc + t_tick / effective_tick_rate`, using `tick_rate_hz` or `tick_rate_num / tick_rate_den` |
| R8 §3 | Part 02 §9.3 | missing | A | the three values carry declared meanings: `succeeded` completed with usable outputs, `failed` did not complete, `partial` completed for some inputs only so committed outputs are incomplete |
| R14 §2.3.2 | Part 04 §5.1 | missing | A | a writer SHOULD prefer to own core tables where their size permits |
| R22 §3 | Part 02 §9.3 | weakened | B | `label` MUST be recorded as the source emitted it; a writer MUST NOT rewrite it onto the normalized set |
| R22 §3 | Part 02 §9.3 | weakened | B | where a source's label has no honest projection, `normalized_label` MUST be null rather than forced |
| R26 §3 | Part 02 §10.2 | weakened | B | an advisory rule MUST NOT run unless the caller asks for it |
| R27 §5.3 | Part 01 §3.9 | missing | A | between two anchors separated by at most 2m (m the clock's median anchor interval) the mapping is linear interpolation on the bracketing pair |
| R27 §5.3 | Part 01 §3.9 | missing | A | beyond the terminal anchors a consumer MUST use the rate fitted over the clock's full anchor sequence and MUST NOT extend the terminal segment's slope |
| R27 §5.3 | Part 01 §3.9 | missing | A | the bound applies per edge of the parent chain, each edge against its own m |
| R30 §4 | the core registry | weakened | B | a consumer MUST NOT assume the two tables are row-aligned or that a count from one applies to the other |
| R32 §4 | Part 05 §15.1 | weakened | D | the amended manifest MUST be derived from the superseded one: every packet-level field the amendment does not change MUST carry over unchanged |
| R32 §4 | Part 05 §15.1 | missing | A | `created_at` is the packet's creation and MUST be preserved by an amendment; `validation.validated_at` is replaced |
| R35 §5 | Part 05 §15.4 | weakened | D | a check meeting neither condition MAY be skipped |
| R36 §2.3 | Part 04 §5.3 | weakened | B | level 3a establishes that the URI resolves, that `size_bytes` holds, and that the declared `codecs` match the metadata document |
| R36 §2.3 | Part 04 §5.3 | missing | A | a validator offering level 3 MUST offer 3a and MAY offer 3b |
| R36 §2.3 | Part 04 §5.3 | weakened | B | a validator MUST NOT run the digest level unless separately asked |
| R37 §3.1 | Part 01 §3.9 | missing | A | beyond the terminal anchors a consumer MUST compute parent(t) = parent(a) + rate * (t - a), with `a` the nearest terminal anchor and `rate` fitted over that clock's anchors |
| R37 §3.1 | Part 01 §3.9 | missing | A | a consumer MUST NOT use the intercept of a fit over the whole anchor sequence |
| R37 §3.2 | Part 02 §12.6 | missing | D | a writer MUST NOT emit an anchor whose parent tick it has reason to believe is misplaced |
| R37 §3.2 | Part 02 §12.6 | missing | A | a writer SHOULD test each terminal anchor by predicting it from a fit over its neighbours and comparing the residual with the distribution of the same residual over that clock's interior anchors |
| R38 §2.3 | Part 01 §2.3 | missing | A | a clock's own interval is not derived from what it recorded either: it is the extent of the acquisition |
| R45 §2.1 | Part 01 §2.3 | weakened | B | a consumer MUST NOT treat a stop_tick as excluded |
| R51 §2.4 | Part 04 §5.4 | weakened | B | A validator that skipped every member because none recorded a store_digest reports that it verified nothing, not that everything passed |
| R52 §2.3 | Part 04 §5.3 | missing | A | A disagreement on a packet-owned resource's digest is reported as an error, not a warning |
| R57 §2.1 | Part 02 §9.2 | missing | D | A writer SHOULD emit `$schema` first |
| R61 §2.1 | Part 05 §15.5 | missing | A | A conforming implementation SHOULD offer cleanup over a committed packet |
| R61 §2.1 | Part 05 §15.5 | weakened | B | Cleanup MUST default to reporting what it would remove without removing it |
| R68 §2.5 | Part 01 §3.18 | weakened | B | A consumer MUST NOT use pts to measure elapsed time or to align a frame to anything else in the packet |
| R69 §2.2 | Part 01 §3.18 | weakened | B | a consumer MUST NOT read frame_index as a count of exposures, a camera's own frame counter, or an offset into anything but this asset |
| R70 §2.2 | Part 01 §3.18 | missing | A | a writer MUST declare neither rate column where it wrote no pts |
| R80 §2.1 | Part 04 §5.5 | weakened | D | an external resource entry SHOULD carry source, naming the body of data it belongs to, where its bytes belong to a nameable one |
| R80 §2.1 | Part 04 §5.5 | weakened | B | where source is present the entry's uri MUST be a path relative to the source and MUST NOT be absolute |
| R80 §2.1 | Part 04 §5.5 | missing | A | a source name SHOULD be unique beyond the packet, so one resolution document serves many packets |
| R80 §2.2 | Part 04 §5.5 | missing | A | a reader MUST NOT dereference the document's $schema |
| R80 §2.3 | Part 04 §5.5 | weakened | B | a writer SHOULD write sources.json at the packet root, naming every source the packet references and where it read each one |
| R80 §2.3 | Part 04 §5.5 | missing | A | a reader MUST NOT infer that the packet vouches for what the default document says |
| R81 §2.5 | Part 02 §12.1 | weakened | D | a consumer relating a unit to anything outside the packet MUST use (sorting_run_id, local_unit_label) |
| R81 §2.5 | Part 02 §12.1 | missing | D | a consumer MUST NOT use unit_id to relate a unit to anything outside the packet |
| R82 §2.3 | Part 05 §12 | weakened | B | a consumer that meets an unresolved alternative is holding a packet that failed validation and MUST report that |
| R85 §2.3 | Part 01 §3.5 | weakened | B | a consumer MUST NOT read two rows sharing a parent and a port as one device |
| R87 §2.3 | Part 05 §3.5 | missing | A | a field an override covers is reported as information, so the log lists every place the recipe corrects a source |
| R88 §2.4 | Part 02 §7.1 | missing | D | every dependent row (a sorting run, a curation version, a coordinate, a run input) references the copy of the run for its own session |
| R91 §3.3 | Part 01 §3.12 | weakened | D | a stream whose events carry marks MUST name the table holding them through detail_kind |
| R91 §3.3 | Part 02 §8.6 | missing | A | a writer MUST NOT put a mark in core.events.metadata |
| R101 §3.9 | Part 02 §9.3 | missing | D | a writer MUST map the source's spelling onto one of the four values |
| R102 §3.1 | Part 01 §3.17 | missing | D | an array a run produced MUST name that run; an acquired array declares none |
| R102 §3.2 | Part 01 §3.18 | weakened | D | a writer MUST name the device where its source states one |
| R105 §3.4 | Part 01 §3.24 | missing | A | an axis's `unit` MUST be declared |
| R107 §3.4 | Part 02 §9.3 | weakened | D | tables.md MUST render every declaration a column carries: its vocabulary, the closed set, its reserved values, its authorities by name, and a discriminator's `resolves`, generated from the fields |
| R108 §3.3 | Part 05 §3.4 | weakened | D | an `[overrides]` entry naming a fact MUST silence the discarded-fact refusal for that fact |
| R111 §3.3 | Part 00 §2.4 | missing | D | a clause stating a property of an artifact MUST name the part of the artifact it constrains |
| R111 §3.3 | Part 00 §2.4 | missing | D | a clause stating a property of an artifact MUST put the constraint in an active verb |
| R115 §3.1 | the core registry | weakened | B | an adapter MUST declare the kinds whose output it reads, which orders a build |
| R115 §3.10 | Part 05 §4.4 | weakened | D | a build MUST refuse where a resource of the set did not arrive or the process did not exit clean |
| R115 §3.11 | the core registry | missing | D | an adapter MAY attach one `problems` entry to a failing `flight-v0.1` call in the error's `extra_info` |
| R115 §3.11 | the core registry | missing | D | a build MUST NOT refuse a failure whose `extra_info` it cannot parse, and reports the message alone |
| R115 §3.11 | the core registry | missing | A | a build MUST ignore `app_metadata` on `FlightInfo`, which carries no finding |
| R115 §3.3 | the core registry | missing | A | a writer MUST NOT require any adapter to be importable in its own environment |
| R115 §3.4 | Part 05 §3.7 | weakened | B | a build MUST consume standard output and standard error concurrently |
| R115 §3.7 | the core registry | missing | D | a writer SHOULD report what resolving those names cost, as a figure of its own rather than as a comparison |
| R115 §3.9 | the core registry | missing | D | a writer SHOULD ship an implementation of each protocol its profile names, covering both ends, and whoever speaks one MAY use it rather than write their own |
| R115 §3.9 | the core registry | missing | A | a profile MUST NOT make using that implementation a condition of conformance, and a build MUST NOT refuse an adapter that speaks a protocol without it |
| R122 §3.8 | Part 00 §2.1 | weakened | B | the numbered part set MUST remain intelligible without repository-specific developer documentation |
| R123 §3.1 | Part 02 §12.1 | weakened | D | outside the packet, a consumer MUST use the source-facing relation Part 02 §12.1 defines rather than treating the packet-assigned number as globally stable |
| R125 §3.2 | the core registry | weakened | C | `ABS`, `MIN`, `MAX`, and `LAG` MUST return their argument's domain; `COALESCE` its arguments' common domain; `CAST` its target domain; `COUNT`, `ROW_NUMBER`, and `DENSE_RANK` `BIGINT`; `PERCENTILE_CONT` `DOUBLE PRECISION`; a comparison, predicate, Boolean operator, `isnan`, or `isfinite` `BOOLEAN` |
| R125 §3.3 | the core registry | weakened | C | each visible registry table MUST expose exactly its declared columns under the type mapping |
| R125 §3.3 | the core registry | weakened | C | a resource absent from the packet MUST bind as an empty relation with that declared shape |
| R125 §3.4 | the core registry | weakened | C | every exact-to-approximate conversion MUST use round-to-nearest, ties-to-even |
| R125 §3.4 | the core registry | weakened | C | an integer, scale-zero decimal or other exact-decimal literal MUST compare with an exact-decimal literal by mathematical value without rounding |
| R126 §3.3 | Part 02 §9.4 | weakened | B | the same precedence MUST determine a partially evaluated phase's state from its outcome records |
| R126 §3.9 | Part 02 §9.4 | missing | D | a checker without the exact required domain MUST report the external-domain phase as unsupported rather than accept a printable approximation |
| R127 §3.2 | Part 05 §14.1 | weakened | C | an implementation authorized by a valid result to produce packet bytes or registry-derived checks MUST use the decoded document in the same checked context, not reread the source or use the caller's mapping |
| R127 §3.3 | Part 05 §14.2 | weakened | C | when the implementation owns the source bytes it MUST use the byte-oriented entry point |
| R127 §3.3 | Part 05 §14.2 | weakened | C | when given only an already-decoded mapping it MUST use the mapping-oriented entry point |
| R127 §3.3 | Part 05 §14.2 | weakened | C | a low-level generator accepting a registry document directly MUST either establish the checked registry context itself or require one from its caller |
| R127 §3.5 | Part 05 §14.4 | weakened | C | an implementation publishing or releasing a registry or generating registry-derived conformance checks MUST complete that operation only when the result is valid |
| R127 §3.5 | Part 05 §14.4 | weakened | C | an implementation checking a registry for an extension author MUST report success only when the result is valid |
| R127 §3.5 | Part 05 §14.4 | weakened | C | for any other state the implementation MUST stop the requested production or publication and expose the complete result to its caller |
| R127 §3.5 | Part 05 §14.4 | weakened | C | a writer MUST reject a non-valid registry before opening any source or staging any output |
| R127 §3.5 | Part 05 §14.4 | weakened | C | a public writer constructor accepting mappings MAY keep that input form but MUST copy and check the mappings before retaining or interpreting them |
| R127 §3.5 | Part 05 §14.4 | weakened | C | an adapter acquires no registry authority from this process and MUST NOT be opened after the writer has rejected a registry |
| R127 §3.5 | Part 05 §14.4 | weakened | C | an exception used to report rejection MUST make the complete portable result retrievable as structured data |
| R127 §3.5 | Part 05 §14.4 | weakened | C | a command-line tool MUST offer machine-readable output containing that result |
| R127 §3.6 | Part 05 §14.5 | weakened | C | the validator MUST identify which checked core context directs packet checks and MUST use that context for every extension evaluation |
| R127 §3.6 | Part 05 §14.5 | weakened | C | for a non-valid result the validator MUST retain the complete registry result in its report, skip every dependent packet check, and preserve invalid outcomes as registry-document findings |
| R127 §3.7 | Part 05 §14.6 | weakened | C | a report MUST pair each registry result with an external subject label identifying the registry role evaluated |
| R127 §3.7 | Part 05 §14.6 | weakened | C | the subject label MUST NOT replace or manufacture the registry document's own identity |
| R127 §3.7 | Part 05 §14.6 | weakened | C | public checking APIs, machine-readable command output, validation reports and structured exceptions MUST expose the same result representation without reducing it to a Boolean or a list of invalid findings |
| R128 §3.3 | Part 02 §2.3 | weakened | B | a dense-array declaration's `axes_resource` MUST name a visible singleton table declaration |
| R128 §3.4 | Part 02 §2.6 | weakened | B | a catalog declaration's `catalog_resource` MUST resolve to a singleton table declaration visible to that registry |
| R128 §3.4 | Part 02 §2.6 | weakened | B | `resource_id_column` MUST name a required string column with role `identifier`, identity `carried`, and free vocabulary |
| R128 §3.5 | Part 02 §2.5 | weakened | B | `analysis`, `compatibility_projection`, and `documentation` declarations MUST be optional |
| R128 §3.7 | Part 02 §2.7 | weakened | D | a reader MUST expose the resolved policy and content class without requiring a validation receipt for ordinary access |
| R128 §3.8 | the core registry | weakened | B | a writer MUST preserve the delivered declaration binding when it creates the packet entry and MUST reject a document whose binding does not resolve or does not admit the resource ID |
| R128 §3.8 | the core registry | weakened | B | a packet resource's validation state MUST NOT change its declaration-derived content class or canonicality |
| R129 §3.1 | the core registry | weakened | D | a generic profile checker MUST enforce those invariants without embedding this profile's identifiers or assignments |
| R129 §3.1 | the core registry | missing | A | the generic checker MUST require every listed anchor to resolve uniquely in Part 03 to the clause that defines the entry's meaning |
| R129 §3.11 | Part 03 §6.5 | weakened | F | those physical facts MUST NOT be duplicated merely to make physical validation possible |
| R129 §3.3 | Part 03 §5.1 | weakened | D | a writer MUST NOT emit such a table, and a validator that can inspect the resource MUST reject one |
| R129 §3.4 | Part 03 §6.1 | weakened | D | a reader or validator MUST determine the variant from the Zarr metadata's `zarr_format` when it accesses or physically assesses the resource |
| R129 §3.4 | Part 03 §6.4 | weakened | B | a conforming reader MUST expose logical dense-array values for every valid v2 resource whose metadata matches a floor pattern |
| R129 §3.5 | the core registry | missing | A | an implementation MAY support additional upstream features without changing the descriptor or packet |
| R129 §3.7 | Part 05 §14.3 | missing | A | the failing reader MUST identify the missing support |
| R129 §3.9 | the core registry | weakened | B | lack of a recognized payload format or specialized decoder MUST NOT by itself invalidate the resource |
| R129 §3.9 | the core registry | weakened | B | a generic reader MUST resolve and list an opaque resource and expose its catalog identity and location |
| R129 §3.9 | the core registry | missing | F | a specialized implementation MAY expose members, objects, bytes, parsing, rendering, or other representation-aware operations without changing the resource's logical kind or the reader floor |
| R147 §3.3 | Part 02 §8.3 | weakened | D | where `resolves` is `required`, a validator MUST generate for a paired-value discriminator, beside the forward anti-join, three checks at error over the kinds the packet's rows name: a key-form check built from the registry's key declarations as literals, a per-kind anti-join on non-null paired values, and, where the paired value is on the specialised table, a check returning every specialised row whose discriminator is null |

## Disputed rules

Two readings of each clause below disagree on whether a part still owes the rule. One of them, on byte order
(R3 §7.1), is the subject of an open draft.

| clause | found | rule as the revision states it |
|---|---|---|
| R3 §2.1 | weakened | wall-clock and calendar columns are disjoint from experimental time and the two MUST NOT be mixed: a `*_tick` column has no timezone, epoch or calendar semantics, nothing that aligns data uses a timestamp, and nothing administrative uses a tick |
| R3 §7.1 | missing | arrays MUST be little-endian (the `bytes` codec's `endian` configuration) |
| R14 §2.3.2 | weakened | a validator MUST offer a separate, explicitly requested mode that resolves external URIs and checks `sha256` and `size_bytes` where declared |
| R51 §2.1 | missing | Declaring members makes the listing level (3a) compare each member's size rather than the aggregate |
| R65 §2.2 | weakened | This standard MUST NOT enumerate instruments |
| R65 §2.3 | weakened | A consumer MUST NOT infer an instrument from an asset's semantic_type, its name, or its URI |
| R80 §2.3 | missing | it MUST be stated that the packet's recorded checksums do not cover the default document |
| R93 §3.1 | weakened | Part 02 MUST NOT name a storage technology, a file format, an encoding, or a physical property of a stored resource, except to place such a rule outside its own scope |
| R93 §3.5 | missing | Part 10 does not absorb Part 07's performance notes and MUST NOT repeat them |
| R111 §3.3 | weakened | every MUST, MUST NOT, SHOULD, SHOULD NOT and MAY in the specification MUST either bind a named actor or state a property of an artifact |
| R111 §3.5 | weakened | a carried identifier gets no name column, and a table MUST NOT declare one for it |
| R120 §3.2 | weakened | the withdrawn records require no domain interpretation and remain unchanged |
| R120 §3.3 | weakened | its Scope identifies it as a structural reorganization and explains why append-only placement would impair the specification |
| R120 §3.4 | weakened | an alias does not imply that every former statement remains at that destination |
| R125 §3.11 | missing | such a validator MUST disable external state and side effects defensively |
| R125 §3.2 | weakened | an ISO feature identifier in `iso_feature_dependencies` identifies a definition the profile depends on; it is not a claim of full ISO conformance, does not permit every form the feature covers, and does not permit syntax by itself; the complete permission and semantic boundary is the cited Part 11 clause set |
| R126 §3.1 | missing | the core specification MUST NOT incorporate a concrete extension registry or list one as a member of the core specification candidate |
| R127 §3.6 | weakened | where the core result is not valid, the validator MUST still evaluate each available extension as far as Part 02 permits and preserve the resulting state |
| R129 §3.10 | missing | a view created by a reader or analysis system over packet resources is an operation and MUST NOT be treated as an independently declared packet resource merely because the operation exists |
| R129 §3.2 | weakened | the descriptor's interface names are the exact vocabulary for this profile; an implementation MUST NOT substitute an unincorporated name |
| R129 §3.8 | weakened | it MUST compare those observations with a descriptor that has passed the schema and generic checker, rather than with a packet claim or a local duplicate floor constant |

## Rules a process tool enforces and the revision guide does not state

Six rules of R120 bind a process tool, and the tool carries each one: `stages.py`,
`check_citations.py`, `ledger.py`, `evidence.py` and `headings.py`. The revision guide states none
of them as a rule. The second reading counted them as carried.

| clause | rule |
|---|---|
| R120 §3.2 | `stages.py` rejects an absent or unknown domain where the prospective rule applies and accepts the legacy default only for older accepted records |
| R120 §3.4 | a process section named by an `Amends` target, ledger destination, evidence owner or current citation uses the canonical raw-HTML anchor form |
| R120 §3.6 | the citation checker verifies that the displayed number agrees with the anchor's current heading |
| R120 §3.6 | the citation checker normalizes the resolved link to a canonical repository-relative target |
| R120 §3.7 | the ledger and evidence checker resolve each anchor before applying destination checks |
| R120 §3.7 | mechanical verification rejects a malformed or duplicate anchor, a vanished canonical anchor, and an anchor record that disagrees with its heading |

## Clauses recorded as applied that no target states

Twelve `applied` clauses have no target that states any of their rules, and no other section states
one either. Their disposition is wrong, and not only their target.

| clause | what became of its rules | disposition the reading supports |
|---|---|---|
| R15 §3 | R129 §3.6 retired `required_codecs` and R129 §3.7 replaced the reader rule | superseded by R129 |
| R79 §2.3 | R130 §3.7 withdrew the obligation on an analysis resource to name a run | superseded by R130 |
| R107 §3.1 | R126 §3.8 replaced the ban on restating a declaration with a ban on contradicting one | superseded by R126 |
| R148 §3.4 | R149, R150, R151 and R152 each advanced the registry version again | superseded by R149 |
| R151 §3.2 | R152 §3.4 advanced the registry version again | superseded by R152 |
| R57 §2.1 | R126 made `$schema` required; the recommendation to emit it first is in no part | superseded by R126, with one rule confirmed missing |
| R22 §4 | one registry rule on `core.unit_quality_labels` carries it | registry |
| R27 §3 | `core.clocks.parent_chain_well_founded` carries it | registry |
| R30 §3.1 | the registry carries the column and its partition rules; R130 §3.7 changed the bucket-width rule | registry |
| R41 §2.3 | the registry declares `core.preferred_runs`; R49 §2.3 changed its key | registry |
| R102 §3.1 | the registry declares the column; R130 §3.7 removed the manifest member; the MUST is confirmed missing | registry, with one rule confirmed missing |
| R37 §3.1 | both rules are confirmed missing from Part 01 §3.9 | applied, once restored |

## Ledger targets

The 217 rules stated elsewhere, and the 58 targets that state none of their clause, are listed by
clause in [applied-target-pointers.md](applied-target-pointers.md).

## The remaining classes after a critical reading

The reading that passed the 56 restorations was then given to everything else: the 22 class C
rules, the 17 rules first classed D, the 21 disputed rules, the six tool-enforced rules, the twelve
dispositions and the 140 clauses with a target to change. The 14 rules referred from classes A and
B had that reading already. Each item was read at commit `7eb8b9b7`, after the restorations.
[What was applied on 2026-10-02](#what-was-applied-on-2026-10-02) says which of these have since been entered.

| class | items | restore, as proposed or reworded | needs a decision | not owed, or do not restore |
|---|---:|---:|---:|---:|
| C, indicative sections | 22 | 12 | 9 | 1 |
| D, first classed as a choice | 17 | 8 | 8 | 1 |
| disputed | 21 | 5 | 1 | 15 |
| tool-enforced process rules | 6 | 2 | 0 | 4 |

Of the twelve dispositions the reading confirms nine, corrects one, keeps one as `applied` and
leaves one to a decision. Of the 173 proposed target additions it confirms 135 and rejects 34, with
4 recorded since; of the 58 proposed drops it confirms 49 and keeps 9.

**Class C.** Part 05 §14's indicative is an incorporation habit and no decision, and nothing gives
it force, so the section is repaired one sentence per rule and all at once: eleven further
sentences that no entry covers go in the same change, since a keyword beside an indicative neighbour makes
the neighbour read as optional. Four choices come first: who §14.4's first paragraph binds, given
that Part 05 §1 lists it under a writer (C5 to C7); the byte entry point, which the reference writer
misses on one path (C2); machine-readable output when a command rejects an extension registry,
which `escapewheel import` lacks (C12); and whether the label rule binds a validator's report or
every exposed result, the second needing a revision (C15). Part 11 is the opposite case. Its
indicative is a language definition's style, R125 wrote much of it that way, and the preferred
repair is one sentence in §1 saying the contract is every statement of §§2 to 8, with no keyword on
the five entries. Two Part 11 entries are owed in any mood: the missing rounding rule (C21) and a
lowercase "may" that lets a validator decline a comparison (C22). One needs its wording chosen
(C19) and one is stated and stays (C20).

**Class D.** Eight choices dissolve on a closer reading, each into a sentence the reading gives:
R102 §3.1 conditioned on the packet recording the run (D4), R3 §3.0 without its key shape (D7),
R147 §3.3 as one lead-in over the table (D8), R57 §2.1 as a property of the registry document (D9),
R107 §3.4 listing the five declarations the listing renders (D10), R126 §3.9 (D11), the `unit_id`
prohibition of R81 §2.5 (D13) and R129 §3.1 as an observable outcome (D15). Eight remain choices.
Three are text fixes once chosen: whether R111 §3.3's two drafting rules live in the style guide or
in Part 00 with a sweep of a dozen passive predicates (D1, D2); MUST or SHOULD for naming a media
asset's device (D5); and whether a reader owes the resolved content class and lineage policy, and
in which part (D6). Three need a revision whichever way they go: the relation a consumer uses for
a unit outside its packet, since `(sorting_run_id, local_unit_label)` holds a packet-assigned
number, omits the curation and can be null or tied (D12, D14); whether an `[overrides]` entry
releases a build from the discarded-fact refusal, which the reference build never consults and the
recipe's key form cannot express for a resource column (D16); and removing
`core.clocks.transform_to_parent`, which changes the registry and its version (D17). R91 §3.3 is
not restored (D3): the clause keeps `core.events.payload` as a home for a mark, and Part 02 §8.3
checks the scoped rule.

The reading of the dispositions disagrees with D9 on R57 §2.1: it prefers recording the clause as
superseded by R126 and not carrying the recommendation to emit `$schema` first. One of the two is
chosen.

**Disputed rules.** Fifteen are not owed: the parts state the rule in other words, a later
revision restated it, or the clause's sentence is an instruction to the specification that no
actor can fail. Each names the note or target its ledger entry takes. Five are owed, reworded: that
level 3a compares each declared member's size (R51 §2.1, E4); that a consumer does not read an
instrument from an entry's `uri` (R65 §2.3, E6); five words in the revision guide on withdrawn
records (R120 §3.2, E12); the meaning of `iso_feature_dependencies` in Part 11 §1 (R125 §3.2, E16);
and the validator's duty to evaluate each extension when core is non-valid, which rides with the
class C repair (R127 §3.6, E18). The byte-order sentence (R3 §7.1, E2) is not restored by a fix on
any reading, and the open byte-order draft settles it.

**Process rules and dispositions.** The guide owes two sentences, one in §2 on what `stages.py`
rejects and one in §8.4 on the anchor form of a named process section; the other four rules are
stated as outcomes or describe a tool's method. Nine dispositions stand as proposed, with the
entry text and registry pointers `ledger.py` accepts. R102 §3.1 stays `applied` at Part 01 §3.17
once D4 is entered, R37 §3.1 stays `applied` since its restoration, and R57 §2.1 waits on the
choice above. The reading of the targets adds a thirteenth clause that no target states, R112 §3.1,
which R120 §3.6 superseded.

**Defects the reading found outside the text.** Each was checked against the code or the registry
source before it was written here.

- The reference writer checks an extension registry registered as a file path through the mapping
  entry point (`extensions.py`).
- `escapewheel import` offers no machine-readable result for a rejected extension registry.
- `spec/tools/check.py` prints outcome lines for a non-valid core registry and no complete result.
- The reference validator's `PERCENTILE_CONT` keeps a `DECIMAL(38,0)` or `REAL` ordering domain,
  so `core.clock_anchors.gap_within_bound` can report a gap the binary64 median would not.
- The reference validator does not always round a `DECIMAL` to `DOUBLE PRECISION` conversion to
  nearest, ties to even.
- `refuse_a_discarded_fact` never reads `[overrides]`, and its message names that resolution.
- The description of `processing_run_id` on both array-asset tables says a null means the array
  was acquired, which is false of a computed array whose run the packet does not record.
- Part 05 §1 says the part binds no checker, and §14.2 already binds an implementation performing
  an extension-author registry check.
- Part 11 §3 says a table exposes exactly its registry-declared columns, and Part 02 §10.2 keeps a
  rule from naming an `optional` column because a packet's table may omit it.

Each class file under `repairs/` now carries the reading per entry, with the text to enter or the
choice; [repairs/G-process-and-dispositions.md](repairs/G-process-and-dispositions.md) holds the
process rules and the dispositions, and
[applied-target-pointers.md](applied-target-pointers.md) the targets.

## What was applied on 2026-10-02

Everything the critical reading left without a choice was entered, and
[repairs/decisions.md](repairs/decisions.md) lists every choice, numbered, with its options and
what each changes. Each but the eighth was answered the same day, and that file records the
answer and the commit or proposal that carries it.

- **Parts.** Eleven reworded restorations in Parts 01, 02, 03, 04 and 11 (D4, D7, D8, D10, D11,
  D13, D15, E4, E6, E16, C22), and ten labels on requirements restored the day before that no check
  observes.
- **Revision guide.** §2 says that a withdrawn record remains unedited (E12).
- **Ledger targets.** 132 sections added and 43 dropped.
- **Dispositions.** Six clauses became `superseded` (R15 §3, R79 §2.3, R107 §3.1, R112 §3.1,
  R148 §3.4, R151 §3.2) and five `registry` with guarded pointers (R3 §3.4, R22 §4, R27 §3,
  R30 §3.1, R41 §2.3).
- **Notes.** One on each restored clause, on the fifteen disputed clauses not owed, and on the
  four tool-enforced rules not owed.

Thirteen of the 25 reworded restorations were held for a choice and entered once it was made.
Twelve are sentences of Part 05 §14 (C1, C3, C4, C8, C9, C10, C11, C13, C14, C16, C17, E18): the
section was repaired in one change, since a keyworded sentence beside an indicative one reads as
making the second optional, and four of its rules needed a choice first. The thirteenth, D9, is
the rule on `$schema` coming first, where the reading of the clause and the reading of its
disposition disagreed.

## Pilot reading of 2026-10-01

A sample of 40 of the 770 applied targets was drawn with a fixed seed and read once. The reading
was not reviewed, so each row below is a claim to confirm and not a confirmed defect. Of the 40
targets, 31 stated their clause, 6 stated part of it and 3 stated none of it.

| clause | target | result | what the reading found |
|---|---|---|---|
| R95 §3.3 | Part 07 §4 | none | Both sentences are stated at the clause's other target, Part 05 §5.3. The bound by row-group statistics is in no part, and may be implementation description. |
| R132 §3.1 | Part 05 §14.5 | none | Every sentence is stated at the clause's first target, Part 05 §9.5. |
| R38 §2.3 | Part 01 §2.2 | none | The rule is in Part 01 §2.3, so the section number is stale. No part states that a narrower interval applies instead of the clock's, or that a refinement comes from something that measured it. |
| R80 §2.1 | Part 04 §5.5 | part | The part says an entry MAY carry `source` where the clause says SHOULD, and omits the recommendation that a source name be unique beyond the packet. |
| R129 §3.7 | Part 05 §14.3 | part | The second paragraph is one indicative sentence: both of its requirements lose their keyword, and the duty to identify the missing support is in no part. |
| R126 §3.8 | Part 02 §4 | part | Three sentences are in no part: that a source-provenance label retains its declared type, that a checker does not treat every `_label` suffix as a rule, and that a contradiction in descriptive prose is an authoring defect. The rule on descriptions is in Part 02 §3, which the ledger does not name. |
| R84 §2.1 | Part 07 §2.1 | part | The entry-point group is mentioned without its name, `escapewheel.commands`. |
| R8 §4 | Part 02 §9.3 | part | The column-specific sentences are gone because R103 amended them, and the ledger entry carries no note of that. |
| R120 §3.3 | the revision guide §5.4 | part | The guide does not say that a structural draft's Scope identifies it as a structural reorganization. |
