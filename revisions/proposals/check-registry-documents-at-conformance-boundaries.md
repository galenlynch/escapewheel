# Check Registry Documents at Conformance Boundaries

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-22 |
| **Based on** | `436c8acc3bf032e0b8a039c78786380d04d8c97d` |
| **Decision domain** | specification |
| **Affects** | Part 02 §9.4; Part 05 §§3.5, 5, 9.4, 10, and 11; Part 09 §§5.3–5.6; registry-result artifacts; registry-loading APIs and tools |

## 1. Problem

[Part 02 §9.4](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-conformance)
defines one ordered, four-state result for checking a core or extension registry document. It also
deliberately leaves public invocation, reports, command output, and exception serialization to
another decision. The current implementation therefore has the complete checker without a common
rule for using it.

Different entry points presently give materially different answers for the same document:

- the repository registry checker consumes the complete result;
- direct `PacketWriter` construction indexes an unchecked mapping;
- the extension-author command reduces the complete result to invalid findings and thereby loses
  `unsupported` and `incomplete`;
- packet validation applies only the meta-schema to an embedded core registry, does not apply the
  complete contract to supplied registries, and generates data checks from non-valid documents;
- the writer and validator parse file inputs into ordinary mappings before the complete checker
  can detect duplicate JSON members; and
- several writer and validator paths reread mutable mappings or packet files, so a successful
  result does not identify the exact declarations later used for production or conformance checks.

This proposal does not make validation a prerequisite for reading or analysis. A reader normally
uses registry declarations for session scoping, discriminator resolution, extension-aware access,
and multi-packet analysis; those operations remain available without a conformance result or
receipt. Part 07's dependency discipline keeps the validation stack out of that path. The defect
addressed here occurs when a writer, validator, authoring tool, or check generator uses untrusted
declarations to produce a packet or make a conformance claim after no complete result, or after a
result other than `valid`.

## 2. Evidence

### 2.1 Baseline and current contract

The baseline is commit `436c8acc3bf032e0b8a039c78786380d04d8c97d`. The 31-stage quick
verifier passes at that commit. The latest complete verifier evidence passed 221 reader, 168
validator, 553 writer, and 66 AIND tests; the full command runs outside the restricted agent
sandbox because Arrow Flight needs a Unix-domain socket.

The registry contract incorporated by
[R126](../accepted/R126-a-registry-document-has-one-complete-conformance-contract.md) already
settles the document algorithm:

- exact bytes enter through the byte-oriented entry point, which detects invalid UTF-8, invalid
  JSON, and duplicate object members;
- an already-decoded mapping enters after the JSON phase and records that limitation;
- shape failure prevents later code from indexing the document;
- a core context that is not valid prevents core-dependent extension evaluation; and
- the complete result is exactly one of `valid`, `invalid`, `unsupported`, and `incomplete`, with
  all seven phase records retained.

The remaining question is which operations require that result and what they may do with each
state.

### 2.2 Reproduced boundary failures

The following observations were reproduced against the baseline with the public package entry
points and generated registry documents.

| boundary | input | observed result |
|---|---|---|
| direct writer constructor | generated core mapping with its first column declaration duplicated | `PacketWriter` constructed successfully |
| extension-author compatibility API | released extension with unknown `$schema` | complete result was `unsupported`; legacy author check returned zero failures |
| packet validator with supplied registry | generated core mapping with unknown `$schema`, over the generated valid packet | complete result was `unsupported`; packet report had zero errors, `passed == True`, and a `('core', 'complete')` evaluation |
| packet validator with malformed mapping | mapping containing only the recognized `$schema` | complete result was `invalid`; validator raised `KeyError: 'tables'` |

The raw reader independently opened the generated valid packet before the last validation call.
That is desirable: catalog and raw-resource access do not need to become registry-validation
operations merely because validation rejects a declaration.

These probes demonstrate four distinct losses of information: no invocation, reduction to
findings, reinterpretation of `unsupported` as complete, and unsafe interpretation after a shape
failure.

### 2.3 Current boundary inventory

| boundary | current input handling | current reaction | consequence |
|---|---|---|---|
| released core and repository extensions | `registry/check.py` loads mappings and calls the complete checker | fails unless the result is valid | correct state handling, but byte duplicates have already been erased by ordinary JSON decoding |
| writer import command | JSON is decoded before recipe and writer construction | later code indexes the mapping | duplicate members are lost and non-valid documents can direct normalization |
| direct `PacketWriter` construction | arbitrary mutable core and extension mappings | checks only a small namespace subset | public construction bypasses the complete contract |
| writer recipe check | raw mappings feed registry-dependent feasibility checks | assumes `tables` and column structure | malformed or unsupported declarations can fail inconsistently or direct source arbitration |
| packet validator, embedded core | reader returns a decoded mapping; validator applies the meta-schema alone | shape findings are recorded, then later layers still use the mapping | semantic defects are missed and shape defects can reach unsafe indexing |
| packet validator, supplied core | caller mapping replaces the embedded registry for data checks | no complete document check | an unsupported registry can produce a completed, passing report |
| packet validator, extensions | repeated reader calls omit absent or unparseable documents and return decoded mappings | extension data checks are generated directly | duplicate members and complete document state are lost; missing-document policy is conflated with parsing |
| extension-author command | files are decoded, then `check_extension` returns only invalid findings | zero findings is called sound | unsupported and incomplete are reported as success |
| Tier 1 generator | arbitrary mapping accepted by a public function | indexes `tables` immediately | callers can generate checks from a document whose contract was never selected |
| ordinary reader open and raw resource access | catalog plus resource locations | no registry conformance check | desirable independent read path |
| registry-semantic reader operations | packet registries are decoded and interpreted during scoping, discriminator resolution, reference lookup, and extension-aware analysis | no registry conformance check | desirable normal analysis path; using declarations is not itself a conformance claim |

The final row is deliberately outside the checking boundary. A separate validation operation can
verify the same document, but a reader does not need its result before using the packet as
intended. Later validity-composition work may define local failure and partial-access behavior for
unusable declarations; it cannot retroactively make a validation receipt a prerequisite for
ordinary analysis.

### 2.4 Reuse cost and identity

Three in-process measurements over the generated documents took a mean of 615.674 ms for the core
registry and 3,083.888 ms for all four repository extension registries. The extension path checks
the core again for every extension. These are development-machine measurements, not performance
requirements, but they show that validating on every registry property access would be needless
work.

A result cannot safely be cached by `registry_version`, path, or mutable mapping identity. Two
different documents can claim one version; a file can change at one path; and a mapping can be
mutated after checking. An extension result additionally depends on the exact valid core context
and on the local contract and external-domain capabilities used by its checker.

An immutable snapshot can close that gap. For a byte input it contains the exact bytes, the
decoded document derived from them, and the complete result. For a mapping input it contains an
immutable structural copy and the mapping-entry result, whose JSON phase explicitly remains
skipped. Downstream production and conformance-check code receives the snapshot rather than the
original input. This is an in-process proof of identity; it does not require a portable
canonical-JSON algorithm or a cross-process cache protocol.

### 2.5 Ownership, overlap, and dependencies

Part 02 §9.4 remains the owner of registry-document phases, states, outcomes, and result meaning.
The new rules belong primarily in Part 05 because they govern import, validation, conformance-check
generation, and reporting. Part 09 needs only extension-specific application: an extension is
checked with the same result as core and with the selected valid core snapshot as its context.
Part 07 may describe the reference snapshot and conformance-boundary API arrangement informatively
after the normative boundary is settled; the reader continues to interpret declarations without
that snapshot.

No other proposal or draft is open. R126 is the direct dependency and expressly defers this decision.
The reverse-impact query over Part 02 §9.4 and the affected Part 05 and Part 09 sections reports
113 citations. Current implementation citations concentrate in writer recipe checks, validator
reporting, extension validation, and reader registry loading. Accepted-revision citations are
historical and remain unchanged.

This proposal does not decide whether a missing declared registry makes an extension or packet
fail, how core and extension results compose into the final packet verdict, whether extension table
bytes match their declarations, or which reader operation fails when a declaration it specifically
needs is unusable. Those decisions consume this proposal's exact document results later. They do
not introduce a validation prerequisite for normal reader analysis.

### 2.6 Result-serialization feasibility

A closed Draft 2020-12 result schema can express the complete abstract shape without copying the
phase algorithms into JSON:

| object | required members | optional members and constraints |
|---|---|---|
| result | `$schema`, `descriptor_id`, `state`, `phases` | `descriptor_id` is a string or null; `state` is one of the four Part 02 states; `phases` has exactly seven position-specific entries |
| phase | `phase`, `state`, `outcomes` | a skipped phase also has `reason`; passed and skipped phases have no outcomes; a non-passing phase has at least one outcome |
| outcome | `state`, `id`, `instance` | `owner`, `reason`, `schema_location`, and informative `detail`; a skipped outcome has a reason; pointers have RFC 6901 syntax |

The proposed schema ID is
`https://escapewheel.org/schemas/registry-result/0.1.0`. A local prototype accepted serialization
of the current checker's valid, invalid, unsupported, and incomplete results, including the
mapping-entry skipped JSON phase. It rejected an added root member and a skipped phase without its
reason. State precedence, outcome ordering, applicability, and whether a descriptor ID should be
non-null remain prose algorithms rather than duplicate schema logic.

`detail` is intentionally optional and informative. Stable state, ID, owner, pointer, phase, and
reason fields are the interoperable result; diagnostic wording may differ between implementations
without changing conformance.

## 3. Desired outcome and constraints

A successful resolution would:

- apply the Part 02 result once before a writer, validator, authoring tool, or check generator uses
  a registry document to produce bytes or establish conformance;
- preserve exact bytes at file and embedded-packet boundaries so duplicate members remain
  observable;
- retain the documented mapping entry point for direct programmatic construction without claiming
  anything about unavailable source bytes;
- allow packet production and conformance-check generation only from a `valid` result and the same
  immutable document that produced it;
- preserve all four states and every phase record in APIs, reports, command output, and exceptions
  instead of translating them into findings or generic parse errors;
- stop dependent data-check generation after a non-valid registry result without fabricating a
  packet finding from `unsupported` or `incomplete`;
- keep ordinary packet opening, raw resource access, session scoping, discriminator resolution,
  extension-aware access, and multi-packet analysis independent of registry validation;
- check a valid core snapshot once and reuse it as the context for each extension snapshot;
- give independent implementations a closed machine-readable serialization of the abstract
  result; and
- preserve the existing registry document schema and declarations because the decision changes
  invocation, not the documents' accepted shape or meaning.

It must also preserve the distinction between using a declaration, validating that declaration,
and reporting a packet finding. A reader's interpretation is not a conformance claim. An invalid
outcome is a registry-document finding; `unsupported`, `incomplete`, and skipped work are not. The
later overall-verdict decision must receive those states intact.

## 4. Options and tradeoffs

### 4.1 Keep boundary-specific behavior

This has no migration cost, but public success continues to mean different things. It leaves the
constructor bypass, unsafe indexing, duplicate-member loss, and false completed validation in
place. It also makes the incorporated result largely advisory outside repository generation.

### 4.2 Recheck the original input at every use

This avoids introducing a snapshot type, but it does not protect a mutable mapping between a check
and the writer or validator work authorized by that check. Repeated extension checking reevaluates
the core, and each conformance caller can still choose a different input representation. The
measured cost is small at one boundary and unjustified at every generated check or validation
layer.

### 4.3 Check once and pass an immutable validated snapshot

This is the preferred design. The checking boundary owns input acquisition, creates an immutable
snapshot, and passes that snapshot to production and conformance-check code. Producers and
authoring tools continue only from `valid`. Validators attach every result to the report and
generate dependent checks only from valid snapshots. Exact byte entry points remain distinct from
mapping entry points. A snapshot is reusable only with its captured input, checker contract and
capabilities, and—where applicable—captured valid core context.

The snapshot is not a reader capability token. Reader operations neither request nor consume it.

The costs are deliberate API changes: public constructors reject inputs they accepted, low-level
check generation no longer interprets unchecked mappings as if those were conforming, and the
reference implementation needs one shared result/snapshot representation. A public constructor
may retain its convenient mapping parameter by copying and checking it internally; only downstream
production or check-generation code needs the snapshot. There are no released consumers or remote
compatibility commitments, so preserving acceptance of non-valid input has no value.

### 4.4 Trust callers to attest that a mapping was checked

A Boolean or convention such as `validated=True` is cheap, but it does not bind the assertion to a
document or context. The caller can mutate the object, pair a result with another registry, or
reuse an extension result with a different core. This recreates the problem at a less visible
boundary.

### 4.5 Serialize only implementation-specific classes

Python dataclasses are already sufficient inside the reference checker. They are not a portable
report contract and do not let fixtures validate that another implementation preserved every
phase and state. The preferred alternative is a small incorporated JSON Schema for the result,
while leaving human diagnostic wording informative. A report entry can pair a caller-supplied
subject such as `core` or a declared extension namespace with that result; subject identity is not
part of the registry document result because invalid JSON may contain no usable document identity.

## 5. Impact sketch

| surface | expected effect | evidence |
|---|---|---|
| semantic prose | unchanged; registry checking does not change the meaning of neuroscience facts | semantic-part diff remains empty |
| logical prose | Part 02 §9.4 incorporates the closed result serialization and clarifies snapshot identity without changing phase algorithms | schema vectors plus exact source/vendor comparison |
| registry meta-schema | unchanged; accepted registry-document shape remains 0.4.0 | generated schema bytes remain unchanged |
| registry declarations and rules | unchanged; all five generated/repository documents continue to produce `valid` | core and four-extension checks |
| physical profiles | unchanged; no Parquet, Zarr, media, codec, or storage rule changes | profile-part diff remains empty |
| packet catalog and incorporated packet schemas | unchanged; registry binding and overall report/catalog composition remain separate decisions | catalog schema diff remains empty |
| validation and import | affected; document checks precede recipe interpretation and packet check generation, dependent work consumes only valid snapshots, and exact results remain separately reportable | focused boundary matrix and end-to-end validation tests |
| extension registries | document bytes unchanged; each extension is checked once against the same valid core snapshot and author tooling succeeds only on `valid` | four extension positives plus invalid, unsupported, and incomplete cases |
| reader | ordinary open, raw resource access, session scoping, discriminator resolution, extension-aware access, and multi-packet analysis remain available without validation or a receipt; local behavior when a needed declaration is unusable remains deferred | current reader suite plus normal-analysis regressions without validator installation or a result object |
| writer | startup, recipe checking, CLI loading, and direct construction reject non-valid inputs before opening a source or staging output | constructor and no-I/O-on-rejection tests |
| validator | embedded documents use exact bytes; supplied mappings use the mapping entry point; non-valid documents cannot generate packet checks; report retains the complete result | malformed/unsupported regression probes and report-schema validation |
| adapters | unchanged; adapters receive no registry authority and a rejected registry stops the build before adapter I/O | adapter-not-opened test |
| code generation | affected only where a generator currently accepts unchecked mappings; generation consumes a valid snapshot or an explicitly internal validated document | focused generator tests |
| existing packets | bytes remain compatible; a packet whose registry was previously unchecked can now expose a non-valid result | current corpus plus boundary variants |
| migration and regeneration | no packet or registry regeneration; writer, validator, authoring, and generation boundaries may retain raw byte or mapping inputs and create snapshots internally; reader callers do not migrate | package API tests and migration note |
| conformance fixtures and tests | add byte/mapping entry, mutation isolation, core-context identity, every non-valid state, skip-before-generation, and exact serialization cases | registry-boundary fixture matrix |
| revision lifecycle, ledger, evidence, and process tooling | ordinary incorporation records only; process semantics do not change | lifecycle checks and evidence manifest |
| generated publications and developer documentation | Part 02/05/09 and combined spec regenerate; package guides distinguish ordinary registry-driven analysis from explicit registry conformance checking | generator preservation and documentation review |

## 6. Selected direction

### 6.1 Only valid registries direct production and conformance checks

A producer or authoring boundary rejects every state other than `valid` before it opens sources or
stages output. A validator records the exact state and skips every data check derived from a
non-valid document. It does not translate `unsupported` or `incomplete` into an invalid finding.
Independent packet or catalog checks whose inputs do not depend on that registry may continue, and
every available extension document still receives its own registry result even when core is not
valid.

Existing Part 05 language still prevents a validator from claiming completed core conformance
after a non-valid required core evaluation; final core/extension/packet verdict composition
remains separate.

This restriction does not apply to reader analysis. Accepting another state for production or
check generation would give declarations whose meaning or contract is unknown the power to define
new packet bytes or support a conformance claim.

### 6.2 An immutable snapshot binds result and input

The conformance boundary creates an immutable in-process snapshot containing the checked bytes or
structural copy, the decoded document, the complete result, and its checker context. An extension
snapshot also captures the exact valid core snapshot. This proposal does not define version
strings, paths, mutable object identity, or canonicalized JSON digests as portable cache keys.

This permits one check per trust boundary without inventing a second document-identity protocol
before packet registry binding is defined. It does not require callers of a public writer
constructor to manufacture the snapshot themselves; that constructor can copy and check its input
before storing the snapshot internally.

### 6.3 One incorporated schema serializes the result

The specification incorporates a closed `registry-result` JSON Schema with its own 0.1.0 identity.
It serializes the fields Part 02 §9.4 already defines. Optional human diagnostic detail remains
informative and cannot affect state. Reports pair the result with an external subject label; APIs,
machine-readable command output, and exceptions expose the same structure rather than partial
translations. A command may additionally render that structure for a person.

Keeping only Python classes would leave the data-driven contract incomplete at every non-Python
boundary.

### 6.4 Registry document versions do not advance

The meta-schema, core registry, and extension registry bytes and meanings do not change. The new
result schema receives its own initial identity, while package APIs make an intentional
development-time breaking change. Final release and package version identities remain separate
work.

A registry-version bump would falsely describe an invocation change as a declaration-format
change and force needless packet regeneration.

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
