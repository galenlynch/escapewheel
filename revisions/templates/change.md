# <Declarative statement of the rule, or of the problem while the document is Open>

| | |
|---|---|
| **Status** | **Open** |
| **Opened** | YYYY-MM-DD |
| **Based on** | <full commit hash used for the observations and counts> |
| **Affects** | <concepts and current specification locations, if known> |

<!-- An Open document carries the four rows above. When it becomes Ready, set Status to
**Ready**, replace Affects with the rows below, and add the Decision and conformance sections. Do
not cite roadmap work-item labels; state dependencies and deferred subjects directly. Delete every
comment before committing.

| **Change form** | <ordinary or structural> |
| **Amends** | <specification parts and artifacts> |
| **Depends on** | <accepted revision clauses or “None”> |
| **Profile** | <all, or a profile identifier> |
| **Decision clauses** | <every subsection under §3, or §3 when Decision has no subsections> |

A Ready document also states which numbered sections are normative and which informative, and
that normative keywords follow BCP 14. -->

## 1. Problem

<!-- Describe the current behavior, the concrete problem, and the boundary of the change. A
structural change explains here why append-only placement would impair the specification and
carries its crosswalk. -->

## 2. Evidence

<!-- Record reproducible observations, measurements, affected packets, or contradictory clauses.
Say how each measurement was made and what population it covers. Distinguish facts from inference.
Compare the alternatives considered, including keeping the current design, with their costs. -->

## 3. Preferred direction

<!-- Open: state the direction the document prefers, without BCP 14 keywords. Ready: retitle this
section `Decision` and state the normative rule. Give every requirement a named actor and state
replacement rules directly; for registry fields, declare type, presence, role, references, and
vocabulary. -->

## 4. Questions

<!-- One numbered item per question that must be answered before the Decision can be stated.
Record each answer beneath its question, in the same item, beginning `**Answered YYYY-MM-DD:`. A
Ready document answers every question. -->

## 5. Consequence

<!-- Open: sketch the consequence, marking each surface affected, unchanged with a reason, or
unknown. Ready: state compatibility effects, migration or rebuild costs, and affected
implementation surfaces, and complete the inventory below, writing “unchanged” with a reason
rather than leaving a cell empty. An optional `What this does not change` subsection keeps only
consequences a reasonable reader would otherwise infer from the decision. -->

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | | |
| logical prose and registry | | |
| physical profiles | | |
| packet manifest and JSON Schemas | | |
| validation and import | | |
| extensions | | |
| reader, writer, validator, adapters | | |
| conformance fixtures and tests | | |
| revision process and tooling | | |
| generated publications and developer documentation | | |

<!-- Ready only:

## 6. Conformance and implementation evidence

Name the positive and negative cases that distinguish the rule from the current one, and the
implementation tests or probes that establish feasibility. A test that merely repeats the document
is not evidence that the owning specification artifacts agree. -->
