# R71 — Canonical Data Is Core and Its Extensions

| | |
|---|---|
| **Status** | **Accepted** 2026-09-04 |
| **Amends** | `00` §3 (the layer table), `00` §4.1, `06` §2 (what analysis must be recomputable from) |
| **Depends on** | R54 (a trial is an interval), R55 (a discriminated reference), R17 (extension registries) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

`00` §3 describes the core layer as *"canonical normalized facts; the sole source of truth"*, and
`06` requires an analysis resource to be recomputable from core — adding that anything **not**
recomputable from core belongs in core.

Both were true when written. R54 made them false and nothing propagated the change.

### 1.1 The facts a task owns are canonical and are not in core

R54 §2.3 struck `condition_id`, `stimulus_id`, `choice` and `rewarded` from the interval table and
sent them to an R17 extension, with `registry/extensions/dynamic_foraging.json` already declaring
`choice` and `rewarded` under a closed vocabulary core cannot state — *"`none` is not a choice"*.

Those are not derived quantities. Which side the animal licked is an observation, it is recorded
nowhere else in the packet, and no computation over core recovers it.

Read literally, `06` §2 therefore requires `choice` to be moved **into** core, which is the
outcome R54 §1 exists to prevent: one universal trial table whose nullable columns grow with every
task that adopts the format.

### 1.2 The contradiction is load-bearing, not cosmetic

A reader following `00` §3 concludes that a packet's extensions are optional colour and that core
alone is the dataset. On the measured session that reading loses the entire behavioural record:
450 trials whose task facts live in `dynamic_foraging.trials`, reachable only through R55's
discriminator.

It also mis-frames validation. A packet whose core passes and whose extension fails is not a
conforming packet with a decorative problem; part of its canonical data failed.

## 2. Decision

### 2.1 Canonical is a property of a resource, not of the core layer

> The **canonical** resources of a packet are its canonical core resources together with its
> canonical extension resources. Together they are the packet's record of what was observed.
>
> The **analysis** layer is derived and disposable, and MUST declare lineage to the canonical
> resources it was computed from (`06`).

`00` §3's *"sole source of truth"* is struck. Core remains what every packet has and what every
consumer can read without an extension registry; it stops being the whole of what is canonical.

### 2.2 What core is, restated

Core carries the **domain-general** facts: identity, time, instruments, arrays, units, spikes,
intervals, provenance. An extension carries **domain-specific** canonical facts, typed, with its
own vocabularies and its own Tier 2 rules (R17).

The test for core membership is unchanged (`09` §3): a fact belongs in core when common
interpretation, validation, joining or analysis breaks without it. R54 §2.4 already applies that
test to stimulation parameters and answers no.

### 2.3 Analysis derives from the canonical set

`06` §2's rule becomes:

> An analysis resource MUST be recomputable from the packet's canonical resources — core and
> extension alike — and MUST declare lineage naming each resource it derived from.

A resource that is not recomputable from the canonical set belongs among the canonical resources.
**Which** canonical layer it belongs to is decided by `09` §3's test, not by this rule.

### 2.4 A consumer reading core alone is reading a subset

A consumer **MAY** read core without resolving any extension, and what it reads is conforming and
complete for every core resource. It **MUST NOT** conclude that it has read every canonical fact
the packet holds: R55's discriminators are what say otherwise, and `interval_kind` resolving
`required` (R54 §2.4a) is the case where the omission is guaranteed.

## 3. What this does not change

- **No column, no table, no rule.** Three sentences of prose in two parts.
- **No change to R17's separable verdicts.** A core validator still MUST NOT require an extension's
  schema, and an extension finding is still reported apart (R17 §4). §1.2 changes how a *packet's*
  verdict reads, which R72 specifies; it does not merge the two.
- **No change to what core contains.** `09` §3's test is untouched; this states where its answer
  leaves the rest.
- **No new obligation on a writer.** A packet with no extensions is unaffected.

## 4. Open

- **Whether `canonical: true` should appear on an extension resource's manifest entry.** It already
  may — the field is per-resource — but nothing requires it, so "canonical extension resource" is
  currently a reading of the registry rather than a declaration in the packet. Worth settling when
  something needs to enumerate the canonical set without loading every extension.
