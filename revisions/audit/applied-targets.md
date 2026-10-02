# Audit of the ledger's applied targets

The clause ledger, `revisions/applied.toml`, records where each `applied` Decision clause of an
accepted revision is now stated. The ledger check resolves each target and reads no text inside it,
so a clause can be recorded at a section that does not state it. This audit reads every applied
target against its section once. It adds no field to the ledger and no check to the tools: a finding
is repaired where it lies, in the part or in the ledger entry.

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
