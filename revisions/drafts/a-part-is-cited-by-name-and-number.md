# A Part Is Cited by Name and Number

| | |
|---|---|
| **Status** | Draft |
| **Amends** | Part 00 §10 (adds a subsection on how a citation spells a part) |
| **Depends on** | R112 §3.1 (a requirement is cited from the part that states it), R93 §3.6 (Part 00 lists the parts and what each one binds) |
| **Profile** | all |

Normative, except §2, which is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

The specification is eleven parts, listed by number in Part 00 §9, and a citation of a requirement
names the part that states it (Part 00 §10.1). Neither section says how that name is written, so two
spellings are in use across the parts and the revisions: **`Part 02 §5.2` at 28 sites and
`` `02` §5.2 `` at 340**, with a further 105 and 374 naming a part and no section at all. Every
count here excludes this document, whose own specimens of the second spelling are quotations of
what §3.1 forbids rather than citations subject to it.

The parts themselves carry 20 of the first and 15 of the second, so the document a reader meets with
no context is where the two are most evenly split.

This revision states which spelling a citation uses, in the section that already says which document
a citation names.

## 2. Background

Informative.

### 2.1 A backtick marks a value, and a part number is not one

A backtick in this specification's prose marks a literal a program can hold: a column, a field, a
value. Part 00 §10.2 reads "a registry column's `since`, whose value names the revision that set it
(`02` §9.4)" — one sentence, two backticked tokens, and only the first is something a program has.
The section saying how a requirement is cited is itself where the two collide.

The number alone also says nothing about what it numbers. Two digits in backticks leave a reader who
has not memorised the numbering to infer that a document is being named, where the word says it in
four characters.

### 2.2 R111 and R112 spelled it both ways on one day

R111 wrote `Part 02 §5.2` in three parts and R112 wrote `` `02` §5.2 `` in two, both accepted on
2026-09-10. Neither form is giving way to the other: 8 of the 20 word-form citations in the parts
date from the v0.2 compilation and 3 from R111, while all 15 backtick citations arrived with R92,
R93, R99, R104, R106 and R112.

`check_citations.py` resolves both spellings, so neither was ever reported. A check that accepts
whatever it is given cannot report a preference nobody wrote down, which is how two spellings ran to
368 citations without anyone choosing between them.

## 3. Decision

### 3.1 A citation names a part as Part 02

A citation of a part, in a part or in a revision, **MUST** write the word `Part` before the number,
as `Part 02 §5.2`, and **MUST NOT** name the part by its number alone, with or without backticks.

An implementation's source is not bound, where Part 00 §10.1 binds it, and the asymmetry is the
point. Which document a citation names is a question of fact: naming a revision in a part's place
sends a reader to prose that does not bind them. A spelling is presentation, and a specification
states what an implementation must do with a packet rather than how it writes its comments — an
implementation in another language would inherit a convention it has no reason to keep. Binding it
would add **1,384 sites** and legislate the style of code this specification does not own.

### 3.2 A tool refuses a part named by its number alone

A tool that checks citations **MUST** report a part named by its number alone, in a part, in a
revision or in a draft, and **MUST NOT** report one elsewhere. Both spellings resolve to the same
section, so no other check can see which was written.

A two-digit number in backticks is not certainly a part, so the check **MUST** admit an exception
carrying the reason it is not one, and **MUST** report an exception that matches nothing — the
discipline `registry/check.py` applies to `NAMING_EXCEPTIONS`, so the list cannot go stale. It
starts empty: no backticked two-digit number outside the range 00 to 10 appears in a part or a
revision.

## 4. What this does not change

- **An unprefixed `§5.2` still names a section of the citing document.** §3.1 binds the spelling of
  a part's name, and a citation carrying no part name is not one.
- **Structured data names a part as data, not as a citation.** `applied.toml` records where a clause
  landed as `part = "02"`, and Part 00 §9's table lists the numbers in a column; neither is prose a
  reader follows.
- **No table, column, reference, rule or vocabulary changes, and no packet is rebuilt.**

## 5. Consequence

Part 00 §10 gains a subsection and **714 references are respelled** across the parts, the revisions
and the drafts: 340 naming a section and 374 naming a part alone.

Three shapes take more than inserting the word. **71** are possessive, where `` `02`'s `` becomes
`Part 02's`; **6** name a part and a stage rather than a section, as `` `05` Stage 5 ``; and **2**
are ranges, which take a plural.

Two tools change, neither of them by narrowing what it reads. `check_citations.py` resolves
citations in the source as well as in the documents, so it keeps accepting both spellings and
reports only where §3.1 binds. `repoint.py` prints the part a citation should move to, in the
spelling §3.1 forbids.
