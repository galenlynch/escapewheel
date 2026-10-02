# Class D: rules whose restoration needs a choice

Restoring the words of each rule below would meet a later text, an unanswered question, or a rule no named actor can follow. The proposed text is a starting point and the risk says what it has to settle.

17 rules, ordered by part and section: Part 00 (2), Part 01 (3), Part 02 (9), Part 03 (1), Part 05 (1), the core registry (1).

Nothing here has been applied. The audit record is [applied-targets.md](../applied-targets.md).

## Part 00

### 1. R111 §3.3 at Part 00 §2.4 (ew-specification-actors)

- **The revision decides:** a clause stating a property of an artifact MUST name the part of the artifact it constrains
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A clause stating a property of an artifact MUST name the part of the artifact it constrains.
- **Placement:** Part 00 §2.4 (ew-specification-actors), after 'states a property of an artifact'
- **Risk:** No contradiction, but a MUST here binds the specification's writer, who is not one of §2.4's five actors, so it has to read as a predicate on the specification itself, or be stated in the indicative like the sentence it follows (see finding 85). If drafting rules are meant to live in the style guide, spec/CONTRIBUTING.md §4 is the other candidate owner, and the ledger target would then be wrong rather than the part.
- **Second reading:** R111 §3.3 item 2 says of an artifact predicate: 'Such a clause **MUST** name the part of the artifact it constrains'. Part 00 §2.4 keeps only 'or states a property of an artifact'. No part and no section of revisions/CONTRIBUTING.md states the naming rule (its §5.1 line 'bind a named actor or an artifact' is about a revision's Decision and says nothing of naming the constrained part). spec/CONTRIBUTING.md §4 has an editorial analogue ('A conformance predicate may instead name the artifact being tested'), which is a permission to name the artifact rather than a requirement to name the part constrained, and that guide is neither a part nor an incorporated artifact and says it 'cannot create or override a requirement'. R122, R146 and R155 depend on or apply R111 §3.3 without restating this. R111 §3.5's twelve restatements are instances, not the rule. Not refuted.

### 2. R111 §3.3 at Part 00 §2.4 (ew-specification-actors)

- **The revision decides:** a clause stating a property of an artifact MUST put the constraint in an active verb
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A clause stating a property of an artifact MUST put the constraint in an active verb: "a wall-clock column MUST NOT use `INT96`" rather than "`INT96` MUST NOT be used".
- **Placement:** Part 00 §2.4 (ew-specification-actors), with finding 86's sentence
- **Risk:** As for finding 86: it binds the specification's writer, not an actor of §2.4, and is a drafting rule whose natural owner may be spec/CONTRIBUTING.md §4. Restoring it puts a rule about the specification's own prose into a normative part that otherwise holds none in keyword form.
- **Second reading:** R111 §3.3 item 2 says such a clause '**MUST** put the constraint in an active verb: "a wall-clock column MUST NOT use `INT96`" over "`INT96` MUST NOT be used"'. No part and no section of revisions/CONTRIBUTING.md says so. spec/CONTRIBUTING.md §4's 'Avoid passive or actorless obligations' is guidance in a document that is neither a part nor an incorporated artifact, is addressed to obligations lacking an actor rather than to artifact predicates, and has no requirement force. No later revision withdraws or restates the rule. Not refuted.

## Part 01

### 3. R91 §3.3 at Part 01 §3.12 (Event stream)

- **The revision decides:** a stream whose events carry marks MUST name the table holding them through detail_kind
- **The part now says:** “MAY name a device, a processing run, and a declaration specialising its events.” (Part 01 §3.12)
- **Proposed text:** A stream whose events carry marks MUST name the declaration holding them, and that declaration states how many there are and of what type. ('table' is 'declaration' and `detail_kind` is unnamed in Part 01 since R146; the column is Part 02's and the registry's.)
- **Placement:** Part 01 §3.12 (Event stream), the paragraph beginning 'A stream emits one kind of event'
- **Risk:** One tension: R91 §3.3 itself keeps `core.events.payload` as 'the only home a per-event value has today', Part 01 §3.11 lets an event carry a structured payload, and R97 §6 records the question as open. The restored MUST has to be read as binding where marks are held in a table, or it forbids the payload the same clause retains. No rule can tell whether a stream's events carry marks, so it binds a writer unchecked. The MAY in the bullet is right for a specialising declaration in general and can stay.
- **Second reading:** R91 §3.3: 'A stream whose events carry marks MUST name the table holding them through §3.4's `detail_kind`, and that table declares how many there are and what type each is.' Part 01 §3.12 says a stream 'MAY name ... a declaration specialising its events' and, in the indicative, that what an event carries beyond a tick 'is that named declaration's to declare, not core's'; nothing requires a stream with marks to name one. The registry declares `core.event_streams.detail_kind` nullable with `resolves: optional` and no rule ties it to marks; Part 02 §8.3 defines discriminator resolution generally. R146 changed only 'table' to 'declaration' in §3.12 (its §2.3 table). R97 §4 and §6, accepted later, treat R91 §3.3 as standing. R100, R107 and R152 touch `detail_kind` for other properties.

### 4. R102 §3.1 at Part 01 §3.17 (ew-array-asset-concept)

- **The revision decides:** an array a run produced MUST name that run; an acquired array declares none
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** An array a processing run produced MUST name that run; an acquired array names none.
- **Placement:** Part 01 §3.17 (ew-array-asset-concept), beside the device sentence
- **Risk:** Needs care. Part 01 §2.4 and Part 05 §10 make a packet carrying no provenance conforming, and Part 06 §5 (R130 §3.7) lets a writer not record a run for a materialization, so the sentence can bind only where the packet records the producing run; R102 §5 itself has arrays declare null 'until' the packet records their run. Restored bare, it reads as contradicting the registry description's 'Null means it was acquired' for such arrays. Part 01 §3.8 states the analogous coordinate rule as SHOULD 'where the writer knows it'. The sentence names no actor (Part 00 §2.4) and nothing checks it; the sentence R128 deleted with it, 'A produced array without a declared run is an error', has no rule behind it.
- **Second reading:** R102 §3.1 states it with a keyword ('An array a run produced **MUST** name it; an acquired array declares none'). Part 01 §3.17 carried 'An array a processing run produced MUST name that run; an acquired array names none' from R102's acceptance (95e745ff) until R128's incorporation (6fc02db5) deleted it under a crosswalk row that sends 'producing-run statements' to Parts 02, 04 and 06 'without changing what an array means'; no part received it. R128 §3.7 says it 'retains the existing row-level provenance columns and meanings', and R130 §3.7, which removes the resource-level producing-run policy, says 'Row-level `processing_run_id` columns ... are unchanged', so neither withdraws the row-level rule. Today `processing_run_id` appears in the parts only at Part 05 §12 (preferred runs); the registry description ('The run that produced this array. Null means it was acquired rather than computed.') is indicative and no Tier 2 rule checks it. Not refuted.

### 5. R102 §3.2 at Part 01 §3.18 (ew-media-asset-concept)

- **The revision decides:** a writer MUST name the device where its source states one
- **The part now says:** “A media asset SHOULD name the device that recorded it where its source states one, as an array” (Part 01 §3.18)
- **Proposed text:** A writer MUST name the device that recorded a media asset where its source states one, and MUST NOT infer it from a file name.
- **Placement:** Part 01 §3.18 (ew-media-asset-concept)
- **Risk:** The SHOULD may be a deliberate harmonisation rather than a slip: the sentence ends 'as an array asset does', and Part 01 §3.17 (R65 §2.1) is SHOULD 'where the writer knows which one did'. Restoring MUST makes the two assets differ, so 'as an array asset does' has to go or be reworded. Nothing checks the obligation. The MUST NOT half survives only in the registry description, with a keyword inside a description.
- **Second reading:** R102 §3.2 says 'A writer **MUST** name the device where its source states one'. Part 01 §3.18 says 'A media asset SHOULD name the device that recorded it where its source states one, as an array asset does', and has said SHOULD since the acceptance commit itself (95e745ff). The registry description of core.media_assets.device_id is indicative ('A writer names it where its source states one, and MUST NOT infer it from a file name'). No later revision lowers the force: R121, R128 and R146 each edited the paragraph without touching the keyword, and no accepted revision other than R102 decides it. Part 01 §3.5's 'a writer MUST record every instrument its source declares' is R102 §3.3's rule about device rows, not about the asset naming one. Not refuted.

## Part 02

### 6. R128 §3.7 at Part 02 §2.7 (ew-resource-provenance-policy)

- **The revision decides:** a reader MUST expose the resolved policy and content class without requiring a validation receipt for ordinary access
- **The part now says:** “A reader may expose the resolved facts without validating the registry or possessing a validation receipt for ordinary access.” (Part 02 §2.7 (ew-resource-provenance-policy))
- **Proposed text:** A reader MUST expose the resolved lineage policy and content class, and does so without validating the registry or possessing a validation receipt for ordinary access. ('The resolved policy' is the lineage policy alone since R130 §3.7 removed the producing-run policy.)
- **Placement:** Part 02 §2.7 (ew-resource-provenance-policy)
- **Risk:** An unconditional MUST meets two later texts: Part 05 §14.3 says an unusable declaration need not produce a result for a reader operation, and R130 §3.8 (Part 04 §10) has a reader fail the operation when the bound registry is missing, unreadable or fails its digest. The restored sentence should bind only where the declaration resolves. The 'may' was written in the incorporating commit itself and may have been a choice, but no accepted revision records it.
- **Second reading:** R128 §3.7 says 'A reader MUST expose the resolved policy and content class without requiring a validation receipt for ordinary access'; Part 02 §2.7 has said 'A reader may expose the resolved facts…' since R128's incorporation. The no-receipt half is stated with a keyword by Part 05 §14.3 ('A reader MUST NOT require a validation receipt … to open a packet's manifest, resolve its declarations, list its resources'), but the duty to expose is not: R130 §3.8 and Part 04 §10 say what a reader must check and how it resolves a declaration, Part 05 §13 lists reader operations without it, and no later revision withdraws it. R128 §5 lists 'reader APIs expose resolved facts' as the implementation consequence, which confirms the clause meant a duty.

### 7. R3 §3.0 at Part 02 §5.2 (No nested types)

- **The revision decides:** multiplicity rule: a field that is zero or more X MUST be a child table keyed on the parent's primary key plus the value; never a list, a delimited string or JSON
- **The part now says:** “A repeated value becomes a child table; a semi-structured value becomes a `json_string` in an optional column.” (Part 02 §5.2)
- **Proposed text:** A field whose semantic type is zero or more of a value MUST be a child table, keyed on the parent's primary key plus the value. It MUST NOT be a list, a delimited string or JSON.
- **Placement:** Part 02 §5.2 (No nested types), replacing 'A repeated value becomes a child table'
- **Risk:** The force is safe to restore: Part 02 §12.8 and Part 09 §8.1 already cite §5.2 as forbidding and requiring. The key shape needs care. Several core child tables are keyed on the parent's key plus a position or a qualifier rather than the value: `core.calibration_points` (`calibration_id`, `point_index`), `core.clock_anchors` (`clock_id`, `anchor_index`), `core.unit_quality_labels` (`session_id`, `unit_id`, `source`). Restoring 'plus the value' verbatim would be contradicted by those declarations, so the key clause should be dropped or loosened to 'plus what distinguishes one value from another'.
- **Second reading:** R3 §3.0 states the multiplicity rule as a MUST with three exclusions. Part 02 §5.2 puts only the type prohibition in capitals ('A column's type MUST NOT be `list`, `struct`, or `map`') and gives the affirmative half in the indicative ('A repeated value becomes a child table'); it does not forbid a delimited string or JSON for a multi-valued field and does not state the key shape. Two other sections rely on §5.2 as though it did: Part 02 §12.8 ('an ancestry path is a list, which §5.2 forbids in a delimited string') and Part 09 §8.1 ('declares its own typed child table, as Part 02 §5.2 requires of everything else'), so the intent is unchanged and the force was lost in §5.2 itself. No later revision narrows it: R16, R18, R19 and R105 all cite the rule as governing ('R3 §3.0 settles the shape for a repeated value: it is a child table, never a list, a delimited string'). The ledger target (Part 02 §6) is wrong; the passage is in §5.2.

### 8. R147 §3.3 at Part 02 §8.3 (ew-discriminator-semantics)

- **The revision decides:** where `resolves` is `required`, a validator MUST generate for a paired-value discriminator, beside the forward anti-join, three checks at error over the kinds the packet's rows name: a key-form check built from the registry's key declarations as literals, a per-kind anti-join on non-null paired values, and, where the paired value is on the specialised table, a check returning every specialised row whose discriminator is null
- **The part now says:** “Each check below is at **error**, and a per-kind check is generated for each kind a packet's rows name:” (Part 02 §8.3 (ew-discriminator-semantics))
- **Proposed text:** **Discriminators generate checks.** A validator MUST generate each check below, at **error**, and a per-kind check for each kind a packet's rows name:
- **Placement:** Part 02 §8.3 (ew-discriminator-semantics), the lead-in to the checks table
- **Risk:** The lead-in governs all six rows, not only the three paired-value ones. Their clauses differ in wording: R72 §2.1 has 'a check MUST be generated' for the reverse check, while R90 §3.8 ('two checks are generated') and R152 §3.2 ('Every specialising reference generates a check at error') are indicative, so a MUST over the whole table raises the stated force of the forward and specialisation rows above their clauses' wording. Nothing contradicts that, but a sentence scoped to the key-form, paired-value and kind rows would restore exactly R147 §3.3. The indicative looks inherited from R90's phrasing rather than chosen.
- **Second reading:** R147 §3.3: 'Where `resolves` is `required`, a validator MUST generate, in addition to the forward anti-join, three checks for a paired-value discriminator, each at `error`'. Part 02 §8.3's table states the three checks' content, level and condition exactly (rows 'key form', 'paired value', 'kind'), but its lead-in is 'Each check below is at **error**, and a per-kind check is generated ...', with no actor and no keyword. R147's own incorporation (d587432c) already wrote 'a paired-value discriminator gets a check'. R152 §3.2 later revised the paragraph in place, but restates only the specialisation check, the reverse check's counterpart and the `optional` case ('the paired-value checks are not generated'); it neither restates the paired-value generation in the indicative nor withdraws the validator duty. No other part binds it: Part 02 §10.1's 'A validator MUST generate' lists non-null, foreign-key, vocabulary and finiteness checks; Part 05 §5.1 repeats that list; Part 05 §5.4 extends to extensions the checks 'a core resource receives'; §8.3's own 'Every generated check MUST be built over every resource the packet declares' governs how a check is built, not that a validator builds it. Searched 'MUST generate', 'generated', 'discriminat' in Parts 02 and 05.

### 9. R57 §2.1 at Part 02 §9.2 (ew-registry-self-description)

- **The revision decides:** A writer SHOULD emit `$schema` first
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A writer producing a registry document SHOULD emit `$schema` first, so the declaration is visible without reading the file.
- **Placement:** Part 02 §9.2 (ew-registry-self-description)
- **Risk:** No contradiction, but the reason has thinned: R126 has a checker decode the whole document before it inspects root `$schema`, and JSON member order carries no meaning, so the recommendation now serves only a person or a tool reading the head of the file. Retiring it by a revision is the alternative to restoring it.
- **Second reading:** R57 §2.1 has two SHOULDs. The first (emit `$schema`) became R126's MUST, which Part 02 §9.2 states ('Every registry document conforming to that schema MUST carry that value in `$schema`'). The second (emit it first) appears in no part: searched Part 02 and Part 05 §14 for '$schema', 'first', 'member order', 'emit'. R126 says nothing of member order and does not withdraw it; R139 §5 only moves the ledger destination of R57 §2.1 to Part 02 §9.2. The incorporated core registry does carry `$schema` as its first member, which exhibits the practice and binds no other writer.

### 10. R107 §3.4 at Part 02 §9.3 (ew-registry-vocabularies)

- **The revision decides:** tables.md MUST render every declaration a column carries: its vocabulary, the closed set, its reserved values, its authorities by name, and a discriminator's `resolves`, generated from the fields
- **The part now says:** “A column's declarations are rendered in `informative/tables.md` from the fields holding them — the vocabulary, the closed set itself, the reserved values, the authorities by name, and a discriminator's `resolves`.” (Part 02 §9.3 (ew-registry-vocabularies))
- **Proposed text:** `informative/tables.md` MUST render every declaration a column carries, from the field holding it: its vocabulary, the closed set itself where the vocabulary is `closed`, its reserved values, its authorities by name, and a discriminator's `resolves`.
- **Placement:** Part 02 §9.3 (ew-registry-vocabularies), last paragraph
- **Risk:** The indicative looks deliberate and has been there from acceptance. Part 02 §1 calls the file 'a generated, informative listing', and a MUST on an informative projection binds none of Part 00 §2.4's five actors (the generator is repository tooling), so a restored MUST sits awkwardly with R111 §3.3 and R122's ownership model unless read as a property of an artifact. The generated file does render all five fields today. The paragraph's second sentence ('it showed none of them, which is why 35 descriptions had come to say them in prose') is history that R121 would strike.
- **Second reading:** R107 §3.4 says '`registry/tables.md` **MUST** render every declaration a column carries'. Part 02 §9.3 states the same content in the indicative ('A column's declarations are rendered in `informative/tables.md` from the fields holding them — ...'), and has since R107's acceptance commit (6e60d06d). R122 only records that Part 02 §1 already called the file an informative generated listing, R155 only moves it to `informative/tables.md`, and R139, R147–R152 treat rendering new fields there as a consequence under 'generated publications'; none withdraws or restates the requirement. Under the rule of evidence (keywords bind only in capitals) the indicative is a weakening that no later revision made. Renamed term: `registry/tables.md` is now `informative/tables.md` (R155).

### 11. R126 §3.9 at Part 02 §9.4 (ew-registry-conformance)

- **The revision decides:** a checker without the exact required domain MUST report the external-domain phase as unsupported rather than accept a printable approximation
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** A checker without the exact required domain MUST report the `external_domain` phase as unsupported rather than accept a printable approximation.
- **Placement:** Part 02 §9.4 (ew-registry-conformance)
- **Risk:** Contradicts nothing, and R131's packet-level unit check assumes it. An unsupported phase needs at least one outcome under Part 02 §9.5 and the result schema, and Part 02 assigns no outcome ID for a missing domain; restoring the sentence exposes that gap, which R126 §3.9 did not fill either.
- **Second reading:** Part 02 says only that "External lexical-domain validation runs last and offline" (§9.4) and that "Validation of unit codes and authority URIs is offline" (§13). Nothing says what a checker reports when it lacks the exact UCUM edition: §9.4 assigns `unsupported` to an unknown meta-schema selector and an unknown or ambiguous contract tuple, not to a missing external domain, and it has no outcome ID for the case. Part 05 §14.1 only mentions "external-domain capabilities used". No later revision withdraws the rule; R131 §2.4 relies on it ("A validator lacking that edition obtains an `unsupported` core result"), which the parts no longer support.

### 12. R81 §2.5 at Part 02 §12.1 (ew-unit-identity)

- **The revision decides:** a consumer relating a unit to anything outside the packet MUST use (sorting_run_id, local_unit_label)
- **The part now says:** “consumer relating a unit to anything outside the packet uses `(sorting_run_id, local_unit_label)`.” (Part 02 §12.1 (ew-unit-identity))
- **Proposed text:** A table keyed on a unit carries `unit_id` and not the run or the curation. A consumer relating a unit to anything outside the packet MUST use `(sorting_run_id, local_unit_label)`.
- **Placement:** Part 02 §12.1 (ew-unit-identity), the paragraph 'A table keyed on a unit carries `unit_id` ...'
- **Risk:** The indicative looks like incorporation compression, not a decision: R123 §3.1, accepted later, repeats the MUST. One tension to weigh when restoring: `sorting_run_id` is itself an assigned identifier (registry: identity assigned), so outside the packet the run is reached through `sorting_run_name` (Part 02 §8.2); R123 calls the pair 'the source-facing relation Part 02 §12.1 defines' without changing it, so restoring the clause's own words changes nothing that is stated now. Part 02 §12's interval-identity sentence (R148 §3.1) is indicative by its own clause and is not a precedent for this one.
- **Second reading:** R81 §2.5: 'A consumer relating a unit to anything outside the packet MUST use `(sorting_run_id, local_unit_label)`.' Part 02 §12.1 (ew-unit-identity) has 'a consumer relating a unit to anything outside the packet uses `(sorting_run_id, local_unit_label)`', indicative since the incorporating commit 476a47f1. The later revision that owns the section keeps the force: R123 §3.1 says 'Outside the packet, a consumer MUST use the source-facing relation Part 02 §12.1 defines rather than treating the packet-assigned number as globally stable', and its crosswalk retains §12.1 as owner without rewriting the sentence. R149 and R150 change the numbering order only. No part states R123's sentence either ('source-facing' and 'globally stable' appear in no part); Part 05 §13.1 binds a reader presenting packets together, a different actor and operation. The ledger target Part 02 §9 is stale; R123 repointed R81 to §12.1.

### 13. R81 §2.5 at Part 02 §12.1 (ew-unit-identity)

- **The revision decides:** a consumer MUST NOT use unit_id to relate a unit to anything outside the packet
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** It MUST NOT use `unit_id` for that, which means something only inside the packet that assigned it. (R123 §3.1's later wording of the same prohibition is 'rather than treating the packet-assigned number as globally stable'.)
- **Placement:** Part 02 §12.1 (ew-unit-identity), directly after the sentence finding 61 restores
- **Risk:** Read baldly, 'MUST NOT use `unit_id`' sits beside Part 05 §13.1, where a reader presenting several packets includes `unit_id` with the session discriminator; the two do not conflict (the discriminator names the packet, so the number is not used outside it), but R123 §3.1's wording, 'MUST NOT treat `unit_id` as stable outside the packet that assigned it', avoids the appearance and is the safer text. No check can observe a consumer's use.
- **Second reading:** R81 §2.5: 'It MUST NOT use `unit_id`, which means something only inside the packet that assigned it.' No part forbids it. Part 02 §12.1 says only what a consumer 'uses'; the registry's `core.units.unit_id` description is 'Stable unit ID.'; Part 02 §8.1.1's consumer prohibition concerns a source label used as an offset; Part 01 §2.1 explains why an assigned identifier is paired with a name and binds a writer. R123 §3.1 restates the prohibition rather than withdrawing it ('... rather than treating the packet-assigned number as globally stable') and that sentence is in no part either. R123 §3.3 (Part 05 §13.1) has a reader pair `unit_id` with the session discriminator across packets it presents together, which narrows nothing for a consumer relating a unit to something outside the packet.

### 14. R123 §3.1 at Part 02 §12.1 (ew-unit-identity)

- **The revision decides:** outside the packet, a consumer MUST use the source-facing relation Part 02 §12.1 defines rather than treating the packet-assigned number as globally stable
- **The part now says:** “consumer relating a unit to anything outside the packet uses `(sorting_run_id, local_unit_label)`” (Part 02 §12.1 (ew-unit-identity))
- **Proposed text:** A table keyed on a unit carries `unit_id` and not the run or the curation. A consumer relating a unit to anything outside the packet MUST use `(sorting_run_id, local_unit_label)`, and MUST NOT treat `unit_id` as stable outside the packet that assigned it.
- **Placement:** Part 02 §12.1 (ew-unit-identity)
- **Risk:** No contradiction with Part 05 §13.1, whose discriminator-plus-`unit_id` join is a presentation of packets and not a claim that the number is stable. Two things to weigh: under R149 §3.1 units of one curation that tie on their label may be numbered in either order and a label may be null, so the relation the MUST points at does not identify every unit; and Part 02 §12.9's parallel sentence for intervals is indicative in R148 §3.1 itself, so restoring the keyword here leaves the two subsections in different moods. The weaker form looks inherited from R81's incorporation, not chosen.
- **Second reading:** R123 §3.1: 'Outside the packet, a consumer **MUST** use the source-facing relation Part 02 §12.1 defines rather than treating the packet-assigned number as globally stable.' Part 02 §12.1 (ew-unit-identity) has 'a consumer relating a unit to anything outside the packet uses `(sorting_run_id, local_unit_label)`', indicative in a normative part, and no prohibition on treating `unit_id` as stable. The sentence predates R123: R81 §2.5 decided it with keywords ('MUST use `(sorting_run_id, local_unit_label)`. It MUST NOT use `unit_id`') and it was incorporated without them; R123's crosswalk retains §12.1 and R149 changes only the label order. No other part binds a consumer here: Part 01 §2.1 explains the name pairing without a keyword, Part 02 §8.2 binds the registry and the writer, and Part 05 §13.1 binds a reader presenting packets together, which qualifies `unit_id` by packet and session and does not address relating a unit to something outside any packet.

## Part 03

### 15. R129 §3.1 at Part 03 §1 (ew-portable-profile-scope)

- **The revision decides:** a generic profile checker MUST enforce those invariants without embedding this profile's identifiers or assignments
- **The part now says:** “A conforming distributed copy MUST pass the schema and the generic cross-member checker at a packaging or equivalent conformance boundary” (Part 03 §1 (ew-portable-profile-scope))
- **Proposed text:** The generic cross-member checker MUST enforce the descriptor's cross-member invariants without embedding this profile's identifiers or assignments.
- **Placement:** Part 03 §1 (ew-portable-profile-scope)
- **Risk:** No contradiction. The rule constrains how a checker is built rather than an outcome a test of one profile can observe, which spec/CONTRIBUTING.md §4 discourages, so the incorporating editor may have left it to the word 'generic' on purpose; no accepted revision records that.
- **Second reading:** R129 §3.1 binds 'a generic profile checker' with MUST, and checkers are bound elsewhere in the parts (Part 02 §9.4, Part 04 §10), so it is a rule and not a remark about the reference tool. Part 03 §1 calls the checker 'the generic cross-member checker' twice and says the descriptor 'owns the profile's exact identifiers', but nowhere says with a keyword that the checker enforces the cross-member invariants or that it carries none of the profile's identifiers or assignments; the word 'generic' is all that remains. The text dates from R129's incorporation (commit cbfbccf3). R137 and R154 revised the section and the descriptor without withdrawing the rule, and R154 §3.1 relies on it by phrasing its own check through `kind_interfaces` rather than an interface name. The reference checker (spec/tools/check.py, profile_checks) follows the rule in a comment only.

## Part 05

### 16. R108 §3.3 at Part 05 §3.4 (ew-source-declarations)

- **The revision decides:** an `[overrides]` entry naming a fact MUST silence the discarded-fact refusal for that fact
- **The part now says:** “A recipe resolves the refusal by naming the fact in `[overrides]` with its reason, by preferring the other source, or by correcting the source that states less.” (Part 05 §3.4 (ew-source-declarations))
- **Proposed text:** An `[overrides]` entry naming a fact MUST silence that refusal for that fact: a build MUST NOT refuse over a discarded value of a fact the recipe's `[overrides]` names.
- **Placement:** Part 05 §3.4 (ew-source-declarations), after the discarded-fact refusal
- **Risk:** Not evidently deliberate: the neighbouring sentences of §3.4 all carry keywords. Two frictions to settle when restoring. Part 05 §3.6 has a build 'report an override for a field the source agrees with, or that no source states', written for the recipe-over-source use, and says nothing of this second use. And `[overrides]` is keyed `block.field` (Part 05 §3.1, recipe schema), while the refusal names a column of a resource, so the part does not say how an entry names a discarded column.
- **Second reading:** R108 §3.3 says 'An `[overrides]` entry naming a fact **MUST** silence §3.1's refusal for that fact'. Part 05 §3.4 states the refusal with 'A build MUST refuse where a preference discards a value another source stated' and gives its exception only as 'A recipe resolves the refusal by naming the fact in `[overrides]` with its reason, by preferring the other source, or by correcting the source that states less', which is indicative, describes what a recipe does, and binds no build to accept the entry. The sentence has read so since R108's acceptance (037d2eff). Part 05 §3.6 defines `[overrides]` only for a recipe's value superseding a source's. R133 and R150 mention the table's shape and an amending build's refusal of the member, and neither restates this. Not refuted.

## The core registry

### 17. R3 §3.4 at the core registry

- **The revision decides:** `core.clocks.transform_to_parent` is replaced by the typed columns
- **The part now says:** nothing; the sentence is absent.
- **Proposed text:** Remove the `transform_to_parent` column from `core.clocks`; `transform_slope` and `transform_offset` replace it. No part sentence is needed.
- **Placement:** the core registry, `core.clocks` (source `spec/source/core/core.clocks.toml`, from which `spec/artifacts/logical_schemas.json` and `spec/informative/tables.md` are generated); the ledger target Part 01 §3.9 needs no sentence
- **Risk:** No part or later revision relies on the column. Removing a declared column changes the core registry, so Part 02 §9.2's version rules apply and the generated artifacts must be regenerated rather than edited. R94 §2's informative count of 25 optional columns would then describe the registry at its acceptance, which an accepted record may do. `conformance/spec-sweep/compliance.py` names the column in its R3-covered set and is unaffected. While it stays, a writer could put the alignment in JSON beside the typed columns, which Part 02 §8.6's principle ('A fact required to interpret the data belongs in a column') argues against.
- **Second reading:** R3 §3.4 is headed `core.clocks.transform_to_parent` and opens 'Replaced by typed columns on `core.clocks`'; R3's own table of nested fields lists the column with disposition 'typed columns (§3.4)'. The typed columns exist, but the registry still declares the replaced one: `spec/source/core/core.clocks.toml` line 98 and `spec/artifacts/logical_schemas.json` (`transform_to_parent`, `json_string`, `optional`, 'Clock alignment transform.'). No accepted revision retains or redefines it: R13 §1 and R99 §2.2 both say R3 §3.4 replaced or converted it, and R94 §2 only counts it among the 25 optional columns in an informative inventory. It is a one-time schema change, but it has not lapsed, because it was never completed. No part mentions the column, and none needs to: the defect is the surviving declaration, not a missing sentence.
