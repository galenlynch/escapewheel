# CLAUDE.md

Guidance for writing the revision documents in this directory.

## What a revision is

A **decision record**: what was wrong, what the rule is now, what it cost. It is read by someone
implementing it, months later, who needs the rule and the evidence and nothing else.

It is not an argument to be won. The reader is not an opponent, has not raised an objection, and
does not need to be persuaded that the finding is interesting.

## Structure

Status table, then numbered sections. Motivation, decision in RFC 2119 language, what does not
change, what stays open. Name the documents and sections amended.

**Target length is R50's**, at 857 words: three columns renamed, each with its reason. R45 is
1,633 for a contradiction stated in two places. Past about 1,500, check that the extra words are
carrying a measurement or a rule rather than a case being made twice.

## Tests to apply to a sentence

Each of these is checkable, unlike "be concise".

- **Does it add a fact, a number, a rule, or a named consequence?** If its only job is emphasis,
  cut it.
- **Does it restate the sentence before it?** Then that sentence failed. Fix it and delete this one.
- **Does it tell the reader that something is important, surprising, or the point?** Cut the
  telling. State the thing and let it be judged.
- **Does it answer an objection nobody made?** Cut it.
- **Is there an adjective where a number is available?** Use the number. "10.2x", not "much faster".
- **Does it exist to transition?** Cut it.

A rejected alternative gets one sentence and the reason it fails. Not a paragraph, and not a
paragraph followed by the reason restated.

"What this does not do" lists only what a reader would otherwise reasonably assume it does.

## Claudisms to strike

These are the tics, and they are the bulk of what makes a draft long:

- "It is not X — it is Y." Say what it is.
- "That is the point." / "which is the whole reason" / "and that is what makes it Y."
- Three sentences making one point from three angles.
- "Worth noting", "It is worth", "Notably", "Crucially".
- A section that opens by restating the question it is about to answer.
- A punchy one-line closer at the end of a section.
- **Bold** used for emphasis inside a sentence. Bold a defined term, not a feeling.
- Em-dash asides carrying a second thought the sentence did not need.

## What always stays

Brevity is not worth an implementer's question. Never cut:

- The measurement, its size, and what it was measured on.
- The rule, in MUST / MUST NOT / SHOULD / MAY.
- The one sentence saying why the obvious alternative fails.
- What the change costs and what has to be rebuilt.

A revision that is short because it left out a number is not concise, it is incomplete.
