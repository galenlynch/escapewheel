# A packet binds only the extensions it uses

| | |
|---|---|
| **Status** | **Ready** |
| **Opened** | 2026-10-06 |
| **Based on** | `8cf4dd3df52bd7bd258b5903271c0df43a41432d` |
| **Change form** | ordinary |
| **Amends** | Part 02 §10.2; Part 04 §8; Part 04 §10; Part 05 §15.1 |
| **Depends on** | None |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Problem

A packet's manifest binds the core registry and extension registries under `registries`, and each
bound registry is stored in the packet. Part 04 §8 requires a packet to bind "every extension
registry that declares one of its resources", and says nothing of binding one that declares none.
A packet binding an extension it does not use therefore validates, while its manifest tells a
consumer listing its extensions that it uses that one.

An amending build binds every registry the packet's current manifest binds under an ID for which
its recipe names none, under Part 05 §15.1. An amendment that removes an extension's last resource
therefore keeps a binding it no longer needs, and its recipe has no way to remove it.

The change concerns which extension registries a packet binds. What binding one means, how a bound
registry is stored, and the core registry's binding are unchanged.

## 2. Evidence

Observations are of the tree at the commit this document is based on, and of packets built from it.

- Four packets built for two AIND ecephys sessions, two rebuilds each, bind `aind_opto` and
  `vr_foraging`, and no resource in any of them has a declaration from either, counted by each
  resource's `declaration_id` against the registries bound. Their recipes listed both extensions
  through eleven rebuilds. Every one of those packets passed validation.
- Binding an extension makes its declarations resolvable and, under Part 02 §2.5, activates its
  required declarations. A required singleton must then be present, so a bound extension with a
  required declaration either declares a resource of the packet or fails
  `packet.resource.required_missing`.
- Binding an extension also runs its rules. Part 11 §3 lets an extension rule name core resources,
  and a resource absent from the packet binds as an empty relation, so a bound extension's rules
  run where the packet carries none of its resources. Nothing requires such a rule to find nothing.
  The tree's four extension registries, `aind_opto`, `aind_unit_qc`, `dynamic_foraging` and
  `vr_foraging`, hold 49 rules; each reads a resource of its own extension, and the five that also
  read `core.intervals` join it from their own extension's table, so none returns a row where its
  extension's resources are empty.
- An absent optional singleton creates no empty table (Part 02 §2.5), so binding an unused
  extension does not give a collection of packets a common set of tables.
- The writer binds exactly the extensions its recipe lists, plus those the current manifest binds
  in an amending build, and reports at commit each one that declares none of the packet's
  resources.

Alternatives:

- **Keep the current rule, with the writer's report.** The writer reports, but nothing marks a
  packet another writer built this way, and the amendment gap remains.
- **Forbid an unused binding outright, at `error`.** Which extensions a packet uses can already be
  read off its resources' `declaration_id`s, so no consumer depends on the bindings being exact; an
  error would make every packet built this way nonconforming over an extra file that changes no
  meaning.
- **Count an extension whose rules name the packet's resources as used.** The rule stays checkable,
  but every rule in the tree already finds nothing without its extension's resources, and deciding
  which rules count adds a dependency analysis to binding for no packet that needs it.

## 3. Decision

These clauses concern extension registries only. The core registry's binding is unchanged.

### 3.1 A packet does not bind an extension it does not use

An extension registry **declares** a resource of a packet where the resource's `declaration_id`
names a declaration in that registry. A packet SHOULD NOT bind an extension registry that declares
none of its resources.

### 3.2 An extension rule finds nothing without its extension's resources

An extension rule MUST return no row where every resource of its own registry binds as an
empty relation, which no checker verifies.

### 3.3 A validator warns of an unused extension binding

A checker reports `packet.registry.unused`, in the `declaration` phase and at `warning`, for each
bound extension registry that passed binding, declares none of the packet's resources and has no
required singleton, naming that registry's ID. Under Part 05 §9.5 the finding belongs to the
packet.

### 3.4 An amending build leaves out an unused held binding

An amending build binds each registry its recipe names, and each registry the packet's current
manifest binds under an ID for which the recipe names none, unless that registry is an extension
registry declaring none of the amended manifest's resources. Its writer MUST report each registry
it leaves out this way, naming its ID, which no checker verifies.

## 4. Questions

1. Is an unused binding a warning or an error?
   **Answered 2026-10-06:** A warning. An unused binding changes no meaning, since it activates no
   declaration and its rules find nothing under §3.2, and which extensions a packet uses can
   already be read off its resources; an error would make every packet built this way
   nonconforming over an extra file.
2. Does an amending build drop an unused held binding itself, or only where its recipe asks?
   **Answered 2026-10-06:** Itself, reporting what it left out. Under §3.2 leaving one out cannot
   change the amended packet's findings or meaning, so a recipe member requesting it would add
   surface and protect nothing, and a recipe has no way to remove a held binding today. A registry
   the recipe names is still bound under Part 05 §3.1.
3. Does the rule exempt the core registry, which is always bound since `core.sessions` is a
   required singleton?
   **Answered 2026-10-06:** The rule concerns extension registries only, so it needs no exemption.
   Core always declares a resource of the packet in any case.
4. Is an extension's rule that finds rows without the extension's resources excluded, or is the
   binding counted as used?
   **Answered 2026-10-06:** Excluded, under §3.2. Every rule in the tree already complies, and the
   rule makes "uses" mean only "declares a resource", which a checker reads off the manifest.

## 5. Consequence

Packets already built stay conforming; one binding an unused extension gains a warning, including
the four AIND rebuilds of §2. No registry, schema or packet changes, since every extension rule in
the tree already satisfies §3.2.

A build from a recipe that names an unused extension still binds it, since Part 05 §3.1 requires
binding every extension a recipe names, and the writer reports it as it does now; the recipe's
author removes it. An amending build leaves out a held extension the amended manifest does not
use: one the current manifest already bound needlessly, or one whose last resource the amendment
removes, which Part 05 §15.2 permits for an analysis, compatibility-projection or documentation
resource. The stored copy of that registry stays in the packet while a retained manifest binds it,
under the cleanup rules Part 03 §3.2 and Part 05 §15 apply to a descriptor's `path`.

A bound extension with a required singleton is never reported unused: it either declares a
resource of the packet or fails `packet.resource.required_missing`, which already names the fault.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged: no concept's meaning moves. | None required. |
| logical prose and registry | Part 02 §10.2 gains §3.2's rule. Part 02 §2.5's activation rule is cited, not changed. Every extension registry in the tree already complies. | None required. |
| physical profiles | Unchanged: how a bound registry is stored, and when its copy may be removed, is unchanged. | None required. |
| packet manifest and JSON Schemas | Part 04 §8 gains §3.1's rule and Part 04 §10 §3.3's check; §10's statement that every finding in its table is at `error` names this one as the exception. The manifest schema is unchanged, since the check needs the bound declarations. | `spec/tools` checks. |
| validation and import | Part 05 §15.1's amending-build binding rule changes under §3.4. | The writer suite. |
| extensions | Unchanged: an extension document's shape is unchanged, and its rules already comply with §3.2. | None required. |
| reader, writer, validator, adapters | The validator reports `packet.registry.unused`. The writer's amending build leaves out an unused held extension and reports it. The reader is unchanged, since it resolves only declarations a resource names. | The validator and writer suites. |
| conformance fixtures and tests | A corpus packet binding an unused extension passes with the warning. | The corpus stage of `verify.py`. |
| revision process and tooling | The ledger places §§3.1 to 3.4. | `ledger.py`, `evidence.py`. |
| generated publications and developer documentation | The combined specification regenerates. | `verify.py`. |

## 6. Conformance and implementation evidence

These cases distinguish the new rules from the current ones:

- a packet binding an extension that declares none of its resources passes validation with one
  `packet.registry.unused` warning naming that extension, and with no finding from that
  extension's rules, including those that read `core.intervals`;
- a packet whose bound extension declares one of its resources has no such finding, and neither
  does the core registry;
- an extension registry that failed binding gets no `packet.registry.unused` finding;
- a bound extension whose required singleton is absent gets `packet.resource.required_missing` and
  no `packet.registry.unused` finding;
- an amending build of a packet binding an unused extension, and one removing the last analysis
  resource an extension declares, each write a manifest that does not bind that extension, and the
  writer reports the registry left out;
- an amending build keeps a held extension that declares a resource of the amended manifest, and
  binds an unused extension its recipe names, which validation then warns of; and
- the stored copy of a registry left out of an amendment remains readable through the retained
  manifest that binds it.

The writer's report of an unused binding at commit, in `escapewheel-writer/tests/test_extensions.py`
(`test_an_extension_the_packet_does_not_use_is_reported` and
`test_an_extension_the_packet_uses_is_not_reported`), establishes that a writer can determine which
bound extensions declare none of a packet's resources from the entries it holds.
