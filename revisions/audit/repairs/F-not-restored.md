# Rules the evaluation would not restore

Each rule below was first classed as a plain restoration. A third reading found that other sentences already carry it with force, so the part should not state it again and the ledger entry should say where it is carried.

2 rules, ordered by part and section: Part 03 (2).

Nothing here has been applied. The audit record is [applied-targets.md](../applied-targets.md).

## Part 03

### 1. R129 §3.9 at Part 03 §2 (ew-portable-profile-technologies)

- **The revision decides:** a specialized implementation MAY expose members, objects, bytes, parsing, rendering, or other representation-aware operations without changing the resource's logical kind or the reader floor
- **The part now says:** nothing; the sentence is absent.
- **Text first proposed, rejected:** A specialized implementation MAY expose members, objects, bytes, parsing, rendering, or other representation-aware operations without changing the resource's logical kind or the reader floor.
- **Evaluation:** Do not restore: the permission is already implied by 'need not' in Part 03 §2 and Part 02 §2.3, so a MAY here only describes a possibility, its subject is not a Part 00 actor, and its one substantive claim (logical kind is unchanged) is Part 02 §2.3's. The ledger should keep R129 §3.9 applied at `ew-portable-profile-technologies` with a note that the specialized-implementation permission is carried by those two 'not required' sentences and is not restated.
- **By lens:**
  - *Still decided:* Nothing withdrew it: R143 and R144 add opaque storage and delivery rules and no reader permission, and R129's crosswalk row for Part 03 §2 ('replace with a generated projection and opaque explanation') does not say the sentence is dropped. The clause stands as a record; the question is whether a part may state it.
  - *Contradiction:* None. Part 02 §2.3 already says 'Opaque qualifies only the generic payload model' and 'Generic code is not thereby required to parse, decode, or render its payload', and Part 03 §2 says a reader 'need not retrieve, parse, decode, or render it'; the proposed sentence repeats their consequence.
  - *Exceeds the clause:* It equals the clause except 'the reader floor' for 'the portable reader floor'. An opaque resource maps to no interface and so has no floor, which makes the closing condition empty in the part.
  - *Actor:* 'A specialized implementation' is not a Part 00 §2.4 actor, and 'implementation' is reserved for rules binding every actor alike; the actor is a reader. spec/CONTRIBUTING.md §4 allows a MAY only for 'a permission that would otherwise be uncertain' and not 'merely to describe a possibility': 'need not' in Part 03 §2 and Part 02 §2.3 already leaves no doubt that a reader may do these things.
  - *Checks:* A permission; no check applies and no conformance outcome turns on it.
  - *Placement:* The part that owns the subject of its one substantive claim, that such operations do not change the resource's logical kind, is Part 02 §2.3, which states that kind is the declaration's. Restating it in Part 03 §2 would be a second statement of a Part 02 fact (Part 00 §8).
  - *Implementation and corpus:* Unobservable as a rule. The reference reader exposes an opaque payload's path (`Packet.path` in escapewheel-reader packet.py) and nothing parses or renders one; either behaviour conforms with or without the sentence. No corpus case or validator check is involved.
  - *Wording:* If a reviewer still wants it, the only acceptable form names the reader and drops the floor: 'A reader MAY also expose an opaque payload's bytes or members, or parse or render it; the resource's logical kind is unchanged.' It should follow the 'need not' sentence.

### 2. R129 §3.11 at Part 03 §6.5 (ew-array-metadata-placement)

- **The revision decides:** those physical facts MUST NOT be duplicated merely to make physical validation possible
- **The part now says:** “Self-describing physical facts—version, shape, dtype, chunking, and codec configuration—MUST be obtained from the resource and need not be copied into a table or the manifest.”
- **Text first proposed, rejected:** Self-describing physical facts—version, shape, dtype, chunking, and codec configuration—MUST be obtained from the resource and MUST NOT be duplicated in a table or the manifest merely to make physical validation possible.
- **Evaluation:** Do not restore: the sentence is passive, turns on an unverifiable purpose, and R129's own crosswalk describes the effect as 'need not be copied'; each concrete channel it guards is already closed with force in Part 03 §§2, 6.1 and 6.5, Part 04 §§5.3 and 6 and Part 12 §5. The ledger should keep R129 §3.11 applied with a note that its general 'MUST NOT be duplicated' is carried by those specific prohibitions, and that a determinate ban on registry columns would need a revision.
- **By lens:**
  - *Still decided:* The clause stands, but R129's own structural crosswalk describes the effect on Part 03 §6.5 as 'self-describing physical facts need not be copied', the words the incorporation (cbfbccf3) used, so the part follows the revision's stated disposition and not an accident. R144 moved the adapter half to Part 12 §5 with its MUST NOT intact; R137, R146 and R147 do not touch the sentence.
  - *Contradiction:* No sentence forbids the restoration, but it would sit beside 'Zarr attributes MAY duplicate helpful metadata' in the same paragraph and beside registry columns that legitimately restate facts a payload also holds (`core.array_assets.sample_rate_hz`, `core.media_assets.pts_rate_num`/`pts_rate_den`, any `metadata` column), with only an unverifiable purpose test ('merely to make physical validation possible') separating the permitted from the forbidden.
  - *Exceeds the clause:* The proposed text adds 'in a table or the manifest', which the clause does not say, and drops the clause's Parquet compression and value encoding because §6.5 is an array section; it is therefore both narrower and differently scoped than what was decided.
  - *Actor:* 'MUST NOT be duplicated' is passive and names none of writer, registry document or build, which spec/CONTRIBUTING.md §4 rules out; and no actor can tell whether it complied, because compliance turns on why a copy was made. The style guide requires a requirement to be determinate even where it is not mechanically testable, and this one is not.
  - *Checks:* Nothing can observe a violation of the purpose-conditioned rule. Every determinate channel is already closed and checked: the manifest schema's resource entry is closed, and the registry declares no dtype, shape, chunking, codec or version column on `core.array_assets` or `core.array_dimensions` (confirmed against spec/artifacts/logical_schemas.json).
  - *Placement:* The concrete prohibitions already have owners with force: Part 03 §6.5 ('`core.array_assets` MUST NOT carry dtype or shape'), Part 03 §6.1 ('a packet entry MUST NOT state it'), Part 03 §2 ('A packet entry MUST NOT select or repeat that interface'), Part 04 §6 with the closed manifest schema, Part 04 §5.3 (a validator MUST NOT infer them) and Part 12 §5 (a build MUST NOT require an adapter to restate them). A general ban in §6.5 would be a second, vaguer statement over those.
  - *Implementation and corpus:* The reference implementation and corpus comply with every concrete prohibition: the validator reads version, shape and codecs from the store (escapewheel-validator shim/arrays.py and shim/floors.py) and no table or manifest entry copies them. Whether an extension's column 'duplicates merely to make physical validation possible' is unobservable in code, so no check could be written to honour the restored sentence.
  - *Wording:* A determinate replacement would have to name an actor and drop the purpose test, for example 'A registry document MUST NOT declare a column holding an array's Zarr version, chunking or codec configuration, or a table's Parquet compression or encoding'; that bans more than R129 §3.11 decided and is a new rule for a revision, not a fix.
