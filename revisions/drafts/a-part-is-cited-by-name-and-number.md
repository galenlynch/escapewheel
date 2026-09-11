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

The specification is eleven parts, numbered 00 through 10, and a citation of one names it by that
number (Part 00 §10.1). Two spellings of that name are in use across the tracked documents and the
three distributions' source: **`Part 02 §5.2` at 32 sites and `` `02` §5.2 `` at 1,462**, with a
further 146 and 636 naming a part and no section at all.

Nothing says which to write. The parts themselves carry 20 of the first and 15 of the second, so
the document a reader meets with no context is where the two are most evenly split.

This part states which spelling a citation uses, in the section that already says which document a
citation names.

## 2. Background

Informative.

### 2.1 A backtick marks a value, and a part number is not one

A backtick in this repository's prose marks a literal the program can hold: a column, a value, a
path. `escapewheel-reader`'s `errors.py` reads "The packet declares no `t_zero_tick`, so seconds
are not defined (`01` §2.1)" — one sentence, two backticked tokens, and only one of them is
something a program has. A reader takes both for the same kind of thing and learns otherwise on
reaching the section sign.

The number alone also says nothing about what it numbers. Two digits in backticks leave a reader
who has not memorised the numbering to infer that a document is being named, where the word says
it in four characters.

### 2.2 Two revisions accepted on one day spelled it both ways

R111 wrote `Part 02 §5.2` in three parts and R112 wrote `` `02` §5.2 `` in two, both accepted on
2026-09-10. Neither form is giving way to the other: 8 of the 20 word-form citations in the parts
date from the v0.2 compilation and 3 from R111, while all 15 backtick citations arrived with R92,
R93, R99, R104, R106 and R112.

`check_citations.py` resolves both spellings, so neither was ever reported. A check that accepts
whatever it is given cannot report a preference nobody wrote down, which is how two spellings ran
to 1,494 citations without anyone choosing between them.

## 3. Decision

### 3.1 A citation names a part as Part 02

A citation of a part — in a part, in an implementation's source, in a packet's documentation, or in
a revision — **MUST** write the word `Part` before the number, as `Part 02 §5.2`, and **MUST NOT**
name the part by its number alone, with or without backticks.

Respelling the parts alone was the cheaper alternative and fixes the smaller half: 14 sites against
2,098, and it leaves the collision of §2.1 exactly where it happens, since **1,016 of the 1,462**
citations are in the three distributions' source, where the backticks in the same sentence mark a
column.

### 3.2 A tool refuses a part named by its number alone

A tool that checks citations **MUST** report a part named by its number alone, in a part, in a
revision, in a draft or in a tracked source file. Both spellings resolve to the same section, so no
other check can see which was written.

## 4. What this does not change

- **A section is still `§5.2`.** The section sign, the numbering and an unprefixed `§5.2` naming a
  section of the citing document are all unchanged.
- **Structured data names a part as data, not as a citation.** `applied.toml` records where a clause
  landed as `part = "02"`, and Part 00 §9's table lists the numbers in a column; neither is prose a
  reader follows.
- **No table, column, reference, rule or vocabulary changes, and no packet is rebuilt.**

## 5. Consequence

Part 00 §10 gains a subsection, and **2,098 references are respelled** — 1,462 naming a section and
636 naming a part alone — across the parts, the revisions, the drafts, the root documents and the
three distributions' source.

The sweep is mechanical and not blind. A backticked two-digit number is not always a part, since a
value may be written the same way, so each match is read before it is rewritten and
`check_citations.py` confirms that every citation the sweep produces still resolves.
