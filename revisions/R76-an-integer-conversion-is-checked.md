# R76 — An Integer Conversion Is Checked

| | |
|---|---|
| **Status** | **Proposed** 2026-09-04 |
| **Amends** | `02` §5 (the type system), `05` §? (what an importer must refuse) |
| **Depends on** | R53 (an identifier is an integer), R45 (a tick is a coordinate) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R53 makes every identifier an `int32`, R45 makes every tick a signed `int64`, and `02` §5 pins the
width of both. Nothing says what happens when a source value does not fit.

### 1.1 Silence is the default in every language this format targets

NumPy wraps: `np.int32(2**31)` is `-2147483648`, and casting an `int64` array to `int32` truncates
each element without a warning. Arrow's `cast` will raise, but `pa.array(values, type=...)` on
pre-converted NumPy data has already lost the bits. A packet built that way is internally
consistent, passes every rule in the registry, and joins rows that were never related.

R53 §2.1's range argument — 2.1 billion values against 6,781 units — is why this has not happened.
It is not why it cannot.

### 1.2 The failure is undetectable after the fact

A wrapped identifier is a valid `int32`. It satisfies not-null, it satisfies uniqueness unless it
happens to collide, and its foreign key resolves if the wrapped value happens to name a row. No
Tier 1 or Tier 2 check can see it, because by the time the rules run the evidence is gone.

This is the class R12 §4 already identifies: a property the data cannot testify to, which
therefore belongs in the writer rather than in SQL.

### 1.3 It generalises past identifiers

The same hazard covers a tick, a structural index, a sequence position, and interval arithmetic. A
duration computed as `stop - start + 1` at `INT64_MAX` overflows; a sample index re-based by a
writer that R45 §3 forbids would too.

## 2. Decision

### 2.1 A conversion that would not fit fails

> A writer or importer **MUST NOT** use wraparound, truncating or saturating semantics for a value
> whose R48 role is `identifier`, `coordinate`, `structural_index` or `sequence_position`, nor for
> arithmetic over interval bounds.
>
> A conversion, cast, assignment or arithmetic operation whose result would fall outside the
> declared type **MUST** fail before the value is written, naming the column and the value.

Failing is the whole requirement. What a writer does about it — refusing the build, assigning its
own identifier and recording the mapping — is not this revision's business, except that §2.3
forbids one answer.

### 2.2 The declared width is the writer's obligation, not the source's

R53 §2.4 already requires `int64` for an identifier whose distinct values may exceed `int32`. A
writer meeting a source it cannot represent at the declared width has two conforming answers:
declare the wider type, or assign its own identifier. It has no third.

### 2.3 A carried identifier is never silently re-numbered

R53 §2.3 makes a carried identifier the source's own number. A writer that cannot represent one
**MUST NOT** substitute a different number under the same column: the column would then hold a
value the source never used, indistinguishable from one it did.

Where a writer assigns instead, the identifier's identity becomes `assigned`, its owner carries
the `*_name` R53 §2.3.1 requires, and the source's own value is what that name holds.

### 2.4 Checked where the check is cheap

The obligation is on the boundary, not on every expression: a writer converts a source's values
once, on the way in, and everything after that is already within the declared type. A validator
**MUST NOT** be required to re-derive it, because §1.2 is that it cannot.

## 3. What this does not change

- **No column, no type, no rule.** One prohibition and one obligation on a writer.
- **No change to R53's widths.** `int32` for identifiers stands, with §2.4's existing escape to
  `int64` where the range needs it.
- **No change to what a validator does.** §2.4 is explicit that this is not checkable from a
  packet, which is R12 §4's line.
- **No performance cost worth measuring.** A range test per source column on the way in, against
  a build that hashes 1.2 GB.

## 4. Open

- **Whether the reference implementation should assert it, or rely on Arrow.** `pyarrow.array`
  with an explicit type raises on overflow for Python integers and does not for a pre-converted
  NumPy array, so where a source hands over NumPy the check has to be explicit. Which adapters
  those are is an implementation question this revision does not settle.
