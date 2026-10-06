# A packet binds only the extensions it uses

| | |
|---|---|
| **Status** | **Open** |
| **Opened** | 2026-10-06 |
| **Based on** | `44822ef4e765c8666fc706cabf722c12d969ee48` |
| **Affects** | Part 04 §8, registry bindings; Part 04 §10, manifest conformance; Part 05 §15.1, an amending build's bindings |

## 1. Problem

A packet's manifest binds the core registry and extension registries under `registries`, and each
bound registry is stored in the packet. Part 04 §8 requires a packet to bind "every extension
registry that declares one of its resources", and says nothing of binding one that declares none.
A packet binding an extension it does not use therefore validates, while its manifest tells a
consumer listing its extensions that it uses that one.

An amending build binds every registry the held packet binds, under Part 05 §15.1, so an
amendment that drops an extension's last resource keeps a binding it no longer needs and has no way
to remove.

The change concerns which extension registries a packet binds. What binding one means, how a bound
registry is stored, and the core registry's binding are unchanged.

## 2. Evidence

Observations are of the tree at the commit this document is based on, and of packets built from it.

- Four packets built for two AIND ecephys sessions, two rebuilds each, bind `aind_opto` and
  `vr_foraging`, and no resource in any of them has a declaration from either, counted by each
  resource's `declaration_id` against the registries bound. Their recipes listed both extensions
  through eleven rebuilds. Every one of those packets passed validation.
- Binding an extension does one thing beyond making its declarations resolvable: under Part 02
  §2.5 it activates the extension's required declarations. A required singleton must then be
  present, so a bound extension with a required declaration always declares a resource of the
  packet. An extension binding that declares no resource activates nothing.
- An extension's rules live in its table declarations, so an extension cannot contribute a rule
  over core tables without declaring a resource of its own.
- An absent optional singleton creates no empty table (Part 02 §2.5), so binding an unused
  extension does not give a collection of packets a common set of tables.
- The writer binds exactly the extensions its recipe lists, plus those an amended packet binds, and
  reports at commit each one that declares none of the packet's resources.

Alternatives:

- **Keep the current rule, with the writer's report.** The writer reports, but nothing marks a
  packet another writer built this way, and the amendment gap remains.
- **Forbid an unused binding outright, at `error`.** Which extensions a packet uses can already be
  read off its resources' `declaration_id`s, so no consumer depends on the bindings being exact; an
  error would make every packet built this way nonconforming over an extra file that changes no
  meaning.

## 3. Preferred direction

A packet should not bind an extension registry that declares none of its resources. A validator
reports such a binding at `warning` under a new manifest check, naming the registry, and a packet
carrying one stays conforming. An amending build may leave out a registry the held packet binds
where the amended packet has no resource that registry declares, so an amendment that drops an
extension's last resource can drop its binding too.

## 4. Questions

1. Is an unused binding a warning or an error?
2. Does an amending build drop an unused held binding itself, or only where its recipe asks?
3. Does the rule exempt the core registry, which is always bound since `core.sessions` is a
   required singleton?

## 5. Consequence

Packets already built stay conforming and gain a warning. A writer that binds only what its recipe
lists keeps doing so, and reports what it would leave out.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged: no concept's meaning moves. | None required. |
| logical prose and registry | Unchanged: Part 02 §2.5's activation rule is cited, not changed. | None required. |
| physical profiles | Unchanged: how a bound registry is stored is unchanged. | None required. |
| packet manifest and JSON Schemas | Affected: Part 04 §8 gains the rule and Part 04 §10 the check; the schema is unchanged, since the check needs the resources. | Unknown until Ready. |
| validation and import | Affected: Part 05 §15.1's amending-build bindings. | Unknown until Ready. |
| extensions | Unchanged: an extension document's shape is unchanged. | None required. |
| reader, writer, validator, adapters | Affected: the validator gains the check; the writer drops an unused held binding when amending. | Unknown until Ready. |
| conformance fixtures and tests | Affected: a corpus packet binding an unused extension. | Unknown until Ready. |
| revision process and tooling | Affected: the ledger places the clauses. | Unknown until Ready. |
| generated publications and developer documentation | Affected: the combined specification regenerates. | Unknown until Ready. |
