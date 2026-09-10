# A Requirement Is Cited Where It Is Stated

| | |
|---|---|
| **Status** | Draft |
| **Amends** | `00` (adds a section on how a requirement is cited and how a part is numbered); `07` §2 (what a comment in the reference implementation states and cites) |
| **Depends on** | R93 §3.6 (`00` lists the parts and what each one binds), R93 §4 (where a clause belongs), R29 §2 (a registry column names the revision that set it), R111 §3.3 (a requirement binds an actor or describes an artifact) |
| **Profile** | all |

Normative, except §2, which is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

The parts are the specification and the revisions record how it came to say what it says. R93 §4
states where a clause belongs among the parts and R93 §3.6 has `00` list what each one binds;
neither says which of the two a reader should be sent to for a rule, and the reference
implementation answers one way while the parts answer the other: **754 citations of a revision
against 192 of a part**, across the three distributions' source.

This part states where a requirement is cited from, what a revision may still be cited for, and how
a part is numbered so that citing one stays safe.

## 2. Background

Informative.

### 2.1 A citation into a revision points at a document that has moved on

A revision records a change: what was believed, what replaced it, and what the replacement cost. Its
sections are shaped for that — a Motivation, a Decision, a `What this does not change` — and none of
them is the statement of record once the change has landed. A part is.

Two miscitations found in one week are the same failure:

- **`R83 §3` was cited four times**, twice in R105, once in R103, once in a draft, for a writer's ban
  on inferring a channel list. `R83 §3` is `What this does not change`; the rules are §2.2 and §2.3.
- **`R68 §3` was cited three times** for the tick encoding SHOULD. R68 states no SHOULD at all — the
  rule is original to `03` §5.5 and has been there since the specification's first commit, so the
  citation named a revision that had never made the rule and a section that states nothing.

Both passed `check_citations.py`, because both sections exist. Neither would have survived pointing
at a part: `03` §5.5 either carries the rule or it does not.

### 2.2 The parts already carry the provenance a revision citation was reaching for

Citing the part loses nothing, because the part cites the revision itself. `09` §5.1 reads "An
extension is a registry document in the format of Part 02, in its own namespace (R17 §2)", and
`03` §6 reads "A writer MUST NOT modify a resource the packet owns once it is committed (R14 §2.3)".
Code citing `09` §5.1 is one hop from R17 §2 and zero hops from the sentence that binds it.

`applied.toml` is the map. Of **235 distinct revision clauses cited across the three distributions'
source**, the ledger disposes 192 and **117 landed in a part**, which covers **455 of the 754
citations**. The rest divide the way the dispositions do: 42 landed in the registry, 14 are about
this implementation and belong where they are, 8 are rationale, and **11 are `superseded`** — code
pointing at prose another revision has replaced.

### 2.3 A part's numbers move, and that is what makes them checkable

The objection to citing a part is that its section numbers are not permanent. They move rarely and by
discipline — a subsection appended inside a section renumbers nothing, and a section appended at the
end of a part renumbers nothing — but they do move: `05` §11 was appended twice, so the part carried
two sections of that number until one was renumbered, and every citation of `05` §11 was ambiguous
meanwhile.

That is an argument for citing the part rather than against it. `check_citations.py` resolves a part
citation against the headings that exist and fails the build when one does not, where a revision
citation can be checked only for existence — which is how `R83 §3` and `R68 §3` survived. **The
citation that can move is the one something checks; the citation that cannot is the one that rots
in silence.**

## 3. Decision

### 3.1 A requirement is cited from the part that states it

**Where a part states a requirement**, a citation of it — in the reference implementation, in a
packet's documentation, or in a revision's Decision — **MUST** name that part and section, and
**MUST NOT** name a revision in its place. That sentence is what binds (R93 §3.6), and a revision
naming the same rule records how the part came to say it.

Not every requirement is in a part. The ledger disposes **14 clauses as `implementation`**, which
decided something about this implementation rather than about the format, and **8 as `rationale`**,
which decided nothing and explain. Neither landed in a part, so neither can be cited from one, and a
citation naming the revision is the only citation available. §3.3 covers the second and this covers
the first: where the ledger disposes a clause anywhere but a part, the revision **is** the statement
of record.

### 3.2 A comment states what the code does not

A comment or docstring in the reference implementation **SHOULD** state what the code does not
already say — why this way, what breaks otherwise, the constraint that is not visible locally — and
**SHOULD NOT** restate what the line below it does. Where it gives a reason, §3.1 decides what it
cites: the part for the requirement, and the revision for the measurement behind it (§3.3).

This is not a style preference dressed as a requirement. A comment naming a revision instead of a part is
how the source came to hold 754 citations of the change record against 192 of the specification, and
a comment restating its own line is how a reader learns to stop reading them.

### 3.3 A revision is cited for what a part does not carry

A revision **MAY** be cited for the reasoning a part does not hold: the measurement behind a rule,
the alternative that was rejected and why, and the defect that prompted the change. A part states
what holds; a revision states why, and a reader wanting the second is sent to the revision by name.

Three uses name a revision and are sound, and nobody repoints them at a part:

- a registry column's `since`, which R29 §2 makes revision-keyed so `tables.md` answers both what a
  table is and why;
- `applied.toml`, which maps a revision's clauses to where each landed and is the map §3.1 is
  resolved through;
- a revision citing another revision, which is one record referring to another.

The exemption says which document to cite and not that the citation is right. `10` §2.1 stamped its
`pts` measurement `R68 §3`, which is `What this does not change`, where the measurement is R68 §1.3 —
a provenance citation this section permits, pointing at the wrong section of the revision it
correctly named.

### 3.4 A part is numbered by appending

Whoever amends a part **MUST** add a section at the end of that part, and a subsection at the end of
its section, neither of which renumbers anything already cited. They **MUST NOT** insert one between
two that exist, and a part **MUST NOT** carry two sections with one number.

`01` §3 is the case that made this explicit and is not an exception to it: that section is a flat
list of concepts every later part cites by number, so a concept is appended as the next number.

### 3.5 A build refuses a part whose numbering has drifted

A tool that checks citations **MUST** refuse a part carrying two sections with one number, and
**SHOULD** refuse one whose sections do not ascend. Both are decidable from the headings alone, with
no citation in hand, and both were undetected until `05` carried two sections numbered 11 through
five accepted revisions.

## 4. What this does not change

- **No table, column, reference, rule or vocabulary changes, and no packet is rebuilt.** This binds
  what a citation names, so what changes is where a reader is sent.
- **A revision still records what it amends.** §3.1 binds a citation *of a requirement*, not the
  `Amends` line, which names the part a revision changes and is the thing `applied.toml` is built
  from.

## 5. Consequence

`00` gains a section and `07` §2 gains what a comment states and what it cites. The three distributions carry
**754 revision citations against 192 part citations**, of which 455 repoint by looking the clause up
in `applied.toml` and taking its `where`. The 11 disposed `superseded` are the ones to read rather
than rewrite: each points at prose that no longer stands.

Nothing about a packet changes, and no rule this specification states moves. What moves is the
direction a reader is sent when they ask what binds them. §3.5's numbering check is owed:
`check_citations.py` resolves a citation and does not yet refuse a part carrying two sections with
one number.

Citing a part is only maintainable if a change to one can find its citers, which nothing could do:
`check_citations.py` asks whether a citation resolves, and a citation into a rewritten section
resolves perfectly. `revisions/impact.py` answers the other direction — it maps each changed line to
its section and lists every file citing it — and finding the citers is what §3.1 turns from a
search into a lookup. Run against the commit that accepted R110 it reports **48 sections changed and
138 citations to read**, `03` §5.5 alone carrying **19** — a figure that grows as documents cite a
section, which is the point of reading it before editing one rather than after.

## 6. Open

- **Whether a part's headings should be checked against the citations that resolve to them.** §3.5
  refuses a part whose numbers collide, which catches the `05` §11 case, and catches nothing where a
  section keeps its number and changes its subject. Recording the heading each citation resolved to,
  and flagging a citation whose heading has since changed, would catch that; whether the flag is
  worth the file it needs is unmeasured, since no instance has been found.
