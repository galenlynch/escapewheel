# A build records a recipe without its credentials

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `fca9482429981f84d73a3b7d54be2f2ee3978142` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 05 §§3.2, 3.5 and 7 |
| **Depends on** | R135 §3.4 (the source-file row whose `uri` this qualifies); R150 §3.7 (the amending build's comparison of that `uri`) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

A recipe is the document a build reads to produce a packet, and Part 05 §3.2 has the writer record
it in the import run's `parameters`. A recipe also tells the build how to open each source, through
a `storage_options` table and through options whose names belong to the adapter. A store client
takes a credential among those options, so a recipe can carry one, and Part 05 §3.2 then copies it
into a packet that is immutable and meant to be shared.

The specification says nothing about a credential. It neither lets a build refuse a recipe that
carries one nor lets the record differ from the recipe. A build that protects a credential departs
from Part 05 §3.2, and a build that follows Part 05 §3.2 publishes the credential.

This revision forbids a build to write a credential it recognizes, names the marker a build records
in the credential's place, has a build write a URI the recipe states without a credential it
recognizes inside it, and permits a build to refuse the recipe instead.

The change is structural because it revises rules inside existing sections: Part 05 §3.2's rule
that a writer records the recipe, Part 05 §3.5's refusals, and Part 05 §7's rule that a source
file's `uri` is the root as the recipe states it. Appended sections would leave each stating the
unqualified rule beside its exception.

### 1.1 Structural crosswalk

The `Based on` commit is a metadata-only bootstrap adding `ew-recipe-provenance-record` before
Part 05 §3.2's heading, and changes nothing else. The commit after it regenerated the heading index
and the combined rendering. Part 05 §§3.5 and 7 already carried `ew-recipe-check` and
`ew-import-provenance`. No section moves, splits, merges or retires.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 05 §3.2, a writer records the recipe and its digest | extend in place | same section | a build writes no credential it recognizes; the recorded recipe carries a marker in place of a member's value and a URI without the component | §§3.1, 3.2 |
| Part 05 §3.5, the refusals made before a source is opened | extend in place | same section | a build may refuse a recipe carrying a credential it recognizes | §3.4 |
| Part 05 §7, a source file's `uri` is the root as the recipe states it | revise in place | same section | the `uri` is the root without a component the build recognizes as a credential | §3.3 |

## 2. Background

### 2.1 A recipe admits members that carry a credential

Part 05 §3.1 gives each `source` entry a `storage_options` table and treats every other key as an
option. The incorporated recipe schema declares `storage_options` as an object, describes it as how
to open a store root, and constrains none of its members. The members are a store client's own
parameters. Object-store clients name their credentials there: `key` and `secret` for one client,
`account_key`, `sas_token` and `connection_string` for another, and `token` for a third, where
`token` also takes values such as `anon` that name a way to authenticate and are not secrets. A root
can carry a credential as well, in a URI's userinfo or in a signed query string.

A recipe states a value outside a source entry too. `[packet].replaces` lists where a build reads
each packet it replaces, a `delivery` table's `command` is an argument list, and the `session`,
`subject` and `commit` tables and each `materialize` entry admit members the schema does not name.

The specification owns none of these names, and a later client adds its own. No list in the
specification could say which members are credentials.

### 2.2 A value of the recipe reaches the packet root at four places

Part 05 §3.2 has a writer record the recipe in the import run's `parameters`. Part 05 §7 has it
record one `core.source_files` row for each distinct source root, whose `uri` is the root as the
recipe states it. Two further places take a URI formed from a root. Under Part 12 §5 an adapter
returns a referenced resource's URI as its source already has it, and a build writes that URI in the
resource's manifest entry. Under Part 04 §5.5 a writer should write a source resolution document at
the packet root, whose entries each carry a source's `uri`.

### 2.3 A committed packet cannot shed a recorded credential

Part 03 §8.1 forbids a writer to modify a resource the packet owns once it is committed, and makes a
correction a replacement of the packet. Removing a recorded credential therefore means building a
replacement, and every copy of the replaced packet still carries the credential.

### 2.4 The reference build already departs from the text

Part 05 §3.5 lists what a build refuses before it opens a source, and no entry concerns a
credential. The reference build refuses a recipe whose `storage_options` hold a member it recognizes
as a credential, and in the copy it records it replaces every member of such a name, wherever in the
recipe it lies, with the string `[redacted]`. The first is a refusal Part 05 §3.5 does not list,
and the second records a document that is not the recipe. It recognizes no credential inside a
root.

### 2.5 The recorded digest is not recomputable from the packet

The reference build computes `code_uri` over the bytes of the recipe file, and `parameters` holds
the recipe's decoded form. A reader cannot rebuild the file's bytes from the decoded form, so it
cannot recompute the digest from the packet whether or not a value was replaced. Replacing a value
in the record removes no check a reader can make today.

A run the reference build is asked to sample differs. There it digests a serialization of the
decoded recipe with the sampling cap added, and not the file's bytes, so what it digests is nearer
to what `parameters` holds.

### 2.6 A bracketed marker inside a URI does not parse

A marker standing where a URI's userinfo stood makes `s3://[redacted]@bucket/x`. RFC 3986 admits
square brackets only around an IP literal in the host. Python's `urlsplit` raises `ValueError` on
that string in versions 3.11.16, 3.12.14, 3.13.15 and 3.14.7, and so does `infer_storage_options`
of fsspec 2026.7.0, which calls it. A marker without brackets parses and cannot be told from a user
name. The same marker as a member's whole value is a string like any other.

### 2.7 Alternatives

Forbidding a credential in a recipe would make conformance of a recipe depend on a store client's
vocabulary, so two builds would disagree about whether one recipe conforms. Requiring a build to
replace every credential would put the same indeterminacy on the build, which cannot recognize a
credential under a name it does not know. Binding the build only to what it recognizes gives it an
obligation it can always meet.

Covering only the recorded recipe would leave the other three places of §2.2 writing a root's
credential. One rule over every place a build writes is shorter than a rule for each, and a place
added later falls under it.

Limiting what a build may recognize to a source entry would have the record state every other
value as the recipe does, so a build could not withhold a credential in an argument list, a
`replaces` entry or a member of another table, each of which §2.1 shows a recipe can state.

Requiring a build to recognize some value, such as a password in a root's userinfo, would let a
validator report one in a `uri` a packet holds. It would also put a finding on packets that
conform today, and it is left for a later decision.

Reading `[redacted]` as a value the build withheld would be false where a recipe states that
string, as one rebuilt from a recorded recipe does. Forbidding a consumer to take it for the value
the build used is true in both cases.

## 3. Decision

The subsections state the general prohibition, the recorded recipe, a URI written without a
credential, and the permitted refusal.

### 3.1 A build writes no credential it recognizes

A build decides which values of a recipe it recognizes as credentials. A value is the value of any
member the recipe states, an element of any array, or a component of either where it is a URI. A
build MUST document which values it recognizes. No checker verifies that it does.

A build MUST NOT include a value it recognizes as a credential in anything it composes and writes
to the staging area, to the packet, or to a source resolution document (Part 04 §5.5). A build
composes the manifest, the recipe it records, each other row it records for itself, the
`core.source_files` rows among them (Part 05 §7), and the source resolution document. It does not
compose what an adapter delivers, what a command prints, or a row or resource the packet held
before the build, and the rule reaches none of these. Within the manifest, the `uri` of a
referenced resource is one an adapter returned (Part 12 §5), and §3.3 states what a build owes
there.

No validator checks this rule. Whether a string a packet holds is a credential cannot be decided
from the packet, so the rule binds the build, which alone knows what it recognized.

### 3.2 The recorded recipe withholds each recognized value

The recipe a writer records in the import run's `parameters` (Part 05 §3.2) is the recipe the build
read, differing from it in two ways and no other. Where the build recognizes as a credential the
whole value of a member or of an array element, the record holds the string `[redacted]` under that
member's name or at that element's position. Where the build recognizes as a credential a component
of a URI, the record holds the URI without that component, as §3.3 has a build write it, and no
marker stands in the component's place.

The run's `code_uri` remains the digest of the recipe as the build read it.

A consumer MUST NOT take `[redacted]` in a recorded recipe for the value the build used. No checker
verifies this.

### 3.3 A URI is written without a credential

Where a build recognizes a credential in a component of a URI the recipe states, it MUST write that
URI without the component wherever it writes it. Where an adapter returns for a referenced resource
(Part 12 §5) a URI carrying the same component, a build MUST write that URI without the component
too. No validator checks either rule, for the reason §3.1 gives.

A `core.source_files` row's `uri` (Part 05 §7) is then the root as the recipe states it, less each
such component. Two roots that are equal once such components are removed are one root for Part 05
§7. An amending build compares a root with the `uri` of each row the packet holds after removing
from both every component it would recognize as a credential.

### 3.4 A build may refuse a recipe carrying a credential

A build MAY refuse, before it opens any source, a recipe carrying a value it recognizes as a
credential under §3.1, naming the member that holds the value, and the source where a source entry
holds it, and not the value. A build that does not refuse proceeds under §§3.1–3.3.

## 4. What this does not change

The recipe schema keeps `storage_options` unconstrained, so a recipe conforms whatever a store
client's parameters are named. A build is not required to recognize any value: one that recognizes
none complies and records the recipe whole. The rule therefore gives no assurance about a packet
whose build is unknown.

A packet that already holds a credential keeps it. §3.1 does not reach a row the packet held before
the build, so an amending build links its run to a held `core.source_files` row whose `uri` stays
as recorded, and Part 03 §8.1 leaves a replacement packet as the only correction.

A build supplies a source's options to its adapter as it does now, credentials included, since the
adapter opens the source with them. What the adapter then delivers or prints is outside §3.1.

## 5. Consequence

Every existing packet conforms unchanged. A packet whose recorded recipe holds `[redacted]` conforms
under the new text, and one recorded verbatim conformed before and still does. No packet's bytes or
manifest changes, and no registry, schema or descriptor changes.

A refusal and a replacement answer different failures. A refusal tells a recipe's author that the
file itself holds a secret, which replacing the record would hide from them. A replacement protects
the packet where the build goes ahead.

A source root written without a signed query or userinfo does not open by itself. A reader supplies
its own way to authenticate, as it does for any external resource. A recorded URI shows no sign
that a component was withheld, so a reader learns of it only when the URI does not open.

Two roots that differ only in a component a build recognizes share one `core.source_files` row. A
build that recognizes a user name as well as a password records one row for two users of one
store.

`code_uri` digests bytes that include each withheld value, so it commits to them. A reader able to
rebuild every other digested byte could test a guess at a short value against it. §2.5 says why a
reader cannot for a recipe file, and where the reference build's sampled run differs.

No accepted clause is superseded. Three ledger entries gain notes: R111 §3.5, placed at Part 05
§3.2, that §3.2 qualifies what a writer records; and R135 §3.4 and R150 §3.7, placed at Part 05 §7,
that §3.3 qualifies a source-file row's `uri` and an amending build's comparison.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. Part 01 §3.20 defines a processing run and states no rule about its parameters. | None required. |
| logical prose and registry | Unchanged. `core.processing_runs.parameters` and `core.source_files.uri` keep their declarations, and no rule reads either for a credential. | None required. |
| physical profiles | Unchanged. No storage property is involved. | None required. |
| packet manifest and JSON Schemas | Unchanged. The recipe schema keeps `storage_options` unconstrained. A manifest entry's `uri` and a resolution document's `uri` keep their shapes. | None required. |
| validation and import | Part 05 §3.2 takes §§3.1 and 3.2, Part 05 §3.5 takes §3.4, and Part 05 §7 takes §3.3. No validator check is added. | `evidence/R<N>.json` names the three anchors. |
| extensions | Unchanged. An extension declares no recipe member. | None required. |
| reader, writer, validator, adapters | The reference build already replaces a member of a credential's name with `[redacted]` and refuses one among `storage_options`. It gains recognition of the userinfo of a URI the recipe states, which it withholds whole, a user name included, and applies §3.3 at the four places of §2.2. It recognizes no signed query. Its guide lists the values it recognizes. The reader and validator are unchanged. An adapter is unchanged: it receives a source's options and root as the recipe states them. | The writer suite's cases of §6. |
| conformance fixtures and tests | No packet fixture distinguishes the rule, since a validator cannot decide it. Build tests cover §6's cases. | The writer suite. |
| revision process and tooling | The ordinary ledger and evidence records, and the notes on R111 §3.5, R135 §3.4 and R150 §3.7. | `ledger.py`, `evidence.py` and `verify.py`. |
| generated publications and developer documentation | The combined specification regenerates. The writer's guide documents the recognized values and the marker. | `verify.py`. |

## 6. Conformance and implementation evidence

§§3.1 and 3.2 are `applied` at Part 05 §3.2, §3.3 at Part 05 §7, and §3.4 at Part 05 §3.5, each by
canonical anchor.

No validator finding distinguishes the rule. These build cases do:

- a recipe whose `storage_options` hold a recognized credential is refused before any source opens,
  or builds a packet whose recorded recipe holds `[redacted]` under that member's name and the
  credential nowhere;
- a recognized credential in a member elsewhere in the recipe builds a packet whose recorded recipe
  holds `[redacted]` under that member's name;
- `storage_options.token = "anon"`, which names a way to authenticate, is recorded as stated;
- a root with userinfo the build recognizes yields a recorded recipe, a `core.source_files` row, a
  manifest entry and a resolution document entry whose URIs carry no userinfo;
- a recorded root, read back, parses as a URI;
- two roots differing only in recognized userinfo yield one `core.source_files` row;
- an amending build whose root differs from a held row's `uri` only in userinfo records no new row
  and leaves the held row as recorded;
- a refusal names the member holding a recognized credential and does not state the value; and
- in each case `code_uri` is the digest of the recipe file as read.
