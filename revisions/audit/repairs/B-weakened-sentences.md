# Class B: sentences the parts state with less force

Each rule below is in a part with a weaker keyword, no keyword, or a narrower scope than its revision gives it. A third reading then tried to show each restoration to be a mistake: whether a later revision changed the rule, whether the text contradicts or exceeds anything, whether it names an actor who can comply, whether a check observes it, whether it sits in the part that owns it, and whether the reference implementation and the corpus comply. The rules below passed. "Text to enter" is that reading's wording; where it differs from the text first proposed, both are shown.

29 rules, ordered by part and section: Part 00 (1), Part 01 (4), Part 02 (8), Part 03 (4), Part 04 (6), Part 05 (3), Part 06 (1), Part 12 (2).

All of these were entered on 2026-10-01, one commit per part from `96c0bbcd` to `ef5190df`, and each clause's ledger entry carries a `restored 2026-10-01` note. The audit record, [applied-targets.md](../applied-targets.md), lists where the entered text departs from "Text to enter".

## Part 00

### 1. R122 §3.8 at Part 00 §2.1 (ew-specification-candidate)

- **The revision decides:** the numbered part set MUST remain intelligible without repository-specific developer documentation
- **The part now says:** “The numbered parts remain intelligible without repository-specific developer documentation.”
- **Text to enter:** The numbered parts MUST remain intelligible without repository-specific developer documentation.
- **Placement:** Part 00 §2.1 (ew-specification-candidate), the paragraph beginning 'The specification README, `README.md`, MUST be an informational entry point', replacing its sentence 'The numbered parts remain intelligible without repository-specific developer documentation.'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Evaluation:** Restore the keyword as proposed; it is a one-word transcription loss from the incorporating commit and the parts already comply. The only reservation is that 'intelligible' is not a determinate test and nothing checks it, which is equally true of the clause R122 accepted, so it is a reason to tighten the rule by revision and not a reason to leave the keyword off.
- **By lens:**
  - *Still decided:* R122 §3.8's last paragraph carries the MUST. R155 (the only later revision touching Part 00 §2.1) adds the tree and path rules and points the same way; R146 does not touch the sentence; no crosswalk row drops or rewords it. `git log -S` shows the indicative form entered with the incorporating commit 5cc41afb and never changed, so the loss is a transcription, not a decision.
  - *Contradiction:* None found. Read Part 00 §§2.1-2.5 and §8 in full, and grepped spec/parts for CONTRIBUTING, README, `.py`, `revisions/`, PLAYBOOK, ROADMAP: the parts name no developer document (only Part 00's own README sentences match), so the parts satisfy the restored sentence today. No open draft mentions it.
  - *Exceeds the clause:* No. R122 says 'the numbered part set MUST remain intelligible without repository-specific developer documentation'; the proposal says 'The numbered parts MUST remain ...'. Same subject, force and scope.
  - *Actor:* It states a property of an artifact (the numbered parts), which Part 00 §2.4 admits, and every neighbouring sentence of §2.1 has the same form. The weakness is determinacy: 'intelligible' gives no observable outcome under spec/CONTRIBUTING.md §4; the determinate part of the idea is already carried by R155's sentence that a part names only files within the tree and names outside evidence by what it is.
  - *Checks:* Unchecked. spec/tools/framework.py checks the README (informational opening, no keyword, no reference section) and the tree's path check covers R155; nothing tests intelligibility. The specification can always comply. The 'No checker verifies this' label marks obligations on a Part 00 §2.4 actor that a validator cannot observe, and no framework sentence of Part 00 §2 carries one, so a label here would be the first of its kind; I would not add it.
  - *Placement:* Part 00 §2.1 owns specification-candidate identity and the README's role (Part 00 §2, first paragraph). No other part or artifact states the rule, so no second owner.
  - *Implementation and corpus:* Unobservable in the reference implementation; no code, registry, schema or corpus packet is affected. No tool pins the sentence (grepped spec/tools, conformance, revisions for 'intelligible'). The combined rendering under spec/informative regenerates from the part and must be regenerated in the same commit, not edited.
  - *Wording:* Reads correctly beside its neighbours; 'the numbered parts' is the term §2.1 already uses. No renamed term or moved citation.

## Part 01

### 2. R45 §2.1 at Part 01 §2.3 (Observation)

- **The revision decides:** a consumer MUST NOT treat a stop_tick as excluded
- **The part now says:** “An interval is **closed**: `start_tick` and `stop_tick` both name observed ticks, so an interval covers `stop - start + 1` ticks and a one-tick interval has `start == stop`.”
- **Text to enter:** A consumer MUST NOT treat a `stop_tick` as excluded.
- **Placement:** Part 01 §2.3 (Observation), appended to the third paragraph, after 'so an interval covers `stop - start + 1` ticks and a one-tick interval has `start == stop`.'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Evaluation:** Append the consumer sentence as proposed; the definition, the writer's half in Part 05 §4.3, the registry rules and the reference reader all already take the closed reading. It adds force and no new meaning.
- **By lens:**
  - *Still decided:* R45 §2.1 pairs the closed definition with a writer MUST NOT and a consumer MUST NOT. R54 §2.6 adds the importer's conversion and changes nothing else; R146 moved the writer half's neighbours to Part 05 §4.3 and lists the consumer rules of Part 01 as staying (R146 §2.3). R148 and R152 change how an interval is numbered and specialised, not its bounds. No revision withdraws the consumer half.
  - *Contradiction:* None. Part 01 §2.3's definition, Part 01 §3.10 ('closed per §2.3'), Part 05 §4.3 and the registry's interval rules (`BETWEEN start_tick AND stop_tick`, `stop_tick < start_tick`) all take the closed reading. No draft mentions interval bounds.
  - *Exceeds the clause:* No. The clause says 'a consumer MUST NOT treat one as excluded' of a `stop_tick`; the proposal says the same. The clause's 'or a prefixed form' is not carried by the existing definition either, and the registries declare no prefixed pair.
  - *Actor:* A consumer, a Part 00 §2.4 actor, who can tell whether it complied: it counts `stop - start + 1` ticks and includes the stop tick in a containment test. It forbids a conclusion, not a method.
  - *Checks:* No validator observes a consumer, as with every consumer rule in Part 01 (§§2.6, 3.5, 3.8, 3.17, 3.18), none of which carries a label; a consumer can always comply. No label needed.
  - *Placement:* Part 01 §2.3 owns the meaning of an interval and Part 05 §1 gives a consumer only Part 05 §12, so Part 05 §13 (reader operations) is not a home. Part 05 §4.3 keeps the writer's half and cites 01 §2.3; the consumer's half has no other owner.
  - *Implementation and corpus:* Complies. escapewheel-reader observation.py computes spans as `stop_tick - start_tick + 1` (lines 248 and 288); the validator's rules use the closed comparison. No packet or check changes.
  - *Wording:* Fine as written, directly after the definition, which already names `stop_tick`.

### 3. R85 §2.3 at Part 01 §3.5 (ew-device-concept)

- **The revision decides:** a consumer MUST NOT read two rows sharing a parent and a port as one device
- **The part now says:** “a port says where something was plugged in and not what it was.”
- **Text to enter:** A consumer MUST NOT conclude from a shared parent and port that two devices are one.
- **Placement:** Part 01 §3.5 (ew-device-concept), the paragraph beginning 'Attachment names a device', as a new last sentence after '... so a port says where something was plugged in and not what it was.'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** Two devices sharing a parent and a port are not one device, and a consumer MUST NOT read them as one; nothing declares that they are: [the rest of the sentence unchanged]. ('rows' becomes 'devices', since R146 has Part 01 name no rows.)
- **Evaluation:** Restore the consumer rule as its own sentence at the end of the attachment paragraph instead of splicing it into the existing one. Nothing in the registry, reader or corpus depends on it.
- **By lens:**
  - *Still decided:* R85 §2.3 carries the consumer MUST NOT. No later revision cites or changes it; R146 §2.3 reworded two other phrases of Part 01 §3.5 ('a second device row', the camera-target sentence) and left this one. The indicative dates from the incorporating commit.
  - *Contradiction:* None. The registry's `core.devices.parent_port` description says the same in the indicative and cites Part 01 §3.5, and no rule makes port unique. One awkward neighbour already in the part: the sentence's example is the four bases of a quad-base probe, which the next paragraph makes one Device and four Probes, so it illustrates that a port does not identify and not two devices on one port.
  - *Exceeds the clause:* No in force or actor. Changing 'rows' to 'devices' is right for Part 01 but turns the clause into 'a consumer MUST NOT read two devices as one device', which is close to a tautology; the decided content is that a shared parent and port is no ground for identity.
  - *Actor:* A consumer, bound by what it concludes, and it can tell: it merged two devices on that ground or it did not.
  - *Checks:* A consumer rule no validator observes, like its neighbours in the same paragraph ('MUST report it as such', 'MUST NOT infer attachment'), which carry no label. Always compliable.
  - *Placement:* Part 01 §3.5 owns the device concept and already states the fact; no other part states the prohibition.
  - *Implementation and corpus:* Unobservable: the reader has no code reading `parent_port` (grepped escapewheel-reader and escapewheel-validator), and the writer only records it (sources/openephys.py, sources/nwb/devices.py). No packet or check changes.
  - *Wording:* The proposed splice makes one sentence carry a fact, a requirement, a second fact and an example across a semicolon and a colon; spec/CONTRIBUTING.md §4 says to split a requirement from its rationale. Leave the existing sentence alone and add the requirement after it.

### 4. R68 §2.5 at Part 01 §3.18 (ew-media-asset-concept)

- **The revision decides:** A consumer MUST NOT use pts to measure elapsed time or to align a frame to anything else in the packet
- **The part now says:** “so a consumer MUST NOT compare it between assets or use it to measure elapsed time”
- **Text to enter:** It is not a time on any clock the packet declares, so a consumer MUST NOT compare it between assets, use it to measure elapsed time, or use it to align a frame to anything else in the packet; what it locates is the frame inside the file.
- **Placement:** Part 01 §3.18 (ew-media-asset-concept), replacing the last sentence of the paragraph beginning 'A frame's time is a tick on a declared clock'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Evaluation:** Restore the alignment ban as proposed; it adds the clause's third prohibition to a sentence that already holds the other two and contradicts neither MAY in the section.
- **By lens:**
  - *Still decided:* R68 §2.5's third paragraph forbids both uses. R70 §2.3 says 'R68 §2.5 stands unchanged' and adds only seconds within the asset; R70 §2.4 reverses R68 §2.4, not §2.5. R146 §2.3 rewords §3.18's row and column language and not this sentence. The narrower form dates from incorporation.
  - *Contradiction:* None. The MAY two paragraphs below converts a timestamp to seconds of the asset's own timeline and the MAY above seeks a frame; neither relates a frame to anything on a packet clock. The frame's tick is a required fact, so no frame depends on its presentation timestamp for alignment. No draft touches media.
  - *Exceeds the clause:* No: 'or to align a frame to anything else in the packet' is the clause's wording, and the proposal keeps the existing premise and conclusion around it.
  - *Actor:* A consumer, bound by what it concludes; determinate.
  - *Checks:* No validator observes a consumer; always compliable; the sentence already carries two unlabelled consumer prohibitions.
  - *Placement:* Part 01 §3.18 already holds the sentence. 'Presentation timestamp' is the Part 01 term for R68's `pts`.
  - *Implementation and corpus:* Unobservable in the reader and validator (no code reads `pts`). escapewheel-aind video.py takes each frame's tick from the trigger file and uses presentation timestamps only to find which frames the file holds, which is a writer's reading of the container and not a consumer's alignment.
  - *Wording:* Reads correctly. The existing sentence before it cites '(§2.1)' for time basis, which is §2.2; that is outside this finding.

### 5. R69 §2.2 at Part 01 §3.18 (ew-media-asset-concept)

- **The revision decides:** a consumer MUST NOT read frame_index as a count of exposures, a camera's own frame counter, or an offset into anything but this asset
- **The part now says:** “The index counts the frames the asset **holds**, not the exposures the capture produced.”
- **Text to enter:** A consumer MUST NOT read a frame's index as a count of exposures, as a camera's own frame counter, or as an offset into anything but this asset.
- **Placement:** Part 01 §3.18 (ew-media-asset-concept), appended to the paragraph beginning 'The index counts the frames the asset **holds**'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Evaluation:** Restore as proposed at the end of the paragraph on what the index counts. It agrees with the registry's `structural_index` role and nothing in the implementation is affected.
- **By lens:**
  - *Still decided:* R69 §2.2 ends with the consumer MUST NOT. No later revision cites R69 §2.2; R146 §2.3 rewords the neighbouring sentences ('gets no row' to 'is not recorded') and leaves the fact this rule rests on. `git log -S'own frame counter'` finds the phrase only in the revision.
  - *Contradiction:* None. The registry declares `core.media_frames.frame_index` a `structural_index` (Part 02 §8.1: a zero-based offset into a stored sequence), contiguous from 0 within an asset, which is an offset into that asset and nothing else.
  - *Exceeds the clause:* No. The three prohibited readings are the clause's, with 'frame_index' rendered as 'a frame's index' so Part 01 names no column.
  - *Actor:* A consumer; determinate.
  - *Checks:* No validator observes a consumer; always compliable; no label, as for the section's other consumer rules.
  - *Placement:* Part 01 §3.18, after the indicative fact it enforces. No other part states it; Part 02 §8.1.1's consumer prohibition concerns source labels.
  - *Implementation and corpus:* Unobservable in the reader. The AIND video adapter numbers the frames the file holds with `arange` and keeps the camera's counter out of the index, as the rule assumes.
  - *Wording:* Fine as written; 'this asset' follows 'the asset' in the two sentences before it.

## Part 02

### 6. R128 §3.3 at Part 02 §2.3 (ew-resource-kind)

- **The revision decides:** a dense-array declaration's `axes_resource` MUST name a visible singleton table declaration
- **The part now says:** “Its `axes_resource` names a visible singleton table declaration.”
- **Text to enter:** Its `axes_resource` MUST name a visible singleton table declaration.
- **Placement:** Part 02 §2.3 (ew-resource-kind), second paragraph after the kind table, replacing the sentence 'Its `axes_resource` names a visible singleton table declaration.'
- **Observed by a check:** yes, or the sentence binds nothing.
- **Evaluation:** Restore as written: the keyword changes no conforming checker's behaviour because Part 02 §9.4 and `registry.resource.array_axes` already enforce the sentence, and the incorporated registry complies. The only residue is that sibling sentences of §2.3 stay in the indicative.
- **By lens:**
  - *Still decided:* Read R128 §3.3 in full and the later revisions touching the axes binding or §2.3 (R130, R145, R147): none changes what `axes_resource` names. The indicative dates from 6fc02db5, the commit that accepted and incorporated R128 together; that commit turned several other MUSTs of §§3.3-3.5 into the indicative too (the opaque sentence, 'Each `requires` member resolves', 'makes its axes-table singleton necessary'), so the mood is that commit's compression, not a later decision, and R128's crosswalk records no change of force.
  - *Contradiction:* None. Part 02 §9.4 already says the resource invariants enforce §§2.1-2.7 including 'the dense-array axes binding', the descriptor anchors `registry.resource.array_axes` at ew-resource-kind, and Part 03 follows the declaration. No open draft touches §2.3 (the sidecars draft amends §§2.2, 2.6, 11, 13 only).
  - *Exceeds the clause:* No. The proposed sentence is the clause's sentence with 'Its' for 'A dense-array declaration's'; force, scope and conditions are the same.
  - *Actor:* A conformance predicate on an artifact (the declaration), the form spec/CONTRIBUTING.md §4 allows and the form of the two neighbouring sentences ('A dense-array declaration MUST contain...', 'The axes table MUST have...').
  - *Checks:* Checked. spec/tools/checkers/registry_invariants.py `_resource_array_axes` fails a registry whose axes resource is missing, not table kind, not singleton or not visible (`_resource_direction`), and spec/tools/tests/test_registry_document.py has the `registry.resource.array_axes` mutation case.
  - *Placement:* Part 02 §2.3 owns the kind-specific declaration and is the section the invariant's anchor names, so no second owner arises. Part 09 §6.1 lists references, dependencies and catalog bindings but not the axes resource, so 'visible' for it has no other statement; that gap exists today and the restoration neither widens nor closes it.
  - *Implementation and corpus:* Complies. The two incorporated dense-array declarations (`core.array_asset_instances`, `analysis.array_asset_instances`) name `core.array_dimensions` and `analysis.array_dimensions`, both optional singleton tables; no extension registry under extensions/ declares a dense array. No validator change and no corpus packet is affected, since a conforming checker already enforces §2.3 through §9.4.
  - *Wording:* No renamed term or moved citation. It leaves the paragraph uneven only in that 'Presence of a dense-array instance makes its axes-table singleton necessary' and the opaque sentence stay indicative; the first audit classed those as stated or schema-carried, so that is a consistency remark and not a defect of this sentence.

### 7. R128 §3.5 at Part 02 §2.5 (ew-resource-presence)

- **The revision decides:** `analysis`, `compatibility_projection`, and `documentation` declarations MUST be optional
- **The part now says:** “These three classes are optional under §2.5.”
- **Text to enter:** A singleton declaration whose content class is `analysis`, `compatibility_projection` or `documentation` MUST declare `presence` `optional`.
- **Placement:** Part 02 §2.5 (ew-resource-presence), first paragraph, after the sentence ending 'Merely installing a registry does not.'; Part 02 §2.2's 'These three classes are optional under §2.5.' stays as the pointer
- **Observed by a check:** yes, or the sentence binds nothing.
- **Text first proposed, set aside:** Every `analysis`, `compatibility_projection`, and `documentation` declaration MUST be optional.
- **Evaluation:** Restore in §2.5, but name the `presence` field and the singleton mode, because 'a declaration MUST be optional' is ambiguous beside `lineage: optional` and means nothing for a catalog or family. Record separately that the descriptor's anchors for `registry.resource.instance` name neither §2.5 nor §2.2, a pre-existing gap under Part 02 §9.4 that a text fix should not close by editing the incorporated descriptor.
- **By lens:**
  - *Still decided:* Read R128 §3.5; R130 §3.7 edited §2.5 and R145 added the canonical-target rule to §2.2 without touching optionality. 'These three classes are optional under §2.5' was written by 6fc02db5 (R128's own acceptance-and-incorporation commit) and §2.5 never received the sentence it points at, so this is a dangling pointer, not a later decision.
  - *Contradiction:* The proposed sentence would follow 'An extension selects required or optional for each singleton', which it limits (an extension may declare analysis, compatibility_projection and documentation singletons), so it has to be worded as that limit and placed directly after it. It agrees with §2.2's 'required by class: no' column, Part 06 §2 and the sidecars draft, whose `core.sidecars` is a documentation singleton of `optional` presence.
  - *Exceeds the clause:* Scope matches once read against the schema: only a singleton has `presence`, and §2.5 already says catalog and family declarations have no minimum instance count. 'Every ... declaration MUST be optional' is looser than the clause needs, because a declaration also has `lineage`, whose vocabulary includes `optional`, and the adjacent sentences of §2.2 say these classes require or forbid lineage.
  - *Actor:* 'MUST be optional' names no field and so no observable outcome for a catalog or family declaration. Naming `presence` on a singleton makes it a decidable predicate on the declaration.
  - *Checks:* Checked. `_resource_instance` in spec/tools/checkers/registry_invariants.py reports a singleton of these classes whose `presence` is not `optional` under `registry.resource.instance`, with a mutation case in spec/tools/tests/test_registry_document.py; registry.schema.json alone does not tie `presence` to `content_class`.
  - *Placement:* Part 02 §2.5 is right: it is headed presence, is R128 §3.5's ledger target, and is where §2.2 already points. Cost: the descriptor anchors `registry.resource.instance` at ew-resource-kind and ew-resource-instance-model only, so Part 02 §9.4's 'Every descriptor anchor MUST identify every numbered-part clause defining the invariant' is unmet for this check (as it already is for the lineage halves stated in §2.2); the descriptor is an incorporated artifact and must not be edited inside this fix.
  - *Implementation and corpus:* Complies. Every non-canonical singleton in spec/artifacts/logical_schemas.json (`analysis.array_assets`, `analysis.array_dimensions`, `analysis.array_labels`, `analysis.spike_events`) is optional, and extensions/dynamic_foraging and extensions/vr_foraging declare no non-canonical resource. No packet or fixture changes status and no new validator check is needed.
  - *Wording:* Replace 'MUST be optional' with the field and value, and keep §2.2's pointer sentence as it is. Corrected sentence: 'A singleton declaration whose content class is `analysis`, `compatibility_projection` or `documentation` MUST declare `presence` `optional`.'

### 8. R128 §3.4 at Part 02 §2.6 (ew-resource-catalog-binding)

- **The revision decides:** a catalog declaration's `catalog_resource` MUST resolve to a singleton table declaration visible to that registry
- **The part now says:** “A catalog declaration names a visible singleton table declaration and one column.”
- **Text to enter:** A catalog declaration's `catalog_resource` MUST name a visible singleton table declaration, and its `resource_id_column` names one column of that table.
- **Placement:** Part 02 §2.6 (ew-resource-catalog-binding), first sentence, replacing 'A catalog declaration names a visible singleton table declaration and one column.'
- **Observed by a check:** yes, or the sentence binds nothing.
- **Text first proposed, set aside:** A catalog declaration's `catalog_resource` MUST resolve to a visible singleton table declaration, and it names one column of that table.
- **Evaluation:** Restore the keyword, but word it so each field has its own clause and the sentence still leads into the next one (finding 161). Rerun the sidecars draft's freshness gate, since that draft amends the same section.
- **By lens:**
  - *Still decided:* Read R128 §3.4; no later revision edits the first paragraph of §2.6 (R145 added canonical targets in §2.2, R143 and R147 leave it). The indicative is from 6fc02db5, R128's own incorporation, alongside the same compression elsewhere in §2.
  - *Contradiction:* None in the parts: §2.4 says 'A catalog resource and column satisfy §2.6' and §9.4 names 'unambiguous visible catalog bindings'. The open draft core-declares-a-catalog-of-sidecars amends §2.6's third paragraph only, but it was appraised on 9b8dcff, so its freshness gate has to be rerun after any edit to §2.6.
  - *Exceeds the clause:* The clause says 'MUST resolve to a singleton table declaration visible to that registry'; the proposal keeps that and appends 'and it names one column of that table', which is the current indicative half and adds nothing. No condition is dropped.
  - *Actor:* An artifact predicate on the catalog declaration, as spec/CONTRIBUTING.md §4 allows; the outcome is decidable from the registry and its core context.
  - *Checks:* Checked. `_resource_catalog` in spec/tools/checkers/registry_invariants.py requires the target to exist, be table kind, be singleton and pass `_resource_direction`, reported as `registry.resource.catalog`, whose descriptor anchors include ew-resource-catalog-binding; the test file carries the mutation case.
  - *Placement:* §2.6 is the owner and the anchored section; §2.4 only cites it. Visibility is also Part 09 §6.1's subject ('An extension registry reference, dependency, or catalog binding MUST target...'), but §2.6 already uses 'visible' and already carries the core half with MUST NOT, so the keyword adds no new duplication.
  - *Implementation and corpus:* Complies: the three incorporated catalog declarations name `core.array_assets`, `analysis.array_assets` and `core.media_assets`, all singleton tables in the core registry. No behaviour, packet or fixture changes.
  - *Wording:* As proposed, the tail 'and it names one column of that table' has an unclear 'it' (the declaration or `catalog_resource`), and finding 161's following 'Its `resource_id_column`' then has `catalog_resource` as its nearest antecedent. Use 'name', the verb §2.3 and the rest of §2.6 use, and give each field its own clause.

### 9. R128 §3.4 at Part 02 §2.6 (ew-resource-catalog-binding)

- **The revision decides:** `resource_id_column` MUST name a required string column with role `identifier`, identity `carried`, and free vocabulary
- **The part now says:** “That column is a required string identifier with carried identity and free vocabulary.”
- **Text to enter:** That column MUST be a required string identifier with carried identity and free vocabulary.
- **Placement:** Part 02 §2.6 (ew-resource-catalog-binding), second sentence, replacing 'That column is a required string identifier with carried identity and free vocabulary.'
- **Observed by a check:** yes, or the sentence binds nothing.
- **Text first proposed, set aside:** Its `resource_id_column` MUST name a required string column of that table with role `identifier`, carried identity and free vocabulary.
- **Evaluation:** Restore the keyword by changing 'is' to 'MUST be' in the existing sentence; it pairs with finding 160's reworded first sentence and matches the wording of §2.6's third paragraph. The checker already tests all five properties, so nothing else changes.
- **By lens:**
  - *Still decided:* Read R128 §3.4 and the later revisions that touch identifier columns and catalog tables (R143, R145, R147); none changes what a catalog's resource-ID column must be. The sidecars draft relies on exactly this eligibility for `core.sidecars.resource_id`.
  - *Contradiction:* None. §2.6's third paragraph states the same facts for the three incorporated tables and exempts `resource_id` from §4's integer `_id` rule 'for this exact field'; an extension catalog column of another name is not exempted by that paragraph, which is the present state and not something this sentence changes.
  - *Exceeds the clause:* The proposal adds 'of that table', which the clause implies, and otherwise lists the clause's five properties (required, string, role identifier, carried identity, free vocabulary). Nothing is added or dropped.
  - *Actor:* An artifact predicate on the declaration and the column it names; decidable from the registry.
  - *Checks:* Checked. `_resource_catalog` tests `type == string`, `presence == required`, `role == identifier`, `identity == carried` and `vocabulary == free`, and the `registry.resource.catalog` test case names a non-identifier column (`demo_id` on `demo.rows`).
  - *Placement:* §2.6, anchored by `registry.resource.catalog`. Part 02 §9.4's summary ('unambiguous visible catalog bindings') does not name column eligibility, but it says the invariants enforce §§2.1-2.7, so the sentence is the definition and no second owner exists.
  - *Implementation and corpus:* Complies: `resource_id` on `core.array_assets`, `analysis.array_assets` and `core.media_assets` is a required string identifier with carried identity and free vocabulary. No behaviour or corpus change.
  - *Wording:* With finding 160's sentence ending '...its `resource_id_column` names one column of that table', the smallest correct edit is to keep the current sentence and add the keyword, which also keeps the phrase 'required string identifier' that §2.6's third paragraph uses. The proposed 'Its `resource_id_column` MUST name...' is acceptable only if 160's tail is removed.

### 10. R22 §3 at Part 02 §9.3 (ew-registry-vocabularies)

- **The revision decides:** `label` MUST be recorded as the source emitted it; a writer MUST NOT rewrite it onto the normalized set
- **The part now says:** “- MAY carry the source's own label verbatim, which is open.”
- **Text to enter:** A writer MUST record `core.unit_quality_labels.label` as the source emitted it and MUST NOT replace it with the value it projects onto, which belongs in `normalized_label`. No checker verifies this, since a packet does not hold what the source emitted.
- **Placement:** Part 02 §9.3 (ew-registry-vocabularies), directly after the sentence beginning 'A scorer's own `label` is open'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** A writer MUST record `core.unit_quality_labels.label` as the source emitted it and MUST NOT rewrite it onto the normalized set; `normalized_label` is where the projection goes.
- **Evaluation:** Restore at Part 02 §9.3 with the unchecked label and without the undefined 'normalized set'; the reference writer and fixtures already comply. Leave Part 01 §3.15's MAY and §8.7's indicative sentence alone in this fix, and note that the writer's '|'-joined multi-label string is the one path a strict reader could question.
- **By lens:**
  - *Still decided:* Yes. R22 §3 read in full; R101 §§3.1, 3.9 and 3.10, R106 §3.1 and R105 §2.4 all rely on 'recorded as the source emitted it, never rewritten' and none changes it; R140 §3.1 rewrote only the authority spelling rule. `git log -S` shows the capitalised sentence never entered a part (the v0.2 compile, 4ce6f09c, wrote Part 01 §3.15's MAY; R106's commit f9e4a528 added §8.7's indicative), so no crosswalk row dropped it.
  - *Contradiction:* No contradiction, two awkward neighbours. Part 02 §9.3's 'Otherwise ... a writer MUST write the value as the source states it' could be read as already covering every open column without an `authority`; that reading collides with the reserved-value rule and §8.7's decoding rule, so it is confined to authority columns and does not already state this rule. Part 01 §3.15 says a label 'MAY carry the source's own label' while the registry declares `label` required; that mismatch exists today and the restored sentence neither creates nor resolves it.
  - *Exceeds the clause:* Scope and force match the clause (two capitals, one column). The proposal generalises 'rewrite `good` to `sua`' to 'rewrite it onto the normalized set', which is the clause's meaning; 'the normalized set' is not a term any part defines.
  - *Actor:* The clause's first MUST is passive ('`label` MUST be recorded'); the proposal correctly names a writer, who knows what the source emitted and can always comply.
  - *Checks:* No check can observe a rewrite: the registry rule `core.unit_quality_labels.projection_is_consistent` sees only that one (source, label) pair projects one way, and Tier 1 leaves an open column unconstrained. The writer can always comply and the sentence is scoped to one column, so it is acceptable only with the label 'No checker verifies this', as §9.3 already does for the reserved-set rule.
  - *Placement:* Part 02 owns it: the rule names a column, so Part 01 §3.15 cannot carry it (R146 has Part 01 name no column). Within Part 02, §9.3 holds 'A scorer's own `label` is open' and is the ledger target; §8.7 carries the same content in the indicative for a scorer's label and a source-provenance label together, and putting the keyword there would extend force to source-provenance labels, which R22 §3 did not decide. §9.3 is the destination; §8.7's indicative sentence then reads as the general description and is not a second requirement.
  - *Implementation and corpus:* Complies on the main path: `automated_labels` in escapewheel-writer/src/escapewheel_writer/sources/sorter_labels.py writes `label` as `str(labels[offset])` and the projection separately through `PROJECTION`. One edge: `manual_labels` joins several labels of one curation category into one string with '|' (note code SEVERAL_LABELS, exercised in tests/test_sorter_source.py); the note calls it verbatim, and it rewrites nothing onto the closed set, but a strict reading of 'as the source emitted it' could question a composed string. Fixtures (fixtures/corpus_packets/session.py) keep `good` beside `sua` and conform; no validator check is needed.
  - *Wording:* 'the normalized set' is undefined and '`normalized_label` is where the projection goes' is loose; the sentence also lacks the unchecked label. Corrected text below.

### 11. R22 §3 at Part 02 §9.3 (ew-registry-vocabularies)

- **The revision decides:** where a source's label has no honest projection, `normalized_label` MUST be null rather than forced
- **The part now says:** “`normalized_label` is null where a source's label has no honest projection.”
- **Text to enter:** Where a source's label has no honest projection onto `sua`, `mua` or `noise`, a writer MUST leave `core.unit_quality_labels.normalized_label` null and MUST NOT force a value. No checker verifies this, since no rule can tell a forced projection from an honest one.
- **Placement:** Part 02 §9.3 (ew-registry-vocabularies), after the sentence beginning 'A scorer's own `label` is open' (and after finding 15's sentence if that is restored)
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** Where a source's label has no honest projection onto the closed set, a writer MUST leave `normalized_label` null rather than force one.
- **Evaluation:** Restore at Part 02 §9.3 with the closed values named and the unchecked label added; writer, fixtures and registry description already agree. Nothing pays for it beyond the sentence.
- **By lens:**
  - *Still decided:* Yes. R22 §3 read in full; R101 §3.10 restates it as the standing example of recording a reason for absence, and R22 §5 depends on it for `core.units.quality_label` being null when the designated source's label does not project. No later revision touches the projection; the sentence never entered a part with a keyword (`git log -S'MUST be null rather than forced'` finds nothing outside revisions).
  - *Contradiction:* None. Part 03 §5.6 ('`normalized_label` is null where a source's label has no honest projection') and the registry description ('Null where the source's label does not project') state the same fact; the registry rule `projection_is_consistent` counts null as a projection value, which fits. §8.7's 'a writer that can decode a source's code MUST store the decoded value' does not reach a label with no member of the closed set to decode onto.
  - *Exceeds the clause:* Force and scope match. The clause is passive ('it MUST be null'); naming a writer adds an actor the clause implied and Part 00 §2.4 requires.
  - *Actor:* A writer, which can always comply by writing null. 'Honest projection' is a judgement only the writer can make, so the outcome is determinate for the writer and for nobody else.
  - *Checks:* Unobservable: no rule can tell a forced projection from an honest one (Tier 1 checks membership of the closed set, `projection_is_consistent` checks only that a pair projects one way). The writer can always comply and the sentence is scoped to one column, so it must carry the unchecked label.
  - *Placement:* Part 02 §9.3, beside the closed column's row and the sentence on a scorer's `label`. Part 03 §5.6 uses the fact as an illustration of one-null and is not its owner; Part 01 §3.15 may not name the column.
  - *Implementation and corpus:* Complies: `PROJECTION` in escapewheel-writer/src/escapewheel_writer/sources/sorter_labels.py maps `non_soma` to None, `automated_labels` gives any label outside the mapping a null projection with a LABEL_UNPROJECTED note, and `manual_labels` leaves a multi-label entry unprojected. The corpus row `(2, 'bombcell', 'non_soma', None, None)` in fixtures/corpus_packets/session.py conforms. No packet becomes non-conforming and no validator check is implied.
  - *Wording:* 'the closed set' and 'force one' need their referents, and the sentence needs the unchecked label. If finding 15 is restored in the same paragraph, one closing sentence can label both ('No checker verifies either obligation').

### 12. R126 §3.3 at Part 02 §9.4 (ew-registry-conformance)

- **The revision decides:** the same precedence MUST determine a partially evaluated phase's state from its outcome records
- **The part now says:** “A definitive violation dominates an independent unsupported or incomplete phase; otherwise precedence is `invalid`, `unsupported`, `incomplete`, then `valid`.”
- **Text to enter:** A checker MUST determine a partially evaluated phase's state from its outcome records by the same precedence.
- **Placement:** Part 02 §9.4 (ew-registry-conformance), in the paragraph beginning 'Within a phase, outcomes are ordered', after 'Only completed passing phases produce `valid`.'
- **Observed by a check:** yes, or the sentence binds nothing.
- **Text first proposed, set aside:** The same precedence MUST determine a partially evaluated phase's state from its outcome records.
- **Evaluation:** Restore with a checker as the subject; the reference checker's `_phase` already does this and nothing in the corpus moves. Decide in the same edit whether the neighbouring document-level precedence sentence also takes a keyword, since the restored MUST refers to it.
- **By lens:**
  - *Still decided:* Yes. R126 §3.3 read in full; R127 §3.1 and Part 02 §9.5 both leave 'state precedence' with §9.4, and no revision after R126 mentions a partially evaluated phase. The part's text dates from the commit that accepted and incorporated R126 (278c2d6a); the sentence was never in a part, and R126's crosswalk does not drop it, so the loss is compression.
  - *Contradiction:* None with §9.4, §9.5 or artifacts/registry_result.schema.json: the schema requires an `invalid`, `unsupported` or `incomplete` phase to hold at least one outcome and a `passed` phase to hold none, so a partially evaluated phase can never take the precedence's last term. Awkwardness: the precedence it points to ('A definitive violation dominates ...; otherwise precedence is ...') is itself in the indicative, so a lone MUST would rest on a sentence without a keyword.
  - *Exceeds the clause:* Same force as the clause. Naming a checker adds the actor R126 §3.3's lead sentence ('A registry checker MUST evaluate these phases') already supplies; nothing else is added or dropped.
  - *Actor:* The proposed sentence is actorless ('The same precedence MUST determine ...'), which spec/CONTRIBUTING.md §4 rules out. The actor is a checker (Part 00 §2.4), which can comply and can tell: the outcome is the phase record's `state`.
  - *Checks:* Checkable: the phase state is in the registry result, and a registry-contract case mixing outcome states in one phase would observe a violation. No such case exists today (spec/tools/tests/test_registry_document.py tests dominance only between phases), so the sentence needs no unchecked label but has no corpus witness.
  - *Placement:* Part 02 §9.4 owns phase algorithms and state precedence (§9.5 says so). The sentence belongs in the paragraph beginning 'Within a phase, outcomes are ordered', after 'Only completed passing phases produce `valid`.', where the clause had it.
  - *Implementation and corpus:* Complies: `_phase` in spec/tools/checkers/registry_document.py (identical copy in escapewheel-validator/src/escapewheel_validator/registry_document.py) takes the maximum outcome state under `_PRECEDENCE`, the same table `_complete` uses for the document. One latent edge the sentence does not create: a phase whose only outcomes are `skipped` would get state `skipped` with outcomes, which the result schema rejects; no code path emits a skipped outcome today. No fixture changes.
  - *Wording:* Name the checker and put it before the keyword. The surrounding paragraph is indicative, so the same repair should either capitalise the document-level precedence sentence or state this one in the indicative as well; mixing the two leaves the MUST depending on an unbound sentence.

### 13. R26 §3 at Part 02 §10.2 (ew-tier-2-rules)

- **The revision decides:** an advisory rule MUST NOT run unless the caller asks for it
- **The part now says:** “it is off by default and MUST NOT be `error`, so that enabling it cannot change whether a packet”
- **Text to enter:** A rule MAY be `advisory`. A validator MUST NOT run an advisory rule unless its invocation asks for advisory rules, and an advisory rule MUST NOT be `error`, so that enabling it cannot change whether a packet previously passed.
- **Placement:** Part 02 §10.2 (ew-tier-2-rules), replacing the sentence beginning 'A rule MAY be `advisory`, in which case it is off by default'
- **Observed by a check:** yes, or the sentence binds nothing.
- **Text first proposed, set aside:** A rule MAY be `advisory`, in which case a validator MUST NOT run it unless the caller asks for it, and it MUST NOT be `error`, so that enabling it cannot change whether a packet previously passed.
- **Evaluation:** Restore the keyword in §10.2, but as two subjects (the validator, then the rule) and without 'the caller', which Part 00 §2.4 resolves to a consumer. The reference validator and its tests already behave this way.
- **By lens:**
  - *Still decided:* Yes. R26 §3 read in full; R82 §1.2 and R95 paraphrase it as 'off by default' without amending it, and R125 §1.1's crosswalk replaces Part 02 §10.2 while assigning it 'severity, advisory behavior' with semantic effect confined to the rule language. 'Off by default' predates R125 (it is in the v0.2 compile, 4ce6f09c), and `git log -S'MUST NOT run unless'` finds the capitalised form in no part, so no revision chose the indicative.
  - *Contradiction:* None. §10.2's capitalised neighbours (a validator MUST expose the choice; a report MUST state whether advisory rules were run) presuppose the default, Part 05 §9.2 cites §10.2 only for 'MUST NOT be an error', Part 05 §5.2 does not oblige a validator to run every declared rule, and Part 05 §9.5 counts only evaluations 'the subject requires'. registry.schema.json's `advisory` default false and its level constraint agree.
  - *Exceeds the clause:* Force matches the clause. 'The caller' is the clause's word, but Part 00 §2.4 makes `caller` another name for a consumer, so the proposal would literally stop a writer validating its own staged packet from asking for advisory rules, a narrowing R26 did not decide.
  - *Actor:* The proposal names a validator for the first obligation and then continues 'and it MUST NOT be `error`', where 'it' now reads as the validator; the second obligation is a property of the rule. spec/CONTRIBUTING.md §4 asks for a split where one sentence binds different subjects.
  - *Checks:* Observable, so no label is needed: a report states whether advisory rules were run, and a default run that reports an advisory rule's finding is a visible violation. escapewheel-validator/tests/test_rules.py::test_advisory_rules_are_off_by_default exercises exactly this.
  - *Placement:* Part 02 §10.2. A validator's behaviour would ordinarily be Part 05's, but R125 §1.1 assigns advisory behaviour to §10.2, the two neighbouring validator obligations are already there, and Part 05 §9.2 cites it; stating the default in Part 05 as well would create the second owner Part 00 §8 forbids.
  - *Implementation and corpus:* Complies. `validate` and `check_packet_manifest` in escapewheel-validator/src/escapewheel_validator/validator.py default `advisory=False`; `_tier2` in rules.py and the generator in generate.py skip a rule with `advisory` unless the flag is set; the CLI exposes `--advisory`; the writer never passes the flag. The two advisory core rules (`core.units.observation_declared`, `core.event_streams.observation_declared`) are `info`. No packet or fixture changes and no new check is needed.
  - *Wording:* Split the sentence so the rule's property and the validator's duty each have their own subject, and replace 'the caller' with the invocation. The rest of the paragraph stands.

## Part 03

### 14. R129 §3.9 at Part 03 §2 (ew-portable-profile-technologies)

- **The revision decides:** lack of a recognized payload format or specialized decoder MUST NOT by itself invalidate the resource
- **The part now says:** “Unknown opaque representations do not invalidate a packet.”
- **Text to enter:** A validator MUST NOT report an opaque resource, or the packet holding it, as non-conforming solely because it does not recognize the payload's format or has no decoder for it.
- **Placement:** Part 03 §2 (ew-portable-profile-technologies), replacing the sentence 'Unknown opaque representations do not invalidate a packet.'
- **Observed by a check:** yes, or the sentence binds nothing.
- **Text first proposed, set aside:** An unknown opaque representation, or the lack of a specialized decoder for one, MUST NOT by itself invalidate the resource or its packet.
- **Evaluation:** Restore the force, but as a validator obligation in Part 05 §10's terms, replacing the indicative sentence in Part 03 §2; the proposed actorless 'MUST NOT ... invalidate' is the passive form the style guide rules out. The reference validator and the opaque corpus cases already comply.
- **By lens:**
  - *Still decided:* Yes. R143 extended Part 03 §2's opaque paragraph with ownership (its crosswalk row 'extend in place') and cites R129 §3.9 as still forbidding the descriptor to enumerate opaque formats; Part 12 §5 (from R143/R144) has a build 'record no format'. Neither restates nor withdraws the MUST NOT, and the indicative sentence dates from cbfbccf3.
  - *Contradiction:* None. Part 05 §10 defines conformance as no error-level finding 'from the checks of this part', and Part 05 §5.3's only opaque check, `physical.opaque_name_portability`, is a `warning` about names; Part 05 §9.4 already forbids turning an inability to evaluate into an error. The restored rule agrees with all three and with Part 02 §2.3.
  - *Exceeds the clause:* The proposed text adds 'or its packet' (the clause says 'the resource') and turns 'lack of a recognized payload format' into 'an unknown opaque representation'; both are within the clause's sense, since a packet's verdict composes from its resources' findings (Part 05 §9.5). It keeps 'by itself'.
  - *Actor:* The proposed sentence is actorless ('MUST NOT ... invalidate'), which spec/CONTRIBUTING.md §4 tells authors to avoid. The only actor that decides validity is the validator (Part 00 §2.4), which can comply and can tell that it did: it reports no error-level finding on that ground.
  - *Checks:* Observable: a corpus packet holding an opaque payload of a format the validator does not parse must pass, and fixtures/packets `owned_opaque_object`, `owned_opaque_prefix`, `owned_opaque_singleton` and `owned_opaque_encoded_name` are such cases. No label needed.
  - *Placement:* Part 03 §2 holds the sentence now and owns 'opaque maps to no generic interface'; Part 03 already binds validators (§§5.3, 5.5, 6.4). Part 05 §10 entails the outcome but does not state it, so capitalising it here makes no second owner; Part 05 §5.3 would be the other credible home and is not needed.
  - *Implementation and corpus:* Complies: escapewheel-validator shim/owned.py `check_packet_owned_opaque` reads only the payload's listing and names, and opaque.py `findings` reports names only; nothing inspects a payload's format. No corpus packet changes verdict and no new check is needed.
  - *Wording:* Name the validator and use Part 05 §10's vocabulary ('report ... as non-conforming') rather than 'invalidate'. Replace the indicative sentence 'Unknown opaque representations do not invalidate a packet.' rather than adding beside it.

### 15. R129 §3.9 at Part 03 §2 (ew-portable-profile-technologies)

- **The revision decides:** a generic reader MUST resolve and list an opaque resource and expose its catalog identity and location
- **The part now says:** “a generic reader lists its identity and location but need not retrieve, parse, decode, or render it.”
- **Text to enter:** An opaque resource has no generic value interface: a reader MUST list it with its identity and location, and need not retrieve, parse, decode, or render it.
- **Placement:** Part 03 §2 (ew-portable-profile-technologies), replacing the sentence beginning 'An opaque resource has no generic value interface:'
- **Observed by a check:** yes, or the sentence binds nothing.
- **Text first proposed, set aside:** An opaque resource has no generic value interface: a generic reader MUST resolve and list it and expose its catalog identity and location, but need not retrieve, parse, decode, or render it.
- **Evaluation:** Capitalise the duty in place, binding 'a reader' rather than the undefined 'generic reader', and keep the part's 'identity and location': the proposed 'catalog identity' is a retired term and 'MUST resolve' conflicts with a reader's permitted failure on an unusable declaration. The reference reader already lists opaque resources without touching their payloads.
- **By lens:**
  - *Still decided:* Yes. R143 extended the paragraph with ownership and added no reader rule; R146 §3.7 moved the reader-independence paragraph of Part 04 §5.3 to Part 05 §14.3 as a prohibition ('A reader MUST NOT require ... to ... list its resources') and did not touch Part 03 §2 (its crosswalk has no row for it). The indicative 'lists' dates from cbfbccf3; commit 57e3b41a later renamed the packet's catalog to the manifest throughout.
  - *Contradiction:* The clause's 'MUST resolve' is absolute, while Part 04 §10 has a reader fail the operation when the bound registry declaring a resource is missing or fails its digest, and Part 05 §14.3 says 'An unusable declaration need not produce a result for a reader operation'. A resource known to be opaque has had its declaration resolved, so the duty that remains is to list it; keeping 'resolve' would sit against those two sentences.
  - *Exceeds the clause:* The proposed text matches the clause's duty and the part's 'need not' list. It drops the clause's 'integrity-check' and 'stream' from that list, which are non-requirements already omitted by the part; 'Requested validation owns any integrity check' is Part 04 §5.3's subject.
  - *Actor:* 'generic reader' is not a Part 00 §2.4 actor and no part defines 'generic'; the actor is the reader, 'bound by what it returns', and the duty binds every reader. The outcome is observable: the resource appears in the reader's listing with its identity and location, and no payload access is needed.
  - *Checks:* No packet check observes a reader, as for every reader rule in Part 03 (§§3.1, 5.3, 5.5), none of which carries a label. A reader test observes it: escapewheel-reader tests/test_resources.py asserts `packet.resource('core.qc_report').kind == 'opaque'` and `packet.path(...)` for an opaque payload.
  - *Placement:* Part 03 §2 holds the sentence and owns 'opaque maps to no generic interface', a choice of this profile; Part 03 already binds a reader in §§3.1, 3.3, 4, 5.3, 5.5 and 6.4, and Part 05 §1 lists only which Part 05 sections bind a reader. Part 05 §14.3 states the negative (no receipt needed to list) and not this duty, so no second owner.
  - *Implementation and corpus:* Complies: `Packet.resources(kind=...)` and `Packet.resource` in escapewheel-reader packet.py list every manifest entry with `resource_id`, `declaration_id`, kind and `uri`, and `Packet.path` resolves its location, without reading the payload. No corpus packet or validator check is affected.
  - *Wording:* 'catalog identity' uses the term 57e3b41a retired for the manifest, and 'catalog' now means a Part 02 catalog table; the part's own 'identity and location' is the current wording. Drop 'generic' and 'resolve and'.

### 16. R3 §5.1 at Part 03 §6.2 (Axis order)

- **The revision decides:** readers MUST NOT assume their language presents axes in declared order; a column-major binding enumerates them in reverse
- **The part now says:** “A column-major binding enumerates axes in reverse.”
- **Text to enter:** A reader MUST NOT treat the order in which its language enumerates an array's axes as the declared order: `axis_index` counts axes in stored order, and a column-major binding enumerates them in reverse. The client adapts; the format does not. No check observes this.
- **Placement:** Part 03 §6.2 (Axis order), replacing the second paragraph ('A column-major binding enumerates axes in reverse. The client adapts; the format does not.')
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** A reader MUST NOT assume that its language presents axes in declared order: a column-major binding enumerates axes in reverse. The client adapts; the format does not.
- **Evaluation:** Restore the reader obligation in Part 03 §6.2, worded as an outcome ('MUST NOT treat ... as the declared order') rather than 'MUST NOT assume', and labelled unchecked since nothing observes a reader's axis handling. The Python reference reader complies by construction and no packet changes.
- **By lens:**
  - *Still decided:* Yes. The sentence 'The client adapts; the format does not' entered with the v0.2 compilation (4ce6f09c), which dropped the MUST; no accepted revision other than R3 mentions column-major order (searched 'column-major', 'axis order', 'slowest-varying', 'stored order'). R129 §4 says it does not change 'Zarr axis order', R147 keeps `axis_index` 'in stored order', and R111's actor survey did not list §6.2. R3 §5.1's last sentence on `dimension_names` was changed later and is not part of this finding.
  - *Contradiction:* None. Part 03 §6.2's `transpose` prohibition, §6.5's rule that `dimension_names` follows the axes table by `axis_index`, and the registry's description of `axis_index` ('0-based axis position in stored order (Part 03 §6.2)') all assume stored order is the declared order; the open byte-order draft does not touch §6.2.
  - *Exceeds the clause:* The proposed text matches the clause in force and scope and keeps the part's two existing sentences. Singular 'A reader' for 'Readers' changes nothing.
  - *Actor:* A reader is a Part 00 §2.4 actor, and 'binding' and 'client' are its declared aliases. 'MUST NOT assume' names a state of mind rather than an outcome; the determinate form is that a reader does not treat its language's enumeration order as the declared order when it resolves `axis_index`. The MUST is warranted: a wrong axis mapping returns wrong data without an error.
  - *Checks:* No registry rule, schema, validator check or corpus case observes a reader, and the reference reader is row-major, so its tests cannot fail on this; only conformance/zarr-probe's Julia script exercises a column-major binding. A reader can always comply and the sentence is scoped to axis enumeration, so under the unchecked-requirement rule it must carry a label, although the part's other reader rules (§§5.3, 5.5) carry none.
  - *Placement:* Part 03 §6.2 owns axis order and holds the two sentences the rule belongs with; no other part states it, and Part 02 §8.1's client-boundary rule concerns index base. Part 03 already binds readers, so no second owner and no Part 05 placement is needed.
  - *Implementation and corpus:* The reference reader complies trivially: `ArrayResource.shape` (escapewheel-reader resources.py) and axes.py present axes 'in stored order (Part 03 §6.2)' and numpy enumerates slowest-varying first. No packet, corpus case or validator check is affected.
  - *Wording:* Replace 'assume that its language presents axes in declared order' with an outcome, and say what the declared order is (`axis_index`, stored order) so the sentence stands without R3's surrounding text.

### 17. R129 §3.4 at Part 03 §6.4 (ew-array-codecs)

- **The revision decides:** a conforming reader MUST expose logical dense-array values for every valid v2 resource whose metadata matches a floor pattern
- **The part now says:** “An interface's `reader_floor` states what every conforming reader supports for logical-value access.”
- **Text to enter:** A conforming reader MUST expose the logical values of every valid v2 array that the v2 reader floor admits.
- **Placement:** Part 03 §6.4 (ew-array-codecs), in the paragraph beginning 'The v2 reader floor is exactly', after the sentence ending 'unmentioned configuration members do not participate.'
- **Observed by a check:** yes, or the sentence binds nothing.
- **Text first proposed, set aside:** A conforming reader MUST expose the logical values of every valid v2 array whose metadata matches a floor pattern.
- **Evaluation:** Restore the v2 reader duty beside the v3 one, phrased by what the floor 'admits' so it survives the open byte-order draft, which rewrites this paragraph and would narrow the v2 floor. The reference reader already complies; land it with or before that draft's refresh, since both edit the same paragraph.
- **By lens:**
  - *Still decided:* Yes. R137 §3.1 restated the reader duty for v3 only, and its crosswalk row for Part 03 §6.4 says 'the v2 floor and its rule are unchanged' and §5 'No accepted clause is superseded', so R129 §3.4's duty for v2 stands. The open draft 'The reader floor bounds an array's byte order' reads the current parts as already obliging every conforming reader to decode a v2 array inside the floor and proposes to narrow that floor; it is a draft, not a decision.
  - *Contradiction:* None with accepted text: Part 03 §2 defines `reader_floor` as 'what every conforming reader supports', and §6.1's per-resource failure applies only where support is lacking. It sits beside the open byte-order draft, which rewrites the same paragraph, measures that two of five probed readers fail a big-endian v2 array inside today's floor, and would add a `dtype_byte_orders` bound that is not a 'pattern'; the proposed words 'whose metadata matches a floor pattern' would then be wrong, and the draft's baseline would need refreshing after an edit to §6.4.
  - *Exceeds the clause:* The clause says 'every valid current-profile Zarr resource whose codec sequence or metadata matches an applicable floor entry'; the proposed sentence takes its v2 half and adds nothing. 'Logical values' for 'logical dense-array values' follows the v3 sentence.
  - *Actor:* 'A conforming reader' is the Part 00 §2.4 reader and the form the v3 sentence in the same section uses. The outcome is observable: values are exposed for an array inside the floor. The MUST is an interoperability floor, which spec/CONTRIBUTING.md §4 admits.
  - *Checks:* Observable by reader tests and by conformance/zarr-probe, whose `write.py` writes `v2_zstd` and `v2_blosc_zstd_shuffle` arrays that each probed reader reads back; no packet check observes a reader, as for the v3 sentence, which carries no label. The corpus references no v2 array.
  - *Placement:* Part 03 §6.4 owns the Zarr floors and already holds the v3 duty and Part 03 §5.5 the Parquet one; restoring v2 beside them completes the set. No other part states it with a keyword, so no second owner.
  - *Implementation and corpus:* Complies: `ArrayResource.open` (escapewheel-reader resources.py) opens a v2 store through zarr-python with `zarr_format=2`, which decodes every current v2 floor entry, and `zarr_floor_admits` (profile.py) matches `metadata_patterns`. No packet becomes non-conforming and no validator check is needed.
  - *Wording:* Say 'that the v2 reader floor admits' rather than 'whose metadata matches a floor pattern': 'admits' is the section's own verb ('The v3 reader floor admits exactly', 'A floor without `sharding` admits no sharded pipeline') and stays true if the byte-order draft adds a bound that is not a pattern.

## Part 04

### 18. R36 §2.3 at Part 04 §5.3 (ew-external-resource-verification)

- **The revision decides:** level 3a establishes that the URI resolves, that `size_bytes` holds, and that the declared `codecs` match the metadata document
- **The part now says:** “| 3a | the external resource exists and lists |”
- **Text to enter:** | 3a | the external resource exists and lists, and its recorded `size_bytes` holds |
- **Placement:** Part 04 §5.3 (ew-external-resource-verification), the 3a row of the level table
- **Observed by a check:** yes, or the sentence binds nothing.
- **Evaluation:** Safe as written: the size comparison is R36's and R14's, no later revision removed it, and the reference validator already makes it at level 3a. Leave the retired `codecs` half out, as proposed.
- **By lens:**
  - *Still decided:* Yes for the size half. R36 §2.3's table puts '`size_bytes` holds' in 3a, R14 §2.3.2 has the requested mode check `size_bytes` where declared, and R51 §2.3 still describes the list level as 'sizes and codecs agree'. R129 §3.6 retired the manifest `codecs` field, so that half is rightly left out. R136 §§3.2–3.5 redefine a prefix's `size_bytes` as the sum of its objects' sizes and touch levels 2, 3b and 3c only. The narrow row 'exists and lists' dates from the v0.2 compilation 4ce6f09c, not from a revision.
  - *Contradiction:* None. Part 04 §4.3 defines `size_bytes` for a prefix, §5.2 says it records what held when checked, §5.5 already speaks of a recorded `size_bytes` being verified, and §10's `packet.resource.member_size` compares the manifest with itself. Part 05 §5.3 has a validator read format-owned metadata 'under Part 04 §5.3', which the row never mentioned and still does not; that is a separate gap, not a conflict.
  - *Exceeds the clause:* No. The row says what the level establishes and carries no keyword; 'its recorded `size_bytes`' keeps the clause's and R14's 'where declared', since the field is optional (§4.1).
  - *Actor:* A table row defining a level, not an obligation; the binding sentence is the existing 'a report MUST state which level it reached', which binds a validator's report. A validator can tell whether it compared the size.
  - *Checks:* Observable: the reference validator reports `external.size_bytes` at error when the listed total differs (shim/external.py `_compare_external`), and tests/test_shim_external.py covers it.
  - *Placement:* Part 04 §5.3 owns the level table (R146 moved only its reader paragraph to Part 05 §14.3). No other part defines level 3a, so no second owner.
  - *Implementation and corpus:* Complies: `_compare_external` compares `found.size_bytes` with the entry's `size_bytes` whenever the external mode runs, before any digest. No conformance packet declares an external resource. No new check is needed.
  - *Wording:* Reads consistently with the 3c row ('its recorded `digest` holds'). Finding 40 (per-member sizes, left as a judgement) would add a clause to this row if taken; the row as proposed does not prejudge it.

### 19. R36 §2.3 at Part 04 §5.3 (ew-external-resource-verification)

- **The revision decides:** a validator MUST NOT run the digest level unless separately asked
- **The part now says:** “Structural validation MUST NOT reach the network. Levels 3a to 3c run only in a requested mode.”
- **Text to enter:** A validator MUST NOT run level 3c on a request for level 3a or 3b alone.
- **Placement:** Part 04 §5.3 (ew-external-resource-verification), after 'Levels 3a to 3c run only in a requested mode.' (and after finding 29's sentence if both go in)
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** Levels 3a to 3c run only in a requested mode, and a validator MUST NOT run level 3c unless it is separately asked.
- **Evaluation:** The prohibition stands, but 'unless it is separately asked' does not say separate from what and could be read against the one request that covers level 2 and 3c under R52 §2.3, which the reference validator's `--checksums` is. Restore it as 'A validator MUST NOT run level 3c on a request for level 3a or 3b alone.'
- **By lens:**
  - *Still decided:* Yes. R36 §2.3: 'MUST NOT run 3b unless separately asked', where 3b is today's 3c; R51 §2.3 keeps the levels as separate requests 'as R36 §2.3 requires'. R136 §3.5 lets 3c be reached from store checksums without reading, which weakens the cost argument and withdraws nothing. R52 §2.3 ties level 2 to the same request as the external digest, so 'separately' means apart from 3a and 3b, not apart from level 2. The indicative sentence is from the v0.2 compilation 4ce6f09c.
  - *Contradiction:* None in Part 04 §5.3, §5.4 or Part 05 §5.3 (whose 'checksums outside SQL' names no level or request). The proposed 'unless it is separately asked' does not say separately from what; read as 'apart from every other level' it would forbid the single request that R52 §2.3 makes cover level 2 and the external digest together.
  - *Exceeds the clause:* The force is the clause's. The ambiguity above could be read as a wider prohibition than R36 and R52 together decided, so the sentence should name 3a and 3b as what a request for 3c is separate from.
  - *Actor:* A validator, before the keyword; a test can observe whether a request for 3a alone causes digests to be established.
  - *Checks:* No packet check or corpus case observes it; it is validator behaviour, testable in the validator's suite, always compliable and scoped to level 3c.
  - *Placement:* Part 04 §5.3, where the weaker sentence is. §5.4 gives the store-digest level its own request ('asked to verify content without reading'); no other part states this rule.
  - *Implementation and corpus:* Complies with the reworded sentence: `shim/external.py` `_compare_external` establishes an external digest only under `checksums`, which `--external` and `--store-digests` do not set (`verification.py`, `scripts/cli.py`). `--checksums` runs level 2 and 3c on one request (`validator.py` `_check_resources`), which the proposed wording could be read to forbid and the reworded one does not.
  - *Wording:* Keep the indicative sentence about the requested mode as it is (its force is finding 12's question) and add one sentence stating the outcome.

### 20. R51 §2.4 at Part 04 §5.4 (ew-prefix-resources)

- **The revision decides:** A validator that skipped every member because none recorded a store_digest reports that it verified nothing, not that everything passed
- **The part now says:** “A validator MUST report what a verification pass skipped”
- **Text to enter:** A validator that skipped every member because none recorded a `store_digest` reports that the comparison verified nothing, not that it passed.
- **Placement:** Part 04 §5.4 (ew-prefix-resources), after '... is **not checked**, and the report MUST say how many were skipped.'
- **Observed by a check:** yes, or the sentence binds nothing.
- **Text first proposed, set aside:** A validator that skipped every member because none recorded a `store_digest` reports that it verified nothing, not that everything passed.
- **Evaluation:** Restore it, scoped to the store-digest comparison, since the same pass does verify the listing. It enters without a keyword, as the clause has none, so it describes the outcome and binds nothing; giving it MUST force would need a revision.
- **By lens:**
  - *Still decided:* Yes. R51 §2.4 states it; R136 §3.6 restates the store-digest rules, keeps the 'not a checksum verification' requirement by name and does not mention or withdraw this sentence. It was never in a part (`git log -S'verified nothing'` over the parts is empty).
  - *Contradiction:* None. Part 04 §5.4 requires the skipped count and forbids reporting a store-digest pass as a checksum verification; neither says what the outcome is when nothing was compared, and §5.3's 'a report MUST state which level it reached' is left open on whether 3b was reached in that case.
  - *Exceeds the clause:* The clause carries no capital keyword, so it enters as an indicative sentence and binds nothing under Part 00 §2.5; adding MUST would exceed the revision and needs one. Keep the clause's condition ('because none recorded a `store_digest`'); widening it to a store that reports none is plausible but is not what the clause says.
  - *Actor:* A validator is named. 'verified nothing' is too broad as written: the same pass has listed the resource and compared sizes at 3a, so the sentence must say that the store-digest comparison verified nothing.
  - *Checks:* Not a keyword requirement, so nothing is owed. The behaviour is observable in the validator's suite (tests/test_shim_external.py asserts the summary omits `store_digest` when every member was skipped).
  - *Placement:* Part 04 §5.4, in the paragraph that defines the store-digest comparison and its skips, which is itself written in the indicative. No other part speaks of this outcome; Part 02 §9.4's skipped states concern registry checking.
  - *Implementation and corpus:* Complies in substance: `shim/external.py` `_compare_members` reports `external.no_store_digest` (warning, 'N of N member(s) not checked') and adds `store_digest` to the compared fields only when at least one member was compared, so `external.verified` does not claim the level.
  - *Wording:* Scope 'verified nothing' to the comparison, and say 'not that it passed'.

### 21. R80 §2.1 at Part 04 §5.5 (ew-source-resolution)

- **The revision decides:** where source is present the entry's uri MUST be a path relative to the source and MUST NOT be absolute
- **The part now says:** “its `uri` is then a relative reference resolved against wherever that source is”
- **Text to enter:** An entry carrying `source` MUST carry a `uri` that is a relative reference (Part 03 §4 (anchor `ew-portable-uri-rules`)), which resolves against wherever that source is. Neither field is a location.
- **Placement:** Part 04 §5.5 (ew-source-resolution), replacing 'its `uri` is then a relative reference resolved against wherever that source is (Part 03 §4 (anchor `ew-portable-uri-rules`)), and neither field is a location.'
- **Observed by a check:** yes, or the sentence binds nothing.
- **Text first proposed, set aside:** Where an entry carries `source`, its `uri` MUST be a relative reference (Part 03 §4), resolved against wherever that source is, and MUST NOT be absolute; neither field is a location. ('a path relative to' is now 'a relative reference', R143 §3.4.) A writer is the actor to name.
- **Evaluation:** Restore the requirement as a predicate on the entry, with one MUST: a relative reference is by definition not absolute. Do not name a writer as the proposal suggests, because the reference validator reports the violation at error and Part 05 §10 forbids failing a packet for a writer-only obligation.
- **By lens:**
  - *Still decided:* Yes. R80 §2.1 has MUST and MUST NOT; R143 §3.4 renames 'a path relative to' as 'a relative reference' (crosswalk: revise in place) and states 'No accepted clause is superseded'. The indicative 'is then' dates from the incorporating commit 476a47f1.
  - *Contradiction:* None. Part 03 §4 permits a `uri` relative to a source and has a reader or validator resolve it against the source's location; Part 04 §5.1 lets an external entry be relative; Part 12 §5 has a build refuse a `uri` that is neither absolute nor a relative reference. Part 05 §10 forbids a validator to report a packet non-conforming for an obligation that binds only a writer, so the rule must stay a predicate on the entry, as the clause wrote it, and must not be recast as 'A writer MUST' as the proposal suggests.
  - *Exceeds the clause:* The proposal keeps both keywords. Under Part 03 §4 every `uri` is absolute, a relative reference, or malformed (`packet.resource.uri_form`), so 'MUST be a relative reference' already excludes an absolute one and the second keyword adds nothing; one MUST carries the whole clause.
  - *Actor:* A conformance predicate naming the artifact ('an entry carrying X MUST carry Y'), which spec/CONTRIBUTING.md §4 allows. Naming a writer instead would change who is bound and collide with Part 05 §10.
  - *Checks:* Observable today, though not by a check a part names: the reference validator reports `sources.absolute_uri` at error (`escapewheel_validator/declarations.py` `check_sources`). The manifest schema's conditional on `source` requires only `external: true`, and Part 04 §10 has no row for this; adding a named check or a schema conditional is a revision's business.
  - *Placement:* Part 04 §5.5 owns the meaning of `source` beside `uri`; Part 03 §4 owns the URI forms and is cited. No second owner.
  - *Implementation and corpus:* Complies. The writer refuses the combination (`escapewheel_writer/bindings.py` `check_reference`, fault SOURCE_ON_ABSOLUTE_URI) and the validator reports it at error; the reader (`location.py` `Location.resolve`) would follow the absolute `uri` and ignore the source, which is the ambiguity the rule prevents. No conformance packet carries `source`.
  - *Wording:* State one predicate, cite Part 03 §4 for the term, and keep 'neither field is a location' as its own clause.

### 22. R80 §2.3 at Part 04 §5.5 (ew-source-resolution)

- **The revision decides:** a writer SHOULD write sources.json at the packet root, naming every source the packet references and where it read each one
- **The part now says:** “A writer SHOULD write that default.”
- **Text to enter:** A writer SHOULD write that default, naming every source the packet references and where the writer read each one.
- **Placement:** Part 04 §5.5 (ew-source-resolution), replacing 'A writer SHOULD write that default.'
- **Observed by a check:** yes, or the sentence binds nothing.
- **Evaluation:** Safe as written: the SHOULD is already in the part and this restores what the default is meant to contain, which the schema does not imply. The reference writer names only the sources a caller declared, a departure it already has under the present sentence.
- **By lens:**
  - *Still decided:* Yes. R80 §2.3 has the full sentence; R134 §3.3 adds only that a written document satisfies the schema, and R80 §5 leaves open whether a travelling default is wise without withdrawing the SHOULD. The short form is from the incorporating commit 476a47f1.
  - *Contradiction:* None. An empty `sources` object satisfies the schema, which is why the content clause is not already implied. The credentials draft would forbid a build to write a recognised credential into a resolution document, so under it 'where the writer read each one' is the location without its credential; the two sit together. Part 05 §6 lists the document among a promotion record's paths and says nothing of its content.
  - *Exceeds the clause:* No. It is the clause's sentence with 'it' spelled out as 'the writer'; the existing 'A writer SHOULD write that default' already carries the keyword and the place.
  - *Actor:* A writer, before the keyword; it can tell whether the document it wrote names every source its manifest references.
  - *Checks:* Partly observable: the reference validator reports `sources.unresolved` at info for each source no available document locates (`declarations.py` `check_sources`), which a default naming every source would empty. It is a SHOULD, always compliable, scoped to the default.
  - *Placement:* Part 04 §5.5, extending the sentence already there. No other part states what the default contains.
  - *Implementation and corpus:* Partly complies, and no worse than under the present sentence. `escapewheel_writer/documents.py` `sources_document` writes the default from the sources passed to `PacketWriter.declare_source`, silently omits a referenced source that was not declared, and writes no document when none was; nothing outside the tests calls `declare_source`, and no shipped adapter names a source. No conformance packet carries `source`, and no validator check is needed.
  - *Wording:* Reads well after the resolution order. No change.

### 23. R128 §3.8 at Part 04 §9 (ew-packet-validation-block)

- **The revision decides:** a packet resource's validation state MUST NOT change its declaration-derived content class or canonicality
- **The part now says:** “It does not alter a resource's declaration-derived content class or canonicality.”
- **Text to enter:** An implementation MUST NOT treat a resource's validation state as changing its declaration-derived content class or canonicality. No checker verifies this.
- **Placement:** Part 04 §9 (ew-packet-validation-block), replacing 'It does not alter a resource's declaration-derived content class or canonicality.'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** A resource's validation state MUST NOT change its declaration-derived content class or canonicality.
- **Evaluation:** The keyword is still decided, but the proposed sentence has no actor and nothing a packet can violate. Restore it as a rule on an implementation, label it unchecked, leave Part 05 §2's twin indicative, and correct the ledger target to Part 04 §9.
- **By lens:**
  - *Still decided:* Yes. R128 §3.8 has MUST NOT and replaced the v0.2 rule that a failed manifest 'MUST NOT present its resources as canonical'. R132 §3.4 edited Part 04 §9 only to cite Part 05 §9.2, and R146 moved the Part 05 twin from §1 to §2 unchanged. Both indicative sentences come from R128's own incorporation (6fc02db5); R128's crosswalk row for Part 04 §9 summarises the change in the indicative, which describes the disposition and does not override the Decision's keyword.
  - *Contradiction:* None. Part 04 §4.2 says the checked declaration supplies content class and canonicality, Part 02 §2.2 derives canonicality from content class and forbids declaring it independently or promoting with a Boolean, and Part 00 §3.2 forbids an entry repeating either. Those fix the facts and forbid promotion; none forbids demoting a canonical resource because its `validation_state` is `failed` or `not_run`, the case the clause names. Part 06 §7 says the same informatively.
  - *Exceeds the clause:* No added force. The clause has no actor, so naming one is a choice; 'an implementation' is the subject Part 00 §2.4 reserves for a rule that binds every actor alike, and it is the one Part 02 §2.2 uses for the promotion half, so it is the minimal reading.
  - *Actor:* As proposed the subject is 'a resource's validation state', an actorless obligation that no artifact can violate (the manifest has no member for content class or canonicality), which spec/CONTRIBUTING.md §4 and R111 bar. With 'an implementation' it is determinate: a reader that returns a different content class for a failed resource violates it.
  - *Checks:* No registry rule, schema, validator check or corpus case can observe it, since nothing in a packet records the treatment. An implementation can always comply and the sentence is scoped to validation state, so it must carry the parts' label.
  - *Placement:* Part 04 §9 owns the validation block and the meaning of `validation_state`, so a rule about what that field may be read as belongs there; Part 02 §2.2 owns the derivation and is not restated. Part 05 §2 keeps an indicative twin ('Validation state does not change the content class or canonicality selected by its declaration'); leave it indicative as a statement of consequence, or have it cite Part 04 §9, so that only one sentence carries the keyword. The ledger target (Part 04 §4.1) should be corrected to `ew-packet-validation-block`.
  - *Implementation and corpus:* Complies and is unobservable as a defect: `escapewheel_reader/manifest.py` exposes `validation_state` as a plain property and takes content class from the resolved declaration; the writer sets every published entry to `passed` (`publication.py`). No conformance packet or fixture is affected and no validator check is needed.
  - *Wording:* Name the actor and the field's effect, and add the label.

## Part 05

### 24. R115 §3.4 at Part 05 §3.7 (ew-source-command)

- **The revision decides:** a build MUST consume standard output and standard error concurrently
- **The part now says:** “MUST read what the command produces while it writes”
- **Text to enter:** A build MUST consume a command's standard output and standard error concurrently: one that read either to its end first would wait on a command that had filled the other's pipe. No checker verifies this.
- **Placement:** Part 05 §3.7 (ew-source-command), fourth paragraph (beginning 'A build MUST capture a command's standard output and standard error'), as its last sentence
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** A build MUST consume a command's standard output and standard error concurrently: a pipe holds tens of kilobytes, so reading one to completion first waits on any command whose diagnosis outruns that buffer.
- **Evaluation:** Restore it in §3.7: the rule was never withdrawn, R116 presupposes it, and the reference writer already drains both streams together. Use the reworded sentence, which does not repeat the pipe-size figure the preceding paragraph already carries.
- **By lens:**
  - *Still decided:* Read R115 §3.4, R116 §3.2, R144 (which keeps Part 05 §3.7 as the build's procedure) and R146's crosswalk row for §3.7 (only the standard-input half moved to Part 12 §4). R115's accepting commit 092707be added the argument-list sentence and never the concurrency one, and R116 §3.2 describes the §3.7 capture obligation as existing 'for the same reason', so the rule was assumed present and no revision withdrew it.
  - *Contradiction:* None in Part 05 §§3.7 and 4.4, Part 12 §§3-4 and 9, Part 09 §5.7 or the open drafts. It sits beside the paragraph's indicative close ('a build writes the streams to a file'): a build that hands the command a file reads no pipe and satisfies the rule trivially, which the rationale should make evident.
  - *Exceeds the clause:* Force and scope match: the clause binds every command a build runs, as §3.7's 'a command' does, unlike the neighbouring R116 sentence, which binds only a command a build reaches a source through. The proposal's rationale swaps the clause's 'deadlocks' for 'waits', which is the part's own wording in the third paragraph and adds nothing.
  - *Actor:* A build is named before the keyword and can always comply. 'Concurrently' is close to a method, but the clause leaves the technique to Part 07 and the outcome is determinate (a build never reads one stream to its end while the command is blocked on the other), in the same register as the accepted 'MUST read what the command produces while it writes'.
  - *Checks:* No registry rule, schema, validator check or corpus case observes how a build drains a child's streams, and the writer's suite has no test of a diagnosis larger than a pipe. The build can always comply and the sentence is scoped to a command's two output streams, so it is acceptable as a writer-conformance obligation (Part 05 §10) and must be labelled as unchecked.
  - *Placement:* Part 05 §3.7 owns what a build does with a command's streams and Part 12 §4 owns only what crosses on standard input, so §3.7 is the single owner; Part 07's former section 7 says nothing on it. The rule binds a converting command too, which Part 12 does not cover, so Part 12 is not a credible second home.
  - *Implementation and corpus:* The reference writer complies: escapewheel-writer/src/escapewheel_writer/reading.py drains standard error on its own thread (`_drain`, used by `_read_stream` and `_read_flight`, whose docstring already cites Part 05 §3.7 for this rule) and `_read_files` uses `subprocess.run(..., capture_output=True)`, whose `communicate` drains both together. No packet, fixture or validator check is affected.
  - *Wording:* The proposed rationale repeats 'a pipe holds tens of kilobytes', which the paragraph above already states, so the section would give the same measurement twice. State the consequence without the number.

### 25. R82 §2.3 at Part 05 §12 (ew-alternatives-resolved)

- **The revision decides:** a consumer that meets an unresolved alternative is holding a packet that failed validation and MUST report that
- **The part now says:** “A consumer that meets an unresolved alternative is holding a packet that failed validation and reports that.”
- **Text to enter:** A consumer that meets an unresolved alternative is holding a packet that does not conform, and MUST report that, which no checker verifies.
- **Placement:** Part 05 §12 (ew-alternatives-resolved), second paragraph, replacing the sentence beginning 'A consumer that meets an unresolved alternative'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** A consumer that meets an unresolved alternative is holding a packet that failed validation and MUST report that.
- **Evaluation:** Restore the keyword: the clause is still decided, §12 is the section that binds a consumer, and nothing in code or the corpus changes. Word the report as non-conformance rather than 'failed validation', which a consumer holding no receipt cannot know, and label it as unchecked.
- **By lens:**
  - *Still decided:* Read R82 §§2.1 and 2.3, R41 §2.4 (the consumer rule R82 says 'stands'), R123 (exact selection is not rejected for an unresolved preference, and a guarded operation 'MUST continue to report an unresolved alternative', now Part 05 §13), R146 §§2.5 and 3.1 (§12 binds a consumer) and R150 (import runs are not alternatives). None withdraws the duty; the indicative 'reports that' dates from the accepting commit 476a47f1 and no revision quotes or decides it.
  - *Contradiction:* Part 01 §2.6 lets a consumer either refuse or report the ambiguity, so a MUST to report could be read as removing the refusal that R82 §2.3 itself says 'stays correct'; read as a duty that holds whether or not the consumer also refuses, it adds to Part 01 §2.6 without contradicting it. It agrees with Part 05 §13's reader rule and with the registry rule at `error` level, and no open draft touches §12.
  - *Exceeds the clause:* The proposed sentence is the part's own sentence with 'reports' made 'MUST report', which is the clause's force and scope exactly; it drops only the clause's rhetorical tail 'rather than treating it as a state to design around'. Nothing is added.
  - *Actor:* A consumer is a Part 00 §2.4 actor and Part 05 §1 lists §12 as the section binding one; it can always comply by saying so to whoever it answers to. What it must report is the weak point: 'a packet that failed validation' asserts a history the consumer cannot know, since Part 05 §14.3 forbids requiring a validation receipt and a packet may never have been validated, whereas that the packet does not conform (Part 05 §10) is something it can state.
  - *Checks:* No registry rule, schema, validator check or corpus case can observe a consumer, which may be a person. The consumer can always comply and the sentence is scoped to an unresolved alternative as the paragraph above defines one, so it is acceptable and must be labelled as unchecked.
  - *Placement:* Part 05 §12 is the right owner: the duty is to report non-conformance, which is Part 05's subject, while Part 01 §2.6 owns what a consumer may conclude from coexisting results. The sentence 'A consumer MUST NOT silently choose' in §12 already restates Part 01 §2.6, an existing duplication this restoration neither creates nor worsens.
  - *Implementation and corpus:* A consumer's conduct is unobservable in code. The nearest reference behaviour is the reader's `preferred_run` and `check` in escapewheel-reader/src/escapewheel_reader/runs.py, which raise `AmbiguousRun` naming the runs and citing Part 05 §12; that refuses and reports the alternative but does not say the packet fails validation. No packet, fixture or validator check is affected.
  - *Wording:* Replace 'failed validation' with 'does not conform', the term Part 05 §10 defines, so the mandated report is one a consumer can truthfully make; if the minimal edit is preferred, changing only 'reports' to 'MUST report' is also within the clause. The label is folded into the sentence because the paragraph continues after it.

### 26. R61 §2.1 at Part 05 §15.5 (ew-packet-cleanup)

- **The revision decides:** Cleanup MUST default to reporting what it would remove without removing it
- **The part now says:** “The operation reports by default and acts only when asked.”
- **Text to enter:** A writer performing cleanup MUST NOT remove anything unless it was asked to remove, and MUST otherwise report what it would remove. No checker verifies a writer's cleanup.
- **Placement:** Part 05 §15.5 (ew-packet-cleanup), second paragraph, replacing the sentence 'The operation reports by default and acts only when asked.'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** A writer performing cleanup MUST by default report what it would remove without removing it, and acts only when asked.
- **Evaluation:** Replace the indicative sentence in §15.5 with the keyword form, stated as an outcome and not as a 'default'; the reference `prune` already behaves this way. Do not add the proposed sentence beside the old one, which would state the rule twice.
- **By lens:**
  - *Still decided:* Read R61 §2.1, R111 §3.5, R135 §3.5 and R146 §3.2. The indicative 'The operation reports by default and acts only when asked' dates from the v0.2 compilation (4ce6f09c) and R146 (d7c0dcef) moved it unchanged; R146 §3.2 restates the order, stray and no-deletion rules with actors and is silent on the default, and R111's sweep counted only capitalised keywords. No revision chose the weaker form.
  - *Contradiction:* None in Part 05 §15.5, Part 03 §9, Part 07 or the drafts (the sidecar draft cites §15.5 only for what a packet may carry). The existing indicative sentence says the same thing, so the restored sentence must replace it, not sit beside it.
  - *Exceeds the clause:* The clause is 'Cleanup MUST default to reporting what it would remove without removing it'. The proposal adds 'and acts only when asked' in the indicative, which is the part's current wording and adds no force; nothing is dropped.
  - *Actor:* 'A writer performing cleanup' is the actor the section's other sentences use. 'By default' is not determinate for an operation with no default (a required report-or-remove argument); the outcome is that nothing is removed unless removal is asked for, and that is what a test can observe.
  - *Checks:* No validator check or corpus case observes a writer's cleanup; only the writer's own suite (escapewheel-writer tests/test_prune.py) exercises it. The writer can always comply and the sentence is scoped to cleanup, so it is acceptable, and it should be labelled unchecked; the section's two neighbouring cleanup requirements are equally unchecked and carry no label, so one label for the paragraph would serve all three.
  - *Placement:* Part 05 §15.5 is the owner and binds a writer (Part 05 §1). MUST is warranted under CONTRIBUTING §4 as data integrity: the section itself says a deletion is what must not happen by accident. No second owner.
  - *Implementation and corpus:* Complies: prune.py `prune(..., apply=False)` returns the plan and removes nothing unless `apply` is true, and scripts/cli.py's `prune` removes only with `--apply`, printing 'nothing was removed; pass --apply' otherwise. No packet or fixture is affected.
  - *Wording:* Split requirement from the indicative tail and state the outcome; replace the existing sentence.

## Part 06

### 27. R30 §4 at Part 06 §4 (ew-analysis-spike-events)

- **The revision decides:** a consumer MUST NOT assume the two tables are row-aligned or that a count from one applies to the other
- **The part now says:** “**Rows are not preserved.**”
- **Text to enter:** A consumer MUST NOT pair a row of this table with a row of `core.spike_events` by position, and MUST NOT take a count of one table's rows as a count of the other's; no check observes this.
- **Placement:** Part 06 §4 (ew-analysis-spike-events), in the paragraph 'Rows are not preserved', directly after the sentence ending 'so this table MAY hold fewer rows than core's.'
- **Observed by a check:** no; the sentence is labelled as unchecked where it carries a keyword.
- **Text first proposed, set aside:** A consumer MUST NOT assume that this table and `core.spike_events` are row-aligned, or that a count from one applies to the other.
- **Evaluation:** Restore the consumer obligation in Part 06 §4 directly after the 'MAY hold fewer rows' sentence, worded as the two conclusions it forbids rather than 'MUST NOT assume', and marked unchecked. Nothing in the implementation or corpus changes.
- **By lens:**
  - *Still decided:* Yes. Commit a0d153c3 restored R30 §4's writer MUST to Part 06 §4 and left the consumer sentence out; R145 §3.7 made the section normative and §3.8 revised only the omitted-count rule, describing the section as a writer's obligations without withdrawing the consumer's; R146 moved only the measurement; R151 added a registry rule on the table's clock. Later changes add reasons the tables differ (Part 03 §5.4's different stored order, no rows for a session without a reference clock, no table at all on a collision), which strengthen the rule.
  - *Contradiction:* None. Part 03 §5.3's 'A reader MUST NOT depend on stored order for correctness' binds a reader and says nothing of counts; Part 08's former section 5's `SELECT count(*) FROM analysis_spike_events` counts within the one table; the registry's descriptions of `analysis.spike_events` claim no row correspondence with core.
  - *Exceeds the clause:* The proposed text equals the clause, with 'this table and `core.spike_events`' for 'the two'. It adds no actor or condition.
  - *Actor:* A consumer is a Part 00 §2.4 actor, 'bound by what it concludes', and Part 01 already binds one in this form ('a consumer MUST NOT conclude', 'MUST NOT read it as'). 'MUST NOT assume' names a belief; pairing rows by position and carrying a count across are the conclusions it forbids, and a consumer can tell whether it did either. The MUST prevents a defined harm: an undercount of spikes read as complete.
  - *Checks:* No registry rule, schema, validator check or corpus case observes a consumer. A consumer can always comply and the sentence is scoped to two named tables, so under the unchecked-requirement rule it must carry a label, although Part 01's consumer rules carry none.
  - *Placement:* Part 06 §4 is normative since R145 §3.7 and owns this table's policy; the rule depends on no storage property and names columns of no table, so Part 03 and Part 01 are not candidates, and Part 05 §12, the only Part 05 section binding a consumer, concerns run preference. No other part states it, so no second owner. Part 05 §1's table lists only Part 05's sections and does not bar a consumer rule in Part 06.
  - *Implementation and corpus:* Unobservable in a validator. The reference code agrees with it: escapewheel-writer materialize.py documents the table as 'not row-aligned with `core.spike_events`', and escapewheel-reader clocks.py `on_clock` drops the same rows rather than pairing the tables by position. No packet or corpus case changes verdict and no check is needed.
  - *Wording:* State the two forbidden conclusions directly, and place the sentence straight after 'so this table MAY hold fewer rows than core's.': appended at the paragraph's end it would follow 'No checker verifies this, since `parameters` names no key for the counts', which is about the writer's count.

## Part 12

### 28. R128 §3.8 at Part 12 §5 (ew-referenced-resource-delivery)

- **The revision decides:** a writer MUST preserve the delivered declaration binding when it creates the packet entry and MUST reject a document whose binding does not resolve or does not admit the resource ID
- **The part now says:** “A build preserves that binding, rejects one that does not resolve or admit the resource ID, and merges the entry into the manifest.”
- **Text to enter:** A build MUST preserve each entry's `declaration_id` in the packet resource entry it creates from it, and MUST refuse a document holding an entry whose `declaration_id` resolves to no declaration of a loaded registry or does not admit the entry's `resource_id`. It merges each entry it accepts into the manifest.
- **Placement:** Part 12 §5 (ew-referenced-resource-delivery), replacing the sentence 'A build preserves that binding, rejects one that does not resolve or admit the resource ID, and merges the entry into the manifest.'
- **Observed by a check:** yes, or the sentence binds nothing.
- **Text first proposed, set aside:** A build MUST preserve that binding when it creates the packet entry, MUST reject a document whose binding does not resolve or does not admit the resource ID, and merges the entry into the manifest. (R128's 'writer' is 'a build' since R134.)
- **Evaluation:** Restore both keywords in place in Part 12 §5, but name `declaration_id` instead of the dangling 'that binding', say it is the document that is refused, and leave out the proposal's parenthesis about R134. The reference writer already preserves and checks the binding, so no behaviour changes; add Part 12 §5 to the clause's ledger targets.
- **By lens:**
  - *Still decided:* Read R128 §3.8 in full, then R130, R134 §3.4, R143, R144 and R145, which later touched the paragraph. None changes the two duties; R143 added the external-only and URI rules beside them and R144 moved the paragraph to Part 12 §5 with 'semantic effect: none'. The indicative dates from R128's own incorporation (commit 6fc02db5), which also turned the earlier 'A build MUST merge each entry' into 'merges'; no crosswalk row records dropping the keywords, so it reads as drafting rather than a decision.
  - *Contradiction:* None. The paragraph's next sentences already bind a build with MUST (refuse a document failing the schema; record every entry as external; rewrite the uri), and Part 04 §4.2 and §10 (packet.resource.declaration_unknown, singleton_identity, family_namespace, catalog_row_binding) state the same conditions as packet findings. Preserving the binding does not collide with the uri rewrite or the forced `external`, since the binding is `declaration_id`. The open draft on compensations amends Part 12 §5 elsewhere and does not touch this sentence.
  - *Exceeds the clause:* The proposed MUSTs are the clause's two. The proposal adds a parenthesis '(R128's 'writer' is 'a build' since R134.)' that is history and must not enter a part (R121, CONTRIBUTING §3). 'Refuse' for the clause's 'reject' is the part's own verb and changes nothing.
  - *Actor:* 'A build' is a Part 00 §2.4 term that resolves to the writer the clause bound, and both outcomes are observable: the manifest entry carries the delivered `declaration_id`, and a document with an unresolvable or inadmissible binding stops the build.
  - *Checks:* Checked. The validator would report the same defects on the staged packet (Part 04 §10), and the writer suite has test_delivery.py::test_a_referenced_resource_no_row_declares_is_refused for the admission half. I found no writer test of a delivered document naming an unknown `declaration_id`; the code path exists and a test should accompany the fix.
  - *Placement:* Part 12 §5 owns what a build does with a resource document; Part 04 owns the packet-side rule and is not restated, since this is a refusal of a delivery before a manifest exists. The ledger targets of R128 §3.8 (Part 00 ew-packet-catalog, Part 04 ew-packet-resource-entry-fields) omit Part 12 §5 and need ew-referenced-resource-delivery added.
  - *Implementation and corpus:* Complies. escapewheel_writer/attachments.py (reference_array, reference_media) passes each delivered entry's `declaration_id` to registries.py::Declarations.family, which raises UsageError for an unknown declaration, a wrong kind, a non-family mode or a foreign namespace, and array_entries/media_entries write that same `declaration_id` into the manifest entry; reading.py::Delivered.unresolved refuses an entry no catalog row declares. No conformance packet changes and no validator check is needed.
  - *Wording:* 'that binding' has had no antecedent since the sentence 'Every entry MUST carry `resource_id`, `declaration_id`, and `uri`' left the paragraph; name the member. 'Rejects one' leaves unclear whether an entry or the document is refused; the clause says the document. Drop the parenthesis.

### 29. R115 §3.1 at Part 12 §7 (ew-adapter-declaration-document)

- **The revision decides:** an adapter MUST declare the kinds whose output it reads, which orders a build
- **The part now says:** “The kinds whose output an adapter reads order a build.”
- **Text to enter:** `consumes` names the kinds of the sources whose output the adapter reads, which is what orders a build (Part 05 §3.4).
- **Placement:** Part 12 §7 (ew-adapter-declaration-document), appended to the paragraph beginning 'A document MUST carry all eight members', after the sentence defining `accepts` and `contributes`
- **Observed by a check:** yes, or the sentence binds nothing.
- **Text first proposed, set aside:** An adapter MUST declare the kinds whose output it reads, which orders a build rather than being passed to it; `consumes` names them.
- **Evaluation:** Restore the meaning of `consumes` in Part 12 §7 as a definition, not as a second MUST: the duty to declare already binds through the eight-member rule, and R146 sent Part 05 §3.4's list to §7 without the definition arriving. Leave Part 05 §3.4's ordering sentence as it is; nothing in the writer or corpus changes.
- **By lens:**
  - *Still decided:* Read R115 §3.1, R119, R133 §3.5 (a recipe lists a kind once, so a kind identifies a source), R134 §3.1 (the document MUST carry all eight members, `consumes` among them) and R146. Until R146, Part 05 §3.4 said an adapter declares six facts, the last 'the kinds whose output it reads, which is what orders a build', published as `consumes`; R146's crosswalk replaced that list 'with a citation' to Part 12 §7 at 'semantic effect: none' (commit d7c0dcef), but Part 12 §7 never said what `consumes` holds. The loss is a side effect of that move, not a decision.
  - *Contradiction:* None with Part 12 §7, Part 05 §§3.4 and 3.5, adapter.schema.json (its informative description of `consumes` says the same) or Part 07 §4. One thing to hold in mind: under amendment (Part 05 §4.3) the packet's rows stand in for a source 'before any source runs', so the kinds an adapter reads from need not all be sources of the recipe; a definition that says only what the member names does not disturb that, where a new MUST to declare might.
  - *Exceeds the clause:* The proposed 'An adapter MUST declare the kinds whose output it reads' restates an obligation that already has force through 'A document MUST carry all eight members' and through the class being checked as its document; a second MUST on the same act is a second statement of one rule in one section. What is missing is only the member's meaning, so the restoration should be a definition with no keyword.
  - *Actor:* As proposed, the MUST binds an adapter to an outcome no one can observe: a build cannot see what an adapter reads, and an adapter does not read another source's output directly but receives terms (`clocks`, `units`, `first_samples`) a build fills from it. A definition of the member avoids binding anyone to that.
  - *Checks:* The member's presence and shape are checked by the incorporated schema and by the recipe check (escapewheel_writer/declaration.py::shape_problems; test_recipe_check.py parametrized over all eight members). Whether its content is truthful cannot be checked, which is a further reason not to add a MUST about content.
  - *Placement:* Part 12 §7 owns 'what each member means' by its own words, and R146 pointed Part 05 §3.4 at it for exactly these facts; Part 05 §3.4 keeps the ordering sentence and needs no change. Do not add the ordering rule to Part 12 as well.
  - *Implementation and corpus:* Complies and is unaffected by a definition: recipe.py::declared reads `consumes` from the document or `CONSUMES` from the class, and sourcing.py::order runs each source after the kinds it names (test_sourcing.py). order also refuses a recipe whose source consumes a kind the recipe does not list, a refusal no part states; that is outside this finding but argues against any wording that makes the member's content a conformance duty.
  - *Wording:* Match the neighbouring member definitions in the same paragraph (`accepts` names ..., `contributes` names ...), cite Part 05 §3.4 for the ordering, and drop 'rather than being passed to it', which answers a question the part does not raise.
