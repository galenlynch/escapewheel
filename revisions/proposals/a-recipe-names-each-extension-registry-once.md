# A recipe names each extension registry once

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-24 |
| **Based on** | `f5f33647eb9c3e29ff8c850afa480468fea0c582` |
| **Decision domain** | specification |
| **Affects** | Part 05 §3.1 and Part 05 §3.5; `registry/recipe.schema.json` (unchanged under the preferred direction); the reference writer's recipe check and `PacketWriter` |

## 1. Problem

A session recipe's `[packet]` table admits `extensions`, a list naming the extension registries the
packet binds. [Part 05 §3.1](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-recipe-purpose)
states that its prose owns what each recipe member means, but it gives `extensions` no meaning, and
[Part 05 §3.5](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#35-checking-a-recipe) has no
refusal for a list naming one extension twice.

Two entries can name one extension in three ways: the same string twice, a path and an installed
identifier for one document, or two paths to different versions. A packet binds each extension
once, because [Part 04 §8](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-registry-bindings)
keys its registry descriptors by registry identifier, and
[Part 02 §9.1](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-document)
makes an extension's registry identifier its `extension_id`. So one of the two entries has to go,
and at present nothing states which one or requires a report.

## 2. Evidence

- `registry/recipe.schema.json` declares `extensions` as an array of strings without
  `uniqueItems`, so a recipe listing one string twice passes the schema. Its `$defs.resources`,
  which `owns` and `contributes` use, does carry `uniqueItems`.
- `Recipe.check` in `escapewheel_writer/recipe.py` merges each extension's tables into one mapping
  and has no duplicate test. `PacketWriter.__init__` stores each extension under
  `self._extensions[extension_id]`, so the later document replaces the earlier one.
- A probe at the baseline built a `PacketWriter` with two extension documents sharing
  `extension_id` `task`, at `registry_version` 0.1.0 and 0.2.0, the second admitting one more
  `enum` value. The writer kept one extension, at version 0.2.0, and raised and reported nothing.
  The packet would bind 0.2.0 whatever order the author meant.
- Part 05 §3.1 already refuses the parallel case for sources: a recipe lists each source kind in
  one `source` entry, and a build refuses a recipe that lists one twice, naming the kind.

A manifest cannot carry the defect, because a repeated registry identifier is a duplicate JSON
member and Part 04 reports it as `packet.manifest.duplicate_member`. The loss happens in the build,
before any manifest exists.

## 3. Desired outcome and constraints

A build that is given two entries resolving to one extension says so and stops before it opens a
source. The recipe's `extensions` member has a stated meaning. The recipe schema's `$id` and every
valid recipe stay as they are.

## 4. Options and tradeoffs

**Refuse by resolved `extension_id`** (preferred direction). Part 05 §3.1 would state that each
`extensions` entry names one extension registry the packet binds under
[Part 09 §5.3](../../escapewheel_poc_docs_v0.2/09_metadata_and_extensions.md#ew-extension-registration).
A recipe would not name two registries with one `extension_id`, and a build would refuse one that
does, naming the extension and both entries before it opens any source. The rule sits beside the
source-kind rule and uses the same wording.

Resolution precedes the test because only the loaded document carries `extension_id`. A build
already loads every extension before it checks the recipe, since Part 05 §3.5's checks read extension
tables.

Rejected: **`uniqueItems` in the schema alone.** It catches only a repeated string. It cannot see
a path and an identifier naming one registry, nor two paths to different versions, which is the
case that loses a version. Adding it beside the preferred rule would give one fault two findings.

Rejected: **accept duplicates that resolve to identical bytes.** Nothing is gained, and a recipe
listing one extension twice is a mistake its author would want reported.

Rejected: **keep the current behavior.** The last entry silently decides which version a packet
binds.

How an entry resolves to a document, whether as a path beside the recipe or as an identifier an
implementation has installed, stays the build's concern. The schema's description already names
both forms, and the refusal does not depend on which form is used.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. |
| logical prose, registries, rules | Unchanged. |
| physical profiles | Unchanged. |
| packet manifest and schemas | Unchanged; the manifest already cannot bind one registry twice. `recipe.schema.json` is unchanged under the preferred direction. |
| validation and import | Affected: Part 05 §3.1 states the meaning of `extensions` and the refusal. |
| extension registries | Unchanged. |
| writer | Affected: `Recipe.check`, or the extension loading that precedes it, refuses the duplicate, naming both entries. `PacketWriter` raises instead of overwriting when given two documents with one `extension_id`. |
| reader and validator | Unchanged; neither reads a recipe. |
| adapters | Unchanged. |
| existing packets | Unchanged; each already binds at most one registry per extension. |
| conformance fixtures and tests | Affected: writer tests for a repeated string, and for a path and a second document with one `extension_id`. |
| revision tooling | Unchanged. |
| documentation | Unchanged. |

## 6. Open questions

None blocks drafting. Part 05 §3.1 also gives no meaning to `id`, `out`, `registry` or
`description` under `[packet]`. That gap is related but independent of this decision, and closing
it is left out of scope here.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [x] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.
