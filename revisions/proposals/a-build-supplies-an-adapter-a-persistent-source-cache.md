# A build supplies an adapter a persistent source cache keyed by URI and store identity

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-24 |
| **Based on** | `92c3a2ca5ec8f012895a589c1fac6f16f87040bb` |
| **Decision domain** | specification |
| **Affects** | Part 03 §11.2 (a new supplied term, and the rule that `accepts` names no term); Part 05 §2 (the delivery-location rule); Part 07 §4's informative object model; the writer's store module, recipe loading and delivery entry point; the AIND package's adapter declarations; the writer README |

## 1. Problem

An adapter reading a source on an object store keeps the objects it fetched in a local cache, so
that a second read of one object, in the same build or a later one, costs no transfer. The
specification says nothing about that cache. R134 §3.4 confined its delivery rule to deliveries and
deferred the cache in its §7, noting that a later revision would settle the location's lifetime and
how an adapter declares a term it can run without.

The reference writer fills the gap with an environment variable, `ESCAPEWHEEL_SOURCE_CACHE`, and a
cache keyed on the object's path alone. Three consequences follow. An object that changes at the
store is read from the old entry indefinitely, so a build can publish a packet from bytes the
source no longer holds and record nothing that shows it. The location reaches an adapter outside
the one JSON object Part 03 §11.2 makes the channel for everything a build supplies, which that
section's closed vocabulary does not admit, and an adapter written in another language has no way
to find it. And where nothing sets the variable, the cache falls back to `TMPDIR`, which on a host
whose `/tmp` is a tmpfs holds fetched objects in memory no cgroup limit bounds.

## 2. Evidence

Observations were read from the writer and AIND packages and from fsspec 2026.7.0, the version in
the writer's lock, at the recorded baseline. Cache contents were counted on this workstation on
2026-09-24. Store responses were requested anonymously from `aind-open-data` in `us-west-2` for
three known objects; no prefix was listed.

### 2.1 One module chooses the location, and an environment variable carries it

Every adapter that reads a store opens its root through `source_root` in
`escapewheel_writer.sources.store`: the writer's `sorter`, `waveforms`, `lfp`, `nwb`, `sync`,
`harp` and `openephys` adapters and the AIND package's `session`, `video` and `aind_unit_qc`. A
local root resolves to a path and is never cached. A store root is opened through fsspec's
`simplecache`, which the module replaces with a subclass, `WholeObjectCache`, and the cache
directory comes from `cache_directory()`: the variable where set, otherwise
`$TMPDIR/escapewheel-source-cache`.

`Recipe.load` calls `cache_beside`, which sets the variable to `.escapewheel-source-cache` in the
packet's parent directory unless an operator already set it. An adapter the build runs out of
process inherits the environment, and `escapewheel deliver` opens the supplied `root` through the
same `source_root`, so the variable is the only channel the location has. The module's own comment
says the variable is not a Part 03 §11.2 term. That section forbids a build to apply a facility of
its own to an adapter that does not name the option carrying it; the reference build applies this
one to every adapter, and none names it.

The validator and reader read stores without any cache, and the LFP adapter's external digests go
through the validator's store module, uncached. `zarr_compat` and the `waveforms` adapter read chunk
bytes through the cached root, as `SourceStore` hands it to them.

### 2.2 An entry is keyed on the object's path alone, and a changed object is never re-read

`simplecache` names an entry by the SHA-256 of the object's path without its scheme, so
`s3://aind-open-data/<asset>/session.json` is cached as the SHA-256 of
`aind-open-data/<asset>/session.json`. A probe reading that object through `source_root` created
exactly that entry. `SimpleCacheFileSystem` sets `cache_check`, `expiry_time` and `check_files` to
false and keeps no metadata, and its `_check_file` tests only whether the entry exists. Once an
object is cached, no build sends another request for it, so an object replaced at the same key
is served from the old entry in every later build that shares the directory. Nothing records the
entry's age or what the store held when it was fetched.

### 2.3 Concurrent builds share entries without a lock

`WholeObjectCache` fetches into `<entry>.<pid>.part` and renames it onto the entry, so on one host
an entry appears whole or not at all, and two builds fetching one object each publish a complete
copy. Two builds whose packets share a parent directory share a cache, which is the ordinary case
for rebuilds. Three hazards remain:

- fsspec's `cat` route fetches straight into the entry's final name, bypassing the rename; the
  adapters' reads observed here go through `open`, which the subclass covers;
- two hosts sharing a network filesystem can run processes with the same pid and write one `.part`
  file (inference, not reproduced); and
- `cache_beside` sets a process-wide variable, so two recipes loaded in one process move the
  location for every root resolved after the second load.

A build killed between fetch and rename leaves a `.part` file that no later read mistakes for an
entry. None was found on this machine.

### 2.4 `core.source_files` records the root, and a cached read changes nothing in it

Under Part 05 §7 the writer records one `core.source_files` row per distinct recipe `root`, with
`uri` as the recipe states it and `sha256`, `size_bytes`, `format` and `modified_at` null. A store
root is recorded as its `s3://` URI whether its objects came from the store or the cache. A packet
built from a stale entry therefore carries the same rows as one built from current bytes.

### 2.5 Three real recipes read one or two store roots, and their caches hold duplicates

| recipe | sources with an `s3://` root | of those, run out of process | distinct store roots |
|---|---|---|---|
| `776259-packet/recipe.toml` | `session`, `sorter`, `waveforms`, `aind_unit_qc` | `session`, `aind_unit_qc` | 1 |
| `786867-packet/recipe.toml` | `session`, `sorter`, `waveforms`, `aind_unit_qc` | `session`, `aind_unit_qc` | 1 |
| `df-packet/recipe.toml` | `waveforms`, `aind_unit_qc` | `aind_unit_qc` | 1 |

`df-packet` and `786867-packet` read the same sorted asset. Every NWB root in the three recipes is
local, so no NWB object is read from a store. Five of the ten store-rooted sources run out of
process and receive the cache location only through the environment.

Four cache directories hold entries:

| directory | entries | bytes | written |
|---|---:|---:|---|
| `/mnt/Data/786867-packet/.escapewheel-source-cache` | 2,617 | 3,238 MB | 2026-09-24, 14:00–15:00 |
| `/mnt/Data/.escapewheel-source-cache` | 2,244 | 3.6 MB | 2026-09-24, 15:00–16:00 |
| `/tmp/escapewheel-source-cache` (tmpfs) | 1,589 | 3.8 MB | 22 on 2026-09-16, 1,567 on 2026-09-24 |
| `/mnt/Data/776259-packet/.escapewheel-source-cache`, `/mnt/Data/df-packet/.escapewheel-source-cache` | 0 | 0 | — |

The 786867 entries were written by one build, logged in `build-maint.log`, that ran `sorter` over
the sorted asset and failed at 190 s, shortly after `waveforms` began. Ten of its 2,617 objects
exceed 10 MB and hold 3,154 MB, 97% of the bytes; the median entry is 2 KB. That count is the best
available measure of what one build reads from a sorted asset, and it is a lower bound, since
`session` and `aind_unit_qc` never ran.

The same objects sit in several caches. 1,524 of the tmpfs cache's 1,589 entries are also in
`/mnt/Data/.escapewheel-source-cache`, and 1,051 of the 786867 entries are in the tmpfs cache.
`df-packet` and `786867-packet` read one asset through two caches, because the default location is
per packet parent rather than per machine. The 1,567 tmpfs entries written today show that some
process read a store with the variable unset, which leaves the fallback in use.

### 2.6 An anonymous read sees an entity tag, a version ID and sometimes a checksum

A `HeadObject` with checksum mode enabled on `session.json`, `subject.json` and `rig.json` under the
786867 sorted asset returned, for each, `ContentLength`, `ETag`, `LastModified`, `VersionId`,
server-side encryption `AES256`, and a full-object `ChecksumCRC32`. The bucket reports versioning
`Enabled`. `GetObjectAttributes` was refused as `AccessDenied` without credentials. A `GetObject`
returned the same `ETag`, `VersionId` and CRC32 with the bytes; its `ETag` equals the MD5 of those
bytes, as R136 §2.2 predicts for a single-part SSE-S3 object; and a `GetObject` with a mismatched
`If-Match` failed with `PreconditionFailed`.

Thirty sequential anonymous `HeadObject` requests from this workstation took 18.2 ms median and
22.9 ms at the 90th percentile. One request per object for the 2,617 objects above costs about 48 s
sequentially, against 141 s for the `sorter` source in the same build.

## 3. Desired outcome and constraints

- **A build supplies the location.** Part 05 §2 has an adapter deliver only where a build points it,
  and R135 makes the staging area the build's own. A cache location is supplied the same way, as a
  Part 03 §11.2 term inside the one input object, so an adapter in any language finds it.
- **The location lies outside the packet root and outside the staging area.** A writer may empty
  the staging area when a build begins (Part 05 §2); a file under the packet root that no manifest
  names is a stray no writer may remove (Part 03 §9.5); and a packet root may be an object-store
  prefix (Part 03 §4).
- **The location persists.** A build does not empty or remove it, and Part 05 §2's empty-location
  rule, which exists so a leftover file cannot pass for a delivery, does not apply to it.
- **A hit changes no packet byte.** Part 05 §4.3 and Part 05 §11 have two runs of one recipe over
  the same source bytes produce the same packet. An entry is used only for the bytes the store holds now.
- **Store identity follows R136.** An entity tag is evidence that an object changed in place and
  never a digest of its bytes (Part 04 §5.4). A version ID or a full-object checksum identifies
  bytes more strongly where a store reports one, and an anonymous read of the public bucket sees
  all three except where an object was uploaded without a checksum.
- **Concurrent writers are safe.** Builds at different packet roots, and several adapters of one
  build in and out of process, share one location, and no build holds a lock another could leave
  behind.
- **The specification governs only what interoperability needs.** No validator observes a cache
  and no packet names one. What an independent adapter and build need to agree on is the term, the
  location's lifetime, and when an entry may be read; layout, eviction and size remain an
  implementation's.

## 4. Options and tradeoffs

### 4.1 Whether the specification governs the cache

**Leave it to implementations, as now.** Rejected: an adapter from another implementation cannot
find the location, the reference build keeps applying a facility Part 03 §11.2 forbids, and a stale
entry silently changes packet content.

**Fix the keying in the reference writer and specify nothing.** Holds for the reference writer's
own adapters, and fails for any other: the location still travels outside the input object, and a
third-party adapter has no rule saying when it may trust an entry.

**Specify the term, the location's properties and when an entry may be read, and leave layout and
eviction to implementations** (preferred direction).

### 4.2 Where the location lies and who chooses it

**A directory the build chooses from its own configuration, outside the packet root and the
staging area, which it creates where absent and never empties or removes** (preferred direction).

**Name it in the recipe.** Rejected: Part 05 §3.2 records the recipe in the packet, so a machine
path would enter the packet and two builds of one recipe on two machines would differ.

**Under the staging area.** Rejected: a writer may empty the staging area when a build begins, so
nothing persists.

**Under the packet root outside staging.** Rejected: the entries would be strays under
Part 03 §9.5, would not exist where the root is a store prefix, and would travel with every copy of
the packet.

**Have the build prefetch objects into a delivery location.** Rejected: the build would need the
list of objects each adapter reads, which only the adapter knows.

### 4.3 How an adapter declares the term

**`accepts` may name `source_cache`, the one term an adapter can run without** (preferred
direction). A build supplies it to an adapter that accepts it wherever the build has a cache
location, and otherwise supplies nothing; absence means the adapter reads through. This amends
Part 03 §11.2's rule that `accepts` names no term, for this term alone, and keeps its rule that a
term in `needs` is never passed absent.

**Declare it in `needs`.** A build can always fill it by choosing some directory, so no recipe is
refused. The cost is a false declaration, since the adapter can be constructed without it, and a
build then cannot build without a writable persistent location. This is open question 1.

**Supply it to every adapter unconditionally.** Rejected: Part 03 §11.2 has a build supply exactly
what an adapter declares.

**An adapter persists source bytes only in the supplied location** (preferred direction). This
retires the environment variable and the `TMPDIR` fallback. Whatever an adapter buffers within one
run stays its own matter. This is open question 4.

### 4.4 What identifies an entry

**The object's URI and the entity tag the store reported in the response that carried the bytes**
(preferred direction). Before an adapter first uses an entry in a run, it obtains the object's
current entity tag from the store and reads an entry only under the same URI and tag. A changed
object gets a new tag and so a new entry; the stale one is never read again. Taking the tag from the
response that delivered the bytes, or fetching with `If-Match`, closes the race in which an object
changes between the metadata request and the fetch. S3, Google Cloud Storage, Azure Blob Storage
and HTTP servers generally report an entity tag, and a rewrite of identical bytes with a different
part size changes it, which errs toward fetching again. An object whose store reports no tag is not
cached. The cost is one metadata request per object per run, about 48 s sequentially for the 2,617
objects of §2.5.

**The URI alone.** Rejected: §2.2's stale read.

**The URI with `Last-Modified` and size.** Rejected: a rewrite of the same size within the
timestamp's one-second resolution keeps both.

**The URI with a version ID.** A version ID never names two contents, but only a versioned bucket
reports one; `aind-open-data` does. This is open question 2.

**A full-object checksum as the key.** Rejected as the sole key: not every object carries a
full-object checksum (R136 §2.2), a 32-bit CRC does not identify bytes across a cache, and reading
the value needs the same request as the tag.

### 4.5 Concurrency

**An entry appears only whole and never changes after it appears; any writer of one key writes the
same bytes, so either copy may win; no build removes an entry; and a partial fetch never carries an
entry's name** (preferred direction). Rename within the cache's filesystem gives the first two
without a lock. Eviction runs outside every build, and an implementation choosing to evict
concurrently with a build is responsible for not removing an entry an adapter is reading.

**A lock file per entry or per location.** Rejected: a killed build leaves the lock, and
publication by rename needs none.

**Leave concurrency unspecified.** Rejected: builds at different roots share a location in the
ordinary case, and two implementations sharing one directory need the same guarantee.

### 4.6 What the packet records

**Unchanged: a `core.source_files` row names the source URI as the recipe states it and never a
cache path, and a hit changes no packet byte** (preferred direction). Recording which version of
each object a build read would need a row per object, which R135 §2.5 rejected for requiring a
delivery field every out-of-process adapter fills.

R136 left the `sha256` column of `core.source_files`, a free string describing a source root, to
this proposal. A cache neither reads nor fills it, so it stays out of this decision (open question
5).

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged; no concept's meaning changes. |
| logical prose, registry declarations, rules | Unchanged under the preferred direction; `core.source_files` keeps its declaration. Affected only if open question 5 is answered otherwise. |
| physical profiles | Affected: Part 03 §11.2 gains the `source_cache` term, the properties of its location, and when an entry may be read; its rule that `accepts` names no term gains the one exception. |
| packet manifest and schemas | Unchanged. `registry/adapter.schema.json` already admits any name in `accepts`; only its `accepts` description, which says a name there is never a term, changes. The recipe schema is unchanged, since the recipe does not name the location. |
| validation and import | Affected: Part 05 §2 states that a cache location is not a delivery location, that a build reads no delivery from it, and that its empty-location and no-reliance rules do not reach it. |
| extension registries | Unchanged. |
| writer | Affected: the build chooses the location from its own configuration and supplies it in the input object; `cache_beside`, `cache_directory`, the variable and the `TMPDIR` fallback go; entries are keyed by URI and entity tag and revalidated once per object per run; the `cat` route publishes by rename. |
| adapters | Affected: each store-reading adapter in the writer and the AIND package declares `source_cache` in `accepts` and reads through where it is absent. |
| reader, validator | Unchanged; neither caches, and no packet byte changes. |
| existing packets | Unchanged; no rebuild follows from this decision. |
| conformance fixtures and tests | No packet fixture, since a validator cannot observe a cache. Writer tests below. |
| revision tooling | Unchanged. |
| documentation | Affected: Part 07 §4 names the term; the writer README's section saying the specification governs none of this is rewritten. |

Writer tests distinguish the preferred direction from the current behavior:

- an adapter accepting `source_cache` finds it in its input object with no environment variable
  set, and one not accepting it receives none;
- an object whose entity tag changes at a store double after it was cached is fetched again, and the
  packet carries the new bytes, where the current writer reads the old entry;
- a build with a warm cache and one with a cold cache publish identical packets, including
  `core.source_files`;
- two processes fetching one object leave one whole entry, and a fetch killed before its rename
  leaves no entry under the object's name;
- a build leaves the location and every entry in place, including after a refused build; and
- an object whose store reports no entity tag is read through and not cached.

## 6. Open questions

1. **Declaring the term.** Preferred: `accepts` admits `source_cache` alone among terms, absence
   means read through, and a build without a location still builds. Declaring it in `needs` changes
   no declaration rule, but misstates what the adapter can run without and makes a persistent
   location a precondition of every build.
2. **The identity.** Preferred: the entity tag, which every store considered reports and which
   R136 §3.6 already records as change evidence. A version ID where the store reports one is
   stronger and costs the same request, but needs a second rule for unversioned stores.
3. **A shared layout.** Preferred: leave how an entry is named inside the location to
   implementations, so adapters of two implementations sharing a location miss each other's
   entries and never misread them. Fixing the name as a function of URI and tag would let them share
   entries, at the cost of a layout every implementation keeps.
4. **Other persistent caches.** Preferred: an adapter keeps source bytes across runs only in the
   supplied location, which retires the environment variable and the tmpfs fallback §2.5 found in
   use. Permitting other locations leaves the current behavior conforming.
5. **`core.source_files.sha256`.** Preferred: leave it out of this decision, since a cache neither
   reads nor fills it and a row describes a root rather than an object. Renaming it to an
   `{algorithm, value}` digest under R136's functions would be a registry change of its own.

Overlaps: moving Part 03 §11 into its own part would carry the term with it, and a proposal for
packet-owned opaque delivery may add another supplied location to Part 03 §11.2's table; each
appends a row and neither changes the other's. R135 §7's two builds at one packet root remain outside this
decision, which concerns builds at different roots sharing a cache. A reverse-citation query for
Part 03 §11.2 and Part 05 §2 lists 137 citations, most in R134 and R135; incorporation would read
those in the writer, Part 03 and Part 07. This proposal depends on R134 §3.4 for the delivery
boundary it extends, R135 §3.2 for the staging area the location lies outside, and R136 §3.6 for
the standing of an entity tag.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [ ] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.
