# A build records a recipe without its credentials

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-10-01 |
| **Based on** | `f8d62ab0e79945a68d9aa8f7d3446cb60d956bca` |
| **Decision domain** | specification |
| **Affects** | Part 05 §3.2's rule that a writer records the recipe; Part 05 §3.5's refusals; Part 05 §7's rule that a `core.source_files` row carries a source root as the recipe states it |

## 1. Problem

A recipe is the document a build reads to produce a packet, and Part 05 §3.2 has the writer record
it in the import run's `parameters`. A recipe also tells the build how to open each source, through
a `storage_options` table and through options whose names belong to the adapter. A store client
takes a credential among those options, so a recipe can carry one, and Part 05 §3.2 then copies it
into the packet. The packet is immutable and is meant to be shared, so the credential travels with
every copy and cannot be removed from one.

The specification says nothing about a credential. It neither lets a build refuse a recipe that
carries one nor lets the record differ from the recipe. A build that protects a credential therefore
departs from Part 05 §3.2, and a build that follows Part 05 §3.2 publishes the credential.

## 2. Evidence

Observed in the tracked files at the baseline commit.

### 2.1 The recipe reaches the packet whole, and its source roots reach a table

Part 05 §3.2 requires a writer to record the recipe in the import run's parameters and the recipe's
digest as the run's `code_uri`, and states no exception. Part 05 §7 requires one `core.source_files`
row for each distinct source root, whose `uri` is the root as the recipe states it. These are the
two places a value of the recipe is written into a packet.

### 2.2 A recipe admits members that carry a credential

Part 05 §3.1 gives each `source` entry a `storage_options` table and treats every other key as an
option. The incorporated recipe schema declares `storage_options` as an object, describes it as how
to open a store root, and constrains none of its members. The members are a store client's own
parameters. Object-store clients name their credentials there: `key` and `secret` for one client,
`account_key`, `sas_token` and `connection_string` for another, and `token` for a third, where
`token` also takes values such as `anon` that name a way to authenticate and are not secrets. A root
can carry a credential as well, in a URI's userinfo or in a signed query string.

The specification owns none of these names, and a later client adds its own. No list in the
specification could therefore say which members are credentials.

### 2.3 A committed packet cannot shed a recorded credential

Part 03 §8.1 forbids a writer to modify a resource the packet owns once it is committed, and makes a
correction a replacement of the packet. A build writes the import run's row and each source-file row
into tables the packet owns (Part 05 §7). Removing a recorded credential therefore means building a
replacement, and every copy of the replaced packet still carries the credential.

### 2.4 No refusal covers a credential

Part 05 §3.5 lists what a build refuses before it opens a source. No entry concerns a credential,
and a recipe carrying one satisfies the recipe schema. The reference build already departs from the
text on both counts. It refuses a recipe whose `storage_options` hold a member it recognizes as a
credential, and it replaces every such member, wherever it sits in the document, in the copy it
records. The first is a refusal Part 05 §3.5 does not list, and the second records a document that
is not the recipe.

### 2.5 The recorded digest is not recomputable from the packet

The reference build computes `code_uri` over the bytes of the recipe file, and `parameters` holds
the recipe's decoded form. A reader cannot rebuild the file's bytes from the decoded form, so it
cannot recompute the digest from the packet whether or not a value was replaced. Replacing a value
in the record removes no check that a reader can make today.

## 3. Desired outcome and constraints

A credential that a build recognizes in a recipe reaches no resource of the packet, and a reader of
the packet can tell a value the build replaced from one the recipe stated. The resolution preserves:

- Part 05 §3.2's purpose, that a committed packet states what produced it;
- `code_uri` as the digest of the recipe the build read;
- the recipe schema, so that a recipe remains free to carry whatever a store client needs; and
- determinacy for the build: an obligation it can always meet, bounded by what it can recognize.

## 4. Options and tradeoffs

| option | effect |
|---|---|
| keep Part 05 §3.2 as it is | a build following the text copies a credential into an immutable, shared packet; the remedy is revoking the credential and replacing the packet |
| forbid a credential in a recipe and require a build to refuse one | no conforming recipe leaks, but the rule is indeterminate: which members are credentials is a store client's vocabulary, so two builds disagree about whether a recipe conforms; a machine with no ambient credentials cannot build at all |
| require a build to replace every credential in what it records | the same indeterminacy falls on the build, which cannot recognize a credential under a name it does not know, so it cannot always comply |
| a build does not record a credential it recognizes: it replaces the value in what it records, or refuses the recipe (preferred direction) | the obligation is bounded by the build's own recognition, so a build can always meet it; the record stays the recipe apart from marked values; a build that would sooner tell the author than repair the record is free to refuse |

Under the preferred direction Part 05 §3.2 keeps its rule and gains one exception. Where a build
recognizes a value of the recipe as a credential, it records a fixed marker in place of that value
in the import run's `parameters`. The marker is one string that the specification names, so a reader
can tell a replaced value from a stated one, and the member's name stays in the record. `code_uri`
remains the digest of the recipe as the build read it. Which values a build recognizes is its own to
decide and to document, because the names are a store client's.

Part 05 §3.5 gains a permission: a build is free to refuse, before it opens any source, a recipe
carrying a value it recognizes as a credential. The permission is needed because the recipe
satisfies the schema and no listed refusal applies. Refusing and replacing answer different
failures. A refusal tells the author that the recipe file itself holds a secret, which replacing the
record would hide from them. A replacement protects the packet where the build goes ahead.

The same rule covers a source root, the other value of a recipe that Part 05 §7 writes into a
packet. A build that recognizes a credential inside a root records the root without it, or refuses
the recipe.

No validator checks the rule. Whether a recorded string is a credential cannot be decided from the
packet, so the obligation binds the build, which alone knows what it recognized. The revision would
state that the rule is unchecked.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. Part 01 §3.20 defines a processing run and states no rule about its parameters. |
| logical prose, registry meta-schema, declarations and rules | Unchanged. `core.processing_runs.parameters` and `core.source_files.uri` keep their declarations, and no rule reads either for a credential. |
| physical profiles | Unchanged. No storage property is involved. |
| packet manifest and other JSON Schemas | Unchanged. The recipe schema keeps `storage_options` unconstrained, and the manifest records no recipe value. |
| validation and import | Part 05 §3.2 states the exception and names the marker. Part 05 §3.5 states the permitted refusal. Part 05 §7 lets a recorded root omit a credential. No validator check is added. |
| extension registries | Unchanged. An extension declares no recipe member. |
| reader, writer, validator, adapters, code generation | The reference build already replaces and refuses; it adopts the named marker and extends recognition to a source root. The reader and validator are unchanged. An adapter is unchanged: it receives its options from the build and records nothing itself. |
| existing packets | Unchanged in conformance. A packet whose recorded recipe holds a replaced value conforms under the new text, and one recorded verbatim conformed before and still does. |
| conformance fixtures and implementation tests | No packet fixture distinguishes the rule, since a validator cannot decide it. Build tests cover a recognized credential in `storage_options`, in another option, and in a root: the record carries the marker or the build refuses, and `code_uri` is the digest of the recipe as read. |
| revision lifecycle, ledger, evidence and tooling | Unchanged. |
| generated publications and developer documentation | The combined rendering regenerates. The writer's guide lists the values its build recognizes. |

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
