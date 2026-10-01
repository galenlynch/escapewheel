# The ledger resolves a superseded entry's successor and keeps no ratchet

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `0d35f40200b28fa0c0a746054c1620f93fd200f2` |
| **Decision domain** | process |
| **Change form** | ordinary |
| **Amends** | `revisions/CONTRIBUTING.md#ew-current-owner-ledger` |
| **Depends on** | R120 §3.7 (the ledger's dispositions and destination forms) |
| **Profile** | not applicable |
| **Decision clauses** | §3.1; §3.2; §3.3 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

The clause ledger, `revisions/applied.toml`, gives each Decision clause of each accepted revision a
disposition, and the ledger check, `revisions/ledger.py`, verifies it. The revision guide defines
the four dispositions at `revisions/CONTRIBUTING.md#ew-current-owner-ledger`.

Two of the checks are weaker than the guide's account of them. A `superseded` entry is defined as a
clause that a later accepted revision replaced, and nothing checks that the entry names that
revision. The check for a clause with no disposition is written as a ratchet whose mark is zero, so
its lowering branch cannot run, and the guide and three other texts still describe a mark that
lowers itself.

This revision defines the field in which a `superseded` entry names its successor and has the
ledger check resolve it, states how a clause replaced only in part is recorded, and removes the
ratchet. It is a process-domain decision and changes no packet requirement, numbered part, registry
declaration, schema or implementation behavior.

## 2. Background

The counts below come from reading the ledger as TOML at the baseline commit.

### 2.1 No tool reads a superseded entry's successor

The ledger holds 830 clauses: 501 applied, 177 rationale, 109 registry and 43 superseded. Of the 43
superseded entries, 42 carry a field `by`, and each of the 42 values names one accepted revision
numbered later than the clause's own. The guide names no field for the successor, and a search of
`revisions/`, `spec/tools/` and `tools/` finds no Python source that reads `by`. A missing or
misspelled successor passes the check.

### 2.2 One superseded entry has no successor

R107 §3.5 is recorded `superseded` with no `by`. Its `where` is the string
`02_core_logical_schemas.md §2`, a form the ledger check parses only for an `applied` entry.

The entry misdescribes the clause, which no later revision replaced. R107 §3.5 strikes one sentence
of R7 §2, that a table declaring a null primary key state the reason in its description, and adds a
rule of its own: a consumer does not read a null primary key as a declaration not yet made, because
null declares that the table admits duplicate rows. Part 02 §9.4 states that a null key admits
duplicate rows.

R7 §2, the clause that lost a sentence, is recorded `applied` at Part 02 §2 with no note. Two other
entries record a clause that a later revision replaced in part, and each is `applied` with a note
that names the later clause.

### 2.3 The ratchet cannot fire

The ledger records `undisposed = 0` under `[baseline]`. The ledger check fails where the count of
undisposed clauses exceeds the mark. Where the count is below the mark it rewrites the mark in the
ledger, reports that the ratchet was lowered, and exits successfully. No count is below zero, so
that branch is unreachable, and the check already fails on any undisposed clause.

Four texts still describe a ratchet:

- the guide's failure-handling rule, which forbids raising one;
- the root contribution guide, which says that the backlog may fall and must not rise, and that the
  high-water mark lowers itself;
- the ledger check's closing line, which reports the count as at the recorded high-water mark; and
- a comment on the verifier's ledger stage.

### 2.4 Alternatives

Checking only that `by` is present would catch the missing successor of §2.2 and pass a misspelled
or earlier revision.

Requiring `by` to name the superseding clause, and not only the revision, would give the most exact
record. It would need a clause chosen for each of the 42 entries, and a clause is often replaced by
several clauses of the later revision. An entry's note already carries that detail where someone
recorded it.

Admitting a list of revisions in `by` would describe a shape no entry has: all 42 values name one
revision.

## 3. Decision

The three clauses below state what a `superseded` entry carries, how a clause replaced in part is
recorded, and what the ledger check does with a clause that has no entry.

### 3.1 A superseded entry names the revision that replaced its clause

A `superseded` entry **MUST** carry `by`, a string naming one accepted revision as `R<N>`. That
revision **MUST** be numbered later than the revision of the entry's own clause. A `superseded`
entry **MUST NOT** carry `where`. Its `note` **MAY** name the replacing clause or a further
revision.

The ledger check **MUST** fail, naming the clause, where a `superseded` entry:

- carries no `by`;
- carries a `by` that is not one string of the form `R<N>`;
- names a revision that no accepted record states;
- names a revision numbered no later than the clause's own; or
- carries `where`.

### 3.2 A clause replaced in part keeps its disposition

`superseded` describes a clause that a later revision replaced whole. Whoever records an entry for
a clause that a later revision replaced only in part **MUST** give the entry the disposition of the
part that remains, and **MUST** name the later clause in the entry's `note`.

No tool checks this clause. It binds the person or agent recording the entry and no other actor.

### 3.3 The ledger keeps no ratchet

The ledger **MUST NOT** record a count of undisposed clauses. The ledger check **MUST** fail where
any Decision clause of an accepted revision has no entry, and it **MUST NOT** write the ledger or
any other file.

## 4. What this does not change

The four dispositions keep their meanings, and a `registry`, `rationale` or `applied` entry is
checked as before. The ledger check still claims no semantic fidelity: a resolved `by` shows that
the named revision exists and is later, and does not show that it replaced the clause.

## 5. Consequence

No packet, part, registry, schema or package changes, so no packet is rebuilt and no release
identity moves. The cost is confined to `revisions/`, one comment in the verifier and two sentences
of the root contribution guide.

Two ledger entries change so that the ledger satisfies §3.1 and §3.2. R107 §3.5 becomes `applied`
at the Part 02 anchor `ew-registry-conformance`, the section that states its rule about a null
key, and loses its string `where`. R7 §2 gains a note that R107 §3.5 struck its sentence about a
stated reason. The other 42 `superseded` entries already satisfy §3.1.

The guide's failure-handling rule is outside the amended anchor and loses only its mention of a
ledger ratchet. Its prohibition on weakening a check to make a candidate pass is unchanged and
covers the ledger check.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged: the decision is in the process domain and states no packet rule. | No numbered part differs from the baseline. |
| logical prose and registry | Unchanged: no part, registry declaration or rule is edited. | The registry checks pass unchanged. |
| physical profiles | Unchanged: no profile is edited. | The profile descriptors are byte-identical. |
| packet manifest and JSON Schemas | Unchanged: no schema is edited. | The schemas are byte-identical. |
| validation and import | Unchanged: no validator or build reads the ledger. | The conformance corpus passes unchanged. |
| extensions | Unchanged: no extension registry is edited. | The extension registry checks pass unchanged. |
| reader, writer, validator, adapters | Unchanged: no package reads the ledger. | The package suites pass unchanged. |
| conformance fixtures and tests | No packet fixture. The process tests gain the cases of §6. | The process tests pass. |
| revision process and tooling | The guide defines `by` and the record of a clause replaced in part beside the dispositions, and its failure-handling rule no longer mentions a ratchet. The ledger check resolves `by`, loses the branch that rewrites the ledger, and reports no high-water mark. The ledger loses `[baseline]` and its two entries change as above. The comment on the verifier's ledger stage is corrected. | `ledger.py` passes and leaves the ledger's bytes unchanged; the evidence manifest places §3.1 to §3.3 at the amended anchor. |
| generated publications and developer documentation | The root contribution guide's two sentences on the backlog and the high-water mark are restated. No generated publication changes. | A search of the tracked Markdown and Python for `ratchet` and `high-water` finds no description of the ledger. |

## 6. Conformance and implementation evidence

The decision is checked by process tests and by no packet fixture.

Positive cases:

- the ledger as incorporated passes, with its 42 `superseded` entries resolved; and
- the ledger file's bytes are the same before and after the check, on a passing run and on a failing
  one.

Negative cases, each failing and naming the clause:

- a `superseded` entry with no `by`;
- one whose `by` is a list or a string not of the form `R<N>`;
- one naming a revision that no accepted record states;
- one naming the clause's own revision, and one naming an earlier revision;
- one carrying `where`; and
- an accepted Decision clause with no entry.

§3.2 has no executable evidence. Its record is the pair of entries of §5 and the two entries of
§2.2 that already follow it.
