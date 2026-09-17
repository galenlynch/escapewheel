# Contributing specification revisions

This guide defines the file-based process for proposing, drafting, accepting, and incorporating a
change to the Escapewheel specification. The repository-wide
[authority model](../README.md#authority) applies throughout.

## Scope of this process

This is a specification-change process, not a general repository-change process. Use it when a
change would alter what a conforming packet or actor is permitted or required to do, how a
normative statement is interpreted, or the packet contract expressed by an incorporated registry
or schema. Changes to specification authority, identities, required resources, validation
outcomes, and other conformance rules are in scope.

Use the ordinary repository workflow instead for:

- root and package README improvements that do not change the specification;
- agent instructions, contribution guidance, and other developer documentation;
- implementation changes that bring code into conformance with an unambiguous existing rule;
- tests, continuous integration, refactoring, and maintenance that do not change the contract;
- meaning-preserving specification edits such as spelling, formatting, repaired links, and
  regenerated facts or renderings.

The specification README is governed by the same boundary. Navigation, publication status, and a
clear reference to an existing authority are editorial. Changing which artifacts bind, how a
conflict is resolved, or what constitutes a specification release is a specification change and
uses this process.

When classification is uncertain, ask whether two conforming implementations could behave
differently after the change while both following the text. If so, treat it as a specification
change. A proposal is still optional when the user has already settled the problem, scope, and
direction, as described below.

## Authority and lifecycle

The process has three deliberately different artifacts:

| stage | location | purpose | authority |
|---|---|---|---|
| **Proposal** | `proposals/<slug>.md` | Establish the problem, evidence, constraints, alternatives, and questions worth deciding. | None. It contains no normative language and may be abandoned or substantially changed. |
| **Revision draft** | `drafts/<slug>.md` | State one candidate decision precisely enough to appraise and implement. | None. It has no revision number and does not change the specification. |
| **Accepted revision** | `R<N>-<slug>.md` | Preserve the approved decision, evidence, cost, and provenance of the corresponding spec change. | Historical decision record. The change binds through its incorporation into the generated v0.2 specification, which remains the normative source. |

Use the templates in `templates/`. Start with a proposal unless the user has already supplied a
settled problem, scope, and intended direction. Promotion is not a rename: carry forward the facts
that survived review, resolve or record the open questions appropriate to the next stage, and remove
stage-specific discussion. Delete the superseded proposal or draft once promoted; Git retains it.

Acceptance and incorporation are one reviewable change. Only the user authorizes acceptance. Until
the accepted text and its implementation have been incorporated into the generated v0.2 parts and
all checks pass, the existing generated specification continues to state what holds.

## Writing a revision

Follow the shared specification style in
`../escapewheel_poc_docs_v0.2/CONTRIBUTING.md`. A revision adds one genre-specific constraint: it
is a decision record rather than the current statement of the standard. Its reader needs to recover
what was wrong, what decision was approved, why the obvious alternative failed, and what the change
cost.

Read the current generated parts, relevant registry declarations, and the proposal before drafting.
Describe the current rule accurately before replacing it. If the proposal still contains unresolved
questions that would change the normative clauses, it is not ready to become a draft.

### Title and outline

Use a literal, declarative title that states the candidate rule. Do not use an imperative, aphorism,
or metaphor. Avoid using a defined Escapewheel term loosely in the title.

Number the sections. Use the template's stable subjects—Scope, Background, Decision, Consequence,
and optional sections only where they carry content. A subsection heading either names the thing it
defines or states the finding the section establishes. It must make sense in the outline without its
body, and each section should carry one subject.

### Normative boundary

State which sections are normative near the top. Background, evidence, alternatives, and
measurements are informative. Decision clauses use the requirement form defined by the shared style
guide. Do not hide an obligation in Background, Consequence, a note, or an example.

The draft names every part and section it amends. State the replacement rule rather than describing
an editing operation. The accepted revision records that decision, while the incorporated v0.2 part
becomes the authoritative current rule.

### Evidence and consequences

A revision retains the evidence on which its decision depends: what was measured, how, over what
population, with which relevant versions, and the result. Distinguish measurements from inferences.
Summarize a rejected alternative with the concrete reason it fails; do not build a case against an
unnamed opponent.

State compatibility effects, migration or rebuild work, implementation surfaces, and conformance
fixtures that must change. If a writer obligation depends on source data, identify the source field
or explicitly record that no source currently supplies it.

`What this does not change` is optional. A denial belongs there only when a specific statement in
the decision invites the inference being denied, the decision has not already answered it, and the
denial is consistent with every normative clause. Delete the section when it has no such content.
Delete an empty `Open` section rather than writing “None”.

### Citations

Place a citation beside the claim it supports. Cite the current part for a current rule and an
accepted revision for provenance or rationale not carried by the part. A draft may cite accepted
revisions, but an accepted revision never cites a proposal or draft. No proposal, draft, revision,
or part cites an instruction or contribution guide.

## A proposal and a draft carry no number

`revisions/proposals/` holds questions that have not yet become candidate normative text. A
proposal uses no BCP 14 keywords to prescribe behavior, does not claim consensus, and is never
cited from the specification or an accepted revision. When its problem, scope, and intended
direction are settled, write a draft from the draft template and delete the proposal in the same
change.

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
  remains a draft while the registry moves under it. R86 was drafted saying 32 of 34 tables were
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
- **Every citation resolves to the section that says it.**
  `uv run --project escapewheel-writer python revisions/check_citations.py` does this and
  `verify.py` runs it, so a broken `R<n> §<x>` or a part citation in a draft fails
  the build. It cannot check that the cited section *says* what the citing sentence claims, which
  is still a read: R89 §2.3 cited R56 §2.2 for the one-hop `resource.column` form, which R56 §2.3
  defines and §2.2 does not. Open the cited section.

  **A citation landing on a boilerplate section is the commonest form of this.** `R83 §3` was cited
  four times — twice in R105, once in R103, once in a draft — for a writer's ban on inferring a
  channel list and a consumer's duty to report one unresolvable. R83 §3 is `What this does not
  change`; the two rules are §2.2 and §2.3. The checker passed all four, because §3 exists. Neither
  a keyword comparison nor a heading blacklist is worth building: the first flags **77** citations
  across the accepted revisions, most of them sound, and the second flags six of which half are
  arguable. What catches it is reading the heading you are about to cite and asking whether that
  section, and not its neighbour, states the thing.
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
- **A writer obligation nothing can satisfy.** For every **MUST** or **SHOULD** that binds a writer,
  name the source field it reads, or record that no source states it. This is R66 §1.3's discipline
  turned on the obligation rather than on the column: a field a producer never fills is not
  evidence anyone needs it, and an obligation no source can meet is a clause that will be recorded
  as blocked rather than implemented. R102 §3 bound three and implementation found all three
  blocked — `waveform_mean` spans twelve sortings so no single run produced it, emitting a camera
  device needs `core.devices` in an adapter's `PRODUCES` and in every recipe, and no source links a
  video file to a camera except by its name, which R102 §3.2 itself forbids.
- **A claim whose population is defined by the quantity it measures.** "None of the 80 columns is
  more than 15% off the best encoding" was measured over columns reaching 2 kB *after* the rules
  had shrunk them, so every column a rule fixed had left the set that justified it — and three
  columns over the threshold went unseen. Three claims of the form "none more than X" failed this
  way in one session, each sound in its own terms and each measured with a filter that excluded
  part of what it claimed to cover. Ask what defines the population, and whether the change being
  measured moves anything in or out of it; where it does, state the population against the state
  *before* the change and say so.

- **A measurement stated twice.** Adding a section to one that already carries a number leaves the
  number in both. State it where the rule it supports lives.
- **"What this does not change" listing the unassumed.** Most denials belong in the **body**, where
  the clause they qualify is; this section is for the ones that fit nowhere else, which is why it
  is the commonest place a revision pads. A bullet earns its place by passing three tests, and it
  must pass all three.

  **Does the body already answer it?** R102's "no manifest field changes" was invited by its §2.1
  and already answered by the last sentence of its §3.1, so the bullet said a second time what the
  Decision had settled. A settled question belongs where it was settled; a composition note about
  another revision and an implementation note both belong in Consequence. A bullet running to a
  paragraph is usually one of those three.

  **Does anything invite it?** Name the sentence in the Motivation or the Decision that invites the
  inference, and say what a reader would conclude from it. Where nothing does, the bullet denies
  what nobody was going to think: R102's "no table is added and no column is removed" denied what
  its own `Amends` line and its Consequence had each already stated outright.

  **Is it true?** The first two tests ask whether a denial is wanted, never whether the document
  supports it. Read each bullet against the Decision's clauses and not only against the Motivation
  that invited it — R106 said "no core column changes" while its §3.1 laid down a rule binding
  every column in the registry, and the bullet was struck at acceptance. Such a bullet looks sound in isolation, so the
  check starts from the rule and asks which denials it falsifies, not from the bullet.

  Measured over the accepted revisions: **299 bullets across 75**, a mean of 4, and the recent ones
  run 7 to 9. Of R102's three, one survived.

## After the user accepts

**The sequence tests the revision as much as it applies it, and a step that fails is a result.**
Where one turns up something the document did not anticipate — an obligation no source can satisfy,
a count that moved under it, a clause that fits no section — stop and report it rather than
finishing around it. A correction that leaves the deliverable intact belongs in the document
mid-sequence, since step 1 already edits it and nothing is fixed until step 8 commits; a correction
that changes **what the revision delivers** is a different revision from the one that was accepted,
and goes back to the user with what was found.

R102 is the case to remember. All three of its writer obligations turned out blocked, and rewriting
its Consequence to record that took "the adapter names the run and the cameras land" to "the
registry change is the whole of what lands now" — the same rules, a different cost, and the user
had accepted the first.

Only the user moves a revision to Accepted. What follows is one sequence, in this order, and
`uv run --project escapewheel-writer python verify.py` from the monorepo root is what says it is
complete. `../CONTRIBUTING.md` §4 is the machinery each step
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
5. **The v0.2 parts the revision amends**, which is what `Amends` named. Placing a clause is two
   questions, and both have a stated answer.

   **Which part** is R93 §4's test, which settles it without appeal to judgement: a clause is
   Part 03's where it would change if the profile changed, Part 07's where it would change if the
   reference implementation changed, Part 10's where it is a number rather than a rule and neither of
   those claims it, and Part 02's where none of them does. An ordering rule changes under Iceberg, so
   it is Part 03's; a tick being `int64` is true under any profile, so it is Part 02's. Part 00 §9's table
   says what each part binds, and a clause about what a concept *means* rather than how it is
   computed is Part 01's.

   **Which section** is by subject, never by what is last. `headings.toml` is the map — every
   section number of every part with the subject it carries — so read that part's entry and put
   the clause in the section whose subject it is, as a new subsection at the end of *that* section
   where none of the existing ones fits. A subsection appended inside a section renumbers nothing.
   Where a clause genuinely fits no section, add a section at the **end of the part**, which
   renumbers nothing either, rather than filing it under a heading that does not describe it.

   A new concept is the exception, with a rule of its own: append it to Part 01 §3 as the next
   number, because that section is a flat list of concepts and inserting one renumbers the
   concepts every later part cites. That rule is about Part 01 §3 and no other section.

   Appending to whichever section comes last is what the subject rule prevents, and it had already
   happened three times before anyone stated it: R81, R83 and R89 each added to Part 02 §12, so a
   section then titled "Ordering" came to hold unit identity, channel indices and calibration,
   with 40 of its 44 lines about none of them. R93 §3.1 repaired it by sending ordering to Part 03,
   which is why that section is now "Rules for particular resources" and carries seven subsections
   a later clause can be placed among.
5a. **`uv run --project escapewheel-writer python revisions/impact.py`** once the parts are edited,
   before moving on. It maps each
   changed line to the section it falls in and lists every file citing that section, which is the
   only way to find them: `check_citations.py` asks whether a citation resolves, and a citation
   into a rewritten section resolves perfectly. It searches **every tracked file**, which is what
   makes this the step that keeps the developer documentation current: naming four `src`
   directories left 234 citations across 38 files unreachable — instruction files, root documents,
   and tests — and a sweep later found those documents describing a specification
   of R1–R36 over 33 tables. R110 rewrote Part 03 §5.5, which **16 files cite,
   three of them the writer's own source**, and one of those still named `R68 §3` — the
   miscitation R110's appraisal had just struck from the revision — for two more commits.
6. **`escapewheel_poc_docs_v0.2/applied.toml`**, one entry per clause. `ledger.py` demands a
   disposition for every §2 subsection and for any other section carrying a MUST or a SHOULD, and
   fails equally on an entry naming a clause that no longer exists. An `applied` entry's `where` is
   a list of `{ part = "02", section = "7.1" }` targets, each taking an optional `note` saying which
   piece of the clause landed there, and every one is resolved against that part's own headings, so
   a section that does not exist fails. A section that exists but does not cite the revision is a
   ratchet rather than a failure: cite the revision beside the clause as the parts do and the count
   falls; point at a section that says something else and it rises, which is refused.
6a. **`uv run --project escapewheel-writer python escapewheel_poc_docs_v0.2/headings.py`** where a
   heading changed. It prints every
   file citing that section and rewrites `headings.toml`; committing that file is the record the
   citations were read. Adding or renumbering a section needs the same run, which is what makes a
   rewritten heading visible at all -- `check_citations.py` resolves a number and cannot see that
   the section behind it is now about something else.
7. **`uv run --project escapewheel-writer python escapewheel_poc_docs_v0.2/combine.py`** for the
   single-file rendering.
8. **`uv run --project escapewheel-writer python verify.py`.** Every stage but the three clean-tree
   ones must pass before committing;
   those compare against the committed state and so clear only on the commit itself.

A part's column tables are **generated**: mark the resource with
`<!-- columns: core.foo -->` / `<!-- /columns -->` and run
`uv run --project escapewheel-writer python escapewheel_poc_docs_v0.2/columns.py`. Never retype a
column list. Part 06 §4's kept
`sorting_run_id` and `curation_id` for four revisions after R81 §2.3 removed them, and nothing
could see it: the ledger records where a clause landed, not whether the prose still agrees.

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
