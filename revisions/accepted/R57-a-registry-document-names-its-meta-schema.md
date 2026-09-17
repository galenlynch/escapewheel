# R57 — A Registry Document Names Its Meta-Schema

| | |
|---|---|
| **Status** | **Accepted** 2026-09-03 |
| **Amends** | R2 §2 (the registry document's top level), R2 §9 (the published meta-schema) |
| **Depends on** | R2 (registry format), R17 (extension registries) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

A registry document does not say what it is.

`registry/logical_schemas.json` and `registry/extensions/vr_foraging.json` are the same format —
R17 §2 says so explicitly, "an extension is a registry document in R2's format" — and nothing
inside either one records that. A packet embeds both: the core registry at
`schemas/logical_schemas.json`, and every extension document it declares. A consumer handed one of
those files has no way to learn from the file which schema validates it.

The top level carries three version strings and none of them answers the question:

```
registry_version           "0.1.0"                     the content's version
logical_standard_version   "escapewheel-logical-v0.1"     what the content describes
semantic_standard_version  "escapewheel-semantic-v0.1"    the concepts above that
```

`registry_version` versions the tables and rules. It does not name the format they are written in,
so two documents at `0.1.0` under different meta-schemas are indistinguishable, and a document at
`0.1.0` under *no* meta-schema — a hand-written draft, a file from a project that copied the shape
— is indistinguishable from a conforming one.

### 1.1 This is a shape the specification has already fixed twice

R49: `scope` held an identifier whose table the packet never stated, so resolution was a guess and
a validator could not check the referent. R15: codecs became a per-resource declaration so a reader
could check a resource before opening it, rather than inferring from a packet-level union.

Both are the same defect — a value whose interpretation is known to the writer, needed by the
reader, and recorded nowhere — and this is the third instance, one level up: the document's own
format. R2 §9 publishes a meta-schema and gives it an `$id`
(`https://escapewheel.org/schemas/registry/0.1.0`); no document points at it.

### 1.2 What it costs today

Four extension documents were authored by hand for this project. Nothing checked them until
`registry/check.py` was extended to reach `registry/extensions/`, and the reason nothing checked
them was that nothing tied a document to the schema that governs it — the check had to be told
where to look, by path. A third party writing an extension has no `check.py`, and their editor
cannot help them, because the file does not say what it is.

## 2. The rule

### 2.1 The key

A registry document — core's or an extension's — **MAY** carry a top-level `$schema` whose value is
the `$id` of the meta-schema it conforms to. R2 §2's closed top level is amended to permit it; every
other key is unchanged.

```json
{
  "$schema": "https://escapewheel.org/schemas/registry/0.1.0",
  "registry_version": "0.1.0",
  "extension_id": "vr_foraging",
  ...
}
```

A writer producing a registry document **SHOULD** emit it, and **SHOULD** emit it first, so the
declaration is visible without reading the file.

### 2.2 What a consumer does with it

Where `$schema` is present it **MUST** equal the `$id` of a meta-schema the consumer holds, or the
document **MUST** be reported as governed by a schema this consumer does not have. That is an
`info` finding, not an error: R17 §4 already says a core validator is not required to hold an
extension's schema, and the same logic applies one level up.

A validator **MUST NOT** require `$schema`. A document without one is conforming, and is validated
exactly as today — against whatever meta-schema the consumer was going to use anyway. The key adds
a statement that can be checked; it does not add a requirement.

A validator **MUST NOT** dereference it. R14 §2.2 forbids structural validation from reaching the
network, and nothing here changes that: **`$schema` is identity, not a fetch instruction.** Whether
some other tool can resolve the URI to a document is that tool's local concern, and §4 below is
honest that today nothing serves it.

### 2.3 Why this key and not a new name

`$schema` is the established convention for a JSON *instance* naming the schema that governs it,
and editors implement it already — which is the whole practical return. A new key
(`meta_schema`, `conforms_to`) would carry the same information and be understood by nothing.

It does not collide with JSON Schema's own use of `$schema`. There, the key declares a **dialect**,
and it appears in a schema. A registry document is an instance, not a schema, so the two uses never
occupy the same file.

## 3. What this does not change

No table, no column, no rule, no closed vocabulary, no stored value. As in R45, this is a statement
made explicit rather than a change to what is stated.

**`registry_version` does not bump.** That reading was tried and is wrong. `build.py`'s own comment
sets the policy — the bump "happens when it is forced rather than on a schedule" — and what forces
it is `PacketWriter._install_registry` refusing an *amendment* that would leave two different
documents at one version inside one packet. Adding a key changes the document's bytes, which is
exactly what R48, R53 and R56 each did to far greater extent by adding, retyping and annotating
columns, none of which bumped it. A greenfield packet is regenerated rather than amended, so no
packet ends up holding two. Adding an optional key is strictly the smaller change; treating it as
forced when three column revisions were not would be a rule applied to this change and no other.

Where a packet *is* amended across the change, the existing machinery already handles it: the
writer refuses, and its message names the fix.

## 4. What this does not deliver

`https://escapewheel.org/schemas/registry/0.1.0` is an identity, and nothing serves it. An editor that
fetches `$schema` over the network will get nothing and offer no validation, so the ergonomic
return is **not** automatic — it requires a local mapping from that URI to
`registry/registry.schema.json`, which is per-editor configuration this revision does not
standardise and the format has no opinion about.

What the revision does deliver without any of that is a checkable statement. `registry/check.py`
verifies offline that every document's `$schema`, where present, is the `$id` of the meta-schema in
this repository — so a document copied from an older format, or drafted against a different one,
is caught by the run that is already required after touching the registry.

Stating this plainly is the point: the key's value is identity now and tooling later, not tooling
now.

## 5. Amendments

**R2 §2** — the registry document's top level gains an optional `$schema`. The meta-schema's
`additionalProperties: false` is retained; `$schema` is added to `properties` as a string, and its
exact value is checked by `registry/check.py` rather than by a `const` in the meta-schema, because
pinning the `$id` in the schema would make every document invalid the moment the meta-schema is
versioned — a coupling R2 §9 deliberately does not have.

**R2 §9** — the published meta-schema is the referent of `$schema`. Its `$id` was already stated;
this makes it load-bearing.

## 6. Implementation

| | |
|---|---|
| `registry/registry.schema.json` | `$schema` permitted at the top level |
| `registry/build.py` | emits `$schema` first in `logical_schemas.json` |
| `registry/extensions/*.json` | each gains `$schema` |
| `registry/check.py` | every document carries one, and it names this meta-schema |
| `escapewheel_writer.scaffold` | a draft carries it, as it carries the other top-level keys |

A packet's embedded registry gains the key when it is next built, which for every packet in the
conformance corpus is on the next run of `fixtures/build.py`. R53 §5's rule holds here too:
migration is regeneration.
