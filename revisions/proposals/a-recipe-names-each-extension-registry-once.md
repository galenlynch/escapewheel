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
says its prose owns what each recipe member means, but gives `extensions` no meaning, and
[Part 05 §3.5](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-recipe-check) has no
refusal for a list naming one extension twice.

Two entries can name one extension in three ways: the same string twice, a path and an installed
identifier for one document, or two paths to different versions. A packet binds each extension
once, because [Part 04 §8](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-registry-bindings)
keys its registry descriptors by registry identifier, and
[Part 02 §9.1](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-document)
makes an extension's registry identifier its `extension_id`. A build therefore keeps one of two
such entries, and nothing states which or requires the build to report the loss.

## 2. Evidence

- `registry/recipe.schema.json` declares `extensions` as an array of strings without
  `uniqueItems`, so a recipe listing one string twice passes the schema. Its `$defs.resources`,
  which `owns` and `contributes` use, does carry `uniqueItems`.
- `Recipe.check` in `escapewheel_writer/recipe.py` merges each extension's tables into one mapping
  and has no duplicate test. `PacketWriter.__init__` stores each extension under
  `self._extensions[extension_id]`, so the later document replaces the earlier one.
- A probe at the baseline, run in the writer's environment, built a `PacketWriter` with two
  extension documents sharing `extension_id` `task`, at `registry_version` 0.1.0 and 0.2.0, the
  second admitting one more `enum` value. The writer kept one extension, at version 0.2.0, and
  raised and reported nothing, so the packet binds whichever version comes last.
- Part 05 §3.1 already refuses the parallel case for sources: a recipe lists each source kind in
  one `source` entry, and a build refuses a recipe that lists one twice, naming the kind.

The loss happens in the build, before any manifest exists. A manifest cannot carry the defect,
because a repeated registry identifier is a duplicate JSON member and Part 04 reports it as
`packet.manifest.duplicate_member`.

## 3. Desired outcome and constraints

A build given two entries resolving to one extension reports them and stops before it opens a
source. The recipe's `extensions` member has a stated meaning. The recipe schema's `$id` and every
valid recipe stay as they are.

Part 05 §3.1 also gives no meaning to `id`, `out`, `registry` or `description` under `[packet]`.
That gap is independent of this decision and stays out of scope.

## 4. Options and tradeoffs

**Refuse by resolved `extension_id`** (preferred direction). Part 05 §3.1 would state that each
`extensions` entry names one extension registry the packet binds under
[Part 09 §5.3](../../escapewheel_poc_docs_v0.2/09_metadata_and_extensions.md#ew-extension-registration).
A recipe would not name two registries with one `extension_id`, and a build would refuse one that
does, naming the extension and both entries before it opens any source. The rule sits beside the
source-kind rule and uses the same wording.

The test follows resolution because only the loaded document carries `extension_id`, and a build
already loads every extension before it checks the recipe, since Part 05 §3.5's checks read
extension tables. How an entry resolves, as a path beside the recipe or as an identifier an
implementation has installed, stays the build's concern, and the refusal holds for either form.

**`uniqueItems` in the schema alone.** Rejected: it catches a repeated string but not a path and an
identifier naming one registry, nor two paths to different versions, the case that loses a version,
and beside the preferred rule it would report one fault twice.

**Accept duplicates that resolve to identical bytes.** Rejected: a recipe listing one extension
twice is a mistake its author would want reported, and accepting it gains nothing.

**Keep the current behavior.** Rejected: the last entry silently decides which version a packet
binds.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged: no concept's meaning changes. |
| logical prose, registries, rules | Unchanged: the rule governs a recipe, which no logical schema declares. |
| physical profiles | Unchanged: the recipe is not a physical artifact. |
| packet manifest and schemas | Unchanged: a manifest already cannot bind one registry twice, and `recipe.schema.json` keeps its shape under the preferred direction. |
| validation and import | Affected: Part 05 §3.1 states the meaning of `extensions` and the refusal. |
| extension registries | Unchanged: the rule reads each registry's `extension_id` and changes no declaration. |
| writer | Affected: `Recipe.check`, or the extension loading that precedes it, refuses the duplicate, naming both entries, and `PacketWriter` raises instead of overwriting when given two documents with one `extension_id`. |
| reader and validator | Unchanged: neither reads a recipe. |
| adapters | Unchanged: an adapter never sees the recipe's `extensions`. |
| existing packets | Unchanged: each already binds at most one registry per extension. |
| conformance fixtures and tests | Affected: writer tests cover a repeated string, and a path and a second document with one `extension_id`. |
| revision tooling | Unchanged: no revision check reads a recipe. |
| documentation | Unchanged: no README describes duplicate `extensions` entries. |

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
