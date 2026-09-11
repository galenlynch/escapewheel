# R107 — A Declaration Is Not a Description

| | |
|---|---|
| **Status** | **Accepted** 2026-09-09 |
| **Amends** | R7 §2 (a keyless table states no reason), R48 §2.5 and R101 §3.5 (both fold into one rule), R101 §3.6 (`authority` gains a name), Part 02 §3 and Part 02 §9.3; 35 column descriptions; adds the declarations to `registry/tables.md` and one structural check |
| **Depends on** | R101 §3.1 (a string column declares its vocabulary), R101 §3.3 (a discriminator declares none), R101 §3.6 (`authority`), R55 §2.1 (a discriminator's value space is the declared resource IDs), R55 §2.2 (`resolves`), R53 §2.3.1 (an assigned identifier carries a name beside it), R29 §2 (`since` is a citation a reader follows), R3 §3.0 (duplication must buy otherwise-unavailable access) |
| **Profile** | all |

Normative, except §2, which is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

The registry states five things about a column's values in fields of their own: `vocabulary` and
`enum` since R101 §3.1, `reserved_values` since R11 §4, `authority` since R101 §3.6, and `resolves`
since R55 §2.2. A rule reads a field. A description is prose for a person, and it says these things
again — "Open (R8 §4)", "`resolves: optional`", `succeeded`, `failed` and `partial` typed out beside
the `enum` holding them.

R101 §3.6 already states the principle: "Where one nomenclature covers a whole column, the registry
says so **as a value rather than as prose**." This part applies it to every field a description
restates, renders the fields in the one document that omits them, and puts a check where the four
revisions that wrote the prose left none.

Measured on the registry as R106 left it: 43 core tables and 4 extension registries, 512 columns
between them.

## 2. Background

Informative.

### 2.1 Four of the five requirements on a description are declarations

Every requirement the specification makes of a column's `description`:

| requirement | source | what holds it instead |
|---|---|---|
| an `open` column carries a description stating the **form** its values take | R101 §3.5 | nothing — a form is prose |
| that description names the **nomenclature** where one fixes the spelling | R101 §3.5 | `authority` |
| a **closed** column's description does not imply the set is open | R101 §3.5 | `vocabulary` and `enum` |
| a column whose role is declared does not restate its **base** | R48 §2.5 | `role`, through Part 02 §8.1.1 |
| a table declaring `primary_key: null` states the **reason** in its description | R7 §2 | nothing — see §2.5 |

Only the first survives contact with a field. "Compared exactly, so two spellings are two
manufacturers" is a sentence and not a value, which is what R101 §3.5 asks a description for and
what this part leaves alone.

### 2.2 R101 states the principle and then breaks it

R101 §3.6's own words are that a nomenclature is a value rather than prose. R101 §3.5, one
subsection earlier, requires the description to name that same nomenclature — so a column carrying
`authority` must also say in prose what the field identifies, and `core.subjects.species` does:
"as NCBI Taxonomy spells it: `Mus musculus`, never `mouse`."

Half of that sentence is the form R101 §3.5 exists for and half restates the field beside it.
Nothing compared them, because `registry/check.py` carries exactly one invariant about a
description — that an `open` column has one at all.

### 2.3 Fifty restatements, six of them wrong

| field | descriptions restating it | what that looks like |
|---|---|---|
| `vocabulary` | **35** — 26 core, 9 extension | "Open." beside `vocabulary: open` |
| `authority` | **10** | "as NCBI Taxonomy spells it" beside the URI for it |
| `resolves` | **2** | "`resolves: optional`", the field quoted into prose |
| `reserved_values` | **2** | both `band` columns listing their reserved values |
| `enum` | **1** | `core.processing_runs.status` typing out its three values |

Fifty restatements over **45 distinct columns**, five of them restating two fields at once. Thirty-nine
agree with the field beside them. Six do not:

| column | declares | description says |
|---|---|---|
| `core.intervals.interval_kind` | discriminator, no vocabulary | "Open (R8 §4)" |
| `core.preferred_runs.scope_kind` | discriminator, no vocabulary | "Open." |
| `core.processing_runs.scope_kind` | discriminator, no vocabulary | "Open (R8 §4)" |
| `core.calibrations.detail_kind` | discriminator, no vocabulary | "Open, and `resolves: optional`" |
| `core.event_streams.detail_kind` | discriminator, no vocabulary | "Open, and `resolves: optional`" |
| `core.processing_runs.scope` | `vocabulary: free` | "Open, as `activity_type` is" |

The first five claim what R101 §3.3 forbids: a discriminator's values are the dotted resource IDs the
registry declares (R55 §2.1), not a vocabulary a writer extends, and calling them open invites a
reader to write one the registry does not declare. The sixth is a classification R101 §3.1 settled
the other way — a scope value is an identifier in another table's key space, meaningless without the
`scope_kind` beside it, which is `free`.

Each was written before the revision that settled what its column declares. R54 §2.1, R49 §2.1,
R89 §2.1 and R91 §3.1 each wrote "Open" of a discriminator when nothing said what a discriminator's
value space was; R55 §2.1 said it, R101 §3.3 made the declaration explicit, and neither swept the
prose.

The drift is behind rather than ahead. R100 §2.1 wrote the two `coordinate_resource` descriptions
after R55 and made no claim — "The table whose rows are this axis's positions, as a dotted resource
ID" — and R104 §3.1 described the eighth discriminator the same way unprompted. Three of the
registry's eight discriminators are already right, which is the form the other five take here.

### 2.4 `tables.md` renders no declaration

`registry/tables.md` is the generated document a person reads to learn what a column is, and its
columns are `Column`, `Type`, `Presence`, `Since` and `Description`. A vocabulary, a closed set, a
reserved value, an authority and a `resolves` appear in none of them.

That is what the prose buys, and the whole of it. `core.processing_runs.status` is the clearest
case: its three permitted values reach a reader of that document only because someone typed them
into a sentence beside the `enum` that holds them.

### 2.5 A table cannot carry a description

R7 §2 requires a table declaring `primary_key: null` to "state the reason in its description". A
table's registry entry declares `columns`, `primary_key`, `references`, `rules` and `since`, and R2
§9's meta-schema sets `additionalProperties: false` — so there is no field for the reason to go in
and the clause has been unsatisfiable since the meta-schema was published. No table declares
`primary_key: null`, which is why nothing reached it.

### 2.6 The same correction has been made once before

R56 §1 opens on this defect one field over: R48 gave a column a `role` and left which clock a tick
was on and what unit a value was in as prose, "and both are currently prose." Its independent
evidence was a live pipeline where every unit sat inside a `Field(description=...)` — centimeter,
second, percentage, milliliter, cm/s — "because there was nowhere else to put them."

R101 §3.1 and §3.6 gave the vocabulary and the nomenclature somewhere else to be put. What remains
is the sweep R56 performed and these did not.

## 3. Decision

### 3.1 A description says what no field says

A column's `description` **MUST NOT** restate what one of that column's own fields declares. What it
says is what no field can: the form the values take, how two of them compare, and why the column is
there — R101 §3.5's subject, unchanged.

`core.devices.manufacturer` shows the cut. "The manufacturer's own name for itself, as the source
states it. Open, and compared exactly, so two spellings are two manufacturers" becomes "The
manufacturer's own name for itself, as the source states it, compared exactly, so two spellings are
two manufacturers": the classification goes to the field holding it, and the consequence of
comparing exactly stays, being a fact no field states. A citation leaves with the claim it
supported — `(R8 §4)` cited openness, so it goes with the word.

The rule is about registry text. A **part** stating that a column's vocabulary is open is not the
same duplication: every place one does — Part 01 §3.8, §3.12, §3.17 twice, §3.23 and Part 02 §8.7 —
attaches a requirement that cannot be stated without it, such as a consumer's ban on reading an
unrecognised basis as `measured`, which is the otherwise-unavailable access R3 §3.0 asks for. Nor is
Part 02 §9.3's table of the three values a restatement: it defines what each obliges, as §8.1 does for
`role` and §6 for presence, and the registry has no field for the meaning of its own enum.

This replaces R101 §3.5's second and third sentences and R48 §2.5 entirely. Both were instances of
this rule written for one field each: a description that may not restate `vocabulary` cannot imply a
closed set is open, and one that may not restate `role` cannot restate a base.

### 3.2 A discriminator's description claims nothing about its values

A discriminator's `description` **MUST NOT** call its values open, closed or free at all. R55 §2.1
fixes them to the dotted resource IDs the registry declares, so none of the three words is true of
them, and `resolves` says what an unmatched one means (R55 §2.2). It states which table the value
names and stops, as R100 §2.1's two and R104 §3.1's one already do.

### 3.3 An authority declares a name and a URI

`authority` becomes an array of objects, each declaring a `name` and a `uri`, both required:

```json
"authority": [{"name": "MGI", "uri": "https://www.informatics.jax.org/"},
              {"name": "RGD", "uri": "https://rgd.mcw.edu/"}]
```

The URI stays what R101 §3.6 made it — identity, which a validator **MUST NOT** dereference
(R14 §2.3.2) and **MUST NOT** reject a value for being absent from. The name is what a person reads,
and it is a fact rather than a substring: neither `informatics.jax.org` nor `rgd.mcw.edu` contains
the name of the registry it serves, so no rule derives `MGI` or `RGD` from the URI, and the two
nomenclatures on `core.subjects.strain` are under unrelated hosts.

This is R53 §2.3.1's shape one level over. An assigned identifier is an integer a machine joins on
and carries a `*_name` beside it because a person cannot read the integer; an authority is a URI a
document resolves and carries a name for the same reason. Without it, R101 §3.5's requirement that
the description name the nomenclature is the only thing making an authority legible, and striking
that requirement while leaving `authority` a bare URI would lose the name from the registry
altogether.

### 3.4 `tables.md` renders the declarations

`registry/tables.md` **MUST** render every declaration a column carries: its vocabulary, the closed
set itself where the vocabulary is `closed`, its reserved values, its authorities by name, and a
discriminator's `resolves`. A discriminator renders no vocabulary, which is the declaration R101 §3.3
requires of it.

Generated from the field rather than typed beside it, so a reader of that document loses nothing the
prose gave them and the two cannot disagree again in core. `since` has worked this way since R29 §2,
and so has every count in the registry README.

### 3.5 A keyless table states no reason

R7 §2's requirement that a table declaring `primary_key: null` state the reason in its description
is **struck**. `primary_key: null` is the declaration and `since` names the revision that set it
(R29 §2), which is where every other reason in this specification lives.

A consumer **MUST NOT** read `primary_key: null` as a declaration not yet made. It is the
declaration that the table admits duplicate rows, and R7 §2 already forbids omitting the field, so
a key nobody decided is absent and a key decided against is null. That distinction is what the
struck reason was defending, and it survives without it.

A table-level `description` is not added. It would recreate at table level exactly what §3.1 is
correcting at column level — prose beside a declaration, with nothing comparing them — and R7 §2's
own purpose is served without it: a key that was forgotten declares nothing, where a table admitting
duplicates declares `null` deliberately and cites the revision that decided so.

### 3.6 The check

`registry/check.py` refuses a description that restates a declared field, taking its structural
invariants from 29 to **30**. It reaches four of the five fields exactly: a vocabulary claim is
written `Open`, `Closed` or `Free` capitalised, a `resolves` claim quotes the field's own spelling,
and an `enum` or `reserved_values` claim repeats a declared value in backticks.

An `authority` claim it cannot see, because a name in prose is a name in prose and §3.3 puts the same
string in the field. That half binds the writer and no check, which is R67 §2.4's shape, and §3.3 is
what makes complying cheap: the name is declared once and rendered, so a description repeating it
adds nothing a reader lacks.

Capitalisation is what makes the vocabulary half exact rather than approximate. Four descriptions use
one of the three words in its ordinary sense and lowercase — `left_valve_open_time` and its
right-hand twin read "Calibrated open time", `core.unit_quality_labels.normalized_label` reads "onto
the closed set", and `vr_foraging.sites.last_stop_tick` reads "the name is free" — so none is caught
and no exception need be declared for any of them.

The check is what carries this past core. An extension is a registry document a hand writes and
`build.py` never generates (R17 §2), and **9 of the 35** vocabulary claims are in one, so §3.4's
rendering cannot reach them and only a check can.

## 4. What this does not change

- **No packet is rebuilt.** R101 and each of R103 through R106 required both packaged packets
  rebuilt, so a registry change reads as forcing one. This does not: `authority` is read by no rule
  and appears in no packet's rows, and a description never did.

## 5. Consequence

35 column descriptions change — 26 in core and 9 across three extensions — `authority` becomes an
array of objects on 12 columns naming 5
nomenclatures — NCBI Taxonomy, MGI, RGD, HL7 FHIR administrative gender and UCUM, the last on 8
columns — `registry/tables.md` gains the declarations it never rendered, and `registry/check.py`
gains the invariant §3.6 states. `registry.schema.json` changes with `authority`'s shape. No column,
table, reference, rule or vocabulary moves.

Part 02 §3's declaration table gains `description` and `authority`, listing neither today while R101
§3.5 makes a description required for an open column and `check.py` enforces exactly that — so the
part saying what a column declares omitted two things it does.

Every one of the 35 takes a `since` naming this revision, as R101 §3.5's 25 did: R29 §2 makes
`since` the revision that last changed the column, and the prose is part of what a column is.

The other ten of §2.3's forty-five keep their prose, and that is §3.1's exception doing the work it
was written for: "as a UCUM code" and "as NCBI Taxonomy spells it" are what makes the form legible,
so §3.1's exception is satisfied where it stands and only the field's shape changes under those
ten. Six of the 35 are the disagreements §2.3 lists; the other 29 agreed with their field and
still lose the prose, because agreement today is not the property being bought.

Three clauses are struck rather than relocated — R7 §2's reason, and R101 §3.5's nomenclature and
closed-set sentences — and R48 §2.5 folds into §3.1. Four requirements on a description become one.
