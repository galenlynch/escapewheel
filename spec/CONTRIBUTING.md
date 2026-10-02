# Specification style guide

This guide is for people and tools editing the Escapewheel specification. It governs editorial
quality and document placement, not packet conformance.
[Part 00 §2](parts/00_architecture.md#ew-specification-authority) determines what binds; this guide
cannot create or override a requirement.

Its priorities follow established technical-writing practice: preserve technical meaning, make
the document clear and internally consistent, distinguish normative from informative content, and
write requirements that identify who must do what.

The following authorities provide the fuller guidance behind that summary:

- Gopen and Swan, [*The Science of Scientific Writing*](https://scholars.duke.edu/publication/881487),
  for sentence and paragraph information structure;
- the [RFC Style Guide](https://www.rfc-editor.org/rfc/rfc7322.html) for durable technical prose
  and references;
- [BCP 14](https://www.rfc-editor.org/info/bcp14) for normative keyword semantics; and
- the [W3C Manual of Style](https://www.w3.org/guide/manual-of-style/) for distinguishing normative
  and informative content.

The rules below are the Escapewheel-specific choices those authorities do not settle: where a
statement belongs, which actor it binds, which declaration owns it, and how this repository cites
and generates the result.

## 1. Write for implementation and conformance

The primary reader is implementing or reviewing conformance without access to the conversation
that produced the text. Introduce each term before relying on it, state the rule where the reader
will look for it, and provide enough information to determine whether an implementation complies.

Prefer direct, literal language. Put the established subject near the beginning of a sentence and
the new result near its end. Express the action in the verb, keep the grammatical subject close to
that verb, and use the same term for the same concept throughout. Editorial regularity never
justifies changing technical meaning.

The opening of a part or section must establish its subject and scope. Do not begin with a number,
pronoun, definite article, or internal name whose referent has not been introduced.

## 2. Put each statement at its abstraction layer

Part 00 defines the architecture: the abstraction levels, layer boundaries, conformance targets,
and ownership of the remaining parts. It should make the map explicit without duplicating rules
owned by a lower layer.

| subject | owning part |
|---|---|
| cross-cutting architecture, vocabulary levels, layers, actors, and document organization | Part 00 |
| storage-independent scientific meaning and concept identity | Part 01 |
| logical resources, schemas, references, and registry semantics | Part 02 |
| representation under a particular storage profile | Part 03 |
| packet manifest and resource resolution | Part 04 |
| validation, import, commit, and amendment procedure | Part 05 |
| derived analysis resources and materialization guidance | Part 06 |
| reference APIs and implementation plan | Part 07 |
| worked packet examples | Part 08 |
| metadata boundaries and extension behavior | Part 09 |
| measured performance evidence | Part 10 |
| portable Tier 2 query language, type binding, deterministic semantics, and evaluation outcomes | Part 11 |
| what a build and an adapter exchange under a particular storage profile | Part 12 |

Use two tests when placement is unclear:

1. If changing the physical profile would change the statement, it belongs at the physical level,
   Parts 03 and 12, rather than in the semantic or logical standard.
2. If changing the reference implementation without changing conformance would change the
   statement, it belongs in Part 07 or developer documentation rather than a normative part.

A rule belongs in one place. Higher-level parts may define the boundary and link to the owning
part, but they should not restate a lower-level identity, field, encoding, or procedure. Repetition
creates two independently editable claims.

## 3. Separate normative and informative content

State each part's normative status at the top. If only some sections are normative, identify them
there or mark the sections explicitly. Examples, notes, rationale, measurements, and implementation
sketches are informative and must not contain requirements needed for conformance.

Keep a requirement with the definition or behavior it governs. Put rationale immediately after it
as a clearly informative paragraph when the rationale prevents a likely misreading; otherwise keep
historical argument in the accepted revision.

## 4. Write requirements as observable obligations

Use `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT`, and `MAY` only in their BCP 14 sense and only in
uppercase. Lowercase forms retain their ordinary English meaning. Prefer this small vocabulary over
synonyms such as `SHALL`, `REQUIRED`, `RECOMMENDED`, and `OPTIONAL`.

Each behavioral requirement names an actor defined in Part 00 and puts that actor before the
keyword: “a validator MUST report …”. A conformance predicate instead names the part of
the artifact it constrains and states the constraint in an active verb: “a wall-clock column MUST
NOT use `INT96`”, not “`INT96` MUST NOT be used”. Avoid passive or actorless obligations such as “the two
MUST agree”; name who compares them and what happens when they differ.

A requirement should provide an observable outcome without prescribing an implementation method
that interoperability does not need. Use `MUST` only for conformance, interoperability, data
integrity, or prevention of a defined harmful ambiguity. A `SHOULD` clause states the reason an
implementation might depart from it, or makes that reason evident from adjacent text. A `MAY`
clause grants a permission that would otherwise be uncertain; do not use it merely to describe a
possibility.

Write conditions before the obligation when they limit the whole clause. Split a sentence when it
binds different actors, mixes a requirement with rationale, or makes independent obligations hard
to cite. After drafting, ask how a test, review, or caller could distinguish compliance from
noncompliance. A requirement may be behavioral rather than mechanically testable, but it must still
be determinate.

## 5. Keep terminology and declarations exact

Define a term once before normative use. A definition states meaning; requirements governing the
term belong in the appropriate rules section. Do not use a defined word loosely in a title or
heading, especially when the registry assigns it a narrower meaning.

Use code formatting for literal resource IDs, column names, field names, profile IDs, file names,
and command tokens. Use ordinary prose for concepts and actors. Expand an unfamiliar abbreviation
on first use.

The registry and schemas are declarations, not illustrations. Exact tables, columns, types,
presence, roles, references, and vocabularies belong in the machine-readable registry. Render
repeated column tables through the existing generator rather than maintaining a prose copy. Prose
explains meaning, constraints, and relationships that the declaration cannot express.

## 6. Make structure support lookup

Number sections hierarchically and follow the structural-editing procedure in
`revisions/CONTRIBUTING.md`. A section has one subject. Split it when its paragraphs
belong under different entries in an index or when a citation would have to point at unrelated
rules.

In specification parts, headings normally name a subject a reader can locate: “Column semantics”,
“External resources”, or “Source resolution”. An informative evidence section may instead state a
finding. Avoid headings framed as questions, headings that depend on the unseen paragraph for their
referent, and clever or metaphorical titles. Use a negative heading only when the prohibition itself
is the rule.

The first sentence of a paragraph should connect to established context and state that paragraph's
claim. Put supporting evidence after the claim. Lists use parallel grammar, and a lead-in must fit
every item syntactically.

Use a list when three or more peer requirements are independently checkable under one clear
lead-in. Use bullets when their order is immaterial, numbers when order or precedence matters, and
a table when each item repeats the same attributes. Put one independently testable requirement in
each item. A shared requirement keyword in the lead-in governs every item only when its actor,
force, and conditions are identical; otherwise repeat the actor and keyword. Keep interdependent
logic, qualifications, and argument in prose rather than fragmenting them merely because the
paragraph is long.

## 7. Use citations to identify the current rule

Cite a requirement by part name and section number, such as `Part 02 §9.1`. Cite the section that
actually states the rule, not a neighboring section or the revision that introduced it. Current
specification parts and incorporated machine-readable artifacts do not cite revision records;
accepted records and Git preserve that provenance and rationale.

The specification never cites proposals, drafts, agent instructions, or contribution guides.
Those documents may change or disappear and have no normative standing for packet conformance.

Place a citation next to the claim it supports. Do not collect citations in a provenance paragraph
whose reader must map them back to several claims. Cross-references use section numbers, never line
or page numbers.

Place an external normative reference in the reference section of the only numbered part that
invokes it directly. Keep one shared entry in Part 00 when several parts invoke the authority or
the framework itself does. The invoking prose identifies the entry and its extent; one scope
statement may cover a defined group of requirements. A part relying on another part's contract
cites that contract rather than treating its external authorities as new local dependencies.

## 8. Treat examples and measurements as evidence

Introduce what an example demonstrates, keep it minimal, and make it conform unless its purpose is
to show a failure. State expected results so a reader can tell whether the example supports the
text.

A measurement names the population, method, relevant versions, and unit. Distinguish observation
from inference. Do not turn a result from one dataset or implementation into a universal normative
claim without stating the general condition that makes the inference valid. Performance numbers
belong in Part 10 or the supporting conformance material unless a normative threshold requires
them.

## 9. Edit without creating a second source of truth

Change the smallest authoritative source that owns the fact. Do not repair a generated rendering,
a package's copy, registry output, or combined specification by hand. When a change touches several
parts, each part should contain only the portion at its abstraction layer, linked by citations
rather than duplicated prose.

Before publication, read the headings as an outline, then read the opening sentence and final clause
of each paragraph. Confirm that the outline exposes the subjects, the paragraph openings carry the
argument, and sentence endings emphasize rules or results rather than transitions or pronouns.

## 10. Editorial checklist

- The statement is in the part and section that own its abstraction layer.
- Normative and informative content are distinguishable.
- Every requirement names an actor or an inspectable artifact and has a determinate outcome.
- Terms, field names, and requirement keywords are used consistently.
- No hand-written prose duplicates a machine-readable declaration or generated table.
- Headings form a useful lookup outline, and each section has one subject.
- Citations resolve to the section that states the current rule.
- Examples and notes contain no hidden requirements.
- Measurements state their population, method, versions, and units.
- The edit preserves technical meaning and makes the text easier to read.
