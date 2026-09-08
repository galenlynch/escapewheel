# A Tier 2 Rule Names No Optional Column

| | |
|---|---|
| **Status** | Draft |
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

The registry declares **25** optional columns — twenty-one `metadata`, two `parameters`, `payload`
and `core.clocks.transform_to_parent` — and **none of the 70 Tier 2 rules names any of them**.

The convention is therefore real and unwritten, which is how it has held: every rule author so far
has written against a column that is present. Nothing would have told them otherwise. The writer
omits `metadata` on ten of the twenty tables declaring it and `payload` on both packets, so a rule
naming one of those would have failed on the first packet built rather than on some later one —
which is the accident that has kept the class closed rather than a rule that closed it.

## 3. Decision

A Tier 2 rule's SQL **MUST NOT** reference a column whose presence is `optional`.

`registry/check.py` enforces it: for each rule, the columns its SQL names are matched against the
registry's optional columns, and a hit is a build error. The check is structural — decidable with
no packet in hand, as R56 §2.4's is — because whether a column may be absent is a property of the
declaration and not of any file.

A rule that wants to constrain an optional column has two ways out, and this part prescribes
neither: the column can be made `nullable`, which is a declaration that it is always present and
sometimes empty, or the constraint can move to the shim, where R12 §4 puts what SQL cannot see.

## 4. What this does not change

- **No rule changes.** All 70 already comply; the check passes on the registry as it stands.
- **No column's presence changes.** The 25 optional columns stay optional.
- **`optional` keeps its meaning.** R2 §5's three states are unaltered; this constrains what a rule
  may assume about them, not what a writer may do.
- **Tier 1 is unaffected.** Its checks are generated from structure and already skip a column the
  file does not carry, which is what `schema.column_absent` reports instead.

## 5. Consequence

`registry/check.py` gains one check. No table, column, reference or rule changes, and no packet is
revalidated differently.

## 6. Open

- **Whether the column-name match should be exact.** The check reads a rule's SQL as text, so a
  column name appearing inside a string literal or as another table's column of the same name would
  be a false positive. `metadata` and `payload` are distinctive enough that neither occurs today; a
  parser rather than a substring match would settle it, at the cost of a SQL dialect this
  repository does not otherwise need to parse.
