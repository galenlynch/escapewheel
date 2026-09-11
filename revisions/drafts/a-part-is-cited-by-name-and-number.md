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
names the part that states it (Part 00 §10.1). Neither section says how that name is written, and
two spellings are in use across the tracked documents and source: **`Part 02 §5.2` at 32 sites and
`` `02` §5.2 `` at 1,462**, with a further 146 and 636 naming a part and no section at all. Every
count here excludes this document, whose own specimens of the second spelling are quotations of
what §3.1 forbids rather than citations subject to it.

The parts themselves carry 20 of the first and 15 of the second, so the document a reader meets
with no context is where the two are most evenly split.

This revision states which spelling a citation uses, in the section that already says which
document a citation names.

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

### 2.2 R111 and R112 spelled it both ways on one day

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

That list is wider than Part 00 §10.1's, which binds a revision's Decision and not the rest of it,
and wider deliberately: §10.1 restricts where a requirement **must** be cited from, where a
spelling has no reason to stop at one section of one kind of document.

Respelling the parts alone was the cheaper alternative and fixes the smaller half: the 16 sites in
the parts against 2,098, and it leaves the collision of §2.1 exactly where it happens, since **1,038 of the 1,462**
citations are in tracked Python — 778 of those in the three distributions — where the backticks in
the same sentence mark a column.

### 3.2 A tool refuses a part named by its number alone

A tool that checks citations **MUST** report a part named by its number alone, in a part, in a
revision, in a draft or in a tracked source file. Both spellings resolve to the same section, so no
other check can see which was written.

A two-digit number in backticks is not certainly a part, so the check **MUST** admit an exception
carrying the reason it is not one, and **MUST** report an exception that matches nothing — the
discipline `registry/check.py` applies to `NAMING_EXCEPTIONS`, so the list cannot go stale. It
starts empty: no backticked two-digit number outside the range 00 to 10 appears anywhere in the
repository, so nothing yet needs excusing.

## 4. What this does not change

- **An unprefixed `§5.2` still names a section of the citing document.** §3.1 binds the spelling of
  a part's name, and a citation carrying no part name is not one.
- **Structured data names a part as data, not as a citation.** `applied.toml` records where a clause
  landed as `part = "02"`, and Part 00 §9's table lists the numbers in a column; neither is prose a
  reader follows.
- **No table, column, reference, rule or vocabulary changes, and no packet is rebuilt.**

## 5. Consequence

Part 00 §10 gains a subsection and **2,098 references are respelled**, across the parts, the
revisions, the drafts, the root documents and the tracked source. **135 of them are
in generated artifacts** — 51 in `registry/logical_schemas.json` alone, with the rest in the
manifest schema and the copies the reader and validator carry — so those are respelled by editing
`registry/build.py` and regenerating, which `verify.py`'s clean-tree stage then confirms.

Four shapes need reading rather than substituting. **51** carry a JSON-escaped section sign
(`` `05` \u00a78 ``), which `check_citations.py`'s own pattern does not match and so has never
resolved; **34** name a part and a stage rather than a section (`` `05` Stage 5 ``); **4** are
ranges (`` `00` ``–`` `09` ``), which take a plural; and **4** are doubled for reStructuredText.

Three tools carry the spelling and all three change. `check_citations.py` and `impact.py` accept
either form, so each must stop accepting one, and `repoint.py` **emits** the old form when it names
the part a citation should move to.
