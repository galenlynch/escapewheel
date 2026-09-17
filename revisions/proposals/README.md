# Proposals

This directory holds active, non-authoritative specification proposals. A proposal establishes a
problem, evidence, constraints, alternatives, and the questions that need agreement before anyone
writes candidate normative text. Start from `../templates/proposal.md`.

A proposal:

- has no revision number and uses a descriptive slug;
- does not use BCP 14 keywords to prescribe behavior;
- is never cited by the generated specification or an accepted revision; and
- changes no implementation contract.

When its problem, scope, and intended direction are settled and promotion is approved, carry the
useful content into a draft based on `../templates/draft.md` and delete the proposal in the same
change. Git retains the superseded discussion. If the proposal is abandoned, delete it with a
commit message that records why.
