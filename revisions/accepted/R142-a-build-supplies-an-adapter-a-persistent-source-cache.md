# A Build Supplies an Adapter a Persistent Source Cache, and Kept Source Bytes Are Used Only While Current

| | |
|---|---|
| **Status** | **Accepted** 2026-09-25 |
| **Based on** | `782dbf811f90f8741e1dc735d326996a69df0d36` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 03 §§11, 11.2, and 11.5, and a new last subsection of Part 03 §11; Part 05 §§3.4 and 3.5; Part 07 §4 |
| **Depends on** | R119 §§3.1, 3.3, and 3.4; R134 §3.4; R135 §3.2; R136 §3.6 |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4 |

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
under it a directory outside the packet root that no build empties. Wherever an adapter keeps source
bytes across builds, it uses them only after confirming in the same run that the source still holds
them. In the supplied directory, each storage format keeps to a subdirectory of its own and
publishes only complete data. How a format lays out, keys, publishes, and evicts what it keeps
stays an implementation's, and a layout that several implementations share is left to a later
decision. `core.source_files`, including its `sha256` column, is outside the decision.

The change is structural because it replaces rules inside Part 03 §§11.2 and 11.5 and Part 05 §3.5:
the bar on a term in `accepts`, the refusal of a term a recipe cannot fill, and the refusal of a
declaration accepting a term. Appended sections would leave each rule standing beside its exception.
The location and the rules for what adapters keep there form one new subject, appended as the last subsection of Part 03 §11.

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
| none | add | a new last subsection of Part 03 §11, "The source cache" (`ew-source-cache`) | the location's properties, when kept source data may be used, and how formats share the location | §§3.2–3.4 |

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
from another implementation no location and no rule for trusting what it kept.

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
within the timestamp's one-second resolution, so a modification time confirms nothing. An entity
tag, a full-object checksum, and a version identifier each change when the bytes do, on the sources
§2.5 measured: an S3 single-part `ETag` is the MD5 of the bytes. How a server forms its tag is its
own, and a common web server forms one from modification time and length, so a rule naming the
entity tag relies on the source to change it; the rule says so rather than invoking RFC 9110's
weak and strong tags, which do not settle how a strong tag is formed. A version-pinned URI never
names two contents, so data kept from one needs no confirmation, and a build reading only such URIs
can use kept data offline.

Specifying an entry format, keyed by URI and entity tag, published without replacement and never
removed, was considered and set aside. No build or validator observes an entry, and one
implementation's entries are private to it, so the format would bind every implementation to a
protocol that buys no interoperability; it would confine caching to whole objects, excluding the
block caching a remote HDF5 read relies on; forbidding any other persistent cache would reach the
caches of libraries an adapter does not control; and, with no check of an entry's bytes, a
truncated or corrupt entry that no adapter may remove would stand for good. The rule this revision
keeps is the one those details served: kept source data is used only while the source still holds
it.

A layout that several implementations share, so that adapters from different packages reuse one
another's fetches, is deferred. Its likely form is content-addressed, as the OCI image layout
stores blobs under `blobs/<algorithm>/<digest>` and the Hugging Face Hub cache is shared by several
libraries: blobs named by the SHA-256 of their bytes, which any reader can verify and a reader may
remove on a mismatch, beside small references from a URI, a confirming value, and an optional byte
range to a blob. Today every store-reading adapter in the writer and AIND packages opens stores
through one module and so already shares one cache, so the shared layout would pay only once an
adapter from another implementation exists. Reserving subdirectory names that begin `cache-v` for
layouts this specification defines lets that layout arrive as one more tenant of the location.

A lock per format or per location would outlive a killed build, and publishing only complete data
by a rename or a hard link needs none. Within its own subdirectory a format may let the first of two
concurrent publications stand, which never replaces a file a reader holds open and which NFS and
Windows both favour, or the last; that choice, like eviction, is the format's. Recording which
version of each object a build read would need a `core.source_files` row per object, which R135
§2.5 rejected for requiring a delivery field every out-of-process adapter fills.

### 2.7 Feasibility and overlap

Every store-reading adapter in both packages already resolves its root through one function, and the
writer already builds the input object Part 03 §11.2 defines, so the location travels as one more
member of it. Obtaining an object's current entity tag costs one request per object per run, which
§2.5 prices at about 50 s for one build's 2,617 objects sequentially by `HeadObject`; a listing of
a known prefix reports the entity tags of up to 1,000 objects per request, and a conditional `GET`
confirms and refetches in one request. A format publishing without replacement has a primitive on
the filesystems measured: on this workstation's data disk, an NTFS volume mounted through FUSE,
`link(2)` publishes a new name and fails with `EEXIST` onto an existing one, while `renameat2` with
`RENAME_NOREPLACE` fails with `EINVAL` even onto a new name.

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

Four subsections add the `source_cache` term and how an adapter declares it, set the properties of
the location a build supplies under it, say when an adapter may use source data kept from before a
run, and let storage formats share the location. The crosswalk in §1.1 places each at its owner.

### 3.1 `source_cache` is a term an adapter accepts

Part 03 §11.2's vocabulary gains one term:

| term | what a build passes |
|---|---|
| `source_cache` | the absolute path of the build's **source-cache location** (§3.2), a directory in which an adapter may keep what it reads from a source for later builds (§§3.3–3.4) |

`source_cache` is the one term `accepts` may name: an adapter MUST NOT name any other term of
Part 03 §11.2's list, or a term a protocol requires, in `accepts`, and MUST NOT name `source_cache`
in `needs`. A build MUST refuse a declaration whose `needs` names `source_cache`, naming the adapter,
before it opens any source. An adapter that keeps source data in the location names the term in
`accepts`, since a build supplies it to no other adapter.

A build that has a source-cache location MUST supply it as `source_cache` to every adapter naming
the term in `accepts`. A build that has none supplies the term to no adapter and MUST NOT refuse a
recipe for lacking one; the refusal of a term a recipe cannot fill does not reach `source_cache`. An
adapter supplied no `source_cache` reads its source or keeps data elsewhere, under §3.3.

### 3.2 A build's source-cache location persists

A build takes its source-cache location from its own configuration. A build MUST supply as
`source_cache` only a directory the adapter can write that lies outside the root of the packet being
built and outside every location the build supplies for a delivery (Part 05 §2), and MUST create
the directory where it is absent. A build whose configuration names no such directory has no
source-cache location. A build MUST NOT empty or remove the location or remove anything in it,
whether the build publishes, refuses, or fails.

The location is not a delivery location: a build reads no delivery from it, and Part 05 §2's rules
that a build supplies a delivery location empty and that an adapter does not rely on what one held
do not govern it. Builds at different packet roots MAY share one location. Removing what the location
holds outside any build, to bound its size, is an implementation's matter.

### 3.3 An adapter uses kept source data only while the source still holds it

An adapter's **run** is its execution for one build. **Kept source data** is anything an adapter
uses in a run, in place of reading its source, that holds bytes read from a source before the run
began or is derived from such bytes, wherever it is kept and whatever keeps it.

An adapter MUST NOT use kept source data in a run unless, during that run, it has confirmed that the
source still holds the bytes the data holds or was derived from, or the URI those bytes were read
from names content that cannot change, such as an object version a store identifies. An adapter
confirms that a source still holds bytes only by comparing a value the source reports for the
object now, an entity tag, a full-object checksum, or a version identifier, with the same value
recorded when the bytes were read; a modification time, with or without a size, confirms nothing.
An adapter relying on an entity tag relies on the source to change the tag when the bytes change.
An adapter that cannot confirm reads its source, and within a run it MAY reuse what it read in that
run wherever it keeps it. No build or validator verifies this obligation, since neither observes
what an adapter keeps; an adapter complies in every case by reading its source.

### 3.4 Storage formats share a source-cache location by subdirectory

A **storage format** is the layout in which an implementation keeps data in a source-cache location.
An adapter MUST keep what it stores in a source-cache location under one subdirectory of it, named
by an identifier of its storage format that the format's implementation controls, such as a package
or domain name it holds, and MUST NOT change or remove anything outside that subdirectory. A name
beginning `cache-v` is reserved for a storage format this specification defines, and an adapter MUST
NOT use one for any other. An adapter MUST NOT make data it stores there readable to another run
until the data is complete.

An adapter SHOULD keep the source data it keeps across builds only in the source-cache location the
build supplied it. Before using kept bytes, it SHOULD compare their size, and their full-object
checksum where the source reports one, with the source's, and it MAY remove from its own
subdirectory data that fails that comparison. How a storage format names, publishes, replaces, and evicts what it
keeps is the format's own. No build or validator verifies these obligations, since neither observes
the location's contents.

## 5. Consequence

Packet bytes and packet conformance are unchanged, and no packet is rebuilt. A build with a warm
source-cache location publishes the packet a build with a cold one would, since kept data is used
only while the source still holds it, and `core.source_files` rows name a source as the recipe
states it and never the location. A build that cannot reach a store cannot confirm what it kept from
that store, so a cache makes a build possible offline only for version-pinned URIs. Confirmation
costs at least one request per object used from kept data, once per run, or one listing request per
thousand objects under a known prefix.

Every existing adapter declaration stays valid, since naming `source_cache` is needed only by an
adapter that keeps source data in the location. Every store-reading adapter of the reference writer
and the AIND package now keeps data keyed on the object's path alone, which §3.3 forbids it to use,
and conforms once it confirms what it kept before using it or reads its source. Keeping that data
through the environment variable and its `TMPDIR` fallback departs from §3.4's recommendation and is
already a facility R119 §3.3 forbids a build to apply. A
recipe does not set the location: a declared name resolves to a term before an option
(Part 03 §11.2), so `source_cache` in a declaration always names the term.

No accepted clause is superseded. R119 §3.1's bar on a term in `accepts` and R119 §3.4's refusal of
a declaration accepting one gain the `source_cache` exception, and their ledger entries gain notes.
R119 §3.3's rule that a build applies no facility of its own to an adapter not naming its carrier
stands, and a cache supplied under the term satisfies it. R134 §7's deferred cache location is
settled without amending R134 §3.4, which confined the delivery rule to a delivery. Four ledger destinations naming
Part 03 §11.2 by number, from R116 §3.1 and R119 §§3.1–3.3, move to `ew-build-supplied-values`.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged; no concept's meaning changes. | None required. |
| logical prose and registry | Unchanged; `core.source_files` keeps its declaration, and its `sha256` column, which a cache neither reads nor fills, is outside this decision. | None required. |
| physical profiles | Part 03 §11.2 gains the `source_cache` row and the exception to its `accepts` and unfillable-term rules; §11.5 refuses `needs` naming the term and lets `accepts` name it; §11's opening names the cache; a new last subsection of §11 states §§3.2–3.4. | `evidence/R<N>.json` names `ew-build-supplied-values`, `ew-adapter-declaration-document`, and `ew-source-cache`. |
| packet manifest and JSON Schemas | Manifest, delivery, and recipe schemas unchanged, since no packet or recipe names the location. `registry/adapter.schema.json` keeps its shape, which already admits any name in `accepts`; its `accepts` description, which says a name there is never a term, names the exception, and the vendored copies regenerate. | `registry/check.py` and the vendoring check. |
| validation and import | Part 05 §3.4's description of `accepts` names the one term, and Part 05 §3.5's refusals of an unfillable term and of a declaration accepting a term gain the exception and the refusal of `needs` naming it. Part 05 §2 is unchanged, since its delivery rule governs a delivery only. | The writer tests below. |
| extensions | Registry content unchanged. The AIND package's `session`, `video`, and `aind_unit_qc` adapters declare `source_cache` in `accepts`, and their generated declaration documents carry it. | The AIND suite, whose declaration tests validate its generated documents. |
| reader, writer, validator, adapters | The writer takes the location from its own configuration and supplies it in the input object; the `ESCAPEWHEEL_SOURCE_CACHE` variable and its `TMPDIR` fallback go; kept data is stored under the writer's own subdirectory of the location, keyed so it can be confirmed by URI and entity tag, confirmed once per object per run, and published only when complete by every fetch route; a store-reading adapter declares the term and reads through where it is absent; and the build refuses `needs` naming it. The reader and validator are unchanged, since neither caches. | Writer and AIND tests below. |
| conformance fixtures and tests | No packet fixture, since a validator cannot observe a cache. Writer tests cover the cases in §6. | `escapewheel-writer` and `escapewheel-aind` suites. |
| revision process and tooling | Ordinary ledger and evidence records, with the notes and destination moves stated above. | `ledger.py` and `evidence.py`. |
| generated publications and developer documentation | The combined specification and heading index regenerate. Part 07 §4's `ACCEPTS` description names the term. The writer README's section saying the specification governs none of this is rewritten, and the writer's code comment citing Part 03 §11.2 and the repository TODO's cache item are revised. | `verify.py`. |

## 6. Conformance and implementation evidence

Each clause is `applied` by canonical anchor: §3.1 at `ew-build-supplied-values`,
`ew-adapter-declaration-document`, `ew-source-declarations`, `ew-recipe-check`, and
`ew-reference-object-model`; and §§3.2–3.4 at `ew-source-cache`.

Writer tests distinguish the new rules from the current ones:

- a declaration naming `source_cache` in `accepts` passes the recipe check, where it is now refused
  as a term, and one naming it in `needs` is refused, naming the adapter;
- an adapter accepting `source_cache` finds it in its input object with no environment variable
  set, one not accepting it receives none, and a build with no location supplies none and builds;
- an object whose entity tag changes at a store double after it was kept is fetched again, and the
  packet carries the new bytes, where the current writer reads the old copy;
- a build with a warm location and one with a cold location publish packets with identical rows,
  `core.source_files` included;
- an object whose store double reports no entity tag, checksum, or version is read from the store
  in every run, and a version-pinned URI kept once is used again with the store double unreachable;
- the writer keeps everything under its own subdirectory and leaves a file placed beside it
  untouched, and a fetch killed before publication, by any fetch route, leaves nothing readable;
- a kept object whose size differs from the store double's is not used;
- the location and everything in it remain after a published build and after a refused one;
- a configured location inside the packet root or a delivery location is supplied to no adapter,
  and the build proceeds as one with no location; and
- a build with no location, run twice against one store double, fetches every object both times,
  where the current writer reads the second build's objects from `TMPDIR`.

The positive case beside them is an adapter naming no `source_cache`, which reads its source and is
refused nothing, as today. §§3.3 and 3.4 have no negative case a build or validator can run, because
neither observes what an adapter keeps; the reference implementation's tests against a store double
are their evidence.
