# Class B: sentences the parts state with less force

Each rule below is in a part with a weaker keyword, no keyword, or a narrower scope than its revision gives it, in a section whose other rules carry keywords.

37 rules, ordered by part and section: Part 00 (1), Part 01 (4), Part 02 (9), Part 03 (7), Part 04 (7), Part 05 (6), Part 06 (1), Part 12 (2).

Nothing here has been applied. The audit record is [applied-targets.md](../applied-targets.md).

## Part 00

### 1. R122 §3.8 at Part 00 §2.1 (ew-specification-candidate)

- **The revision decides:** the numbered part set MUST remain intelligible without repository-specific developer documentation
- **The part now says:** “The numbered parts remain intelligible without repository-specific developer documentation.” (Part 00 §2.1 (ew-specification-candidate))
- **Proposed text:** The numbered parts MUST remain intelligible without repository-specific developer documentation.
- **Placement:** Part 00 §2.1 (ew-specification-candidate)
- **Risk:** None found; R155's self-contained tree points the same way. The weaker form does not look deliberate: it is the one indicative sentence in a paragraph of keyword sentences, in a section that is not describing an implementation.
- **Second reading:** R122 §3.8: 'the numbered part set **MUST** remain intelligible without repository-specific developer documentation.' Part 00 §2.1 (ew-specification-candidate) has 'The numbered parts remain intelligible without repository-specific developer documentation.' Part 00 is normative and every neighbouring sentence of that paragraph carries a keyword, so under Part 00 §2.5 this one binds nothing. The indicative form dates from the commit that incorporated R122 (5cc41afb) and R155 only moved the file; no accepted revision other than R122 mentions the sentence. The nearest keyword rules (the README 'MUST NOT be the sole statement of a requirement'; R155's rule that a part names files within the tree) cover narrower ground. The sentence binds an artifact and is a standing constraint, not an editing step.

## Part 01

### 2. R45 §2.1 at Part 01 §2.3

- **The revision decides:** a consumer MUST NOT treat a stop_tick as excluded
- **The part now says:** “An interval is **closed**: `start_tick` and `stop_tick` both name observed ticks, so an interval covers `stop - start + 1` ticks and a one-tick interval has `start == stop`.” (Part 01 §2.3)
- **Proposed text:** An interval is **closed**: `start_tick` and `stop_tick` both name observed ticks, so an interval covers `stop - start + 1` ticks and a one-tick interval has `start == stop`. A consumer MUST NOT treat a `stop_tick` as excluded.
- **Placement:** Part 01 §2.3
- **Risk:** Low. The definition already makes an excluding reader wrong, so the sentence adds force and no new meaning; the omission does not look deliberate, since the same section uses MUST NOT for the window rule and the writer's half survives with a keyword in Part 05 §4.3. Part 05 §13 (reader operations) is an alternative home if Part 01 is to hold only meaning.
- **Second reading:** R45 §2.1 pairs the definition with two prohibitions: 'A writer MUST NOT emit a `stop_tick` one past the last tick the interval covers, and a consumer MUST NOT treat one as excluded.' Part 01 §2.3 keeps the definition in the indicative and Part 05 §4.3 keeps the writer's half with MUST ('A writer MUST NOT carry a half-open bound through unchanged'). No part binds a consumer: searched spec/parts for 'excluded', 'half-open', 'one past', 'inclusive', 'closed'. R54 §2.6 adds the importer's conversion and R54 §3 says 'No change to R45'; R146 moves writer rules to Part 05 and does not mention the consumer's. No later revision withdraws it.

### 3. R85 §2.3 at Part 01 §3.5 (Device)

- **The revision decides:** a consumer MUST NOT read two rows sharing a parent and a port as one device
- **The part now says:** “a port says where something was plugged in and not what it was.” (Part 01 §3.5)
- **Proposed text:** Two devices sharing a parent and a port are not one device, and a consumer MUST NOT read them as one; nothing declares that they are: [the rest of the sentence unchanged]. ('rows' becomes 'devices', since R146 has Part 01 name no rows.)
- **Placement:** Part 01 §3.5 (Device), the attachment paragraph
- **Risk:** None found; consistent with the registry description and with the paragraph's other consumer rules, so the indicative does not look deliberate.
- **Second reading:** R85 §2.3: 'A consumer MUST NOT read two rows sharing a parent and a port as one device.' Part 01 §3.5 states the fact only: 'Two devices sharing a parent and a port are not one device, and nothing declares that they are', with no consumer bound, although the same paragraph and the one before bind a consumer in capitals for the neighbouring rules (MUST report an unrecorded port, MUST NOT infer attachment from a name). The registry's `core.devices.parent_port` description is also indicative ('Establishes nothing about identity: two rows may share a parent and a port'). R146 reworded two other phrases of §3.5 (its §2.3 table) and not this one; no later revision cites R85 §2.3. The indicative dates from the incorporating commit be887329.

### 4. R68 §2.5 at Part 01 §3.18 (ew-media-asset-concept)

- **The revision decides:** A consumer MUST NOT use pts to measure elapsed time or to align a frame to anything else in the packet
- **The part now says:** “so a consumer MUST NOT compare it between assets or use it to measure elapsed time” (Part 01 §3.18)
- **Proposed text:** It is not a time on any clock the packet declares, so a consumer MUST NOT compare it between assets, use it to measure elapsed time, or use it to align a frame to anything else in the packet; what it locates is the frame inside the file.
- **Placement:** Part 01 §3.18 (ew-media-asset-concept)
- **Risk:** None found. R70 §2.3's MAY (seconds of the asset's own timeline) already sits two paragraphs below and concerns time within the asset, which the alignment ban does not reach. Renamed term: R68's `pts` is 'presentation timestamp' in Part 01 since R146 removed column names from it. The narrower form does not look deliberate.
- **Second reading:** R68 §2.5's third paragraph forbids two uses, and Part 01 §3.18 keeps one ('or use it to measure elapsed time'). R70 §2.3 says 'R68 §2.5 stands unchanged' and adds only the conversion to seconds within the asset; its one-line summary omits alignment but it withdraws nothing. R146 rewords §3.18's row-and-column language and does not touch this sentence. The premise survives in the indicative ('A frame's time is a tick on a declared clock', 'It is not a time on any clock the packet declares'), and no keyword forbids using a presentation timestamp to place a frame against a spike or an event. Searched spec/parts for 'align', 'relates', 'presentation timestamp', 'pts'.

### 5. R69 §2.2 at Part 01 §3.18 (Media asset)

- **The revision decides:** a consumer MUST NOT read frame_index as a count of exposures, a camera's own frame counter, or an offset into anything but this asset
- **The part now says:** “The index counts the frames the asset **holds**, not the exposures the capture produced.” (Part 01 §3.18)
- **Proposed text:** A consumer MUST NOT read a frame's index as a count of exposures, as a camera's own frame counter, or as an offset into anything but this asset.
- **Placement:** Part 01 §3.18 (Media asset), after the sentence 'The index counts the frames the asset holds, not the exposures the capture produced. ...'
- **Risk:** None found. §3.18 already binds consumers with MUST NOT for the presentation timestamp, so the indicative here does not look like a deliberate style; the restored sentence names no column, which R146 §2.3 requires of Part 01, and contradicts nothing in Part 02 §8.1.1 or a later revision.
- **Second reading:** R69 §2.2 ends with a capitalised consumer MUST NOT in its Decision. Part 01 §3.18 keeps only the indicative fact that the index counts the frames the asset holds, not exposures; no consumer is bound, and the camera's own frame counter and an offset into anything but the asset are not named. Part 02 §8.1.1 defines a structural index as a 0-based offset into a stored resource and its only consumer prohibition concerns source labels. The registry description of core.media_frames.frame_index is 'Frame index.' and its two rules check contiguity and pts order. No accepted revision other than R69 cites R69 §2.2; R146 reworded §3.18's row/table terms only (its §2.3 table) and did not touch this sentence. git log -S'own frame counter' finds the phrase only in the revision, never in a part.

## Part 02

### 6. R128 §3.3 at Part 02 §2.3 (ew-resource-kind)

- **The revision decides:** a dense-array declaration's `axes_resource` MUST name a visible singleton table declaration
- **The part now says:** “Its `axes_resource` names a visible singleton table declaration.” (Part 02 §2.3 (ew-resource-kind))
- **Proposed text:** Its `axes_resource` MUST name a visible singleton table declaration.
- **Placement:** Part 02 §2.3 (ew-resource-kind)
- **Risk:** No contradiction. Conformance effect is nil because registry.resource.array_axes already fails such a registry; the indicative sits between sentences that keep MUST and looks like an oversight rather than a choice.
- **Second reading:** R128 §3.3 has MUST; Part 02 §2.3 has 'Its `axes_resource` names a visible singleton table declaration' since R128's incorporation (commit 6fc02db5), and no later revision (R130, R145, R147 searched) touches it. The schema checks only the declaration-ID syntax of `axes_resource`. The next sentence, 'The axes table MUST have exactly one binding reference…', presupposes a table and a table MUST be a singleton, but visibility is not implied by it and Part 09 §6.1's MUST names references, dependencies and catalog bindings, not the axes resource. Part 02 §9.4 says the resource invariants 'enforce §§2.1–2.7 … the dense-array axes binding' and the descriptor anchors registry.resource.array_axes at ew-resource-kind, so a violating registry is still invalid; that enforcement is defined by this same indicative sentence rather than stating the rule elsewhere.

### 7. R128 §3.5 at Part 02 §2.5 (ew-resource-presence)

- **The revision decides:** `analysis`, `compatibility_projection`, and `documentation` declarations MUST be optional
- **The part now says:** “These three classes are optional under §2.5.” (Part 02 §2.2 (ew-resource-content-class))
- **Proposed text:** Every `analysis`, `compatibility_projection`, and `documentation` declaration MUST be optional.
- **Placement:** Part 02 §2.5 (ew-resource-presence)
- **Risk:** No contradiction: Part 06 §2 makes analysis resources disposable and Part 02 §2.2 forbids a canonical resource requiring a non-canonical one. If restored in §2.5, §2.2's pointer becomes true and registry.resource.instance's anchors should name the section that holds it (Part 02 §9.4: every anchor MUST identify every clause defining the invariant).
- **Second reading:** R128 §3.5 has MUST. Part 02 §2.2 says 'These three classes are optional under §2.5' in the indicative and defers to §2.5, which does not state it; the sentence dates from R128's incorporation and no later revision (R130 §3.7 edited §2.5, R145 added canonical targets) touches it. The schema has no condition tying `presence` to `content_class`. Part 02 §9.4's summary names only 'kind and instance eligibility', and the descriptor anchors registry.resource.instance at ew-resource-kind and ew-resource-instance-model, not at ew-resource-content-class where the sentence sits, so no stated clause defines the check the reference checker performs (_resource_instance: 'declarations must be optional'). The §2.2 table column 'required by class: no' says only that class does not make an instance required.

### 8. R128 §3.4 at Part 02 §2.6 (ew-resource-catalog-binding)

- **The revision decides:** a catalog declaration's `catalog_resource` MUST resolve to a singleton table declaration visible to that registry
- **The part now says:** “A catalog declaration names a visible singleton table declaration and one column.” (Part 02 §2.6 (ew-resource-catalog-binding))
- **Proposed text:** A catalog declaration's `catalog_resource` MUST resolve to a visible singleton table declaration, and it names one column of that table.
- **Placement:** Part 02 §2.6 (ew-resource-catalog-binding); the ledger target §2.4 only cites §2.6
- **Risk:** No contradiction. Conformance effect is nil because registry.resource.catalog already fails such a registry (Part 02 §9.4, 'unambiguous visible catalog bindings'); the indicative precedes a sentence that keeps MUST NOT and looks like an oversight.
- **Second reading:** R128 §3.4 has MUST; Part 02 §2.6 has 'A catalog declaration names a visible singleton table declaration and one column' since R128's incorporation, with no later revision. Part of the rule is carried with a keyword: Part 09 §6.1 says an extension's catalog binding MUST target its core context or the same extension, and §2.6 says a core catalog MUST NOT name an extension table, which together give visibility. That the target resolves to a table declaration (hence a singleton) has no keyword: the schema checks only the declaration-ID syntax of `catalog_resource`, and §2.4's table merely describes 'the named singleton table'. registry.resource.catalog (anchored at ew-resource-instance-model and ew-resource-catalog-binding) fails a violating registry, but its definition is this indicative sentence.

### 9. R128 §3.4 at Part 02 §2.6 (ew-resource-catalog-binding)

- **The revision decides:** `resource_id_column` MUST name a required string column with role `identifier`, identity `carried`, and free vocabulary
- **The part now says:** “That column is a required string identifier with carried identity and free vocabulary.” (Part 02 §2.6 (ew-resource-catalog-binding))
- **Proposed text:** Its `resource_id_column` MUST name a required string column of that table with role `identifier`, carried identity and free vocabulary.
- **Placement:** Part 02 §2.6 (ew-resource-catalog-binding)
- **Risk:** No contradiction. The reference checker already fails a violating registry; restoring the keyword makes that enforcement rest on a stated rule.
- **Second reading:** R128 §3.4 has MUST; Part 02 §2.6 has 'That column is a required string identifier with carried identity and free vocabulary' since R128's incorporation, with no later revision. The schema checks only the name syntax of `resource_id_column`. Part 02 §9.4's summary of the resource invariants names 'unambiguous visible catalog bindings' and does not name column eligibility, although the descriptor anchors registry.resource.catalog at ew-resource-catalog-binding and the reference checker (spec/tools/checkers/registry_invariants.py, _resource_catalog) tests type, presence, role, identity and vocabulary. §2.6's third paragraph states the fact for the three incorporated catalog tables only.

### 10. R2 §5 at Part 02 §6 (Presence)

- **The revision decides:** a reader MUST tolerate an absent `optional` column
- **The part now says:** “| `optional` | MAY be absent | MAY be null where present |” (Part 02 §6)
- **Proposed text:** A reader MUST tolerate an absent `optional` column.
- **Placement:** Part 02 §6 (Presence), directly after the presence table
- **Risk:** None found. It agrees with Part 02 §10.2 (a rule's SQL MUST NOT reference an optional column because the file may lack it) and with Part 05 §15.6's reading of an omitted optional column as null. The omission does not look deliberate: the same paragraph's writer SHOULD was also reduced to 'is preferred'.
- **Second reading:** R2 §5 states the reader obligation in capitals beside the presence table. Part 02 §6 keeps only the table row ('`optional` | MAY be absent | MAY be null where present'), which permits a writer and binds no reader. No reader obligation for an absent optional column is stated in any part: Part 02 §10.2 binds a rule's SQL, Part 05 §15.6 ('an `optional` column a file omits reads as null') is scoped to the amendment comparison, and Part 09 §4 ('An import MUST NOT fail because optional extension metadata is absent') is scoped to extension metadata. The later revisions citing R2 §5 (R28, R56, R94, R97, R109) leave it standing; R94 says 'R2 §5's three states are unaltered'. `git log -S'tolerate'` over spec/parts finds no commit, so the sentence never reached a part.

### 11. R22 §3 at Part 02 §9.3 (ew-registry-vocabularies)

- **The revision decides:** `label` MUST be recorded as the source emitted it; a writer MUST NOT rewrite it onto the normalized set
- **The part now says:** “- MAY carry the source's own label verbatim, which is open.” (Part 01 §3.15)
- **Proposed text:** A writer MUST record `core.unit_quality_labels.label` as the source emitted it and MUST NOT rewrite it onto the normalized set; `normalized_label` is where the projection goes.
- **Placement:** Part 02 §9.3 (ew-registry-vocabularies), at 'A scorer's own `label` is open'; alternatively Part 02 §8.7 where the indicative form now sits
- **Risk:** None found; Part 02 §8.7 already says the same without the keyword. Part 01 §3.15's 'MAY carry the source's own label' is weaker than the registry's `required` presence and would read oddly beside the restored sentence, so it should be checked at the same time. No rule can observe a rewrite, so under the repository's convention the sentence would say that no checker verifies it.
- **Second reading:** R22 §3 puts two capitals on the column: `label` MUST be recorded as emitted and a writer MUST NOT rewrite it. No part keeps either. Part 01 §3.15 makes the label a MAY ('MAY carry the source's own label verbatim, which is open'), although the registry declares `label` required. Part 02 §8.7 states the content in the indicative ('A source's own token is a string, kept as the source emitted it, and a consumer MUST NOT use it as an offset. This applies to a scorer's label'), where the only keyword binds a consumer on a different point. Part 02 §9.3 says only that the label is open. The registry description ('The source's own label, verbatim.') is a description, which Part 02 §3 does not make a requirement on a writer. Later revisions rely on the rule as binding and do not change it: R105 §2.4 ('R22 §3's rule for a scorer's label: recorded as the source emitted it, never rewritten') and R106.

### 12. R22 §3 at Part 02 §9.3 (ew-registry-vocabularies)

- **The revision decides:** where a source's label has no honest projection, `normalized_label` MUST be null rather than forced
- **The part now says:** “`normalized_label` is null where a source's label has no honest projection.” (Part 03 §5.6 (ew-one-null))
- **Proposed text:** Where a source's label has no honest projection onto the closed set, a writer MUST leave `normalized_label` null rather than force one.
- **Placement:** Part 02 §9.3 (ew-registry-vocabularies), with the closed column `core.unit_quality_labels.normalized_label`
- **Risk:** None found; Part 03 §5.6 and the registry description already assume it. No rule can tell a forced projection from an honest one, so the sentence would be an unchecked MUST and should say so.
- **Second reading:** R22 §3: 'Where a source's label has no honest projection ... it MUST be null rather than forced.' The parts state it only as a fact: Part 03 §5.6 uses it as an example of recording a reason for absence ('`normalized_label` is null where a source's label has no honest projection'), and the registry describes the column as 'Declared projection onto the closed set. Null where the source's label does not project.' Neither places an obligation on a writer, and the capitals in Part 03 §5.6 forbid a sentinel, which is a different rule: a writer forcing `non_soma` onto `noise` uses no sentinel and breaks no stated MUST. The registry rule `projection_is_consistent` checks only that one (source, label) pair projects one way. R101 §3.10 restates the indicative ('R22 §3 nulls `normalized_label`') and no revision withdraws the MUST.

### 13. R126 §3.3 at Part 02 §9.4 (ew-registry-conformance)

- **The revision decides:** the same precedence MUST determine a partially evaluated phase's state from its outcome records
- **The part now says:** “A definitive violation dominates an independent unsupported or incomplete phase; otherwise precedence is `invalid`, `unsupported`, `incomplete`, then `valid`.” (Part 02 §9.4 (ew-registry-conformance))
- **Proposed text:** The same precedence MUST determine a partially evaluated phase's state from its outcome records.
- **Placement:** Part 02 §9.4 (ew-registry-conformance)
- **Risk:** Contradicts nothing; it agrees with the result schema and with "A definitive violation dominates". The surrounding paragraph is in the indicative, so the part's own form would be "The same precedence determines ...". The omission looks like compression.
- **Second reading:** R126 §3.3 states the precedence and then: "The same precedence MUST determine a partially evaluated phase's state from its outcome records." Part 02 §9.4 keeps only the first, as the document-state precedence (its list ends in `valid`, a document state; a phase's is `passed`). Nothing in Part 02 §9.4 or §9.5 says which state a phase takes when its outcomes mix `invalid`, `unsupported` and `incomplete`; registry_result.schema.json requires only that such a phase have at least one outcome. R127 §3.1 leaves "state precedence" with Part 02 §9.4, and no accepted revision after R126 mentions the precedence or a partially evaluated phase, so none withdraws the sentence.

### 14. R26 §3 at Part 02 §10.2 (ew-tier-2-rules)

- **The revision decides:** an advisory rule MUST NOT run unless the caller asks for it
- **The part now says:** “it is off by default and MUST NOT be `error`, so that enabling it cannot change whether a packet” (Part 02 §10.2)
- **Proposed text:** A rule MAY be `advisory`, in which case a validator MUST NOT run it unless the caller asks for it, and it MUST NOT be `error`, so that enabling it cannot change whether a packet previously passed.
- **Placement:** Part 02 §10.2 (ew-tier-2-rules), the paragraph on levels
- **Risk:** Low. The capitalised neighbours (expose the choice; a report states whether advisory rules were run) presuppose the default, so the restored force contradicts nothing. The indicative looks like compression rather than a decision.
- **Second reading:** R26 §3: 'An advisory rule MUST NOT run unless the caller asks for it. A validator MUST expose that choice.' Part 02 §10.2 keeps the second sentence in capitals ('A validator MUST expose the choice') and the guarantee ('running with advisory rules enabled MUST NOT change whether a packet passed'), but states the first as a property, 'in which case it is off by default'. A validator that ran advisory rules unasked would break no capitalised sentence. Part 05 §9.2 adds only that an advisory rule is not an error. R125 §1.1 replaced §10.2's text and assigned it 'advisory behavior' without restating the rule in its Decision, and R82 and R95 paraphrase it as 'off by default' without amending it, so no later revision made the indicative form.

## Part 03

### 15. R129 §3.9 at Part 03 §2 (ew-portable-profile-technologies)

- **The revision decides:** lack of a recognized payload format or specialized decoder MUST NOT by itself invalidate the resource
- **The part now says:** “Unknown opaque representations do not invalidate a packet.” (Part 03 §2 (ew-portable-profile-technologies))
- **Proposed text:** An unknown opaque representation, or the lack of a specialized decoder for one, MUST NOT by itself invalidate the resource or its packet.
- **Placement:** Part 03 §2 (ew-portable-profile-technologies)
- **Risk:** No contradiction. §2 mixes capitalised rules with indicative description, so the indicative here does not look like a deliberate style; it dates from R129's incorporation. The clause says 'the resource' and the part 'a packet'; the restored sentence names both.
- **Second reading:** R129 §3.9: 'Lack of a recognized payload format or specialized decoder MUST NOT by itself invalidate the resource.' Part 03 §2 has 'Unknown opaque representations do not invalidate a packet', indicative, from R129's own incorporation; R143's incorporation (54afa814) reflowed the paragraph without changing the sentence and R143's clauses do not restate it. Other candidates are also indicative: Part 02 §2.3 'Generic code is not thereby required to parse, decode, or render its payload'. Part 05 defines no check on an opaque payload's format, so no finding can arise, but no part forbids a validator to raise one. Searched 'opaque', 'invalidate', 'decoder', 'unknown', 'unrecognized' across spec/parts.

### 16. R129 §3.9 at Part 03 §2 (ew-portable-profile-technologies)

- **The revision decides:** a generic reader MUST resolve and list an opaque resource and expose its catalog identity and location
- **The part now says:** “a generic reader lists its identity and location but need not retrieve, parse, decode, or render it.” (Part 03 §2 (ew-portable-profile-technologies))
- **Proposed text:** An opaque resource has no generic value interface: a generic reader MUST resolve and list it and expose its catalog identity and location, but need not retrieve, parse, decode, or render it.
- **Placement:** Part 03 §2 (ew-portable-profile-technologies)
- **Risk:** No contradiction. Since R146, Part 05 §1 lists §§13 and 14.3 as the sections binding a reader, so a reader MUST in Part 03 §2 sits outside that list, though Part 03 §§5.5 and 6.4 already bind a reader. The clause's 'need not' list also names integrity-checking and streaming, which the part omits; those are non-requirements and add nothing. The indicative dates from R129's incorporation and does not look deliberate.
- **Second reading:** R129 §3.9: 'A generic reader MUST resolve and list an opaque resource and expose its catalog identity and location.' Part 03 §2 has 'a generic reader lists its identity and location but need not retrieve, parse, decode, or render it', indicative, unchanged in substance since R129's incorporation (R143 only reflowed it). No other part obliges it: Part 05 §14.3 forbids a reader to demand a receipt or whole-packet inspection before it lists resources but does not oblige listing; Part 00 §2.4 describes a reader as returning a packet's resources without a keyword; Part 04 §10's reader paragraph governs decoding the manifest; Part 05 §13 has no opaque operation. Searched 'opaque', 'list', 'identity and location', 'generic reader'.

### 17. R129 §3.3 at Part 03 §5.1 (ew-table-encoding)

- **The revision decides:** a writer MUST NOT emit such a table, and a validator that can inspect the resource MUST reject one
- **The part now says:** “A directory, prefix, glob, explicit member set, or multi-file dataset MUST NOT realize a table in this profile.” (Part 03 §5.1 (ew-table-encoding))
- **Proposed text:** A writer MUST NOT emit one, and a validator that can inspect the resource MUST reject one.
- **Placement:** Part 03 §5.1 (ew-table-encoding), after the sentence ending 'MUST NOT realize a table in this profile.'
- **Risk:** No contradiction found. The writer half is arguably already implied by the artifact-level MUST NOT under Part 00 §2.4; the validator half is the real loss. No part assigns the rejection a check ID or level, and since R145/R146 Part 05 §5.3 (ew-validation-shim) is where validator checks sit, so the validator half may belong there rather than in Part 03 (Part 03 §5.5 does already bind a validator). The omission dates from R129's incorporation and does not look deliberate.
- **Second reading:** R129 §3.3 states both actor obligations in capitals. Part 03 §5.1 keeps only the artifact rule ('A directory, prefix, glob, explicit member set, or multi-file dataset MUST NOT realize a table in this profile'), and has done since R129's own incorporation (cbfbccf3); no later revision (R137, R145, R146, R154 searched for the clause, 'multi-file', 'ew-table-encoding') withdraws or restates the actor sentence. Refutations tried: Part 00 §2.4 lets a requirement state 'a property of an artifact', which arguably carries the writer half; but the validator half is not carried. Part 05 §5.3 obliges a validator to 'check available resource-owned metadata: physical order, file presence, Parquet types and footer features', names no check that a table resource is one object, and assigns no finding or level; Part 05 §10 defines conformance by error-level findings from Part 05's checks; Part 04 §10's phases have no such outcome. Searched 'single_object', 'one object', 'multi-file', 'resolves to', 'reject' across spec/parts.

### 18. R129 §3.4 at Part 03 §6.1 (ew-array-version)

- **The revision decides:** a reader or validator MUST determine the variant from the Zarr metadata's `zarr_format` when it accesses or physically assesses the resource
- **The part now says:** “A reader or validator determines the version from the resource's `zarr_format` metadata when it accesses or assesses that resource; a packet entry MUST NOT state it.” (Part 03 §6.1 (ew-array-version))
- **Proposed text:** A reader or validator MUST determine the version from the resource's `zarr_format` metadata when it accesses or assesses that resource; a packet entry MUST NOT state it. (The clause's 'variant' is the part's 'version'.)
- **Placement:** Part 03 §6.1 (ew-array-version)
- **Risk:** No contradiction. §6.1 uses capitals for its other rules, so the indicative is not a deliberate style of the section; it dates from R129's incorporation. The validator is already bound by Part 05 §5.3, so the restored MUST adds force only for a reader.
- **Second reading:** R129 §3.4: 'A reader or validator MUST determine the variant from the Zarr metadata's `zarr_format` value when it accesses or physically assesses the resource.' Part 03 §6.1 has 'determines' in the indicative, from R129's own incorporation (git log -S'determines the version from' shows only cbfbccf3 and the R155 move); R137 revised §6.4 only and says 'No accepted clause is superseded'. The validator half is carried elsewhere with force: Part 05 §5.3 'A validator MUST ... check available resource-owned metadata: ... Zarr version, rank and codecs', and Part 04 §5.3 forbids inferring the version from the URI or packet. Nothing binds a reader: Part 05 §14.3's 'it inspects only the metadata that resource needs' is also indicative. So the weakening survives for the reader.

### 19. R3 §5.1 at Part 03 §6.2 (Axis order)

- **The revision decides:** readers MUST NOT assume their language presents axes in declared order; a column-major binding enumerates them in reverse
- **The part now says:** “A column-major binding enumerates axes in reverse.” (Part 03 §6.2)
- **Proposed text:** A reader MUST NOT assume that its language presents axes in declared order: a column-major binding enumerates axes in reverse. The client adapts; the format does not.
- **Placement:** Part 03 §6.2 (Axis order)
- **Risk:** None found. The weaker form does not look deliberate: §6.2 states the writer-side rule beside it in capitals ('An array's codec chain MUST NOT include `transpose`'), and the same compression also left 'Array axes are stored order, slowest-varying first' in the indicative where R3 §5.1 has MUST.
- **Second reading:** R3 §5.1 says 'Readers MUST NOT assume that their language presents axes in declared order. Bindings that present column-major order enumerate axes in reverse.' Part 03 §6.2 keeps only the second sentence and an indicative gloss ('The client adapts; the format does not'), so the reader obligation has no keyword. No other part states it: the registry describes `axis_index` as '0-based axis position in stored order (Part 03 §6.2)' and Part 02 §8.1's client-boundary conversion concerns index base, not axis order. No accepted revision other than R3 mentions column-major order or cites R3 §5.1, so nothing withdrew it.

### 20. R129 §3.4 at Part 03 §6.4 (ew-array-codecs)

- **The revision decides:** a conforming reader MUST expose logical dense-array values for every valid v2 resource whose metadata matches a floor pattern
- **The part now says:** “An interface's `reader_floor` states what every conforming reader supports for logical-value access.” (Part 03 §2 (ew-portable-profile-technologies))
- **Proposed text:** A conforming reader MUST expose the logical values of every valid v2 array whose metadata matches a floor pattern.
- **Placement:** Part 03 §6.4 (ew-array-codecs), after the v2 pattern-matching sentence
- **Risk:** No contradiction: it mirrors the v3 sentence R137 §3.1 placed in the same section. v2 is external-only (§6.1), so the duty reaches only referenced arrays a reader accesses. The gap looks like an accident of R137 rewriting only the v3 half, not a deliberate choice.
- **Second reading:** R129 §3.4 obliges a conforming reader to expose values for 'every valid current-profile Zarr resource whose codec sequence or metadata matches an applicable floor entry', v2 included. R129's incorporation (cbfbccf3) put no reader MUST in Part 03 §6.4 for either variant; R137 §3.1 then added 'A conforming reader MUST expose the logical values of every valid v3 array whose pipeline matches the floor' for v3 only, and R137 §5 says 'No accepted clause is superseded', so it did not narrow the v2 duty. For v2 the parts have only 'The v2 reader floor is exactly ...' (§6.4) and §2's 'An interface's `reader_floor` states what every conforming reader supports for logical-value access', both indicative. That definition could be read as binding by defining a conforming reader, but beside an explicit v3 MUST and Part 03 §5.5's 'A reader MUST support' for Parquet it is the only floor without a capitalised reader duty. Searched 'v2', 'conforming reader', 'reader MUST (support|expose)' across spec/parts.

### 21. R129 §3.11 at Part 03 §6.5 (ew-array-metadata-placement)

- **The revision decides:** those physical facts MUST NOT be duplicated merely to make physical validation possible
- **The part now says:** “Self-describing physical facts—version, shape, dtype, chunking, and codec configuration—MUST be obtained from the resource and need not be copied into a table or the manifest.” (Part 03 §6.5 (ew-array-metadata-placement))
- **Proposed text:** Self-describing physical facts—version, shape, dtype, chunking, and codec configuration—MUST be obtained from the resource and MUST NOT be duplicated in a table or the manifest merely to make physical validation possible.
- **Placement:** Part 03 §6.5 (ew-array-metadata-placement)
- **Risk:** No contradiction: 'Zarr attributes MAY duplicate helpful metadata' concerns attributes repeating logical facts, the opposite direction. The purpose condition ('merely to make physical validation possible') is not mechanically testable, which may be why the incorporation wrote 'need not'; no accepted revision records that choice. The part's list omits the clause's Parquet compression and value encoding because §6.5 is an array section.
- **Second reading:** R129 §3.11 says the self-describing physical facts 'MUST be obtained from the resource and MUST NOT be duplicated merely to make physical validation possible'; Part 03 §6.5 keeps the first MUST and turns the second into 'need not be copied into a table or the manifest', as written at R129's incorporation (commit cbfbccf3) and unchanged since. Other keywords close most channels: the manifest schema's resource entry is closed and has no such member, Part 03 §6.1 says a packet entry MUST NOT state the Zarr version, Part 03 §2 forbids an entry repeating the interface, §6.5 says `core.array_assets` MUST NOT carry dtype or shape, and Part 12 §5 forbids a build requiring an adapter to restate such facts. What no keyword forbids is a copy of chunking, codec configuration or version in a table, or of Parquet compression and value encoding anywhere, made so that validation can use it; Part 04 §6 says the manifest carries no replacement in the indicative.

## Part 04

### 22. R36 §2.3 at Part 04 §5.3 (ew-external-resource-verification)

- **The revision decides:** level 3a establishes that the URI resolves, that `size_bytes` holds, and that the declared `codecs` match the metadata document
- **The part now says:** “| 3a | the external resource exists and lists |” (Part 04 §5.3 (ew-external-resource-verification))
- **Proposed text:** | 3a | the external resource exists and lists, and its recorded `size_bytes` holds |
- **Placement:** Part 04 §5.3 (ew-external-resource-verification)
- **Risk:** Do not restore 'declared `codecs` match the metadata document': R129 §3.6 removed the field. `size_bytes` is optional on an entry (Part 04 §4.1), so the row applies where it is recorded, as R14 §2.3.2's 'where declared' says. No conflict with R136: level 3c's prefix digest also covers sizes, but 3a is the level that reads no bytes.
- **Second reading:** Confirmed for `size_bytes` only. The codecs half is changed-by-later: R129 §3.6 retires the manifest's `codecs` field ('A manifest resource entry ... MUST NOT contain `physical_profile`, `partitioning`, or `codecs`') and R129 §3.8 has a validator read actual feature use from the resource's metadata 'rather than with a packet claim', which Part 04 §5.3 and Part 05 §5.3 carry. For the size, R36 §2.3's table defines 3a as including '`size_bytes` holds', R14 §2.3.2 requires the requested mode to check '`sha256` and `size_bytes` where declared', and R51 §2.3 still calls the list level 'the resource resolves; sizes and codecs agree'. No later revision (searched R51, R52, R73, R80, R129, R130, R136, R137 for size_bytes, 3a, 'level') removes the size comparison. Part 04 §5.3's row is 'the external resource exists and lists'; Part 04 §5.2 says only what `size_bytes` records; the one size check in Part 04 §10 (`packet.resource.member_size`) compares the manifest with itself. The v0.2 compilation (4ce6f09c) already carried the narrow row, so no revision made the change.

### 23. R36 §2.3 at Part 04 §5.3 (ew-external-resource-verification)

- **The revision decides:** a validator MUST NOT run the digest level unless separately asked
- **The part now says:** “Structural validation MUST NOT reach the network. Levels 3a to 3c run only in a requested mode.” (Part 04 §5.3 (ew-external-resource-verification))
- **Proposed text:** Levels 3a to 3c run only in a requested mode, and a validator MUST NOT run level 3c unless it is separately asked.
- **Placement:** Part 04 §5.3 (ew-external-resource-verification)
- **Risk:** Renamed term: R36's 3b is the part's 3c. The weaker form does not look deliberate: the section uses capitals for its other obligations and the sentence dates from the v0.2 compilation, not from a revision. R136 §3.5 lets 3c be reached from store checksums without a read, which weakens the cost rationale but changes no rule. Finding 41 (R51 §2.3) is the same requirement and is met by this sentence.
- **Second reading:** R36 §2.3: a validator 'MUST NOT run 3b unless separately asked'. R51 §2.3 keeps it ('The three levels stay separate flags, as R36 §2.3 requires') and R136 §3.5 adds a no-read route to the digest level without withdrawing the separate request. Part 04 §5.3 has 'Levels 3a to 3c run only in a requested mode' in the indicative, which one mode running all three satisfies; the MUST NOT in the same line binds structural validation and the network only. Part 04 §5.4 conditions the store-digest level on being 'asked to verify content without reading', so that level alone keeps its own request. Searched spec/parts for 'separately', 'requested', 'asked', 'offer'.

### 24. R51 §2.4 at Part 04 §5.4 (ew-prefix-resources)

- **The revision decides:** A validator that skipped every member because none recorded a store_digest reports that it verified nothing, not that everything passed
- **The part now says:** “A validator MUST report what a verification pass skipped” (Part 04 §5.4 (ew-prefix-resources))
- **Proposed text:** A validator that skipped every member because none recorded a `store_digest` reports that it verified nothing, not that everything passed.
- **Placement:** Part 04 §5.4 (ew-prefix-resources)
- **Risk:** The status is better read as missing than weakened: the clause has no capitalized keyword, so restoring it verbatim restores its full force and adding MUST would exceed the revision. Nothing in the part contradicts it.
- **Second reading:** The clause sentence is a rule about what a validator reports, stated in the indicative in R51 §2.4 itself. Part 04 §5.4 carries the per-member skip count ('the report MUST say how many were skipped') and 'A validator MUST report what a verification pass skipped', and neither says what the level's outcome is when every member was skipped: 'passed, N skipped' satisfies both. Searched spec/parts for 'verified nothing', 'skipped every', 'nothing', 'skipp'; Part 02 §9.4's skipped states govern registry-document checking, not external verification. R136 §3.6 restates the store-digest rules without this sentence and does not withdraw it.

### 25. R80 §2.1 at Part 04 §5.5 (ew-source-resolution)

- **The revision decides:** an external resource entry SHOULD carry source, naming the body of data it belongs to, where its bytes belong to a nameable one
- **The part now says:** “An external resource entry MAY carry `source`, an identifier naming the body of data it belongs to;” (Part 04 §5.5 (ew-source-resolution))
- **Proposed text:** A writer SHOULD give an external resource entry `source`, an identifier naming the body of data it belongs to, where its bytes belong to a nameable one; [the rest of the sentence unchanged]. (The clause's subject is the entry; 'A writer' names the actor as R111 requires.)
- **Placement:** Part 04 §5.5 (ew-source-resolution), first sentence
- **Risk:** No contradiction: the manifest schema leaves `source` optional, which a SHOULD permits, and an entry carrying no `source` keeps §5.1's meaning. The MAY looks like an incorporation slip, not a decision: no accepted revision argues for it. A SHOULD makes the reference writer's and adapters' entries without `source` deviations to justify, which is what R80 intended.
- **Second reading:** R80 §2.1 says 'An external resource entry SHOULD carry `source` ... where its bytes belong to a nameable one' and defends the keyword ('SHOULD rather than MUST, because the escape below is real'). Part 04 §5.5 has MAY and no condition, and has had since the commit that incorporated R80 (476a47f1 wrote 'MAY carry `source`'), so no revision decided the weaker force. The later revisions that amend §5.5 do not touch it: R111 §3 names actors for the unresolved-source sentence only, R134 §3.3 incorporates the schema and makes a source name any string, R136 §3.3 renames sha256 to digest, R143 §3.4 changes only how the uri is described; R134 says 'No accepted clause is superseded whole' and R143 'No accepted clause is superseded'. Part 03 §4 and the manifest schema describe the field without a recommendation.

### 26. R80 §2.1 at Part 04 §5.5 (ew-source-resolution)

- **The revision decides:** where source is present the entry's uri MUST be a path relative to the source and MUST NOT be absolute
- **The part now says:** “its `uri` is then a relative reference resolved against wherever that source is” (Part 04 §5.5 (ew-source-resolution))
- **Proposed text:** Where an entry carries `source`, its `uri` MUST be a relative reference (Part 03 §4), resolved against wherever that source is, and MUST NOT be absolute; neither field is a location. ('a path relative to' is now 'a relative reference', R143 §3.4.) A writer is the actor to name.
- **Placement:** Part 04 §5.5 (ew-source-resolution), first sentence
- **Risk:** No contradiction with Part 03 §4, whose MAY lists the three permitted forms. No schema conditional or Part 04 §10 check reports an entry with `source` and an absolute uri, so the restored requirement is unchecked until a check is added by revision. The indicative does not look deliberate: the same paragraph's neighbours are capitalised.
- **Second reading:** R80 §2.1: 'Where `source` is present the entry's `uri` MUST be a path relative to wherever that source turns out to be, and MUST NOT be absolute.' Part 04 §5.5 says in the indicative that the uri 'is then a relative reference resolved against wherever that source is'; Part 03 §4 says a manifest URI 'MAY be relative ... or — where the entry names a `source` — relative to that source' and binds a reader or validator to resolve a relative reference against the source's location, but no capitalised sentence requires the uri beside `source` to be relative or forbids an absolute one. The manifest schema's conditional on `source` requires only external: true, and Part 04 §10's packet.resource.uri_form accepts any absolute uri. R143 §3.4 only renamed 'a path relative to' as 'a relative reference' (crosswalk: 'revise in place') and says 'R80 §2.1's source-relative `uri` becomes a relative reference' and 'No accepted clause is superseded', so the MUST and MUST NOT stand. The indicative dates from the incorporating commit 476a47f1.

### 27. R80 §2.3 at Part 04 §5.5 (ew-source-resolution)

- **The revision decides:** a writer SHOULD write sources.json at the packet root, naming every source the packet references and where it read each one
- **The part now says:** “A writer SHOULD write that default.” (Part 04 §5.5 (ew-source-resolution))
- **Proposed text:** A writer SHOULD write that default, naming every source the packet references and where the writer read each one.
- **Placement:** Part 04 §5.5 (ew-source-resolution), the resolution-order paragraph
- **Risk:** None found; consistent with R134 §3.3's schema requirement. The short form looks like compression at incorporation (476a47f1), not a decision.
- **Second reading:** R80 §2.3: 'A writer SHOULD write `sources.json` at the packet root, naming every source the packet references and where it read each one.' Part 04 §5.5 keeps 'A writer SHOULD write that default' (the default being `sources.json` at the packet root) and nothing about what the default names. The only other writer rule is R134 §3.3's that a written document satisfies the schema, which an empty `sources` object does. Part 05 §6 lists the document among a promotion record's paths and says nothing of its content. No later revision narrows the sentence.

### 28. R128 §3.8 at Part 04 §9 (ew-packet-validation-block)

- **The revision decides:** a packet resource's validation state MUST NOT change its declaration-derived content class or canonicality
- **The part now says:** “It does not alter a resource's declaration-derived content class or canonicality.” (Part 04 §9 (ew-packet-validation-block))
- **Proposed text:** A resource's validation state MUST NOT change its declaration-derived content class or canonicality.
- **Placement:** Part 04 §9 (ew-packet-validation-block); the ledger target Part 04 §4.1 does not hold the sentence
- **Risk:** No contradiction. Part 05 §2 repeats the statement in the indicative, so restoring the keyword in Part 04 §9 leaves a second, weaker copy there. Both date from the incorporation and nothing records the indicative as a decision.
- **Second reading:** R128 §3.8 has MUST NOT. Part 04 §9 ('It does not alter a resource's declaration-derived content class or canonicality') and Part 05 §2 ('Validation state does not change the content class or canonicality selected by its declaration') both give it in the indicative, and no later revision changed its force (R132 edited Part 04 §9 for the status rule only). Nearby keywords cover adjacent ground but not this: Part 02 §2.2 forbids declaring canonicality independently and promoting with a Boolean, and Part 00 §3.2 forbids a packet entry repeating content class or canonicality, yet none forbids an implementation demoting a canonical resource because its `validation_state` is failed or not_run, which is the case the clause names ('does not turn a canonical core or extension resource into analysis content').

## Part 05

### 29. R115 §3.4 at Part 05 §3.7 (ew-source-command)

- **The revision decides:** a build MUST consume standard output and standard error concurrently
- **The part now says:** “MUST read what the command produces while it writes” (Part 05 §3.7)
- **Proposed text:** A build MUST consume a command's standard output and standard error concurrently: a pipe holds tens of kilobytes, so reading one to completion first waits on any command whose diagnosis outruns that buffer.
- **Placement:** Part 05 §3.7 (ew-source-command), in the paragraph beginning 'A build MUST capture a command's standard output and standard error'
- **Risk:** None found. It sits beside R116 §3.2's sentence on reading while writing and agrees with the paragraph's indicative description of writing the streams to a file. The omission looks like an incorporation slip, not a deliberate weakening: the ledger note for R115 §3.4 names only the argument-list rule.
- **Second reading:** R115 §3.4: 'A build **MUST** consume standard output and standard error concurrently.' It binds every command a build runs. Part 05 §3.7 (ew-source-command) has only 'A build MUST capture a command's standard output and standard error', which fixes no order, and 'MUST read what the command produces while it writes', which is R116 §3.2's rule for standard input and binds only a command a build reaches a source through. The closing sentence 'a build writes the streams to a file' is indicative. `git log -S'standard error concurrently'` finds the sentence in drafts only; R116 §3.2 calls the existing obligation one 'to capture standard output and standard error', confirming the part never said 'concurrently'. No later revision withdraws it. Not a statement about the implementation: the clause leaves only the technique to Part 07.

### 30. R115 §3.10 at Part 05 §4.4

- **The revision decides:** a build MUST refuse where a resource of the set did not arrive or the process did not exit clean
- **The part now says:** “Part 12 §5 has a resource an adapter owns and has nothing for arrive empty, so a build reads a resource that did not arrive as the run having failed, and never as the source having had nothing to say.” (Part 05 §4.4)
- **Proposed text:** A build MUST refuse where a resource of that set did not arrive or the process did not exit clean, naming the source.
- **Placement:** Part 05 §4.4, after the definition of a successful run
- **Risk:** Not evidently deliberate: every other sentence of §4.4 that binds a build carries a keyword, and Part 12 §5 cites §4.4 as holding this rule. 'Naming the source' now means by its kind (R133 §3.5, Part 05 §3.1), not 'by the name the recipe gave it' (finding 94). 'The process exited clean' has no referent for an adapter run in the writer's process, and the exit half duplicates Part 05 §3.7, so the restored sentence could be limited to the missing resource.
- **Second reading:** R115 §3.10 says 'A run succeeded when every resource in that set arrived and the process exited clean. A build **MUST** refuse where either fails'. Part 05 §4.4 keeps the definition of success and gives the exit half force ('A build MUST report one as a failure'; Part 05 §3.7 'A command that exits non-zero MUST fail the build'), but the missing-resource half is only 'so a build reads a resource that did not arrive as the run having failed', indicative both before and after R146's rewording (d7c0dcef). Part 12 §5 has the adapter's side with force ('MUST arrive empty rather than not arriving') and then describes the build's side in the indicative ('a resource that does not arrive states that the run failed'; 'a resource that does not arrive is already a failed run (Part 05 §4.4), which is the rule this needs and does not restate'), pointing back to §4.4 for a rule §4.4 does not state with a keyword. No part says a build refuses, or fails, on a failed run as such, and R133–R135, R144 and R146 do not restate it. Not refuted.

### 31. R82 §2.3 at Part 05 §12 (ew-alternatives-resolved)

- **The revision decides:** a consumer that meets an unresolved alternative is holding a packet that failed validation and MUST report that
- **The part now says:** “A consumer that meets an unresolved alternative is holding a packet that failed validation and reports that.” (Part 05 §12 (ew-alternatives-resolved))
- **Proposed text:** A consumer that meets an unresolved alternative is holding a packet that failed validation and MUST report that.
- **Placement:** Part 05 §12 (ew-alternatives-resolved), second paragraph
- **Risk:** None found. The section is not written in the indicative throughout, and R146 §3.1 lists §12 as the section binding a consumer, and this sentence is that consumer's only positive obligation there.
- **Second reading:** R82 §2.3: 'A consumer that meets one is holding a packet that failed validation and MUST report that'. Part 05 §12 (ew-alternatives-resolved) has '... and reports that', indicative since the incorporating commit 476a47f1, in a paragraph whose neighbouring consumer rule is capitalised ('A consumer MUST NOT silently choose'). R150 §§3.7 and 3.8 revise §12 in place only to exempt import runs and add the build's preference rows; R146 §3.1 names a consumer as the actor §12 binds and does not reword the sentence. No accepted revision quotes or decides the indicative form.

### 32. R32 §4 at Part 05 §15.1 (ew-amendment-definition)

- **The revision decides:** the amended manifest MUST be derived from the superseded one: every packet-level field the amendment does not change MUST carry over unchanged
- **The part now says:** “| Change `packet_id`, `profile_id`, the standard versions, the major version of `packet_version`, or `replaces` | MUST NOT |” (Part 05 §15.2 (ew-amendment-scope))
- **Proposed text:** A writer performing an amendment MUST derive the amended manifest from the superseded one and MUST NOT rebuild it: every packet-level member the amendment does not change MUST carry over unchanged.
- **Placement:** Part 05 §15.1 (ew-amendment-definition), after the sentence on `replaces`; §15.2 holds the enumerated form and is not a ledger target
- **Risk:** Compatible with what the part now says, provided 'does not change' is read with the members an amendment does change: `packet_version`, `resources`, the validation block, `registries` where the recipe names one (R150 §3.5), and `description` where the recipe gives one. R32's list of what a rebuild drops names 'the codec union', a field R129 §3.6 retired, so that example must not be restored. The enumerations in §15.1 and §15.2 would then be instances of the general rule, not rivals to it.
- **Second reading:** R32 §4 states a general rule: the amended manifest is derived from the superseded one and every packet-level field the amendment does not change carries over. The parts state it only member by member. Part 05 §15.2 forbids changing `packet_id`, `profile_id`, the standard versions, the major version and `replaces`; §15.1 carries `replaces` (MUST), the bound registries the recipe does not name, and `description` ('keeps', in the indicative); the session inventory is protected indirectly, by R150 §3.5's refusals and the `core.sessions.manifest_sessions_match` shim. Nothing covers the remaining packet-level members, `created_at` and `retention`, and no sentence says the manifest is derived and not rebuilt, which is the failure R32 names ('A writer that regenerates the manifest from only the resources it was handed will silently drop ...'). R150 §3.5 and R153 §3.5 added the specific rules without withdrawing the general one; R61 supersedes R32 §4 only for what a packet retains. `amendment.identity_changed` (Part 05 §15.6) checks the enumerated members and would not report a dropped `retention` or a reset `created_at`.

### 33. R35 §5 at Part 05 §15.4 (ew-incremental-revalidation)

- **The revision decides:** a check meeting neither condition MAY be skipped
- **The part now says:** “A shim without a complete declaration MUST run rather than be skipped.” (Part 05 §15.4 (ew-incremental-revalidation))
- **Proposed text:** A validator MAY skip a check only when no member of its input set was written and the check's prior verdict remains established from immutable inputs.
- **Placement:** Part 05 §15.4 (ew-incremental-revalidation)
- **Risk:** None found. Restore R125 §3.10's conditional form, not R35 §5's 'a check meeting neither condition MAY be skipped': R125 replaced the two syntactic conditions with layer-owned input sets. The sentence agrees with the section's 'what is bounded is the work, not the verdict' and with R35 §7's limit that a standalone validate checks everything, which the section already scopes to 'a writer performing an amendment'.
- **Second reading:** R35 §5's unconditional permission was narrowed by R125 §3.10 ('A validator MAY skip it only when no member was written and the check's prior verdict remains established from immutable inputs'), so R35's own wording must not come back; but the permission survives in R125 and no part grants it with a keyword. Part 05 §15.4 opens with 'MUST validate the whole packet' and says only what MUST run and that skipping a check whose inputs could have changed 'stays forbidden'; Part 03 §8.1 says in the indicative that immutability 'is what allows an amendment to skip revalidating untouched files'. Searched spec/parts for 'MAY skip', 'MAY be skipped', 'prior verdict', 're-run', 'skipp'; searched revisions/accepted for a later withdrawal of the permission and found none. The exception to whole-packet validation and its two conditions are therefore implied, not stated.

### 34. R61 §2.1 at Part 05 §15.5 (ew-packet-cleanup)

- **The revision decides:** Cleanup MUST default to reporting what it would remove without removing it
- **The part now says:** “The operation reports by default and acts only when asked.” (Part 05 §15.5 (ew-packet-cleanup))
- **Proposed text:** A writer performing cleanup MUST by default report what it would remove without removing it, and acts only when asked.
- **Placement:** Part 05 §15.5 (ew-packet-cleanup)
- **Risk:** The weaker form does not look deliberate: the surrounding sentences of the section use MUST and MUST NOT, and the sentence is a leftover of the compilation. Renamed actor as in finding 45.
- **Second reading:** R61 §2.1: 'Cleanup **MUST** default to reporting what it would remove without removing it.' Part 05 §15.5 has it in the indicative ('The operation reports by default and acts only when asked'), wording that dates from the v0.2 compilation and was moved unchanged by R146. R146 §3.2 enumerates the cleanup rules it restates with actors (order, strays, no deletion while amending) and is silent on the default, so no later revision chose the weaker form; R111 and R135 §3.5 do not touch it. Part 00 §2.5 gives the indicative no force.

## Part 06

### 35. R30 §4 at Part 06 §4 (ew-analysis-spike-events)

- **The revision decides:** a consumer MUST NOT assume the two tables are row-aligned or that a count from one applies to the other
- **The part now says:** “**Rows are not preserved.**” (Part 06 §4 (ew-analysis-spike-events))
- **Proposed text:** A consumer MUST NOT assume that this table and `core.spike_events` are row-aligned, or that a count from one applies to the other.
- **Placement:** Part 06 §4 (ew-analysis-spike-events), in the paragraph 'Rows are not preserved'
- **Risk:** None found. Since R145 §3.7 the section is normative, so the restored sentence binds. It is uncheckable by a validator and binds the consumer, like the other consumer rules of Parts 01 and 02.
- **Second reading:** R30 §4 ends with an obligation on a consumer. Part 06 §4 keeps the writer's obligation and the permission ('MUST be omitted by the writer rather than given an extrapolated value, so this table MAY hold fewer rows than core's') and drops the consumer's MUST NOT. Nothing else states it: Part 03 §5.3's 'A reader MUST NOT depend on stored order for correctness' covers positional alignment only by implication and says nothing of counts, and Part 05 §13 has no rule on `analysis.spike_events`. R145 §3.7 made Part 06 §4 normative and R151 added a check on its clock; neither mentions the consumer rule, and R145 §2.4 lists the section's content as 'the obligations of a writer'. No revision withdraws it.

## Part 12

### 36. R128 §3.8 at Part 12 §5 (ew-referenced-resource-delivery)

- **The revision decides:** a writer MUST preserve the delivered declaration binding when it creates the packet entry and MUST reject a document whose binding does not resolve or does not admit the resource ID
- **The part now says:** “A build preserves that binding, rejects one that does not resolve or admit the resource ID, and merges the entry into the manifest.” (Part 12 §5 (ew-referenced-resource-delivery))
- **Proposed text:** A build MUST preserve that binding when it creates the packet entry, MUST reject a document whose binding does not resolve or does not admit the resource ID, and merges the entry into the manifest. (R128's 'writer' is 'a build' since R134.)
- **Placement:** Part 12 §5 (ew-referenced-resource-delivery)
- **Risk:** No contradiction; the neighbouring sentences already bind a build with MUST, including refusal of a schema-invalid document before a manifest is written, so the indicative reads as an oversight. The ledger targets for this clause (Part 00 ew-packet-catalog, Part 04 ew-packet-resource-entry-fields) do not include Part 12 §5.
- **Second reading:** R128 §3.8 has two MUSTs on the writer; the part's sentence ('A build preserves that binding, rejects one that does not resolve or admit the resource ID…') has been indicative since R128's incorporation in Part 03's former section 11.3 and stayed so when R134 and R144 moved it to Part 12 §5 and renamed the actor to a build. The rejection half is carried in effect by other keywords: an unresolved binding is packet.resource.declaration_unknown and an inadmissible ID is singleton_identity, family_namespace or catalog_row_binding (Part 04 §10, all error), and Part 05 §2 forbids promotion until validation returns passed, so no such packet is published; that is later than a refusal of the document and names no document. The preservation half has no keyword: Part 04 §4.2's 'MUST NOT infer a declaration from URI, directory placement, namespace alone, or logical kind' forbids some substitutes but does not oblige the build to keep the delivered `declaration_id`, and the schema refusal in the same paragraph covers only the document's shape.

### 37. R115 §3.1 at Part 12 §7 (ew-adapter-declaration-document)

- **The revision decides:** an adapter MUST declare the kinds whose output it reads, which orders a build
- **The part now says:** “The kinds whose output an adapter reads order a build.” (Part 05 §3.4 (ew-source-declarations))
- **Proposed text:** An adapter MUST declare the kinds whose output it reads, which orders a build rather than being passed to it; `consumes` names them.
- **Placement:** Part 12 §7 (ew-adapter-declaration-document), with the other member meanings; Part 05 §3.4 keeps the ordering sentence
- **Risk:** No contradiction. The obligation to declare already has MUST force through the eight-member rule, so the smallest repair is the definition of `consumes` in Part 12 §7 and, in Part 05 §3.4, an actor for the ordering ('a build orders its sources by the kinds each adapter declares it reads'). The indicative in Part 05 §3.4 does not look deliberate: the paragraph enumerates declared facts and this one trails it without being called declared.
- **Second reading:** R115 §3.1 says 'an adapter **MUST** declare the kinds whose output it reads, which orders a build rather than being passed to it'. R134 §3.1 later restated half of it with force: Part 12 §7 says 'A document MUST carry all eight members', `consumes` among them, and 'in any other member, an empty array declares none'. But no normative sentence says what `consumes` holds or that a build orders by it. Part 12 §7 says 'this prose owns what each member means' and that 'The schema's descriptions are informative', then defines `protocols`, `accepts`, `contributes` and `states` and never `consumes`; the only statements of its meaning are adapter.schema.json's informative description and informative Part 07 §4. Part 05 §3.4's 'The kinds whose output an adapter reads order a build' is indicative, does not name the member, and does not say the kinds are declared. So an adapter is bound to carry a member whose content no part defines. Not refuted.
