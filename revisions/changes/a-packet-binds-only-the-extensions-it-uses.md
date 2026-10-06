# A packet binds only the extensions it uses

| | |
|---|---|
| **Status** | **Ready** |
| **Opened** | 2026-10-06 |
| **Based on** | `44822ef4e765c8666fc706cabf722c12d969ee48` |
| **Change form** | ordinary |
| **Amends** | Part 04 §8; Part 04 §10; Part 05 §15.1 |
| **Depends on** | None |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

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

## 3. Decision

These clauses concern extension registries only. The core registry's binding is unchanged.

### 3.1 A packet does not bind an extension it does not use

An extension registry **declares** a resource of a packet where the resource's `declaration_id`
names a declaration in that registry. A packet SHOULD NOT bind an extension registry that declares
none of its resources.

### 3.2 A validator warns of an unused extension binding

A checker reports `packet.registry.unused`, in the `declaration` phase and at `warning`, for each
bound extension registry that passed binding and declares none of the packet's resources, naming
that registry's ID. Under Part 05 §9.5 the finding belongs to the packet.

### 3.3 An amending build leaves out an unused held binding

An amending build binds each registry its recipe names, and each registry the packet's current
manifest binds under an ID for which the recipe names none, except an extension registry that
declares none of the amended packet's resources. An amending build MUST NOT bind such an extension
registry, and its writer MUST report each one it leaves out, naming its ID, which no checker
verifies.

## 4. Questions

1. Is an unused binding a warning or an error?
   **Answered 2026-10-06:** A warning. An unused binding changes no meaning, since it activates no
   declaration and contributes no rule, and which extensions a packet uses can already be read off
   its resources; an error would make every packet built this way nonconforming over an extra file.
2. Does an amending build drop an unused held binding itself, or only where its recipe asks?
   **Answered 2026-10-06:** Itself, reporting what it left out. Leaving one out cannot change the
   amended packet's validity or meaning, so a recipe member requesting it would add surface and
   protect nothing, and a recipe has no way to remove a held binding today. A registry the recipe
   names is still bound under Part 05 §3.1.
3. Does the rule exempt the core registry, which is always bound since `core.sessions` is a
   required singleton?
   **Answered 2026-10-06:** The rule concerns extension registries only, so it needs no exemption.
   Core always declares a resource of the packet in any case.

## 5. Consequence

Packets already built stay conforming; one binding an unused extension gains a warning, including
the four AIND rebuilds of §2. No registry, schema or packet changes.

A build from a recipe that names an unused extension still binds it, since Part 05 §3.1 requires
binding every extension a recipe names, and the writer reports it as it does now; the recipe's
author removes it. An amending build leaves out a held extension the amended packet does not use:
one the held packet already bound needlessly, or one whose last resource the amendment removes,
which Part 05 §15.2 permits for an analysis, compatibility-projection or documentation resource.
The stored copy of that registry stays in the packet while a retained manifest binds it, under the
cleanup rules Part 03 §3.2 and Part 05 §15 apply to a descriptor's `path`.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged: no concept's meaning moves. | None required. |
| logical prose and registry | Unchanged: Part 02 §2.5's activation rule is cited, not changed. | None required. |
| physical profiles | Unchanged: how a bound registry is stored, and when its copy may be removed, is unchanged. | None required. |
| packet manifest and JSON Schemas | Part 04 §8 gains §3.1's rule and Part 04 §10 §3.2's check. The manifest schema is unchanged, since the check needs the bound declarations. | `spec/tools` checks. |
| validation and import | Part 05 §15.1's amending-build binding rule changes under §3.3. | The writer suite. |
| extensions | Unchanged: an extension document's shape is unchanged. | None required. |
| reader, writer, validator, adapters | The validator reports `packet.registry.unused`. The writer's amending build leaves out an unused held extension and reports it. The reader is unchanged, since it resolves only declarations a resource names. | The validator and writer suites. |
| conformance fixtures and tests | A corpus packet binding an unused extension passes with the warning. | The corpus stage of `verify.py`. |
| revision process and tooling | The ledger places §§3.1 to 3.3. | `ledger.py`, `evidence.py`. |
| generated publications and developer documentation | The combined specification regenerates. | `verify.py`. |

## 6. Conformance and implementation evidence

These cases distinguish the new rules from the current ones:

- a packet binding an extension that declares none of its resources passes validation with one
  `packet.registry.unused` warning naming that extension;
- a packet whose bound extension declares one of its resources has no such finding, and neither
  does the core registry;
- an extension registry that failed binding gets no `packet.registry.unused` finding;
- an amending build of a packet binding an unused extension, and one removing the last analysis
  resource an extension declares, each write a manifest that does not bind that extension, and the
  writer reports the registry left out;
- an amending build keeps a held extension that declares a resource of the amended packet, and
  binds an unused extension its recipe names, which validation then warns of; and
- the stored copy of a registry left out of an amendment remains readable through the retained
  manifest that binds it.

The writer's report of an unused binding at commit, in `escapewheel-writer/tests/test_extensions.py`
(`test_an_extension_the_packet_does_not_use_is_reported` and
`test_an_extension_the_packet_uses_is_not_reported`), establishes that a writer can determine which
bound extensions declare none of a packet's resources from the entries it holds.
