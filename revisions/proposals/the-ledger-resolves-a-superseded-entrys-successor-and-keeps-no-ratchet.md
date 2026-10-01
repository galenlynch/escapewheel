# The ledger resolves a superseded entry's successor and keeps no ratchet

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-10-01 |
| **Based on** | `14a5fb67265c1f8154529b39e8384b405f5a66da` |
| **Decision domain** | process |
| **Affects** | the revision guide's ledger dispositions at `revisions/CONTRIBUTING.md#ew-current-owner-ledger`; its failure-handling rule on a ledger ratchet; the root contribution guide's two sentences on the undisposed backlog and its high-water mark |

## 1. Problem

The clause ledger, `revisions/applied.toml`, gives each Decision clause of each accepted revision a
disposition, and `revisions/ledger.py` checks it. Two of the checks are weaker than the guide's
description of them.

A `superseded` entry is defined as a clause that a later accepted revision replaced. Its entry
names that revision in a field, `by`, that the guide does not define and no tool reads. A missing or
misspelled successor passes the check.

The check for a clause with no disposition is written as a ratchet: the ledger records a high-water
mark, and the tool rewrites the mark in the ledger when the count falls below it. The mark is zero,
so the rewriting branch cannot run, and four texts still describe a ratchet that lowers itself.

## 2. Evidence

Observed in the tracked files at the baseline commit. The counts come from reading the ledger as
TOML.

### 2.1 No tool reads a superseded entry's successor

The ledger holds 830 clauses: 501 applied, 177 rationale, 109 registry and 43 superseded. Of the 43
superseded entries, 42 carry `by`, each naming one accepted revision numbered later than the
clause's own. The guide lists `superseded` among the dispositions at
`revisions/CONTRIBUTING.md#ew-current-owner-ledger` and names no field for the successor. A search
of `revisions/`, `spec/tools/` and `tools/` finds no Python source that reads `by`.

### 2.2 One superseded entry has no successor

R107 §3.5 is recorded `superseded` with no `by`. Its `where` is the string
`02_core_logical_schemas.md §2`, a form the applied targets no longer use and the tool does not
parse for this disposition.

The entry describes the wrong clause. R107 §3.5 was not replaced by a later revision. It strikes one
sentence of R7 §2, that a table declaring a null primary key state the reason in its description,
and it adds a rule of its own: a consumer does not read a null primary key as a declaration not yet
made, because null declares that the table admits duplicate rows. Part 02 §9.4 states that a null
key admits duplicate rows.

R7 §2, the clause that lost a sentence, is recorded `applied` at Part 02 §2 with no note. Elsewhere
the ledger records a clause that a later revision superseded in part as `applied` with a note naming
the later clause; three entries carry such a note.

### 2.3 The ratchet cannot fire

The ledger records `undisposed = 0` under `[baseline]`. `ledger.py` fails where the count of
undisposed clauses exceeds the mark. Where the count is below the mark it rewrites the mark in
`applied.toml`, prints that the ratchet was lowered, and exits successfully. No count is below zero,
so that branch is unreachable, and the check already fails on any undisposed clause.

Four places still describe a ratchet:

- the guide's failure-handling rule, which forbids raising one;
- the root contribution guide, which says that the backlog may fall and must not rise, and that the
  high-water mark lowers itself;
- the tool's closing line, which reports the count as at the recorded high-water mark; and
- a comment on the verifier's ledger stage.

## 3. Desired outcome and constraints

A `superseded` entry is checked to name a real successor, and the tool that checks the ledger never
writes it. The resolution preserves:

- every accepted revision, unedited;
- the four dispositions and their meanings;
- one-way traceability, under which no current owner cites a revision back; and
- the rule that any undisposed clause fails.

## 4. Options and tradeoffs

| option | effect |
|---|---|
| keep the ledger as it is | a `superseded` entry can name nothing; the guide describes a ratchet that cannot run; the checker holds a branch that writes the file it checks |
| define `by` and check only that it is present | catches a missing successor; a misspelled or earlier revision still passes |
| define `by`, resolve it, and remove the ratchet (preferred direction) | a `superseded` entry names an accepted revision later than its own clause, and the check fails otherwise; the undisposed check is a plain one and the tool writes nothing |
| also require `by` to name the superseding clause, not only the revision | the most exact record; 42 entries would need a clause each, and a clause is often replaced by several clauses of the later revision |

Under the preferred direction the guide defines `by` as a required field of a `superseded` entry.
It names one or more accepted revisions, each numbered later than the clause's own, and the ledger
check fails where the field is absent, names no accepted revision, or names an earlier one. A
`superseded` entry carries no `where`.

A clause superseded in part keeps its disposition and gains a note naming the later clause, which is
the ledger's existing practice (§2.2). The guide says so beside the dispositions.

R107 §3.5's entry becomes `applied` at Part 02 §9.4, where its rule about a null key is stated, and
R7 §2's entry gains a note that R107 §3.5 superseded its sentence about a stated reason. Neither
change alters a disposition's meaning.

The ratchet is removed. The ledger loses `[baseline]`, the tool loses the branch that rewrites the
ledger, and the four places of §2.3 describe a check that fails on any undisposed clause.

The two changes are independent and are kept in one proposal because each is a few lines of the
same tool and the same section of the guide, and neither leaves the other in a worse state.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. The decision is in the process domain and states no packet rule. |
| logical prose, registry meta-schema, declarations and rules | Unchanged. No numbered part, registry or rule is edited. |
| physical profiles | Unchanged. |
| packet manifest and other JSON Schemas | Unchanged. |
| validation and import | Unchanged. No validator or build reads the ledger. |
| extension registries | Unchanged. |
| reader, writer, validator, adapters, code generation | Unchanged. No package reads the ledger. |
| existing packets | Unchanged. |
| conformance fixtures and implementation tests | No packet fixture. The process tests gain cases: a `superseded` entry with no `by`, one naming no accepted revision, and one naming an earlier revision each fail; an undisposed clause fails; the tool leaves the ledger's bytes unchanged on every path. |
| revision lifecycle, ledger, evidence and tooling | The guide defines `by`, states the note for a clause superseded in part, and drops the ratchet from its failure-handling rule. The ledger tool resolves `by` and loses the rewriting branch. The ledger loses `[baseline]`; the entries of R107 §3.5 and R7 §2 change as §4 says. The verifier's comment is corrected. |
| generated publications and developer documentation | The root contribution guide's two sentences are restated. No generated publication changes. |

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [x] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [x] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.
