# R75 — Determinism Is Logical, Not Byte-Identical

| | |
|---|---|
| **Status** | **Accepted** 2026-09-04 |
| **Amends** | `05` §? (the fifth property of a conforming import) |
| **Depends on** | R52 (a packet-owned resource records a digest) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

`05` requires a conforming import to *"produce byte-identical output from two runs over the same
sources"*. No conforming importer can, and the reference one does not.

### 1.1 The packet timestamps itself

Every manifest carries `created_at` and `validated_at`, and every `core.processing_runs` row
carries `started_at`. Two runs a second apart differ in all three, so the requirement is
unsatisfiable by any packet that records when it was made — which `04` requires of all of them.

### 1.2 Encoders are not required to be stable

Parquet and Zarr writers are free to change how they encode identical logical content between
library versions: a dictionary threshold, a compression level default, a page boundary. Two
importers reading the same sources through different library versions produce the same rows and
different bytes, and both are correct.

Requiring otherwise makes conformance depend on a dependency's version, which nothing in this
standard declares.

### 1.3 What the requirement was reaching for

The property worth having is that an import is a **function of its inputs**: the same recipe over
the same sources yields the same rows, the same values, the same assigned identifiers and the same
declared ordering. That is what makes a packet reproducible, an amendment predictable, and two
implementations comparable. None of it needs identical bytes.

## 2. Decision

### 2.1 Logical determinism is normative

> For the same recipe, the same source bytes, and the same declared normalization, an importer
> **MUST** produce the same canonical rows, the same values, the same assigned identifiers, the
> same resource identities, and the same declared physical ordering.
>
> Identifier assignment **MUST** be a function of the recipe and the sources, never of wall-clock
> time, iteration order over an unordered collection, or the order in which a filesystem listed a
> directory.

R53 §2.5 already requires assigned identifiers to be stable for the life of a packet. This
requires two builds to agree about them in the first place.

### 2.2 Byte determinism is a build property, not a conformance one

> An implementation **MAY** offer a deterministic-build mode that pins volatile timestamps,
> encoder settings and library versions so repeated runs produce byte-identical packet-owned
> resources. A packet **MUST NOT** be judged non-conforming for lacking one.

Where such a mode exists it belongs in `07` and in the implementation's own tests, which is where
a regression against a pinned build is a useful signal and where the pinning is possible.

### 2.3 What a digest then means

R52's recorded `sha256` says what a packet's bytes **are**, not what a second build would produce.
Two conforming builds of one dataset may record different digests for the same rows, and neither
is wrong; comparing them answers "are these the same bytes", never "did these come from the same
sources".

A consumer wanting the second question compares the canonical rows, or the recipe recorded in
`core.processing_runs.parameters`.

## 3. What this does not change

- **No field, no column, no rule.** One property of a conforming import is replaced by two.
- **No weakening of reproducibility.** §2.1 is the stronger half of what `05` asked for, and it is
  the half that was achievable.
- **No change to R52 or R35.** A digest still pins the bytes a packet holds, and R35 still bounds
  revalidation by immutability.
- **No change to the reference implementation**, which already satisfies §2.1 and never satisfied
  the struck requirement.

## 4. Open

- **Whether a canonical row fingerprint is worth defining.** §2.3 says a consumer comparing two
  builds should compare rows; nothing says how, and a digest over canonically ordered rows would
  make it one value rather than a join. It is a different construction from R52's and would need
  its own normalization rules, so it waits for something that wants it.
