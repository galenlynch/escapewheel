# CLAUDE.md

Guidance for writing the revision documents in this directory. Prose structure — topic and stress
position, and the symptom table for a draft that reads badly — is in the global `CLAUDE.md` and the
`prose` skill. What follows is what a revision specifically needs.

## Before drafting

**Invoke the `prose` skill.** Not optional and not only for long ones: the failure it prevents is
a clause a reader has to re-parse, and a revision's reader is implementing it months later with
no author to ask.

**A title is a declarative statement of the rule, not an imperative.** A commit title is
imperative because a commit is an action applied at a moment; a revision outlives the action, and
its reader wants the rule that now holds. "An Identifier Is an Integer" answers the question they
arrived with, where "Make Identifiers Integers" describes a finished task. Where the rule is that
something declares a fact, R44, R48 and R56 give the form: "A Run Declares Its Scope".

**A title says what the revision does, literally.** Not an aphorism, and not a metaphor a reader
has to unpack before they know whether to open it. "A Packet Holds Only One Interpretation" over
"A Second Interpretation Is a Second Packet"; "Unit IDs Are Assigned by the Packet" over "A Packet
Numbers Its Own Units". Someone scanning the revision list is deciding whether this one is
relevant, and a clever title makes them read the document to find out.

**A section heading states one finding.** A comma or an "and" joining two of them means the
section is doing two things and wants splitting, or the heading is describing the route to a claim
rather than stating it. "The label repeats across runs" over "A carried label is not an
identifier, so the key grew to four columns"; "A channel index is an offset into the run's channel
list" over "A channel index counts the channels the run kept".

**Two clauses are right where the second corrects the first.** The count is of findings, not of
clauses: a heading may put the reader's wrong assumption in the topic position and the fact in the
stress position, which is the order Gopen and Swan prescribe and one finding delivered against the
belief it displaces. "SpikeInterface does not index electrodes; it indexes a subset of the original
channels" says more than either half alone. Join them with a semicolon — a comma between two
independent clauses is a splice.

**The opening paragraph introduces what the rest refers to.** A revision's first section is the
reader's first contact with the problem, so it has no old information to put in a topic position
and must create some. Name the column, the table or the file, say what was believed about it, then
correct the belief — the measurement lands after that, in a reader who can be surprised by it.
"`extremum_channel_index` is the NWB's statement of which electrode a unit peaks on" before
anything counts how often it was read wrongly.

**The headings must read as an outline on their own.** Someone deciding whether to open a section
reads the contents and nothing else, so a heading leaning on the body for its referent tells them
nothing: "Only one session records the list" leaves *which* list in a paragraph they have not
read. Name the thing. A pronoun pointing back at an *earlier heading* is fine, since they are read
in order — "A consumer resolves a channel index through the new table" works because the heading
above it introduced one.

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
- **A measurement taken while drafting goes stale.** A revision sits Proposed while the registry
  moves under it. R86 was drafted saying 32 of 34 tables were session-scoped and R83 added one
  before it was accepted; its name-collision count was measured before `core.events` carried
  names, and missed the largest collision of all. Re-run every count against the current registry
  and the current packets before the status line changes.

## Length

R50 is 857 words and renames three columns, each with its reason. R45 is 1,633 for a contradiction
written in two places. Past about 1,500, check that the extra words carry a measurement or a rule
rather than a case made twice.
