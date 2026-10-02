# Class C: sections written in the indicative throughout

Part 05 §14 and Part 11 state every rule below without a keyword, as they state the rest of their text.

22 rules, ordered by part and section: Part 05 (17), Part 11 (5).

Nothing here has been applied. The audit record is [applied-targets.md](../applied-targets.md).

## Part 05

### 1. R127 §3.2 at Part 05 §14.1 (ew-checked-registry-context)

- **The revision decides:** an implementation authorized by a valid result to produce packet bytes or registry-derived checks MUST use the decoded document in the same checked context, not reread the source or use the caller's mapping
- **The part now says:** “A valid context authorizes production or registry-derived checks only from the decoded document in that same context.” (Part 05 §14.1 (ew-checked-registry-context))
- **Proposed text:** An implementation that a valid context authorizes to produce packet bytes or registry-derived checks MUST work from the decoded document in that same context, and MUST NOT reread the source or use the caller's original mapping.
- **Placement:** Part 05 §14.1 (ew-checked-registry-context)
- **Risk:** Part 05 §14 has read this way since the commit that incorporated R127 (107c4b59), and no later revision touches this sentence (R130, R132 and R146 amend only §§14.3, 14.5 and 14.6 and the §1 scope table). The indicative looks like compression of an implementation boundary, not a decision: the same section keeps MUST in §14.2's lead sentence, §14.3 and §14.5, and Part 05 §1 lists this subsection among those that bind an actor. Restoring the keyword contradicts nothing.
- **Second reading:** Clause: an implementation authorized by a valid result "MUST use the decoded registry document in the same checked context, not reread the source or use the caller's original mapping". Part 05 §14.1 states it as a property of the context with no keyword. Scope survives ("only from the decoded document in that same context" excludes rereading and the caller's mapping). The only MUST nearby binds a validator alone (§14.5, "MUST direct packet checks only from the checked contexts"); a writer or generator has none.

### 2. R127 §3.3 at Part 05 §14.2 (ew-registry-conformance-boundary)

- **The revision decides:** when the implementation owns the source bytes it MUST use the byte-oriented entry point
- **The part now says:** “A boundary that owns source bytes uses the byte entry point.” (Part 05 §14.2 (ew-registry-conformance-boundary))
- **Proposed text:** An implementation that owns the source bytes MUST use the byte entry point.
- **Placement:** Part 05 §14.2 (ew-registry-conformance-boundary)
- **Risk:** Part 05 §14 has read this way since the commit that incorporated R127 (107c4b59), and no later revision touches this sentence (R130, R132 and R146 amend only §§14.3, 14.5 and 14.6 and the §1 scope table). The indicative looks like compression of an implementation boundary, not a decision: the same section keeps MUST in §14.2's lead sentence, §14.3 and §14.5, and Part 05 §1 lists this subsection among those that bind an actor. Restoring the keyword contradicts nothing.
- **Second reading:** Clause: "When the implementation owns the source bytes, it MUST use the byte-oriented entry point." Part 05 §14.2 says "uses". Elsewhere only Part 04 §10 has a validator obtain the result "through the byte-oriented entry point", and Part 02 §9.4 binds what that entry point does, not who must call it.

### 3. R127 §3.3 at Part 05 §14.2 (ew-registry-conformance-boundary)

- **The revision decides:** when given only an already-decoded mapping it MUST use the mapping-oriented entry point
- **The part now says:** “A boundary given only a decoded mapping uses the mapping entry point and does not claim byte-level JSON checks.” (Part 05 §14.2 (ew-registry-conformance-boundary))
- **Proposed text:** An implementation given only a decoded mapping MUST use the mapping entry point and MUST NOT claim byte-level JSON checks.
- **Placement:** Part 05 §14.2 (ew-registry-conformance-boundary)
- **Risk:** Part 05 §14 has read this way since the commit that incorporated R127 (107c4b59), and no later revision touches this sentence (R130, R132 and R146 amend only §§14.3, 14.5 and 14.6 and the §1 scope table). The indicative looks like compression of an implementation boundary, not a decision: the same section keeps MUST in §14.2's lead sentence, §14.3 and §14.5, and Part 05 §1 lists this subsection among those that bind an actor. Restoring the keyword contradicts nothing.
- **Second reading:** Clause: given only a decoded mapping, the implementation "MUST use the mapping-oriented entry point and MUST NOT claim byte-level JSON checks were performed". Part 05 §14.2 says "uses ... and does not claim". The second half keeps its force elsewhere (Part 02 §9.4: a mapping-oriented entry point "MUST NOT claim that the source bytes had unique members"); the first half, the finding's rule, has no keyword anywhere.

### 4. R127 §3.3 at Part 05 §14.2 (ew-registry-conformance-boundary)

- **The revision decides:** a low-level generator accepting a registry document directly MUST either establish the checked registry context itself or require one from its caller
- **The part now says:** “A low-level generator either establishes the checked context or requires one; a mapping accompanied by a result, Boolean, or caller assertion is insufficient.” (Part 05 §14.2 (ew-registry-conformance-boundary))
- **Proposed text:** A low-level generator MUST either establish the checked context or require one; a mapping accompanied by a result, Boolean, or caller assertion is insufficient.
- **Placement:** Part 05 §14.2 (ew-registry-conformance-boundary)
- **Risk:** Part 05 §14 has read this way since the commit that incorporated R127 (107c4b59), and no later revision touches this sentence (R130, R132 and R146 amend only §§14.3, 14.5 and 14.6 and the §1 scope table). The indicative looks like compression of an implementation boundary, not a decision: the same section keeps MUST in §14.2's lead sentence, §14.3 and §14.5, and Part 05 §1 lists this subsection among those that bind an actor. Restoring the keyword contradicts nothing.
- **Second reading:** Clause: a low-level generator accepting a registry document directly "MUST either establish the checked registry context itself or require one from its caller". Part 05 §14.2 says "either establishes ... or requires one". §14.2's lead MUST makes an implementation obtain a complete result before generating checks, but does not require the checked context, which is what stops a generator accepting a mapping plus a Boolean. The rule is generic, not a statement about the reference implementation.

### 5. R127 §3.5 at Part 05 §14.4 (ew-registry-producer-boundary)

- **The revision decides:** an implementation publishing or releasing a registry or generating registry-derived conformance checks MUST complete that operation only when the result is valid
- **The part now says:** “Registry publication, release, and generation of registry-derived conformance checks complete only from a `valid` context.” (Part 05 §14.4 (ew-registry-producer-boundary))
- **Proposed text:** An implementation MUST complete registry publication, release, or generation of registry-derived conformance checks only from a `valid` context.
- **Placement:** Part 05 §14.4 (ew-registry-producer-boundary)
- **Risk:** Part 05 §14 has read this way since the commit that incorporated R127 (107c4b59), and no later revision touches this sentence (R130, R132 and R146 amend only §§14.3, 14.5 and 14.6 and the §1 scope table). The indicative looks like compression of an implementation boundary, not a decision: the same section keeps MUST in §14.2's lead sentence, §14.3 and §14.5, and Part 05 §1 lists this subsection among those that bind an actor. Restoring the keyword contradicts nothing. Part 05 §1 lists §14.4 among the sections that bind a writer, whereas this clause's actor is an implementation publishing, releasing, checking for an author or generating checks; a restored sentence should keep that actor.
- **Second reading:** Clause: such an implementation "MUST complete that operation only when the associated result is `valid`". Part 05 §14.4 says the operations "complete only from a `valid` context". §14.2's MUST requires obtaining a result first, not that it be valid; §14.5 covers only a validator's packet checks. No other statement.

### 6. R127 §3.5 at Part 05 §14.4 (ew-registry-producer-boundary)

- **The revision decides:** an implementation checking a registry for an extension author MUST report success only when the result is valid
- **The part now says:** “An extension-author check reports success only for `valid`.” (Part 05 §14.4 (ew-registry-producer-boundary))
- **Proposed text:** An extension-author check MUST report success only for `valid`.
- **Placement:** Part 05 §14.4 (ew-registry-producer-boundary)
- **Risk:** Part 05 §14 has read this way since the commit that incorporated R127 (107c4b59), and no later revision touches this sentence (R130, R132 and R146 amend only §§14.3, 14.5 and 14.6 and the §1 scope table). The indicative looks like compression of an implementation boundary, not a decision: the same section keeps MUST in §14.2's lead sentence, §14.3 and §14.5, and Part 05 §1 lists this subsection among those that bind an actor. Restoring the keyword contradicts nothing. Part 05 §1 lists §14.4 among the sections that bind a writer, whereas this clause's actor is an implementation publishing, releasing, checking for an author or generating checks; a restored sentence should keep that actor.
- **Second reading:** Clause: an implementation checking a registry for an extension author "MUST report success only when that result is `valid`". Part 05 §14.4 says "reports success only for `valid`". No other part states it.

### 7. R127 §3.5 at Part 05 §14.4 (ew-registry-producer-boundary)

- **The revision decides:** for any other state the implementation MUST stop the requested production or publication and expose the complete result to its caller
- **The part now says:** “For another state, the operation stops and exposes the complete result.” (Part 05 §14.4 (ew-registry-producer-boundary))
- **Proposed text:** For another state, the implementation MUST stop the operation and expose the complete result to its caller.
- **Placement:** Part 05 §14.4 (ew-registry-producer-boundary)
- **Risk:** Part 05 §14 has read this way since the commit that incorporated R127 (107c4b59), and no later revision touches this sentence (R130, R132 and R146 amend only §§14.3, 14.5 and 14.6 and the §1 scope table). The indicative looks like compression of an implementation boundary, not a decision: the same section keeps MUST in §14.2's lead sentence, §14.3 and §14.5, and Part 05 §1 lists this subsection among those that bind an actor. Restoring the keyword contradicts nothing. Part 05 §1 lists §14.4 among the sections that bind a writer, whereas this clause's actor is an implementation publishing, releasing, checking for an author or generating checks; a restored sentence should keep that actor.
- **Second reading:** Clause: "For any other state, the implementation MUST stop the requested production or publication and expose the complete result to its caller." Part 05 §14.4 says "the operation stops and exposes the complete result". §14.6 on exposing the complete representation is also in the indicative.

### 8. R127 §3.5 at Part 05 §14.4 (ew-registry-producer-boundary)

- **The revision decides:** a writer MUST reject a non-valid registry before opening any source or staging any output
- **The part now says:** “A writer rejects a non-valid registry before opening a source or staging output.” (Part 05 §14.4 (ew-registry-producer-boundary))
- **Proposed text:** A writer MUST reject a non-valid registry before opening a source or staging output.
- **Placement:** Part 05 §14.4 (ew-registry-producer-boundary)
- **Risk:** Part 05 §14 has read this way since the commit that incorporated R127 (107c4b59), and no later revision touches this sentence (R130, R132 and R146 amend only §§14.3, 14.5 and 14.6 and the §1 scope table). The indicative looks like compression of an implementation boundary, not a decision: the same section keeps MUST in §14.2's lead sentence, §14.3 and §14.5, and Part 05 §1 lists this subsection among those that bind an actor. Restoring the keyword contradicts nothing.
- **Second reading:** Clause: "A writer MUST reject a non-valid registry before opening any source or staging any output." Part 05 §14.4 says "rejects". The nearest keyworded rules do not reach it: §14.2 requires a result before a build starts, §3.5 has a build refuse a defective recipe, and §11's "refuses a recipe that cannot produce a valid packet" is about the recipe and is itself in the indicative.

### 9. R127 §3.5 at Part 05 §14.4 (ew-registry-producer-boundary)

- **The revision decides:** a public writer constructor accepting mappings MAY keep that input form but MUST copy and check the mappings before retaining or interpreting them
- **The part now says:** “A public mapping constructor copies and checks the mapping before retaining or interpreting it.” (Part 05 §14.4 (ew-registry-producer-boundary))
- **Proposed text:** A public mapping constructor MUST copy and check the mapping before retaining or interpreting it.
- **Placement:** Part 05 §14.4 (ew-registry-producer-boundary)
- **Risk:** Part 05 §14 has read this way since the commit that incorporated R127 (107c4b59), and no later revision touches this sentence (R130, R132 and R146 amend only §§14.3, 14.5 and 14.6 and the §1 scope table). The indicative looks like compression of an implementation boundary, not a decision: the same section keeps MUST in §14.2's lead sentence, §14.3 and §14.5, and Part 05 §1 lists this subsection among those that bind an actor. Restoring the keyword contradicts nothing.
- **Second reading:** Clause: a public writer constructor accepting mappings "MUST copy and check those mappings before retaining or interpreting them". Part 05 §14.4 says "copies and checks". Checking before interpretation is half carried with force by §14.2 (a result MUST be obtained before constructing a public writer from registry input); copying before retention rests only on §14.1's indicative definition of the context. The clause's MAY (the mapping form may be kept) is implied by the sentence admitting such a constructor.

### 10. R127 §3.5 at Part 05 §14.4 (ew-registry-producer-boundary)

- **The revision decides:** an adapter acquires no registry authority from this process and MUST NOT be opened after the writer has rejected a registry
- **The part now says:** “Rejection does not open an adapter.” (Part 05 §14.4 (ew-registry-producer-boundary))
- **Proposed text:** A writer MUST NOT open an adapter after it has rejected a registry.
- **Placement:** Part 05 §14.4 (ew-registry-producer-boundary)
- **Risk:** Part 05 §14 has read this way since the commit that incorporated R127 (107c4b59), and no later revision touches this sentence (R130, R132 and R146 amend only §§14.3, 14.5 and 14.6 and the §1 scope table). The indicative looks like compression of an implementation boundary, not a decision: the same section keeps MUST in §14.2's lead sentence, §14.3 and §14.5, and Part 05 §1 lists this subsection among those that bind an actor. Restoring the keyword contradicts nothing.
- **Second reading:** Clause: an adapter "MUST NOT be opened after the writer has rejected a registry". Part 05 §14.4 says "Rejection does not open an adapter." The other half, that an adapter acquires no registry authority, carries no keyword in the clause and is covered: Part 02 §2 makes the core and extension registries the only declaration authorities, and Part 12 has a build read an adapter's declarations with nothing open. The finding stands on the MUST NOT alone.

### 11. R127 §3.5 at Part 05 §14.4 (ew-registry-producer-boundary)

- **The revision decides:** an exception used to report rejection MUST make the complete portable result retrievable as structured data
- **The part now says:** “A structured rejection exception makes the complete portable result retrievable; a command-line boundary offers machine-readable output containing the same result.” (Part 05 §14.4 (ew-registry-producer-boundary))
- **Proposed text:** A structured rejection exception MUST make the complete portable result retrievable.
- **Placement:** Part 05 §14.4 (ew-registry-producer-boundary)
- **Risk:** Part 05 §14 has read this way since the commit that incorporated R127 (107c4b59), and no later revision touches this sentence (R130, R132 and R146 amend only §§14.3, 14.5 and 14.6 and the §1 scope table). The indicative looks like compression of an implementation boundary, not a decision: the same section keeps MUST in §14.2's lead sentence, §14.3 and §14.5, and Part 05 §1 lists this subsection among those that bind an actor. Restoring the keyword contradicts nothing.
- **Second reading:** Clause: "An exception used to report rejection MUST make the complete portable result retrievable as structured data." Part 05 §14.4 says "makes". §14.6 says structured exceptions "expose the same Part 02 §9.5 representation", also without a keyword; Part 02 §9.5's MUST binds the serialized result's shape, not its availability from an exception.

### 12. R127 §3.5 at Part 05 §14.4 (ew-registry-producer-boundary)

- **The revision decides:** a command-line tool MUST offer machine-readable output containing that result
- **The part now says:** “A structured rejection exception makes the complete portable result retrievable; a command-line boundary offers machine-readable output containing the same result.” (Part 05 §14.4 (ew-registry-producer-boundary))
- **Proposed text:** A command-line boundary MUST offer machine-readable output containing the same result.
- **Placement:** Part 05 §14.4 (ew-registry-producer-boundary)
- **Risk:** Part 05 §14 has read this way since the commit that incorporated R127 (107c4b59), and no later revision touches this sentence (R130, R132 and R146 amend only §§14.3, 14.5 and 14.6 and the §1 scope table). The indicative looks like compression of an implementation boundary, not a decision: the same section keeps MUST in §14.2's lead sentence, §14.3 and §14.5, and Part 05 §1 lists this subsection among those that bind an actor. Restoring the keyword contradicts nothing.
- **Second reading:** Clause: "A command-line tool MUST offer machine-readable output containing that result and MAY additionally render it for a person." Part 05 §14.4 says "offers"; §14.6 ("machine-readable command output ... expose the same Part 02 §9.5 representation", "Human rendering may differ") is also in the indicative. No part states the obligation with a keyword.

### 13. R127 §3.6 at Part 05 §14.5 (ew-validator-registry-boundary)

- **The revision decides:** the validator MUST identify which checked core context directs packet checks and MUST use that context for every extension evaluation
- **The part now says:** “The validator identifies the checked core context directing packet checks and supplies that exact context to every extension evaluation.” (Part 05 §14.5 (ew-validator-registry-boundary))
- **Proposed text:** The validator MUST identify the checked core context directing packet checks and MUST supply that exact context to every extension evaluation.
- **Placement:** Part 05 §14.5 (ew-validator-registry-boundary)
- **Risk:** No contradiction: R130 §3.9's paragraph in the same section already binds the validator to the bound core. The indicative looks like the incorporating editor's style for §§14.4-14.6 as a whole rather than a decision; restoring this sentence alone leaves its neighbours indicative, so the paragraph is better restored together (ids 150, 151).
- **Second reading:** R127 §3.6 carries both MUSTs. Part 05 §14.5 has stated them in the indicative since R127 was first incorporated (the same sentence is in the pre-R130 text of commit 7bee7a43^), so no later revision weakened it. R130 §3.9 and Part 04 §10's packet.registry.core_count leave exactly one bound core, which makes 'identify which' trivial, but nothing with a keyword obliges the validator to supply that core context to every extension evaluation: Part 04 §10 says 'supplying the core context to every extension' inside an indicative sentence (R130 §3.6 wrote it so), Part 05 §14.1 only defines the context, and Part 02 §9.4 says what an extension result is without a usable core context, not that the validator must supply one.

### 14. R127 §3.6 at Part 05 §14.5 (ew-validator-registry-boundary)

- **The revision decides:** for a non-valid result the validator MUST retain the complete registry result in its report, skip every dependent packet check, and preserve invalid outcomes as registry-document findings
- **The part now says:** “For a non-valid result, the validator retains the complete result, skips every dependent packet check, preserves invalid outcomes as registry-document findings, and does not fabricate packet findings for unsupported, incomplete, or skipped work.” (Part 05 §14.5 (ew-validator-registry-boundary))
- **Proposed text:** Only a `valid` context directs generation or execution of registry-derived packet checks. For a non-valid result, the validator MUST retain the complete result in its report, MUST skip every dependent packet check, MUST preserve invalid outcomes as registry-document findings, and MUST NOT fabricate packet findings for unsupported, incomplete, or skipped work.
- **Placement:** Part 05 §14.5 (ew-validator-registry-boundary)
- **Risk:** No contradiction with §9.5, which already treats a non-valid core result as withholding every extension's packet checks and a withheld subject as at best incomplete. The indicative is the section's style since incorporation, not a recorded decision.
- **Second reading:** R127 §3.6 lists four MUST items after 'For a non-valid result, the validator MUST:'. Part 05 §14.5 has given them in one indicative sentence since first incorporation; R130 and R132 revised the section without touching it. Partial cover exists: §9.5 (R132) obliges attributing 'each outcome of a bound registry's Part 02 §9.4 result' to its registry, which carries the third item, and Part 11's 'MUST NOT fabricate a packet finding' covers only Tier 2 rule evaluation. Nothing with a keyword obliges retaining the complete result in the report (§9.5 says the specification defines no report schema) or skipping the dependent packet checks: §14.5's MUST limits direction to contexts that passed registry_binding, which a non-valid registry can pass, and 'Only a `valid` context directs' is indicative, as are §14.1 and Part 04 §10's 'runs only from checked contexts that Part 05 §14.5 permits'.

### 15. R127 §3.7 at Part 05 §14.6 (ew-registry-result-reporting)

- **The revision decides:** a report MUST pair each registry result with an external subject label identifying the registry role evaluated
- **The part now says:** “Each reported result has an external subject label.” (Part 05 §14.6 (ew-registry-result-reporting))
- **Proposed text:** A report MUST pair each registry result with an external subject label. A bound registry's label MUST be its registry ID, and a registry checked outside a packet MUST receive a source-distinguishing label.
- **Placement:** Part 05 §14.6 (ew-registry-result-reporting)
- **Risk:** The clause's 'identifying the registry role, such as core or a manifest-declared extension identifier' must not be restored: R130 §3.9 replaced it with the registry ID for a bound registry. Otherwise no contradiction; the indicative is the section's style since incorporation.
- **Second reading:** R127 §3.7 has the MUST; Part 05 §14.6 has said 'Each reported result has an external subject label' since first incorporation. R130 §3.9 changed what the label is for a bound registry (its registry ID, replacing the role label) but kept the pairing obligation, and Part 05 states that too in the indicative. Part 05 §9.5 (R132) requires a packet validator's report to state each finding's subject, which covers registry outcomes inside a packet validation report only; a report of a registry checked outside a packet (publication, extension-author check, caller-supplied document) has no keyword-bearing labelling rule.

### 16. R127 §3.7 at Part 05 §14.6 (ew-registry-result-reporting)

- **The revision decides:** the subject label MUST NOT replace or manufacture the registry document's own identity
- **The part now says:** “A label does not replace or manufacture the document's own identity.” (Part 05 §14.6 (ew-registry-result-reporting))
- **Proposed text:** A label MUST NOT replace or manufacture the document's own identity.
- **Placement:** Part 05 §14.6 (ew-registry-result-reporting)
- **Risk:** None found. Since R130 a bound registry's label equals its registry ID and Part 04 §10 fails a document whose own registry_id differs, so the two cannot disagree in a packet that passes binding; the rule still matters for an invalid or unparseable document. The indicative looks like section style.
- **Second reading:** R127 §3.7 states MUST NOT; Part 05 §14.6 states 'A label does not replace or manufacture the document's own identity', unchanged since first incorporation and untouched by R130 §3.9 or R132. No other part restates it: Part 04 §10's packet.registry.identity compares a document's registry_id with its descriptor name, which is a different rule, and registry_result.schema.json carries no label member.

### 17. R127 §3.7 at Part 05 §14.6 (ew-registry-result-reporting)

- **The revision decides:** public checking APIs, machine-readable command output, validation reports and structured exceptions MUST expose the same result representation without reducing it to a Boolean or a list of invalid findings
- **The part now says:** “Public checking APIs, machine-readable command output, validation reports, and structured exceptions expose the same Part 02 §9.5 representation rather than reducing it to a Boolean or invalid-finding list.” (Part 05 §14.6 (ew-registry-result-reporting))
- **Proposed text:** Public checking APIs, machine-readable command output, validation reports, and structured exceptions MUST expose the same Part 02 §9.5 representation without reducing it to a Boolean or an invalid-finding list.
- **Placement:** Part 05 §14.6 (ew-registry-result-reporting)
- **Risk:** No contradiction. Part 05 §9.5 says the specification defines no validation-report schema; the restored sentence fixes only the registry-result representation inside a report, as R127 did. The indicative looks like section style.
- **Second reading:** R127 §3.7 states MUST; Part 05 §14.6 states 'expose the same Part 02 §9.5 representation rather than reducing it' in the indicative since first incorporation. Part 02 §9.5 obliges a portable result to validate against registry_result.schema.json but obliges no boundary to expose it, §14.4's 'makes the complete portable result retrievable' is indicative, and §9.5 of Part 05 defines no report schema. No later revision restates or withdraws it.

## Part 11

### 18. R125 §3.2 at Part 11 §2 (ew-tier-2-query-profile)

- **The revision decides:** `ABS`, `MIN`, `MAX`, and `LAG` MUST return their argument's domain; `COALESCE` its arguments' common domain; `CAST` its target domain; `COUNT`, `ROW_NUMBER`, and `DENSE_RANK` `BIGINT`; `PERCENTILE_CONT` `DOUBLE PRECISION`; a comparison, predicate, Boolean operator, `isnan`, or `isfinite` `BOOLEAN`
- **The part now says:** “`ABS`, `MIN`, `MAX`, and `LAG` return their argument's domain.” (Part 11 §2 (ew-tier-2-query-profile))
- **Proposed text:** `ABS`, `MIN`, `MAX`, and `LAG` MUST return their argument's domain. `COALESCE` MUST return its arguments' common domain, and `CAST` MUST return its target domain. `COUNT`, `ROW_NUMBER`, and `DENSE_RANK` MUST return `BIGINT`, as does `CHARACTER_LENGTH`; `PERCENTILE_CONT` MUST return `DOUBLE PRECISION`. Comparisons, predicates, Boolean operators, `isnan`, and `isfinite` MUST return `BOOLEAN`.
- **Placement:** Part 11 §2 (ew-tier-2-query-profile)
- **Risk:** Part 11 has stated its language definitions in the indicative since the commit that incorporated R125 (408e6465); no later revision changed the mood. The form looks deliberate rather than accidental: the obligation is carried by actor sentences, Part 11 §1 ("A validator claiming support for this language MUST support the identified contract as a whole", the descriptor's `contract_clauses` naming this anchor) and Part 05 §5.2 (a validator "MUST parse, statically validate, bind, and type-check the rule as Part 11 requires"). Restoring the keyword contradicts nothing, but the clause's MUST is actorless, which spec/CONTRIBUTING.md §4 discourages. R149 §3.2 decided `CHARACTER_LENGTH`'s result in the indicative, so a MUST on that routine would exceed its clause; the text above keeps it outside the keyword.
- **Second reading:** The clause has six MUSTs on the routines' result domains; Part 11 §2 states the same content in the indicative ("return", "returns"), and Part 00 §2.5 binds keywords only in capitals. No later revision restated these routines: R149 §3.2 extended the sentence in place for `CHARACTER_LENGTH` alone, and decided that routine in the indicative ("It returns `BIGINT`"). The only force on these sentences is indirect, through Part 11 §1 and Part 05 §5.2.

### 19. R125 §3.3 at Part 11 §3 (ew-tier-2-relation-environment)

- **The revision decides:** each visible registry table MUST expose exactly its declared columns under the type mapping
- **The part now says:** “Each visible table exposes exactly its registry-declared columns under §4.” (Part 11 §3 (ew-tier-2-relation-environment))
- **Proposed text:** Each visible table MUST expose exactly its registry-declared columns under §4.
- **Placement:** Part 11 §3 (ew-tier-2-relation-environment)
- **Risk:** Part 11 has stated its language definitions in the indicative since the commit that incorporated R125 (408e6465); no later revision changed the mood. The form looks deliberate rather than accidental: the obligation is carried by actor sentences, Part 11 §1 ("A validator claiming support for this language MUST support the identified contract as a whole", the descriptor's `contract_clauses` naming this anchor) and Part 05 §5.2 (a validator "MUST parse, statically validate, bind, and type-check the rule as Part 11 requires"). Restoring the keyword contradicts nothing, but the clause's MUST is actorless, which spec/CONTRIBUTING.md §4 discourages.
- **Second reading:** Clause: "Each visible registry table MUST expose exactly its declared columns under the mapping in §3.4." Part 11 §3 says "exposes", with no keyword, while the neighbouring sentence on an unreadable resource keeps MUST NOT. No later revision touches the sentence. Scope is unchanged; only the force differs, and the only binding route is indirect (Part 11 §1, Part 05 §5.2 "bind ... as Part 11 requires").

### 20. R125 §3.3 at Part 11 §3 (ew-tier-2-relation-environment)

- **The revision decides:** a resource absent from the packet MUST bind as an empty relation with that declared shape
- **The part now says:** “the packet binds as an empty relation of that shape.” (Part 11 §3 (ew-tier-2-relation-environment))
- **Proposed text:** A resource absent from the packet MUST bind as an empty relation of that shape.
- **Placement:** Part 11 §3 (ew-tier-2-relation-environment)
- **Risk:** Part 11 has stated its language definitions in the indicative since the commit that incorporated R125 (408e6465); no later revision changed the mood. The form looks deliberate rather than accidental: the obligation is carried by actor sentences, Part 11 §1 ("A validator claiming support for this language MUST support the identified contract as a whole", the descriptor's `contract_clauses` naming this anchor) and Part 05 §5.2 (a validator "MUST parse, statically validate, bind, and type-check the rule as Part 11 requires"). Restoring the keyword contradicts nothing, but the clause's MUST is actorless, which spec/CONTRIBUTING.md §4 discourages.
- **Second reading:** Clause: "A resource absent from the packet MUST bind as an empty relation with that declared shape." Part 11 §3 says "binds", with no keyword, and the very next sentence keeps MUST NOT for the unreadable case, so the paragraph mixes moods. No later revision changes it; R151 merely relies on it ("the absent table binds as an empty relation (Part 11 §3)"). Scope unchanged, force indirect only.

### 21. R125 §3.4 at Part 11 §4 (ew-tier-2-type-binding)

- **The revision decides:** every exact-to-approximate conversion MUST use round-to-nearest, ties-to-even
- **The part now says:** “A cast to `DOUBLE PRECISION` accepts an exact or approximate numeric and rounds to nearest, ties to even.” (Part 11 §4 (ew-tier-2-type-binding))
- **Proposed text:** Every exact-to-approximate conversion MUST use round-to-nearest, ties-to-even.
- **Placement:** Part 11 §4 (ew-tier-2-type-binding)
- **Risk:** Contradicts nothing: it agrees with the explicit-cast, literal and arithmetic sentences and with the descriptor setting. The omission looks like compression, not a decision. Part 11 words its neighbours in the indicative ("rounds to nearest, ties to even"), so the sentence would be the only keyword in its paragraph besides the bind-and-type-check MUST.
- **Second reading:** The clause's general sentence closes the common-type paragraph of R125 §3.4. Part 11 names round-to-nearest, ties-to-even for the explicit cast to `DOUBLE PRECISION` (§4), the approximate literal (§5) and approximate arithmetic and `ABS` (§5), but for the implicit conversions it says only that an exact with an approximate numeric "yields the approximate domain" (§4), that an exact value "converts to the approximate domain" (§5) and that `PERCENTILE_CONT` "converts its ordering value to binary64" (§5), with no rounding mode. The nearest carrier is the descriptor's `execution.approximate_arithmetic`: "IEEE 754-2019 roundTiesToEven", but Part 11 §5 ties that setting to arithmetic and `ABS` and states conversion rounding separately case by case, so it does not reach a comparison, `CASE`, `COALESCE` or set-operation conversion. No later revision narrows the rule. ISO SQL leaves exact-to-approximate rounding implementation-defined, so the gap is one the profile was written to close.

### 22. R125 §3.4 at Part 11 §4 (ew-tier-2-type-binding)

- **The revision decides:** an integer, scale-zero decimal or other exact-decimal literal MUST compare with an exact-decimal literal by mathematical value without rounding
- **The part now says:** “An exact-decimal literal may instead compare with an exact numeric by mathematical value.” (Part 11 §4 (ew-tier-2-type-binding))
- **Proposed text:** An exact-decimal literal MUST instead compare with an exact numeric by mathematical value, without rounding.
- **Placement:** Part 11 §4 (ew-tier-2-type-binding)
- **Risk:** "may" was probably meant as admission (the comparison is allowed without a materialized common type), since §4 gives such a pair no common type and so no other way to compare; the weaker form looks accidental. Restoring contradicts nothing. Part 11 has stated its language definitions in the indicative since the commit that incorporated R125 (408e6465); no later revision changed the mood. The form looks deliberate rather than accidental: the obligation is carried by actor sentences, Part 11 §1 ("A validator claiming support for this language MUST support the identified contract as a whole", the descriptor's `contract_clauses` naming this anchor) and Part 05 §5.2 (a validator "MUST parse, statically validate, bind, and type-check the rule as Part 11 requires"). Restoring the keyword contradicts nothing, but the clause's MUST is actorless, which spec/CONTRIBUTING.md §4 discourages.
- **Second reading:** Clause: an integer, scale-zero decimal, or other exact-decimal literal "MUST compare by its mathematical value without rounding". Part 11 §4 has lowercase "may instead compare", which under Part 00 §2.5 is ordinary English and reads as a permission, leaving open that such a comparison might be decided otherwise. Two parts of the finding are refuted: the operand scope is kept ("an exact numeric" covers the integer, scale-zero decimal and other literal), and "without rounding" is implied by "by mathematical value" and by §5's "admitted only in an exact comparison". The force is what is lost, and no later revision accounts for it.
