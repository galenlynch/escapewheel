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
in the credential's place, has a build write a source root without a credential it recognizes
inside it, and permits a build to refuse the recipe instead.

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
| Part 05 §3.2, a writer records the recipe and its digest | extend in place | same section | a build writes no credential it recognizes; the recorded recipe carries a marker in place of each | §§3.1, 3.2 |
| Part 05 §3.5, the refusals made before a source is opened | extend in place | same section | a build may refuse a recipe carrying a credential it recognizes | §3.4 |
| Part 05 §7, a source file's `uri` is the root as the recipe states it | revise in place | same section | the `uri` is the root without a credential the build recognizes in it | §3.3 |

## 2. Background

### 2.1 A recipe admits members that carry a credential

Part 05 §3.1 gives each `source` entry a `storage_options` table and treats every other key as an
option. The incorporated recipe schema declares `storage_options` as an object, describes it as how
to open a store root, and constrains none of its members. The members are a store client's own
parameters. Object-store clients name their credentials there: `key` and `secret` for one client,
`account_key`, `sas_token` and `connection_string` for another, and `token` for a third, where
`token` also takes values such as `anon` that name a way to authenticate and are not secrets. A root
can carry a credential as well, in a URI's userinfo or in a signed query string.

The specification owns none of these names, and a later client adds its own. No list in the
specification could say which members are credentials.

### 2.2 A value of the recipe reaches the packet root at four places

Part 05 §3.2 has a writer record the recipe in the import run's `parameters`. Part 05 §7 has it
record one `core.source_files` row for each distinct source root, whose `uri` is the root as the
recipe states it. Two further places take a URI derived from a root. Under Part 12 §5 an adapter
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
as a credential, and in the copy it records it replaces every such member with the string
`[redacted]`. The first is a refusal Part 05 §3.5 does not list, and the second records a document
that is not the recipe. It recognizes no credential inside a root.

### 2.5 The recorded digest is not recomputable from the packet

The reference build computes `code_uri` over the bytes of the recipe file, and `parameters` holds
the recipe's decoded form. A reader cannot rebuild the file's bytes from the decoded form, so it
cannot recompute the digest from the packet whether or not a value was replaced. Replacing a value
in the record removes no check a reader can make today.

### 2.6 Alternatives

Forbidding a credential in a recipe would make conformance of a recipe depend on a store client's
vocabulary, so two builds would disagree about whether one recipe conforms. Requiring a build to
replace every credential would put the same indeterminacy on the build, which cannot recognize a
credential under a name it does not know. Binding the build only to what it recognizes gives it an
obligation it can always meet.

Covering only the recorded recipe would leave the other three places of §2.2 writing a root's
credential. One rule over every place a build writes is shorter than a rule for each, and a place
added later falls under it.

## 3. Decision

The subsections state the general prohibition, the recorded recipe, a written source root, and the
permitted refusal.

### 3.1 A build writes no credential it recognizes

A build decides which values of a recipe it recognizes as credentials. A value is a member of a
source entry's `storage_options`, another option of a source entry, or a component of a source
`root`. A build MUST document which values it recognizes.

A build MUST NOT include a value it recognizes as a credential in anything it composes and writes
to the staging area, to the packet, or to a source resolution document (Part 04 §5.5). A delivery an
adapter writes and the output a command prints are not composed by the build.

No validator checks this rule. Whether a string a packet holds is a credential cannot be decided
from the packet, so the rule binds the build, which alone knows what it recognized.

### 3.2 The recorded recipe carries a marker in place of a credential

The recipe a writer records in the import run's `parameters` (Part 05 §3.2) is the recipe the build
read, in which each value the build recognizes as a credential under §3.1 is replaced by the string
`[redacted]`. The member's name stays, and the record differs from the recipe nowhere else.

The run's `code_uri` remains the digest of the recipe as the build read it.

A consumer MUST read `[redacted]` in a recorded recipe as a value the build withheld and not as a
value the recipe stated.

### 3.3 A source root is written without a credential

Where a build recognizes a credential in a component of a source `root`, it MUST write the root
without that component wherever it writes the root or a URI derived from it, other than in the
recorded recipe, where §3.2 puts the marker in the component's place. A `core.source_files` row's
`uri` (Part 05 §7) is then the root as the recipe states it, less each such component.

Two roots that are equal once such components are removed are one root for Part 05 §7, and an
amending build compares a root with the rows a packet holds after removing them.

### 3.4 A build may refuse a recipe carrying a credential

A build MAY refuse, before it opens any source, a recipe carrying a value it recognizes as a
credential under §3.1, naming the source and the member or the root. A build that does not refuse
proceeds under §§3.1–3.3.

## 4. What this does not change

The recipe schema keeps `storage_options` unconstrained, so a recipe conforms whatever a store
client's parameters are named. A build is not required to recognize any value: one that recognizes
none complies and records the recipe whole.

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
its own way to authenticate, as it does for any external resource.

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
| reader, writer, validator, adapters | The reference build already replaces with `[redacted]` and refuses. It gains recognition of a credential in a root's userinfo and applies §3.3 at the three places of §2.2 other than the recorded recipe, where the marker stands in the userinfo's place. Its guide lists the values it recognizes. The reader and validator are unchanged. An adapter is unchanged: the build writes what an adapter returns. | The writer suite's cases of §6. |
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
- the same for a recognized credential in another option of a source entry;
- `storage_options.token = "anon"`, which names a way to authenticate, is recorded as stated;
- a root with userinfo the build recognizes yields a `core.source_files` row, a manifest entry and
  a resolution document entry whose URIs carry no userinfo, and a recorded recipe whose root holds
  `[redacted]` in the userinfo's place;
- two roots differing only in recognized userinfo yield one `core.source_files` row; and
- in each case `code_uri` is the digest of the recipe file as read.
