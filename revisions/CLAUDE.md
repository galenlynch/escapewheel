# CLAUDE.md

Guidance for writing the revision documents in this directory.

## What a revision is

A decision record: what was wrong, what the rule is now, what it cost. Its reader is implementing
it months later and needs the rule and the evidence. Nothing in it has to persuade — the reader has
raised no objection and is not an opponent.

## Read it the way Gopen and Swan do

*The Science of Scientific Writing* (Gopen and Swan, American Scientist, 1990) is the standard this
directory is written to. Its claim: a reader spends interpretive energy on structure before
content, so where information sits decides how much energy the content gets. Clarity is therefore a
property of the reader's interaction with the prose, never of the prose alone — a sentence that
*can* be read correctly will not necessarily *be* read correctly.

Two positions in a sentence do the work.

- **Topic position** — the opening. It says whose story this is, and it is where **old**
  information belongs, linking back to what the reader already holds.
- **Stress position** — the point of syntactic closure, at a full stop or a properly used colon or
  semicolon. A reader emphasises whatever arrives there, so it belongs to the **new** information.

Their principles, in the order they matter here:

1. Put the new information in the **stress position**. This is the one that fixes most drafts.
2. Put old information in the **topic position**, so context precedes anything new.
3. Articulate the action of a clause in its **verb**, not in a nominalisation.
4. Follow a grammatical subject promptly with its verb.
5. Make the emphases of the substance match the emphases the structure creates.

The last one is the test for a revision specifically: **the rule should land in a stress
position.** If the closure of a sentence falls on rhetoric, the rule is somewhere weaker.

## Symptoms, and what they mean

Each of these is a structural fault with a familiar surface. Treat the cause, not the wording.

| symptom | what has gone wrong |
|---|---|
| "It is not X — it is Y." | X, a negation of old information, holds the stress position; Y needs a second clause to arrive |
| Three sentences making one point from three angles | the point never reached a stress position, so it was attempted again |
| A punchy one-line closer | the stress position spent on rhetoric rather than on new information |
| **Bold** inside a sentence | a confession that the emphasis is not structural. Bold a defined term; never a feeling |
| An em-dash aside carrying the key fact | the fact arrived after closure, in the weakest place available |
| A trailing "which is …" clause | the sentence closes on a pronoun |
| "That is the point." / "Worth noting" / "Crucially" | the reader is being told an evaluation instead of given a fact |
| A section that opens by restating its own heading | the topic position spent on information the reader already has |

Two further rules that are not positional:

- Prefer a number to an adjective. "10.2x", never "much faster".
- A rejected alternative gets one sentence and the reason it fails.

## What always stays

Brevity is never worth an implementer's question. Never cut:

- the measurement, its size, and what it was measured on;
- the rule, in MUST / MUST NOT / SHOULD / MAY;
- the one sentence saying why the obvious alternative fails;
- what the change costs and what has to be rebuilt.

A revision that is short because it dropped a number is incomplete, not concise.

## Length

R50 is 857 words and renames three columns, each with its reason. R45 is 1,633 for a contradiction
written in two places. Past about 1,500, check that the extra words carry a measurement or a rule
rather than a case made twice.
