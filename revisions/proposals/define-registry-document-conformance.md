# Define registry-document conformance

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-21 |
| **Based on** | `408e64651c5799783252648aa230647d0e640e45` |
| **Decision domain** | specification |
| **Affects** | Part 02 §§2–10; Part 09 §5.1, Part 09 §5.2, and Part 09 §6.1; the registry meta-schema, core registry, extension registries, registry-document checker, and registry conformance fixtures |

## 1. Problem

Part 02 says that it owns the rules a registry obeys and incorporates the generated core registry
for the exact declarations that registry carries. Part 09 says that an extension is a registry
document on the same terms as core. The current candidate nevertheless has no single, complete,
language-neutral definition of when either kind of registry document conforms.

Three partial definitions disagree:

1. `registry/registry.schema.json` establishes JSON shape and some local conditional constraints.
2. `escapewheel_validator.registry_document` implements 35 checks described as the invariants of
   any registry document.
3. `registry/check.py` adds 46 repository checks, including several logical invariants that an
   external extension author cannot invoke through the shared checker.

The shared checks also contain repository-only ordering conventions, omit rules Part 02 states,
and reject one form Part 02 expressly permits. Passing one layer therefore does not mean that a
document satisfies the contract, while failing another can mean only that it violates this
repository's house style.

This proposal covers the first half of roadmap P4: define registry-document classes, assign each
constraint to JSON Schema or a named semantic invariant, and provide portable evidence. A
dependent P4.2 proposal will decide where writers, validators, repository tooling, embedded packet
copies, and public entry points must invoke that contract and how they expose the result. Roadmap
P7's packet-verdict work will still decide missing registries, extension table-byte validation, partial
reader access, and the composition of core, extension, and packet validity.

## 2. Evidence

### 2.1 Baseline and current authority

The baseline is the R125 incorporation commit
`408e64651c5799783252648aa230647d0e640e45`. At that commit:

- `uv run --project escapewheel-writer python verify.py --quick` passes all 30 stages;
- the repository has no open proposal or draft other than this new proposal;
- the generated registry contains 43 core and analysis tables;
- four shipped extension registries contain 11 further tables; and
- the five registries contain 121 Tier 2 rules, all of whose IDs are presently unique and begin
  with the owning resource ID.

The unrelated untracked file
`revisions/drafts/define-a-portable-tier-2-rule-language.html` was present during the observations
below and was not read or modified.

Part 02 §1 currently says that Part 02 is the rules a registry obeys and that the incorporated core
registry is the schema. Part 02 §§2–10 state declaration, key, reference, role, identity,
discriminator, unit, clock, metadata, vocabulary, and rule constraints. Part 09 §5.1 says an
extension declares those things on exactly the same terms as core, while Part 09 §5.2 and Part 09 §6.1 add
extension namespace and reference-direction restrictions.

### 2.2 Schema-valid documents can violate stated registry semantics

A probe copied the current generated core registry, made one mutation at a time, ran it through
the published meta-schema, and then ran `registry_document.structural`. Both layers accepted each
of these mutations:

| accepted mutation | rule or identity it defeats |
|---|---|
| duplicate a column object under one table, preserving its `name` | a column name no longer identifies one declaration |
| duplicate a rule object and its `id` | a reported rule ID no longer identifies one rule |
| put `identity: assigned` on a non-identifier | Part 02 §8.2's role-dependent meaning |
| remove `resolves` from a discriminator | Part 02 §8.3's required resolution policy |
| remove the root `$schema` | Part 02 §9.2's self-description |
| put `extension_id` and `extends` on the core document | the core/extension document distinction |
| replace `logical_standard_version` with an arbitrary string | the document's claimed logical contract |
| replace one rule with `SELECT * FROM ghost.absent` | Part 11's static relation boundary |

Removing `identity` from an identifier was caught only when that particular column participated in
a reference, because the reference comparison happened to see `None` on one side. An unreferenced
identifier has no general check. Conversely, setting one table's `primary_key` to `null` passes the
meta-schema but fails the shared invariant named “every table declares a primary key,” although
Part 02 §2 expressly permits `primary_key: null` and defines it as admitting duplicate rows.

The meta-schema also treats `format` as an annotation in the way it is currently invoked. A
declared URI is not checked with a format assertion, and the shared check's `http://` or `https://`
prefix test is neither RFC 3986 validation nor the meta-schema's stated rule.

### 2.3 Core and extension document shape already disagree

The core registry carries:

```json
"semantic_standard_version": "escapewheel-semantic-v0.1",
"logical_standard_version": "escapewheel-logical-v0.1"
```

Every shipped extension instead carries both:

```json
"logical_standard_version": "0.1",
"extends": "escapewheel-logical-v0.1"
```

The meta-schema requires `logical_standard_version` but accepts either spelling and makes
`extends` optional. The shared extension checker ignores the first field and checks only the
second. A single document consequently makes two claims about the same logical-standard relation,
and the value in the field required of every registry does not equal the core registry's value.

The schema likewise permits a core document to carry extension fields and an extension-shaped
document to omit them. Context supplied by a caller, not the document contract, currently decides
what those fields mean.

### 2.4 The shared checker is neither complete nor limited to conformance

The shared checker includes these two rules even though root `CONTRIBUTING.md` explicitly says
column order is a convention of this generated registry and not a conformance requirement:

- `session_id` must be the first column; and
- a non-key `clock_id` must sit beside a coordinate.

It also applies “source labels are strings” to every column ending in `_label`, although Part 02
names three source-provenance labels, and requires one vocabulary and authority for every repeated
column name across a document even though no declaration states that equal local names create one
global field.

In the other direction, logical checks that remain only in `registry/check.py` include rule-ID
uniqueness and ownership, optional-column exclusion from Tier 2 rules, session-scope graph rules,
discriminator shape and path resolution, unit and clock source resolution, and most naming
semantics. An extension author invoking `check_extension` does not receive the same answer as the
repository's core and shipped-extension gate.

Some checks cannot safely run after a shape failure. Removing one column's `role` produces the
expected meta-schema finding and then raises `KeyError` from the semantic checker instead of
returning a complete validation result. The checker therefore has no defined phase boundary
between parse, shape, and semantic validation.

### 2.5 The defect reaches public behavior

The same duplicate-column mutations accepted by the two document-checking layers were accepted by
both direct public constructions below:

```text
PacketWriter(invalid_core, packet_id="probe")
PacketWriter(core, packet_id="probe", extensions=[invalid_extension])
```

No exception was raised. Separately, validation of the generated valid fixture with a supplied
core registry containing a duplicate rule ID returned `passed=True` and no `registry.*` finding.
Replacing the embedded extension view with a copy containing a duplicate rule ID likewise left
that extension passed and produced no registry finding.

Those invocation defects belong to the dependent P4.2 proposal. They are evidence here because a
uniform call path cannot be designed until this proposal supplies one coherent result to call.

### 2.6 JSON text has a pre-schema boundary

Registry table IDs are JSON object member names. Ordinary mapping construction makes them unique,
but a JSON text can repeat an object member and common parsers disagree about which value survives.
RFC 8259 explains that unique object names are the interoperable form. The current Python loaders
silently retain the last value, so neither JSON Schema nor post-parse semantic checks can observe a
duplicate table ID, extension field, or other object member. Registry conformance therefore needs
a raw-JSON parse boundary before mapping-level validation.

## 3. Desired outcome and constraints

A successful resolution should:

- define one registry-document conformance model for the core registry and extensions, with only
  explicitly identified context-specific rules;
- distinguish invalid JSON, meta-schema-invalid shape, unsupported declared contracts, incomplete
  evaluation, and failed semantic invariants without allowing a later phase to crash on an earlier
  failure;
- put every constraint expressible faithfully as document shape in the registry meta-schema and
  every cross-declaration, graph, or language constraint in a named semantic invariant;
- give semantic invariants stable, language-neutral IDs and declared applicability so reports,
  fixtures, and independent implementations refer to the same checks;
- retain prose ownership of meanings and algorithms, while using machine-readable data for exact
  IDs, applicability, and incorporated assignments;
- preserve `primary_key: null` as the deliberate declaration Part 02 already defines;
- make core and extension documents self-describing without two fields making the same
  logical-standard claim;
- validate each Tier 2 rule under the Part 11 profile selected by its document and derive its base
  resource dependencies from the checked query;
- separate conformance requirements from generator layout, editorial style, and repository
  maintenance checks;
- supply portable positive and negative fixtures for every named semantic invariant and for the
  phase boundaries; and
- permit development registries and packets to be regenerated rather than preserving accidental
  compatibility for the unreleased shapes.

This proposal must not define packet-to-registry identity or digest binding, resource requiredness,
overall packet verdict composition, extension table physical validation, final release membership,
or a direct declarative source for the generated core registry. Those remain P6, P7, P11, and P10
respectively.

## 4. Options and tradeoffs

### 4.1 Keep the current schema plus two Python check layers

This minimizes edits but preserves the demonstrated false accepts, false rejection, crashes, and
different answers for repository and external documents. The set of semantic rule identities and
applicability would remain an implementation detail. This does not satisfy the roadmap's
data-driven objective.

### 4.2 Reconcile the prose and meta-schema, but keep semantic rules as code constants

This can produce correct reference behavior with fewer artifacts. It still makes the list of
semantic invariants, their stable IDs, and their core/extension applicability discoverable only by
reading one implementation. Other implementations could reproduce the prose, but fixture coverage
and reports would have no machine-readable common index.

### 4.3 Use a layered contract with a small invariant descriptor — tentative preference

Under this option:

1. Part 02 owns field meaning and the language-neutral algorithm for each cross-document invariant.
2. An expressly incorporated registry meta-schema owns exact JSON shape and local conditional
   constraints.
3. A small expressly incorporated registry-contract descriptor owns the contract ID, supported
   meta-schema, semantic-standard, logical-standard, and rule-language IDs, and the exact stable
   ID, phase, applicability class, and owning specification anchors of every semantic invariant.
   It does not restate algorithms in JSON.
4. The incorporated core and extension registries own their exact declarations.
5. A non-normative conformance corpus supplies at least one positive and one focused negative case
   for every descriptor entry and phase outcome.

This is the same hybrid pattern selected for the Tier 2 language: prose defines semantics, a small
descriptor carries exact machine assignments, and vectors prove implementations agree. It adds one
artifact and its schema, but removes the more consequential hidden registry of checks now spread
between two Python modules.

The proposed artifacts are `registry/registry_contract.schema.json` and
`registry/registry_contracts/escapewheel-registry-contract-v0.1.json`, following the accepted
schema-plus-versioned-descriptor layout used for rule languages. Their initial identities would be
`https://escapewheel.org/schemas/registry-contract/0.1.0` and
`escapewheel-registry-contract-v0.1`. The descriptor's closed shape is equivalent to:

```json
{
  "$schema": "https://escapewheel.org/schemas/registry-contract/0.1.0",
  "id": "escapewheel-registry-contract-v0.1",
  "registry_schema": "https://escapewheel.org/schemas/registry/0.4.0",
  "semantic_standard": "escapewheel-semantic-v0.1",
  "logical_standard": "escapewheel-logical-v0.1",
  "rule_languages": ["escapewheel-rule-sql-v0.1"],
  "phases": [
    "json",
    "schema_selection",
    "shape",
    "contract_selection",
    "semantic",
    "rule_static",
    "external_domain"
  ],
  "invariants": [
    {
      "id": "registry.column.name_unique",
      "phase": "semantic",
      "applies_to": ["core", "extension"],
      "clauses": ["ew-registry-conformance"]
    }
  ]
}
```

The draft will replace the illustrative clause anchor with the exact globally unique stable
destination anchors
and enumerate every row in §4.3.1. Arrays are ordered and duplicate-free. The descriptor does not
contain messages, algorithms, exception lists, code selectors, or executable expressions. Part 02
and Part 09 remain the owners of what each entry means; the descriptor makes their applicability
and selection mechanically complete.

#### 4.3.1 Meta-schema and semantic-invariant boundary

The revised meta-schema should own constraints that depend only on one JSON value and its local
shape. That includes the closed root, table, column, reference, authority, and rule objects; required
fields; scalar types and enumerations; identifier syntax; unique members of a declared key or
reference side; and local conditionals such as these:

- an identifier requires `identity`, and another role forbids it;
- a discriminator is a string, requires `resolves`, and forbids `vocabulary`;
- another string column requires `vocabulary`, while a non-string column forbids vocabulary fields;
- `closed` and `enum` occur together, `reserved_values` occurs only with `open`, and an open
  vocabulary has a non-empty description;
- `unit` and `unit_from` are mutually exclusive, and `clock_from` occurs only on a coordinate;
- `json_string` is optional;
- the declaration-backed suffix relations selected in §4.8 hold; and
- an advisory rule is not an error.

The schema should use conditionals for these rules rather than repeat them in procedural code. A
schema finding is identified by the selected meta-schema ID plus its schema-location JSON Pointer;
the semantic descriptor therefore does not duplicate IDs for local shape rules.

Cross-member, cross-table, graph, and external-language rules belong to the semantic phase. The
initial descriptor should carry exactly the following entries. The IDs below are proposed contract
identities, not Python function names or messages:

| invariant ID | phase | applies to | owned meaning |
|---|---|---|---|
| `registry.namespace.owned` | semantic | core, extension | each table key is its resource/schema ID and uses a namespace its document class owns |
| `registry.namespace.reference_direction` | semantic | core, extension | core references core; an extension references core or itself, never another extension |
| `registry.column.name_unique` | semantic | core, extension | column names are unique within a table |
| `registry.primary_key.resolves` | semantic | core, extension | every non-null key member resolves once to a required column |
| `registry.reference.resolves` | semantic | core, extension | source and target resources and columns resolve, with equal nonzero arity |
| `registry.reference.target_key` | semantic | core, extension | the target columns are the complete non-null target primary key in declared order |
| `registry.reference.compatible` | semantic | core, extension | paired columns have compatible type, role, and identifier identity, including the declared shared-discriminator exception |
| `registry.session_scope.path` | semantic | core, extension | every and only session-scoped table carries the required assigned `session_id` through a value-preserving, non-nullable reference path to `core.sessions` |
| `registry.identity.name` | semantic | core, extension | a table owning an assigned identifier has one corresponding name; a carried or referenced identifier does not create one |
| `registry.metadata.eligibility` | semantic | core, extension | the key/reference ownership bands require or forbid the standard optional `metadata` declaration |
| `registry.determined_by.resolves` | semantic | core, extension | every named determinant is a column of the same table |
| `registry.discriminator.declaration` | semantic | core, extension | discriminator fields select exactly one declared resolution shape; named local columns exist and have the required presence, type, and role |
| `registry.discriminator.path` | semantic | core, extension | `discriminates_via` resolves through the declared one-hop reference in the stated direction |
| `registry.context_source.resolves` | semantic | core, extension | `unit_from` and `clock_from` resolve locally or through the declared one-hop reference, and a clock source resolves to `core.clocks` |
| `registry.unit.ucum_2_2_cs` | `external_domain` | core, extension | every literal `unit` parses as a case-sensitive UCUM 2.2 expression |
| `registry.authority.uri` | semantic | core, extension | each authority URI is an absolute RFC 3986 URI without dereferencing it |
| `registry.rule.id_unique` | semantic | core, extension | rule IDs are unique within the document |
| `registry.rule.id_owner` | semantic | core, extension | a rule ID begins with the resource ID whose rule array contains it |
| `registry.rule.required_inputs` | `rule_static` | core, extension | a rule names no optional column |
| `registry.core.device_detail` | semantic | core | core declares no device-detail table reserved to an extension |

Part 11's static check is then a separate ordered phase, not another partial registry checker. Its
own stable outcomes establish that each rule is syntactically and statically valid, names only
permitted base relations, and produces the required finding relation. The registry result attaches
those Part 11 outcomes to the owning rule ID.

The target-specific shared-key, paired-value, and by-position obligations in Part 02 §8.3 remain
packet-validation semantics. Which target a row names is not a registry-document fact, and a
declared resource is not defective merely because no discriminator of one shape can name it. The
registry checker establishes that the discriminator declaration is unambiguous and that a
validator can derive the candidate resolution information. When a row supplies a target, the
generated packet check applies Part 02's whole-key, single-key, or structural-index condition.
P4.1 neither turns those data-dependent checks into document invariants nor defers their existing
normative owner.

This inventory deliberately excludes repository release identities, the Part 02 table ledger,
authored-rule expansion and cleanup round trips, vendored-copy freshness, generated README text,
column order, and the other authoring checks named in §4.8. It also exposes two current prose gaps
that the draft must close: the object member key is the table's schema identifier, rather than a
missing field inside the table object, and the algorithms for the three discriminator shapes must
say exactly which declarations make a target nameable.

### 4.4 Validation phases and outcomes

The tentative preference is one ordered result rather than a bag of checks that callers compose
differently:

1. A byte-oriented entry point decodes UTF-8 JSON while rejecting duplicate object members. A
   mapping-oriented entry point begins after this phase and cannot make a claim about source JSON
   bytes it did not receive.
2. The checker reads only the root `$schema` selector. A missing or non-string selector is invalid;
   an unknown selector is unsupported. A known selector chooses a locally held meta-schema and its
   registry contract without dereferencing either identifier.
3. The selected meta-schema validates the complete shape. A shape-invalid document produces all
   deterministic schema findings and semantic phases do not index into it.
4. A shape-valid document's class and semantic-standard, logical-standard, and rule-language
   claims select the exact locally held contract recorded by the descriptor. An unknown contract
   is unsupported.
5. Named semantic invariants run in descriptor order for the document class and context. Core is
   its own table universe. An extension additionally requires an already conforming core registry
   with the logical-standard ID it declares. A missing or unusable required context makes that
   extension evaluation `incomplete`; it does not make the extension invalid.
6. Each Tier 2 rule is statically checked under the document's selected Part 11 language. A known
   language with a non-conforming rule makes the document invalid; an unknown language leaves the
   applicable evaluation unsupported.
7. Any externally defined lexical domain that the contract requires, presently UCUM, is checked
   offline. A checker lacking the required exact domain cannot establish registry conformance.

A complete result therefore reuses Part 11's four outcome classes: `valid`, `invalid`,
`unsupported`, and `incomplete`. It identifies the phase and uses stable schema, semantic, or
Part 11 IDs. A definitive violation makes the document invalid even if another independent phase
is unsupported or incomplete; otherwise any unsupported required contract makes the result
unsupported, any incomplete required evaluation makes it incomplete, and only completed passing
phases make it valid. A dependent phase is skipped after an earlier invalid shape, and the result
records why it did not run. P4.2 will decide how each caller reports or raises that result; P7 will
decide how packet-level claims compose it.

### 4.5 Document classes

Three credible shapes are available:

- add a new `registry_kind: core|extension` discriminator;
- infer the class from `extension_id`; or
- leave class entirely to caller context.

The tentative preference is to infer it from `extension_id` and make the meta-schema a closed
`oneOf`: a core registry forbids extension-only fields and requires its semantic and logical
standard IDs; an extension requires `extension_id`, carries the same full
`logical_standard_version` value as the core contract it targets, and omits redundant `extends`.
This avoids adding a second discriminator whose only purpose is to agree with `extension_id`.
Caller context may still require a particular class and expected extension ID without becoming the
definition of the document's class.

The core registry would presently permit only `core` and `analysis` table namespaces. An extension
would permit only its own namespace, which cannot be `core`, `analysis`, or `nwb`, and could refer
only to the core registry it targets or to itself. P5 may later change which resources the core
registry contains; it need not change this document-class mechanism.

The meta-schema requires the applicable ID fields and their identifier syntax but does not hard-code
the current release's values. The incorporated registry-contract descriptor assigns those exact
values. A core document is checked against all of them; an extension carries and is checked against
the full logical-standard and rule-language IDs, but does not independently restate the semantic
standard whose logical contract it extends.

### 4.6 Identifier, key, and reference rules

The tentative preference is to make the following registry facts explicit:

- raw JSON object member names are unique;
- table IDs are unique by their object representation and namespace rules;
- column names are unique within a table;
- rule IDs are unique within their registry document and begin with their owning resource ID; the
  resource prefix makes them distinct across core and extension documents whenever the resource
  namespaces are distinct;
- primary-key members are unique, resolve to required columns, and may be `null` only as the
  deliberate declaration that duplicate rows are admitted;
- every reference has unique source and target members, equal nonzero arity, and resolves at both
  ends;
- a reference targets the target table's complete non-null primary key, in declared key order,
  because the registry declares no other candidate key; a table declaring `primary_key: null`
  cannot be a reference target;
- referenced columns have compatible type and role, and compatible identity when identifiers are
  involved; and
- Tier 2 rule IDs and semantic-invariant IDs are report identities and remain stable within a
  registry version.

The complete-primary-key rule matches every one of the 128 currently shipped core and extension
references. Allowing a reference to arbitrary non-unique columns would make “foreign key” and
discriminator resolution ambiguous; adding declared alternate candidate keys later would be a
separate format extension.

### 4.7 Session references

Part 02 §7.1 currently requires every session-scoped table to declare a direct
`session_id -> core.sessions.session_id` reference. Four shipped extension tables instead carry
`session_id` inside a composite reference to another session-scoped table. The repository checker
deliberately accepts that weaker form and reports the discrepancy in a comment.

The tentative preference is to state the invariant in terms of an integrity-preserving reference
path: every session-scoped table carries required assigned `session_id`, and that same column is
carried through a declared reference path ending at `core.sessions.session_id`. A direct reference
is one valid path but is not required when a composite parent reference already proves the same
fact. This removes four redundant foreign keys while preserving the reason for the rule.

This is stricter than graph reachability. One reference is a **session-preserving edge** only when:

1. its source contains `session_id` exactly once and maps it to the target's `session_id` at the
   same reference position;
2. every source column of the reference is required, so the composite reference cannot evade its
   anti-join because another component is null;
3. the reference targets the target's complete non-null primary key under §4.6; and
4. the ordinary type, role, and identity compatibility checks hold.

A table proves session scope only through a chain of those edges terminating at
`core.sessions.session_id`; a cycle or an edge that relates only some other identifier proves
nothing. The registry checker can find that path without reading rows. Packet validation then runs
the ordinary foreign-key anti-join for every edge, rather than constructing a special recursive
row query. If all edge checks pass, equality and referential integrity compose: a child row has a
parent row with the same `session_id`, and that parent eventually has a `core.sessions` row with
that same value. A failure may be reported on the first parent edge that fails rather than repeated
on every descendant row; the packet still cannot pass.

All four current indirect cases have such a path. `dynamic_foraging.trials` also has a composite
reference through nullable `block_id`, which is not sufficient by itself, but its separate fully
required reference through `core.intervals` is sufficient.

### 4.8 Conformance versus authoring style

The current checks mix facts consumers depend on with presentation regularity. The tentative
preference is to keep only declaration-backed naming relations in registry conformance:

- lowercase resource and column syntax;
- an identifier is named `_id`, and a name ending `_id` declares an integer identifier;
- a coordinate is named `_tick`, and a name ending `_tick` declares a coordinate;
- a structural index is named `_index`, and a name ending `_index` declares either a structural
  index or a sequence position;
- a name ending `_name` is a string; and
- a name ending `_uri`, or the bare name `uri`, declares a string column; whether packet row values
  are valid URIs is not a registry-document check.

The discriminator algorithm should read its declared shape rather than infer it from `_kind`:
`coordinate_resource` is a by-position discriminator, while the two `interval_kind` data columns
copy a parent discriminator into a shared key. Those are not arbitrary exceptions and need no
free-form exception field. A new extension receives the same answer from its role and discriminator
fields.

Column order, adjacency, reserved-word and plural-name preferences, prose-restatement detection,
and same-spelled-column vocabulary uniformity should remain repository authoring checks rather
than registry conformance requirements. Part 02 should state that descriptions cannot override
declarations, while concise, non-duplicative prose remains specification style rather than an
English-equivalence test implemented with a regex.

This preserves a predictable public vocabulary without allowing array position, unrelated local
names, or a prose heuristic to become logical semantics.

### 4.9 External lexical domains

Part 02 says a literal `unit` is a UCUM code, but the shared checker currently accepts any printable
ASCII without spaces. That is not a UCUM parser. The tentative preference is to cite
[UCUM 2.2](https://ucum.org/ucum) locally in Part 02, require its case-sensitive form, and treat
inability to validate that external vocabulary as unsupported registry validation rather than as a
pass. UCUM publishes `ucum-essence.xml` for implementers and a case-sensitive unit artifact. As a
feasibility probe, the case-sensitive UCUM 2.2 grammar generated from that artifact accepted all 61
literal-unit declarations in the five shipped registries: 16 distinct expressions, including `%`,
`1`, compound units, and the two annotation units. A network service is therefore unnecessary.

The probe does not select a normative software dependency. The available Python parser bundles a
small generated Lark grammar but its distribution also depends on Pint for conversion, which
registry validation does not need. The draft should require offline behavior and conformance
vectors, while leaving an implementation free to use that parser, use only an equivalent syntax
parser, or generate its own parser from the official artifact. Exact UCUM release data and any
vendored copy remain subject to UCUM's license; acceptance evidence must record the implementation
and distribution choice.

URI-valued declarations are simpler: invoke the already shared RFC 3986 authority and make URI
syntax one named semantic invariant unless the revised JSON Schema dialect makes `format`
assertion mandatory. Prefix matching is not an alternative URI grammar.

### 4.10 Compatibility and versioning

The candidate has no external consumers or remote release to preserve. Keeping the old ambiguous
shape would cost more than regenerating development packets. If the preferred shape is selected,
the registry meta-schema needs a new `0.4.0` identity, the core registry advances to `0.4.0`, and
each extension registry advances its current minor version because its top-level contract changes.
No old registry is silently reinterpreted under the new schema ID.

This is an intentional exception to the roadmap's provisional registry-version hold: changing the
document class, required root fields, and meaning of conformance under an old identifier would make
two incompatible development documents claim one identity. P10 still assigns and verifies all
final release identifiers after the contract stabilizes. If this recommendation is approved, the
roadmap must say that the hold yields to an incompatible intermediate contract change rather than
implying that P4.1 violated its plan.

A follow-on P4.2 implementation revision can use the same contract without another registry or
meta-schema version change unless its feasibility work exposes a missing declaration.

## 5. Impact sketch

| surface | disposition | expected evidence |
|---|---|---|
| semantic prose | unchanged: no substrate-independent scientific concept changes | Part 01 remains byte-identical |
| logical prose | affected: Part 02 gains an explicit registry-conformance model and reconciles the rules identified above | owner diff, anchor/citation sweep, and invariant crosswalk |
| registry meta-schema | affected: distinguish document classes, require self-description, strengthen local conditionals, and acquire a new identity | schema self-validation and positive/negative shape cases |
| registry declarations and rules | affected at the document root; table declarations and rule predicates otherwise remain unchanged | exact generated diff, rule predicate comparison, and version checks |
| rule-language profile | unchanged: Part 11 remains the owner; registry conformance invokes its existing static check | all 121 rules retain profile and predicate behavior |
| physical profiles | unchanged: registry-document validity selects no storage encoding | Part 03 remains byte-identical |
| packet catalog and packet schemas | unchanged here: P6 owns registry binding, embedding, and digests | manifest and resource schemas remain byte-identical |
| validation and import | declaration semantics only; invocation points and result handling are deferred to P4.2 | proposal boundary check and no premature Part 05 behavior change |
| extension registries | affected by one coherent document class, namespace/reference invariants, full logical-standard ID, and version bumps | every shipped extension passes the same descriptor-indexed suite as core |
| reader | unchanged here; ordinary packet access and registry-dependent APIs are P4.2/P7 concerns | reader source remains unchanged except generated fixtures if required |
| writer and adapters | unchanged behavior here; P4.2 will validate public construction and startup | no constructor change in this revision |
| validator and code generation | affected only enough to expose one complete registry-document checker and generate or verify the new artifacts; boundary invocation is P4.2 | focused checker tests, no crash after shape failure, repository checker delegates to the same result |
| existing packets and migration | incompatible development registry shape; regenerate the 28-packet corpus and prototypes | corpus regeneration records new embedded documents without packet-data predicate changes |
| conformance fixtures and tests | affected: add raw-JSON, schema, semantic, unsupported, incomplete, core-context, and extension-context cases keyed by stable IDs | descriptor coverage check and independent runner over every case |
| revision lifecycle, ledger, evidence, and process tooling | no process semantics change; ordinary specification lifecycle and evidence records apply | stages, ledger, evidence, citation, and repoint checks |
| generated publications and developer documentation | affected: registry README, rendered tables/counts where applicable, combined specification, package documentation, and extension-author guidance | generation preserves candidate state and no documentation claims a partial checker is complete |
| final release publication | unchanged here; P11 later chooses exact bundle membership and digests | proposal explicitly does not publish a release |

## 6. Resolved direction

The proposal was approved for promotion on 2026-09-22 with all eight recommendations selected:

1. use the expressly incorporated registry-contract descriptor, its schema, identifiers, and
   narrow fields in §4.3;
2. infer document class from `extension_id`, remove redundant `extends`, and use one full
   `logical_standard_version` in both classes;
3. use §4.4's ordered phases and four outcomes, require a conforming core context for extension
   semantics, and apply invalid-over-unsupported-over-incomplete precedence when independent
   phases differ;
4. reject duplicate raw-JSON members, column names, and rule IDs; retain `primary_key: null`; and
   require references to target a complete ordered non-null primary key;
5. permit a session-scoped table to prove its session through §4.7's value-preserving,
   non-nullable reference path;
6. retain only §4.8's declaration-backed naming relations in conformance and treat order,
   adjacency, reserved/plural-name preferences, description-restatement heuristics, and same-name
   vocabulary coupling as authoring concerns;
7. validate exact case-sensitive UCUM 2.2 syntax offline and report a checker without that
   capability as unsupported; and
8. regenerate incompatibly with meta-schema and core registry `0.4.0`, increment each shipped
   extension's minor version once, and record the exception to P10's provisional version hold.

The P4.1/P4.2/P7 split in §1 is already reflected in the roadmap. No further split is recommended:
the document-class fields select the contract, the descriptor enumerates its semantic invariants,
and the outcome model says whether their evaluation establishes conformance. Accepting any one
without the others would introduce another knowingly partial registry contract. Invocation and
packet-verdict policy remain independently reviewable because they consume this result rather than
define it.

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
- [x] The proposal has explicit approval to advance to a revision draft.
