# R94 — A Tier 2 Rule Names No Optional Column

| | |
|---|---|
| **Status** | **Accepted** 2026-09-08 |
| **Amends** | R2 §5 (what `optional` permits), R2 §7.2 (what a Tier 2 rule may reference) |
| **Depends on** | R2 (the registry format and three-state presence) |
| **Profile** | all |

Normative, except §2, which is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

R2 §5's third presence state, `optional`, permits a column to be **absent from the file** rather
than merely null in it. A Tier 2 rule is SQL executed against that file (R2 §7.2). Nothing says
what happens when a rule names a column a conforming packet has left out, and the answer is worse
than a missed check: the query fails to parse, so the run that was meant to find defects reports an
error of its own.

This part states the rule the registry has always obeyed and adds the check that keeps it obeyed.

## 2. What the registry does today

Informative.

The registry declares **25** optional columns — twenty-one `metadata`, two `parameters`,
`core.events.payload` and `core.clocks.transform_to_parent` — and **none of the 69 Tier 2 rules
names any of them**.

The convention is therefore real and unwritten, which is how it has held: every rule author so far
has written against a column that is present. Nothing would have told them otherwise. The writer
omits `metadata` on ten of the twenty-one tables declaring it and `payload` on both packets, so a
rule naming one of those would have failed on the first packet built rather than on some later one
— which is the accident that has kept the class closed rather than a rule that closed it.

## 3. Decision

A Tier 2 rule's SQL **MUST NOT** reference a column whose presence is `optional`.

`registry/check.py` enforces it: for each rule, the identifiers its SQL names are matched against
the registry's optional columns, and a hit is a build error. The check is structural — decidable
with no packet in hand, as R56 §2.4's is — because whether a column may be absent is a property of
the declaration and not of any file.

The match is on **identifiers, not text**: string literals and comments are stripped first, and a
name matches only whole. `some_metadata_key` is therefore not a hit, and neither is `'metadata'`
compared against a column. That is exact enough without parsing a SQL dialect this repository
otherwise never parses, and it keeps the check off DuckDB, which `check.py` treats as optional and
which a rule-execution check is already gated behind.

A hit is a true positive because each of the four names §2 lists is optional on every table
carrying it. Only 4 of the 69 rules contain a string literal at all, and none of those literals
holds any of the four.

**That invariant is what the check rests on, and no clause states it.** Qualifying the match by
table is not the repair. **42** of the 69 rules read one relation, where a bare column resolves to
it without ambiguity; the other **27** read two to five, and a bare column in any of those cannot
be resolved without the parser this part has just declined. So a qualified match would cover the
easy majority and fail on exactly the rules that need it.

The repair is to require the presence rather than to qualify the reference: a column named
`metadata` is optional because that is what the column is for, and a revision governing the
free-form column should say so, at which point this check is sound by construction rather than by
observation. That revision is not this one — a naming-to-presence rule belongs with the column it
names — and until it exists, §6 records the exposure.

A rule that wants to constrain an optional column has two ways out, and this part prescribes
neither: the column can be made `nullable`, which is a declaration that it is always present and
sometimes empty, or the constraint can move to the shim, where R12 §4 puts what SQL cannot see.

## 4. What this does not change

- **No rule changes.** All 69 already comply; the check passes on the registry as it stands.
- **No column's presence changes.** The 25 optional columns stay optional.
- **`optional` keeps its meaning.** R2 §5's three states are unaltered; this constrains what a rule
  may assume about them, not what a writer may do.
- **Tier 1 is unaffected.** None of the 25 is an identifier, a reference or a closed vocabulary,
  so Tier 1 generates nothing over them, and the shim reports an absent column only where its
  presence forbids the absence — `schema.column_absent` fires for a `required` or `nullable`
  column and stays silent for an `optional` one, which is the behaviour this part protects.

## 5. Consequence

`registry/check.py` gains one check. No table, column, reference or rule changes, and no packet is
revalidated differently.

The next revision in the application order adds a Tier 2 rule, taking the count to 70, so whichever
of the two lands second re-measures the rule count this part uses as a denominator in §2, §3 and
§4.

## 6. Open

- **What happens if one of the four names is ever declared required.** §3's match is unqualified
  and sound only while they are all optional, which nothing requires. A **required** `metadata` —
  an R17 extension could declare one — would make a rule naming that column a false positive, and
  a false positive here is a build error against a rule that is correct. The failure is loud and
  lands on whoever declared the column, which is why this part ships the check rather than waiting:
  §3 says what closes the exposure, and it is a clause in a different revision rather than a
  mechanism in this one.
