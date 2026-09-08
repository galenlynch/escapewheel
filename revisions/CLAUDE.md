# CLAUDE.md

Guidance for writing the revision documents in this directory. Prose structure — topic and stress
position, and the symptom table for a draft that reads badly — is in the global `CLAUDE.md` and the
`prose` skill. What follows is what a revision specifically needs.

## House style: follow the v0.2 specification, not R1-R89

**The style of the existing revisions is not the target and should not be imitated.** R1 through R89
were written to a house style whose titles and section headings are often hard to interpret, and
`escapewheel_poc_docs_v0.2/` is the model to copy instead. A new revision is read by someone
implementing it months later, and their cost of reading is what the style is chosen to lower.

**A section heading names its subject.** Part 06 numbers its sections `Scope`, `Rules`,
`What justifies materializing`, `analysis.spike_events`, `Provenance of a materialization` —
noun phrases a reader locates by, not findings they must absorb in sequence. The older revisions
put a full-sentence claim in every heading, so a contents list of nine sections is nine
propositions to hold with nowhere to put them. State the finding in the body, where the stress
positions carry it.

This overrides the `prose` skill's heading guidance, which is written for a report or an argument.
A revision is navigated like a specification, by subject.

**Say which sections are normative, at the top.** Part 06 opens "Informative, except §2 and §5,
which are normative", and a reader then knows what binds them without inferring it from the
RFC 2119 keywords.

**Number sections and cite revisions inline**, as the v0.2 parts do: the rule, then `(R30 §2)`.
The citation belongs beside the clause it supports rather than in a paragraph about provenance.

**An accepted revision cites no draft.** A draft has no number, may never be accepted, and may say
something else tomorrow, so a citation of one is a dangling reference the moment it is written.
State the substance instead: name the column, the measurement or the rule rather than the document
that will carry it. The reverse is fine — a draft cites accepted revisions freely, and records its
own debt to them.

**Never cite a `CLAUDE.md`.** These files are guidance for whoever is working, not part of the
specification, and a normative document citing process documentation makes the process normative by
accident — a reader implementing a revision months from now has the spec and the revisions, and
should need nothing else. Where something written here bears on a decision, state the reasoning or
cite the revision that established it: R67 §2.4 for a requirement no rule can observe, R3 §3.0 for
duplication that buys nothing, R62 for striking what nothing writes and nothing reads.

**A title names what the revision settles.** Still declarative, still not an imperative and not an
aphorism, but a subject a reader can recognise before they open it: "Primary-Key Order for Every
Table" over "A Table Sorts Itself the Way It Is Keyed".

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

**A requirement needs an actor who can comply, not a tool that can catch them.** "The two MUST
agree" names nobody who could fail, so it binds nothing and the repair is to say who acts: "a build
MUST refuse where they differ". That a validator cannot see the breach is not the same defect —
"a consumer MUST NOT infer attachment from a device's name" (R67 §2.4) binds a named actor to a
determinable behaviour, and 24 clauses across Parts 00-09 are of that kind, including a reader's
ban on depending on stored order and R39's rule that a consumer without a time origin refuses
rather than invents. Strike the actorless MUST; keep the uncheckable one.

## What a revision must carry

Brevity is never worth an implementer's question. Never cut:

- the measurement, its size, and what it was measured on;
- the rule, in MUST / MUST NOT / SHOULD / MAY;
- the one sentence saying why the obvious alternative fails;
- what the change costs and what has to be rebuilt.

A revision that is short because it dropped a number is incomplete, not concise.

## A draft carries no number

`revisions/drafts/` holds work that is not accepted, named by slug and with a status line of
`Draft`. The `R<N>` space is history: accepted and withdrawn only.

An `R<N>` is permanent once accepted — `applied.toml` keys on it, `build.py` stamps it into every
column's `since`, `derived_from` lists it, and the compiled spec cites it — so numbering at
drafting time would force the application order to match the drafting order. Drafts are reordered
by editing `revisions/drafts/README.md`, which carries the intended order and why each draft sits
where it does. A draft cites another by its file name in backticks, since it has no number to cite.

## Checks before acceptance

Run these against the document before the status line moves. Each has caught a real defect, and
the ones a tool can settle are cheaper than the ones only a reader can.

- **Re-measure every number against the current registry and the current packets.** A revision
  sits Proposed while the registry moves under it. R86 was drafted saying 32 of 34 tables were
  session-scoped and R83 added one before it was accepted; its name-collision count was measured
  before `core.events` carried names, and missed the largest collision of all. R89's §4 arithmetic
  was measured before R88 and was wrong by 18 columns and 14 references.
- **Run `check.py`'s `NAMING` against every column the revision declares.** The conventions are
  data — lift `NAMING`, `RESERVED` and `INTEGERS` out of `registry/check.py` and apply them to the
  proposed names, types and roles rather than reading them. R89 declared `calibration_kind` for an
  open vocabulary of values, which would have failed the build: a `_kind` column is a discriminator
  (R55 §2.1), and an open vocabulary takes `_type`, as `event_type` and `activity_type` do.
- **Every column declares a type, a presence and a role.** R48 §2.2 gives a role no default, so a
  column named in prose but not declared is a build error rather than a guess. R89 gave one table a
  full declaration and two others as tuples, leaving eight columns without a type.
- **Every citation resolves to the section that says it.** R89 §2.3 cited R56 §2.2 for the one-hop
  `resource.column` form, which R56 §2.3 defines; §2.2 is `clock_from`. Open the cited section.
- **No section contradicts another.** R89 §1.2 argued a calibration is reported as in force
  *rather than as having happened*, and §2.5 then said a row records that it happened. Read the
  Decision against the Motivation it rests on, and read §3's bullets against the Decision.
- **Name the other Proposed revisions that touch the same counts, and say which order.** R89 and
  R95 both change the column count and R95's rule adds a column to one of R89's tables, so
  whichever lands second is describing a registry that already has the other. Whatever is measured
  against today is re-measured at the second acceptance.
- **A claim about rows coexisting is a claim about the primary key.** Anything the text says can
  exist together, be distinguished, or be chosen between — write the key out and check it admits
  them. R49 §1 found a colliding key this way and R55 §2.3.1 a reference targeting a non-unique
  set; R58 §2.3 asserted two registrations coexist under a key that admits one, and that survived
  acceptance.
- **A measurement stated twice.** Adding a section to one that already carries a number leaves the
  number in both. State it where the rule it supports lives.
- **"What this does not do" listing the unassumed.** It lists only what a reader would otherwise
  reasonably assume the revision does.

## After the user accepts

Only the user moves a revision to Accepted. What follows is one sequence, in this order, and
`python verify.py` is what says it is complete. `DEVELOPING.md` §4 is the machinery each step
touches.

1. **The draft is numbered and moved.** It takes the next free `R<N>`, moves from
   `revisions/drafts/` to `revisions/R<N>-<slug>.md`, and its status line becomes
   `**Accepted** <YYYY-MM-DD>`. Every citation of it — in other drafts and in this one's own text —
   becomes `R<N> §<x>`; `grep` the slug to find them. Until the file is numbered and accepted,
   `ledger.py` skips it and `check.py` refuses the `derived_from` entry a build block creates.
   Reorder `revisions/drafts/README.md` if accepting this one changed what should come next.

   **Where it supersedes a clause, repoint every citation of the superseded clause too**, in every
   other draft and in the compiled spec — not only in the documents the supersession was written
   against. A citation into a superseded section names a statement that is no longer the one of
   record, and nothing checks it: `ledger.py` sees that the clause has a disposition, and a
   citation sweep sees a section that still exists. `declaring-and-resolving-a-discriminator`
   restated R55 §2 and left **nine** citations of R55 §2.1, §2.2, §2.3, §2.3.2, §2.4 and §2.6
   across two other drafts, each of them pointing at prose the restatement had replaced. Grep the
   superseded section numbers, not just the slug.
2. **`registry/build.py`.** Register every new column name in `ROLES`, every new identifier in
   `IDENTITY`, and every new discriminator in `DISCRIMINATOR` — each refuses an unclassified name
   with a `SystemExit` naming the choice. Then add the block, stamped `SINCE[0] = "R<N> §<x>"`,
   after the last revision's block and before the Tier 2 merge. `derived_from` follows from the
   stamp; a revision that changes no column goes in `UNSTAMPED` instead.
3. **`registry/rules.json`** for each Tier 2 rule, whose query returns offending rows (R2 §7.3).
4. **`conformance/spec-sweep/tables.py`** for a table added or withdrawn, or `check.py` fails
   against the R9 §2 ledger.
4a. **`registry/extensions/*.json`.** An extension is a registry document in the same format
   (R17 §2), so a rule about what a table declares binds one as much as it binds core — and the
   four here drift, because nothing regenerates them. Check every extension against the rule the
   revision states, not only against the rule it changes: R88 §2.1 required a session-scoped table
   to declare its reference and the three `aind_unit_qc` tables carried `session_id` validated by
   nothing for two revisions. A meta-schema change is the case that fails loudly, since
   `registry.schema.json` sets `additionalProperties: false`; a missing reference or a forgotten
   role fails quietly, which is why this is a step rather than something `verify.py` catches.
5. **The v0.2 parts the revision amends**, which is what `Amends` named. **Place a clause by its
   subject, never by what is last.** Every section of a part names a subject — in `02`, §8 is
   column semantics, §11 the resource index, §12 rules for particular resources, §13 stored
   layout — so a clause goes in the section whose subject it is, as a new subsection at the end of
   *that* section where none of the existing ones fits. A subsection appended inside a section
   renumbers nothing.

   A new concept is the exception, with a rule of its own: append it to `01` §3 as the next
   number, because that section is a flat list of concepts and inserting one renumbers the
   concepts every later part cites. That rule is about `01` §3 and no other section.

   Appending to whichever section comes last is what this prevents, and it had already happened
   three times. R81, R83 and R89 each added to `02` §12, so a section titled "Ordering" came to
   hold unit identity, channel indices and calibration, with 40 of its 44 lines about none of
   them, in the one section of Part 02 that had no subsections to place them in. Where a clause
   genuinely fits no section, add a section at the **end of the part** — appending after the last
   one renumbers nothing either — rather than filing it under a heading that does not describe
   it.
6. **`escapewheel_poc_docs_v0.2/applied.toml`**, one entry per clause. `ledger.py` demands a
   disposition for every §2 subsection and for any other section carrying a MUST or a SHOULD, and
   fails equally on an entry naming a clause that no longer exists.
7. **`python escapewheel_poc_docs_v0.2/combine.py`** for the single-file rendering.
8. **`python verify.py`.** Every stage but the three clean-tree ones must pass before committing;
   those compare against the committed state and so clear only on the commit itself.

Three traps, each of which cost time here:

- **`CONTEXT` and the R53 §2.3.1 name block are consumed before a late block runs**, so a table
  added at the end declares its own `unit_from` inline and its own `*_name` column. A `CONTEXT`
  entry for a table that does not yet exist raises.
- **`check.py` skips rule execution without DuckDB**, and a rule referencing a missing column
  passes silently. Run it as `uv run --with duckdb python check.py` from `registry/`, or let
  `verify.py` do it.
- **A generated file edited by hand is overwritten**, `logical_schemas.json` above all. Everything
  in `registry/` except `build.py`, `rules.json`, `check.py` and the two hand-written schemas is
  output.

## Length

R50 is 857 words and renames three columns, each with its reason. R45 is 1,633 for a contradiction
written in two places. Past about 1,500, check that the extra words carry a measurement or a rule
rather than a case made twice.
