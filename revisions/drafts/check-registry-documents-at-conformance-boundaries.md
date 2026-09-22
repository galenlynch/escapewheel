# Registry Documents Are Checked at Conformance Boundaries

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `94950e145cdba57a61bb4a5bfba515c52f207595` |
| **Decision domain** | specification |
| **Change form** | ordinary |
| **Amends** | Part 02 registry section; Part 05, by appending a conformance-boundary section; incorporated registry-result schema |
| **Depends on** | [R126 §§3.1–3.7](../accepted/R126-a-registry-document-has-one-complete-conformance-contract.md#3-decision) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6; §3.7 |

Section 3 is normative. Sections 1, 2, 4, 5, and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

This draft defines where the complete registry-document conformance contract is invoked, which
exact input a successful check authorizes downstream code to use, and how the result crosses
implementation boundaries. It applies to core and extension registry documents used by packet
producers, registry authoring and release tools, validators, and generators of registry-derived
checks.

The generated v0.2 specification already defines one ordered result with the states `valid`,
`invalid`, `unsupported`, and `incomplete`. It does not yet define the public boundaries that must
obtain that result. Consequently, current entry points can interpret a malformed or unsupported
registry as declarations, can lose duplicate JSON members before checking, or can report an
unsupported registry as a completed packet validation.

This draft does not make registry validation, or possession of a validation receipt, a
precondition for ordinary packet reading or analysis. It also does not decide missing-registry
policy, final composition of core and extension validity, validation of extension table bytes, or
the local behavior of a reader when a declaration required by one operation is unusable.

## 2. Background

### 2.1 Existing contract

[Part 02 §9.4](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-conformance)
defines the registry-document phases, state precedence, stable outcome identifiers, and the
distinction between byte and mapping entry points. R126 incorporated that contract but expressly
left invocation boundaries and serialization to a later decision.

A byte entry point can establish UTF-8 validity, JSON syntax, and unique object members. A mapping
entry point starts after the JSON phase and records why that phase was skipped. Later phases must
not index a shape-invalid document. An extension check also depends on its exact core context.
Those properties make a bare Boolean, a list of invalid findings, and an assertion such as
`validated=True` insufficient substitutes for the complete result.

### 2.2 Reproduced failures

The baseline is commit `436c8acc3bf032e0b8a039c78786380d04d8c97d`. Its 31-stage quick
verifier passed. The most recent complete-verifier evidence passed 221 reader, 168 validator, 553
writer, and 66 AIND tests.

Focused probes against that baseline produced these results:

| boundary | input | observed behavior |
|---|---|---|
| direct writer constructor | core mapping with a duplicated column declaration | constructed successfully |
| extension-author compatibility API | released extension with unknown `$schema` | complete state was `unsupported`; legacy check returned no failures |
| packet validator | supplied core mapping with unknown `$schema` | complete state was `unsupported`; packet report passed with no errors |
| packet validator | supplied mapping containing only recognized `$schema` | complete state was `invalid`; later code raised `KeyError: 'tables'` |

The reader independently opened the valid example packet. That is the intended separation:
ordinary use of declarations is not a conformance claim, while producing packet bytes or
registry-derived conformance checks requires a valid declaration contract.

### 2.3 Identity and cost

Three in-process measurements over the generated registries took a mean of 615.674 ms for the
core registry and 3,083.888 ms for all four repository extension registries. These measurements
are feasibility observations rather than performance requirements. They show why a complete check
belongs at a trust boundary and its result should be reused with the exact checked input instead
of recomputed on every property access.

A path, declared registry version, mutable object identity, or digest of an unspecified canonical
JSON form cannot prove that later code uses the checked document. A file can change at one path,
two documents can claim one version, and a mapping can be mutated. An extension result also
depends on the exact core context and the checker capabilities used for the evaluation.

An immutable in-process checked context closes this gap without defining a portable cache
protocol. For byte input it retains the exact bytes, the decoded document derived from them, the
complete result, and the evaluation context. For mapping input it retains an immutable structural
copy, its complete mapping-entry result, and the evaluation context. Downstream production and
conformance code receives the checked context rather than the mutable original.

### 2.4 Portable result feasibility

A closed Draft 2020-12 JSON Schema can express the abstract result without duplicating the phase
algorithms. A prototype accepted serializations of all four current result states and rejected an
extra root member and a skipped phase lacking its reason. Position-specific `prefixItems` can
require the seven phases in their normative order. State precedence, applicability, and outcome
ordering remain prose rules owned by Part 02.

## 3. Decision

### 3.1 The registry result has one portable representation

Part 02 MUST incorporate a closed JSON Schema with the identifier
`https://escapewheel.org/schemas/registry-result/0.1.0`. A serialized registry result MUST validate
against that schema and MUST contain:

- `$schema`, equal to the result-schema identifier;
- `descriptor_id`, containing the selected descriptor ID or null where contract selection did not
  succeed;
- `state`, containing exactly one of `valid`, `invalid`, `unsupported`, and `incomplete`; and
- `phases`, containing exactly the seven Part 02 phase records in their required order.

Each phase record MUST be closed and MUST contain `phase`, `state`, and `outcomes`. A skipped phase
MUST also contain a stable `reason`. A passed or skipped phase MUST have no outcomes, and an
invalid, unsupported, or incomplete phase MUST have at least one outcome.

Each outcome record MUST be closed and MUST contain `state`, `id`, and `instance`. It MAY contain
`owner`, `reason`, `schema_location`, and `detail`. A skipped outcome MUST contain a stable reason.
`instance` and `schema_location`, when present, MUST be RFC 6901 JSON Pointers.

The result schema owns structure only. Part 02 §9.4 continues to own phase algorithms, state
precedence, outcome applicability and order, reason and outcome semantics, and the conditions under
which `descriptor_id` is null. The optional `detail` member is informative diagnostic prose and
MUST NOT affect conformance or result comparison.

### 3.2 A checked registry context binds a result to its input

A **checked registry context** is an immutable in-process association of:

- the exact registry input evaluated at the boundary;
- the decoded registry document derived from that input;
- the complete Part 02 registry result;
- the local descriptor set and external-domain capabilities used for the evaluation; and
- for an extension, the exact checked core context supplied to its evaluation.

For byte input, the exact registry input MUST be the byte sequence given to the byte-oriented
entry point. For mapping input, it MUST be an immutable structural copy made before checking; its
result MUST retain Part 02's skipped JSON phase. Code authorized by a registry result to produce
packet bytes or registry-derived checks MUST use the decoded document in the same checked context,
not reread the source or use the caller's original mapping.

An implementation MAY reuse a checked registry context only while all five associated elements
remain identical. It MUST NOT treat a path, declared version, mutable object identity, or digest
under an unspecified canonicalization as proof of that identity. This specification does not
define a portable registry-result cache or a transferable validation receipt.

### 3.3 Producers and conformance tools check before interpretation

The following operations are registry-document conformance boundaries:

- publishing or releasing a registry document;
- starting a packet build, before checking a recipe, opening a source, or staging output;
- constructing a public writer directly from registry input;
- loading an embedded or caller-supplied registry for packet validation;
- checking a registry with extension-authoring tooling; and
- generating Tier 1, Tier 2, or other conformance checks from registry declarations.

Each boundary MUST obtain one complete Part 02 result before it interprets the registry for the
named operation. A byte-owning boundary MUST use the byte-oriented entry point. A boundary that is
given only an already-decoded mapping MUST use the mapping-oriented entry point and MUST NOT claim
byte-level JSON checks were performed.

A low-level generator that accepts a registry document directly MUST either establish the checked
registry context itself or require one from its caller. Merely receiving a mapping plus a result,
Boolean, or caller assertion does not establish the association required by §3.2.

### 3.4 Ordinary reader analysis is not a conformance boundary

A reader MUST NOT require a registry result, checked registry context, or validation receipt as a
precondition for:

- opening a packet or accessing its catalog and raw resources;
- presenting or correlating sessions;
- resolving discriminators, references, or session scope;
- providing extension-aware access; or
- analyzing one or more packets.

A reader MAY interpret the registry declarations needed for those operations without thereby
asserting that the registry or packet conforms. The reference reader MUST NOT depend on the
validator package merely to perform those operations. A separate explicit validation operation
MAY evaluate the same registry input.

This clause does not require a reader to produce a result from an unusable declaration. The local
failure or partial-access behavior when a particular operation needs such a declaration is outside
this decision, but it MUST NOT be replaced by a general validation-receipt prerequisite for normal
analysis.

### 3.5 Producers proceed only from valid checked contexts

A registry publisher, release tool, extension-authoring tool, packet writer, and registry-derived
check generator MUST proceed with the operation named in §3.3 only when the associated complete
result is `valid`. For any other state, it MUST stop that operation and expose the complete result
to its caller.

A writer MUST reject a non-valid registry before opening any source or staging any output. A public
writer constructor that accepts mappings MAY retain that convenient input form, but it MUST copy
and check those mappings before retaining or interpreting them. An adapter does not acquire
registry authority from this process and MUST NOT be opened after the writer has rejected a
registry.

An exception used to report rejection MUST make the complete portable result retrievable as
structured data. A command-line tool MUST offer machine-readable output containing that result and
MAY additionally render it for a person.

### 3.6 Validators preserve non-valid registry states

A packet validator MUST obtain one complete result for the core registry and for every available
extension registry. It MUST use the checked core context for every extension evaluation; where the
core result is not valid, it MUST still evaluate each available extension as far as Part 02 permits
and preserve the resulting incomplete, unsupported, or invalid state.

Only a `valid` checked registry context may direct generation or execution of packet checks derived
from that registry. For a non-valid result, the validator MUST:

- retain the complete registry result in its report;
- skip every packet check whose definition depends on that registry;
- preserve invalid outcomes as registry-document findings; and
- refrain from fabricating packet findings for unsupported, incomplete, or skipped work.

The validator MAY continue checks whose inputs and definitions are independent of the non-valid
registry. Missing or unreadable declared registry documents, validation of extension table bytes,
and the final composition of core, extension, and packet verdicts remain separate decisions. The
existing rule that an invalid, unsupported, or incomplete required evaluation cannot support a
conformance claim remains in force.

### 3.7 Reports and public boundaries preserve the complete result

A report MUST pair each registry result with an external subject label identifying the registry
role being evaluated, such as `core` or a manifest-declared extension identifier. The subject label
MUST NOT replace or manufacture the registry document's own identity; invalid JSON need not expose
one.

Public checking APIs, machine-readable command output, validation reports, and structured
exceptions MUST expose the same §3.1 result representation without reducing it to a Boolean or a
list of invalid findings. Human rendering MAY differ between implementations. Diagnostic wording
in `detail` is not interoperable identity and MUST NOT determine equality, ordering, or
conformance.

The new result schema begins at version 0.1.0. This decision MUST NOT change the registry
meta-schema, core registry, extension registry, packet catalog, or their version identities merely
because invocation and result-reporting behavior changed.

## 4. What this does not change

The registry-document algorithms and state meanings in Part 02 §9.4 do not change. Registry
documents, packets, physical profiles, and adapter declaration formats do not change. Existing
packet bytes need no regeneration.

The reader remains a registry-driven analysis implementation, not a validation gate. Session
scoping, discriminator resolution, reference lookup, and extension-aware access are ordinary
semantic operations even though they interpret registry declarations.

This decision preserves complete per-document results for later validity composition. It does not
settle whether an absent registry fails an extension, how extension results affect an overall
packet verdict, or which resource-level checks apply to extension table bytes.

## 5. Consequence

The change is behavior-incompatible for writer, authoring, validation, and generation entry points
that currently accept or reinterpret non-valid registries. There are no released consumers or
remote compatibility commitments. Convenient mapping inputs may remain, but their implementations
must copy and check before use.

Registry and packet bytes remain compatible. No registry or packet regeneration is required. The
result schema is a new incorporated artifact with its own version; existing registry document
versions do not advance.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | unchanged; registry checking does not alter the meaning of recorded scientific facts | semantic-part diff remains empty |
| logical prose and registry | append a registry-result subsection to Part 02 and incorporate the result schema; registry declarations remain byte-identical | schema vectors and source/vendor comparison |
| physical profiles | unchanged; no Parquet, Zarr, media, codec, or storage requirement changes | physical-part diff remains empty |
| packet catalog and JSON Schemas | unchanged; result reporting is not added to the packet catalog by this decision | catalog-schema diff remains empty |
| validation and import | append a conformance-boundary section to Part 05; check before interpretation and preserve all result states | focused boundary matrix and end-to-end validation tests |
| extensions | check every available extension against the exact checked core context; extension registry bytes remain unchanged | four extension positives and non-valid core-context cases |
| reader, writer, validator, adapters | reader remains independent; writer and validator consume checked contexts; rejected registries prevent adapter I/O | package tests, dependency test, and no-I/O-on-rejection test |
| conformance fixtures and tests | add byte/mapping entry, mutation isolation, context identity, four-state, skip-before-generation, and serialization cases | fixture matrix validated by both source and vendored schemas |
| revision process and tooling | unchanged; this is an ordinary specification revision | lifecycle and evidence checks |
| generated publications and developer documentation | regenerate Part 02, Part 05, and combined specification; explain explicit checking versus ordinary analysis | publication preservation and documentation review |

## 6. Conformance and implementation evidence

Incorporation must provide evidence for these positive cases:

- valid byte input produces a seven-phase result that validates against the incorporated result
  schema;
- valid mapping input records the skipped JSON phase and cannot be changed through later mutation
  of the caller's mapping;
- a writer uses one checked core context and opens sources only after that result is valid;
- each available extension is checked against the same exact checked core context;
- a validator generates registry-derived checks only from a valid context while continuing
  independent catalog or packet checks; and
- a reader without the validator package performs ordinary session, discriminator, reference,
  extension, and multi-packet operations without a result object.

It must also provide negative cases for invalid UTF-8, invalid JSON, duplicate members, invalid
shape, unknown schema, unknown contract, unusable core context, post-check mapping mutation,
non-valid writer construction, and attempts to generate checks from a non-valid registry. The
four result states and skipped-phase reasons must round-trip through API, report,
machine-readable-command, and exception representations. Schema fixtures must reject extra
members, phase reordering, a skipped record without a reason, an outcome with an invalid pointer,
and an inconsistent outcome count.

Implementation evidence must cover the repository registry checker, writer CLI and public
constructor, recipe preflight, Tier 1 and Tier 2 generators, packet validator and report model,
extension-author command, and reader dependency boundary. The quick verifier and complete
package suites must pass after the source schema is vendored and generated publications are
refreshed.
