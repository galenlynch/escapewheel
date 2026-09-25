# A Build Supplies an Adapter a Persistent Source Cache Keyed by URI and Entity Tag

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `782dbf811f90f8741e1dc735d326996a69df0d36` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 03 §§11, 11.2, and 11.5, and a new last subsection of Part 03 §11; Part 05 §§3.4 and 3.5; Part 07 §4 |
| **Depends on** | R119 §§3.1, 3.3, and 3.4; R134 §3.4; R135 §3.2; R136 §3.6 |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5 |

Section 3 is normative. Sections 1, 2, 5, and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

An adapter reading a source on an object store may keep the objects it fetched, so that a second
read of one object, in the same build or a later one, costs no transfer. Part 03 §11.2 closes the
vocabulary of what a build supplies an adapter and bars `accepts` from naming a term, and Part 05
§2's delivery rule governs a delivery and nothing else an adapter writes. The specification
therefore says nothing about where such a cache lies, how long it lives, or when an adapter may
trust what it holds; R134 §7 deferred exactly those questions.

The reference writer fills the gap outside the channel Part 03 §11.2 defines. An environment
variable carries the cache's location to every adapter, a missing variable falls back to `TMPDIR`,
and an entry is keyed on the object's path alone, so an object replaced at the store is read from
the old entry in every later build, and the packet records nothing that shows it.

This revision adds `source_cache`, the one term an adapter names in `accepts`. A build supplies
under it a directory outside the packet root that no build empties. An adapter reads an entry only
for the object's URI and the entity tag the store reports now, publishes an entry whole, and keeps
source bytes across builds nowhere else. Entry layout, eviction, and size stay an implementation's.
`core.source_files`, including its `sha256` column, is outside the decision.

The change is structural because it replaces rules inside Part 03 §§11.2 and 11.5 and Part 05 §3.5:
the bar on a term in `accepts`, the refusal of a term a recipe cannot fill, and the refusal of a
declaration accepting a term. Appended sections would leave each rule standing beside its exception.
The location and its entries form one new subject, appended as the last subsection of Part 03 §11.

### 1.1 Structural crosswalk

Part 03 §§11, 11.2, and 11.5, Part 05 §§3.4 and 3.5, and Part 07 §4 already carry the canonical
anchors `ew-reaching-a-source`, `ew-build-supplied-values`, `ew-adapter-declaration-document`,
`ew-source-declarations`, `ew-recipe-check`, and `ew-reference-object-model`, so no anchor bootstrap
is needed. The new subsection, "The source cache", takes `ew-source-cache` when it is created. No
section moves, splits, merges, or retires.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 03 §11.2, the table of terms | extend in place | same section | adds `source_cache` | §3.1 |
| Part 03 §11.2, an adapter "MUST NOT name in `accepts` a term of the list above" | replace in place | same section | `source_cache` is the one term `accepts` may name, and `needs` may not name it | §3.1 |
| Part 03 §11.2, a build refuses a recipe where a term cannot be filled and never passes one absent | replace in place | same section | the refusal does not reach `source_cache`, which a build without a location passes to no adapter | §3.1 |
| Part 03 §11.5, a build refuses a declaration whose `accepts` names a term | replace in place | same section | except `source_cache`; a declaration whose `needs` names `source_cache` is refused | §3.1 |
| Part 05 §3.4, `accepts` described as the options an adapter can run without | revise in place | same section | also names the one term an adapter can run without | §3.1 |
| Part 05 §3.5, the refusals of an unfillable term and of a declaration accepting a term | replace in place | same section | as for Part 03 §§11.2 and 11.5 | §3.1 |
| Part 07 §4, `ACCEPTS` described as options | revise the informative text | same section | `ACCEPTS` may carry `source_cache` | §3.1 |
| Part 03 §11, the sentence listing what the section covers | revise in place | same section | names the source cache | none |
| none | add | a new last subsection of Part 03 §11, "The source cache" (`ew-source-cache`) | the location's properties, entries, their publication, and the ban on other caches | §§3.2–3.5 |

## 2. Background

Section 2 is informative. Code observations were read from `escapewheel-writer` and
`escapewheel-aind` at the recorded baseline, where neither package differs from the commit the
proposal was measured against, and from fsspec 2026.7.0, the version in the writer's lock. Cache
contents and store responses were re-measured on one workstation on 2026-09-24. Store responses were
requested anonymously from `aind-open-data` in `us-west-2` for three known objects; no prefix was
listed.

### 2.1 One module places the cache, and an environment variable carries it

Every adapter that reads a store opens its root through `source_root` in
`escapewheel_writer.sources.store`: the writer's `sorter`, `waveforms`, `lfp`, `nwb`, `sync`,
`harp`, and `openephys` adapters and the AIND package's `session`, `video`, and `aind_unit_qc`. A
local root resolves to a path and is never cached. A store root is opened through fsspec's
`simplecache`, which the module replaces with a subclass, `WholeObjectCache`, in a directory
`cache_directory()` names: `ESCAPEWHEEL_SOURCE_CACHE` where set, and otherwise
`$TMPDIR/escapewheel-source-cache`.

`Recipe.load` calls `cache_beside`, which sets the variable to `.escapewheel-source-cache` in the
packet's parent directory unless an operator already set it. An adapter run out of process inherits
the environment, and `escapewheel deliver` opens its supplied `root` through the same `source_root`,
so the variable is the only channel the location has. The module's own comment says the variable is
not a Part 03 §11.2 term. That section forbids a build to apply a facility of its own to an adapter
that does not name the option carrying it; the reference build applies this one to every adapter,
and none names it.

The validator and reader read stores uncached, and so does the LFP adapter's external digest, which
goes through the validator's store module.

### 2.2 An entry is keyed on the object's path, and a changed object is never re-read

`simplecache` names an entry by the SHA-256 of the object's path without its scheme. Its
`SimpleCacheFileSystem` sets `cache_check`, `expiry_time`, and `check_files` to false, keeps no
metadata, and tests only whether the entry exists. Once an object is cached, no build sends another
request for it, so an object replaced at the same key is served from the old entry in every later
build sharing the directory, and nothing records the entry's age or what the store held when it was
fetched.

Under Part 05 §7 the writer records one `core.source_files` row per distinct recipe `root`, with
`uri` as the recipe states it and the other columns null. A packet built from a stale entry
therefore carries the same rows as one built from current bytes.

### 2.3 Concurrent builds share entries without a lock

`WholeObjectCache` fetches into `<entry>.<pid>.part` and renames it onto the entry, so on one host
an entry appears whole or not at all, and two builds fetching one object each publish a complete
copy. Two builds whose packets share a parent directory share a cache, the ordinary case for
rebuilds. Three hazards remain: fsspec's `cat` route fetches straight into the entry's final name,
bypassing the rename, though every adapter read observed goes through `open`, which the subclass
covers; two hosts sharing a network filesystem can run processes with one pid and write one `.part`
file, an inference not reproduced; and `cache_beside` sets a process-wide variable, so a second
recipe loaded in one process moves the location for every root resolved afterwards. No `.part` file
was found in any cache on this workstation.

### 2.4 Real builds read one store root through caches holding duplicates

| recipe | sources with an `s3://` root | of those, run out of process | distinct store roots |
|---|---|---|---|
| `776259-packet/recipe.toml` | `session`, `sorter`, `waveforms`, `aind_unit_qc` | `session`, `aind_unit_qc` | 1 |
| `786867-packet/recipe.toml` | `session`, `sorter`, `waveforms`, `aind_unit_qc` | `session`, `aind_unit_qc` | 1 |
| `df-packet/recipe.toml` | `waveforms`, `aind_unit_qc` | `aind_unit_qc` | 1 |

`df-packet` and `786867-packet` read the same sorted asset. Every NWB root in the three recipes is
local. Five of the ten store-rooted sources run out of process and receive the location only
through the environment.

| directory | entries | bytes | written |
|---|---:|---:|---|
| `/mnt/Data/786867-packet/.escapewheel-source-cache` | 2,617 | 3,238 MB | 2026-09-24, 14:00–15:00 |
| `/mnt/Data/.escapewheel-source-cache` | 2,244 | 3.6 MB | 2026-09-24, 15:00–16:00 |
| `/tmp/escapewheel-source-cache`, a tmpfs | 1,589 | 3.8 MB | 22 on 2026-09-16, 1,567 on 2026-09-24 |
| the `776259-packet` and `df-packet` caches | 0 | 0 | — |

One build wrote the 786867 entries, logged in `build-maint.log`: it ran `sorter` over the sorted
asset for 141 s and failed at 190 s, just after `waveforms` began. Ten of its entries exceed 10 MB
and hold 3,154 MB, 97% of the bytes; the median entry is 2 KB. The count is a lower bound on what
one build reads from a sorted asset, since `session` and `aind_unit_qc` never ran.

The same objects sit in several caches. Of the tmpfs cache's 1,589 entries, 1,524 are also in
`/mnt/Data/.escapewheel-source-cache`, and 1,051 of the 786867 entries are in the tmpfs cache.
`df-packet` and `786867-packet` read one asset through two caches, because the default location is
per packet parent. The 1,567 tmpfs entries written on 2026-09-24 show a process reading a store with
the variable unset, which leaves the fallback in use on a filesystem held in memory.

### 2.5 An anonymous read sees an entity tag, a version ID, and a checksum

A `HeadObject` with checksum mode enabled on `session.json`, `subject.json`, and `rig.json` under
the 786867 sorted asset returned, for each, `ContentLength`, `ETag`, `LastModified`, `VersionId`,
server-side encryption `AES256`, and a full-object `ChecksumCRC32`. The bucket reports versioning
`Enabled`, and `GetObjectAttributes` was refused as `AccessDenied`. A `GetObject` returned the same
`ETag`, `VersionId`, and CRC32 with the bytes, and its `ETag` equals the MD5 of those bytes, as
R136 §2.2 predicts for a single-part SSE-S3 object. A `GetObject` with a mismatched `If-Match` failed
with `PreconditionFailed`.

Thirty sequential anonymous `HeadObject` requests took 19.1 ms median and 21.1 ms at the 90th
percentile. One request per object for the 2,617 objects of §2.4 costs about 50 s sequentially,
against the 141 s the `sorter` source took in the same build.

### 2.6 Alternatives

Leaving the cache to implementations keeps a facility Part 03 §11.2 forbids and lets a stale entry
change packet content silently; fixing the reference writer's keying alone still leaves an adapter
from another implementation no location and no rule for trusting an entry.

The recipe cannot name the location, because Part 05 §3.2 records the recipe in the packet and a
machine path would make two builds of one recipe differ. The staging area cannot hold it, because a
writer may empty one when a build begins (Part 05 §2). The packet root cannot, because its entries
would be strays under Part 03 §9.5, would not exist where the root is an object-store prefix
(Part 03 §4), and would travel with every copy of the packet. A build prefetching objects into a
delivery location would need the list of objects each adapter reads, which only the adapter knows.

Declaring `source_cache` in `needs` would change no declaration rule, but it misstates what an
adapter can run without and makes a writable persistent directory a precondition of every build.
Supplying the term to every adapter unconditionally breaks Part 03 §11.2's rule that a build supplies
exactly what an adapter declares.

Keying on the URI alone is §2.2's stale read. `Last-Modified` with size misses a same-size rewrite
within the timestamp's one-second resolution. A version ID never names two contents, but only a
versioned bucket reports one, so unversioned stores would need a second rule. A full-object checksum
is absent from some objects (R136 §2.2), a 32-bit CRC is weak as an identity across a shared cache,
and reading one costs the same request as the tag. The preferred direction is the entity tag, which
S3, Google Cloud Storage, Azure Blob Storage, and HTTP servers generally report, and which R136 §3.6
already records as evidence of change. A rewrite of identical bytes with a different multipart part
size changes the tag, which errs toward fetching again. The three object stores report strong tags;
excluding HTTP's weak tags would invoke RFC 9110 as a new normative reference for a case no measured
source presents.

Fixing an entry's name as a function of URI and tag would let two implementations share entries, at
the cost of a layout every implementation keeps; without it, adapters of two implementations sharing
a location miss each other's entries and never misread them. A lock per entry or per location would
outlive a killed build, where publishing without replacement needs none. Letting the last of two
concurrent publications replace the first is equally correct under a strong tag, since both hold the
same bytes, but it swaps a file under a reader: on NFS another host reading the replaced file can
fail with a stale handle, and on Windows a rename onto a file another process holds open fails.
Publishing only where no entry stands, as Git publishes a loose object by linking it into place and
treating an existing object as success, leaves a readable entry unchanged. Permitting other
persistent caches would leave the environment variable and the tmpfs fallback §2.4 found in use
conforming. Recording
which version of each object a build read would need a `core.source_files` row per object, which
R135 §2.5 rejected for requiring a delivery field every out-of-process adapter fills.

### 2.7 Feasibility and overlap

Every store-reading adapter in both packages already resolves its root through one function, and the
writer already builds the input object Part 03 §11.2 defines, so the location travels as one more
member of it. Obtaining an object's current entity tag costs one request per object per run, which
§2.5 prices at about 50 s for one build's 2,617 objects sequentially. A writer publishing an entry
by a hard link, or a move that refuses to replace, within the location needs no lock; both fail
where an entry already stands, which tells the later writer to discard its copy. Filesystems differ
in which they offer: on this workstation's data disk, an NTFS volume mounted through FUSE, `link(2)`
publishes a new name and fails with `EEXIST` onto an existing one, while `renameat2` with
`RENAME_NOREPLACE` fails with `EINVAL` even onto a new name, so a writer there publishes by hard
link.

R141, on the core vocabulary's scope, amended Part 00 §§1 and 3.2 and Part 02 §2.2 and shares no
text with this one. The open draft on packet-owned opaque delivery adds a location term under the
staging area to Part 03 §11.2's table and amends §11.3; each draft appends a row and neither
location can serve for the other. The proposal to move Part 03 §11 into a part of its
own would carry the new subsection with it, and its preferred direction incorporates this change
first. R135 §7's two builds at one packet root remain outside this decision, which concerns builds
at different roots sharing a cache. A reverse-citation query for the five amended sections lists 368
citations, 244 of them outside the revision records; incorporation reads those in the writer, the
AIND package, the adapter schema, and Parts 03, 05, and 07.

## 3. Decision

Five subsections add the `source_cache` term and how an adapter declares it, set the properties of
the location a build supplies under it, say when an adapter may read an entry there, make an entry
safe to share, and confine an adapter's cross-build copies of source bytes to that location. The
crosswalk in §1.1 places each at its owner.

### 3.1 `source_cache` is a term an adapter accepts

Part 03 §11.2's vocabulary gains one term:

| term | what a build passes |
|---|---|
| `source_cache` | the absolute path of the build's **source-cache location** (§3.2), a directory in which an adapter may keep entries, each the bytes of one object it read from a store (§3.3), for later builds |

`source_cache` is the one term `accepts` may name: an adapter MUST NOT name any other term of
Part 03 §11.2's list, or a term a protocol requires, in `accepts`, and MUST NOT name `source_cache`
in `needs`. A build MUST refuse a declaration whose `needs` names `source_cache`, naming the adapter,
before it opens any source. An adapter that keeps entries names the term in `accepts`, since a build
supplies it to no other adapter.

A build that has a source-cache location MUST supply it as `source_cache` to every adapter naming
the term in `accepts`. A build that has none supplies the term to no adapter and MUST NOT refuse a
recipe for lacking one; the refusal of a term a recipe cannot fill does not reach `source_cache`. An
adapter supplied no `source_cache` reads its source (§3.5).

### 3.2 A build's source-cache location persists

A build takes its source-cache location from its own configuration. A build MUST supply as
`source_cache` only a directory the adapter can write that lies outside the root of the packet being
built and outside every location the build supplies for a delivery (Part 05 §2), and MUST create
the directory where it is absent. A build whose configuration names no such directory has no
source-cache location. A build MUST NOT empty or remove the location or remove an entry from it,
whether the build publishes, refuses, or fails.

The location is not a delivery location: a build reads no delivery from it, and Part 05 §2's rules
that a build supplies a delivery location empty and that an adapter does not rely on what one held
do not govern it. Builds at different packet roots MAY share one location. Removing entries outside
any build, to bound the location's size, is an implementation's matter.

### 3.3 An adapter reads an entry only for the bytes the store reports now

An **entry** is the whole of one object's bytes, kept in a source-cache location with the object's
URI and the entity tag the store reported in the response that carried those bytes. An adapter's
**run** is its execution for one build. How an entry is named and stored in the location is an
implementation's own, and one implementation need not find another's entries.

An adapter MUST NOT write an entry for an object whose response carried no entity tag. Before it
first reads an object's entry in a run, an adapter MUST obtain that object's current entity tag from
the store, and it MUST read an entry only in place of an object whose URI and current entity tag
equal the entry's. An adapter that cannot obtain a current entity tag reads no entry for that object.
Neither a build nor a validator observes an entry, so no build or validator verifies these
obligations; an implementation's own tests are their evidence.

### 3.4 An entry is published whole and then left in place

An adapter MUST make an entry readable only once all its bytes are in place, and MUST NOT make it
readable where it would replace a readable entry; an adapter that finds its entry already published
discards its own copy. Once an entry is readable, an adapter MUST NOT change, replace, or remove it.
The first entry published for a URI and entity tag therefore stands, and a reader never sees the
entry it opened replaced. No build or validator verifies these obligations.

### 3.5 An adapter keeps source bytes across builds only as entries

An adapter MUST NOT read during a build anything kept from before that build began that holds bytes
read from a source or is derived from them, except an entry §3.3 lets it read from the source-cache
location the build supplied it. Reading the source itself, at the `root` the build supplied, is not
such a read, so an adapter complies in every case by reading its source. Within a build, an adapter
MAY keep and reuse what it reads wherever it chooses. No build, validator, or other tool verifies this
obligation, since none observes where an adapter keeps what it reads.

## 5. Consequence

Packet bytes and packet conformance are unchanged, and no packet is rebuilt. A build with a warm
source-cache location publishes the packet a build with a cold one would, since an entry is read
only for the bytes the store reports now, and `core.source_files` rows name a source as the recipe
states it and never the location. A build that cannot reach a store to obtain an entity tag cannot
read that store's entries either, so a cache does not make a build possible offline. Revalidation
costs one metadata request per object read from an entry, once per run.

Every existing adapter declaration stays valid, since naming `source_cache` is needed only by an
adapter that keeps source bytes across builds. An adapter that keeps them anywhere else, as every
store-reading adapter of the reference writer and the AIND package now does through the environment
variable, conforms only once it keeps them as entries in the supplied location or reads through. A
recipe does not set the location: a declared name resolves to a term before an option
(Part 03 §11.2), so `source_cache` in a declaration always names the term.

No accepted clause is superseded. R119 §3.1's bar on a term in `accepts` and R119 §3.4's refusal of
a declaration accepting one gain the `source_cache` exception, and their ledger entries gain notes.
R119 §3.3's rule that a build applies no facility of its own to an adapter not naming its carrier
stands, and the cache now satisfies it. R134 §7's deferred cache location is settled without
amending R134 §3.4, which confined the delivery rule to a delivery. Four ledger destinations naming
Part 03 §11.2 by number, from R116 §3.1 and R119 §§3.1–3.3, move to `ew-build-supplied-values`.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged; no concept's meaning changes. | None required. |
| logical prose and registry | Unchanged; `core.source_files` keeps its declaration, and its `sha256` column, which a cache neither reads nor fills, is outside this decision. | None required. |
| physical profiles | Part 03 §11.2 gains the `source_cache` row and the exception to its `accepts` and unfillable-term rules; §11.5 refuses `needs` naming the term and lets `accepts` name it; §11's opening names the cache; a new last subsection of §11 states §§3.2–3.5. | `evidence/R<N>.json` names `ew-build-supplied-values`, `ew-adapter-declaration-document`, and `ew-source-cache`. |
| packet manifest and JSON Schemas | Manifest, delivery, and recipe schemas unchanged, since no packet or recipe names the location. `registry/adapter.schema.json` keeps its shape, which already admits any name in `accepts`; its `accepts` description, which says a name there is never a term, names the exception, and the vendored copies regenerate. | `registry/check.py` and the vendoring check. |
| validation and import | Part 05 §3.4's description of `accepts` names the one term, and Part 05 §3.5's refusals of an unfillable term and of a declaration accepting a term gain the exception and the refusal of `needs` naming it. Part 05 §2 is unchanged, since its delivery rule governs a delivery only. | The writer tests below. |
| extensions | Registry content unchanged. The AIND package's `session`, `video`, and `aind_unit_qc` adapters declare `source_cache` in `accepts`, and their generated declaration documents carry it. | The AIND suite, whose declaration tests validate its generated documents. |
| reader, writer, validator, adapters | The writer takes the location from its own configuration and supplies it in the input object; the `ESCAPEWHEEL_SOURCE_CACHE` variable and its `TMPDIR` fallback go; entries are keyed by URI and entity tag and revalidated once per object per run; every fetch route publishes an entry only where none stands, and a later copy is discarded; a store-reading adapter declares the term and reads through where it is absent; and the build refuses `needs` naming it. The reader and validator are unchanged, since neither caches. | Writer and AIND tests below. |
| conformance fixtures and tests | No packet fixture, since a validator cannot observe a cache. Writer tests cover the cases in §6. | `escapewheel-writer` and `escapewheel-aind` suites. |
| revision process and tooling | Ordinary ledger and evidence records, with the notes and destination moves stated above. | `ledger.py` and `evidence.py`. |
| generated publications and developer documentation | The combined specification and heading index regenerate. Part 07 §4's `ACCEPTS` description names the term. The writer README's section saying the specification governs none of this is rewritten, and the writer's code comment citing Part 03 §11.2 and the repository TODO's cache item are revised. | `verify.py`. |

## 6. Conformance and implementation evidence

Each clause is `applied` by canonical anchor: §3.1 at `ew-build-supplied-values`,
`ew-adapter-declaration-document`, `ew-source-declarations`, `ew-recipe-check`, and
`ew-reference-object-model`; and §§3.2–3.5 at `ew-source-cache`.

Writer tests distinguish the new rules from the current ones:

- a declaration naming `source_cache` in `accepts` passes the recipe check, where it is now refused
  as a term, and one naming it in `needs` is refused, naming the adapter;
- an adapter accepting `source_cache` finds it in its input object with no environment variable
  set, one not accepting it receives none, and a build with no location supplies none and builds;
- an object whose entity tag changes at a store double after it was cached is fetched again, and the
  packet carries the new bytes, where the current writer reads the old entry;
- a build with a warm location and one with a cold location publish packets with identical rows,
  `core.source_files` included;
- an object whose store double reports no entity tag is read through and leaves no entry;
- two processes fetching one object leave the entry the first published, unchanged, and no copy
  of the second's, and a fetch killed before publication, by any fetch route, leaves nothing
  readable as an entry;
- the location and every entry remain after a published build and after a refused one;
- a configured location inside the packet root or a delivery location is supplied to no adapter,
  and the build proceeds as one with no location; and
- a build with no location, run twice against one store double, fetches every object both times,
  where the current writer reads the second build's objects from `TMPDIR`.

The positive case beside them is an adapter naming no `source_cache`, which reads through and is
refused nothing, as today. §3.5 has no negative case a tool can run, because no tool observes where
an adapter keeps what it reads; the last writer test checks only the reference writer's own
fallback. §§3.3 and 3.4 are checked by the reference implementation's tests against a store double,
since the entry layout is its own.
