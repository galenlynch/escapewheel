# CLAUDE.md

Guidance for writing the revision documents in this directory. Prose structure — topic and stress
position, and the symptom table for a draft that reads badly — is in the global `CLAUDE.md` and the
`prose` skill. What follows is what a revision specifically needs.

## What a revision is

A decision record: what was wrong, what the rule is now, what it cost. Its reader is implementing
it months later and needs the rule and the evidence. Nothing in it has to persuade — the reader has
raised no objection and is not an opponent.

## Structure

A status table, then numbered sections: motivation, the decision in RFC 2119 language, what does
not change, what stays open. Name the documents and sections amended, and state the replacement
rule rather than describing it.

**MUST is RFC 2119 here.** A lowercase "must" in a Decision section states no requirement, whatever
the surrounding emphasis suggests. Where the implementation enforces something, the document says
**MUST**.

## What a revision must carry

Brevity is never worth an implementer's question. Never cut:

- the measurement, its size, and what it was measured on;
- the rule, in MUST / MUST NOT / SHOULD / MAY;
- the one sentence saying why the obvious alternative fails;
- what the change costs and what has to be rebuilt.

A revision that is short because it dropped a number is incomplete, not concise.

## Checks before proposing

- **A claim about rows coexisting is a claim about the primary key.** Anything the text says can
  exist together, be distinguished, or be chosen between — write the key out and check it admits
  them. R49 §1 found a colliding key this way and R55 §2.3.1 a reference targeting a non-unique
  set; R58 §2.3 asserted two registrations coexist under a key that admits one, and that survived
  acceptance.
- **A measurement stated twice.** Adding a section to one that already carries a number leaves the
  number in both. State it where the rule it supports lives.
- **"What this does not do" listing the unassumed.** It lists only what a reader would otherwise
  reasonably assume the revision does.

## Length

R50 is 857 words and renames three columns, each with its reason. R45 is 1,633 for a contradiction
written in two places. Past about 1,500, check that the extra words carry a measurement or a rule
rather than a case made twice.
