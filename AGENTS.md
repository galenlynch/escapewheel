# Agent instructions for Escapewheel

These instructions apply throughout the monorepo. A nested `AGENTS.md` may add narrower guidance.

## Required context

- For architecture, behavior, or schema work, first read the authority model in `README.md`, then
  read `escapewheel_poc_docs_v0.2/README.md` and the relevant numbered parts.
- Before editing a specification part, read `escapewheel_poc_docs_v0.2/CONTRIBUTING.md`.
- For registry or generation work, read `CONTRIBUTING.md`.
- For package work, read that package's `README.md` and `CONTRIBUTING.md`.
- For specification change work, read `revisions/CONTRIBUTING.md` in full.

## Agent-specific safeguards

- Keep agent instruction files short and agent-specific. Put explanations and developer workflows
  in a `README.md` or `CONTRIBUTING.md`, and normative requirements in the specification.
- Do not accept, number, or incorporate a revision without explicit user direction. Agents may
  prepare proposals and drafts.
- Do not edit generated artifacts directly. Follow the source and generator documented in
  `CONTRIBUTING.md` or the applicable package guide.
- Preserve unrelated working-tree changes and run repository commands from the monorepo root unless
  a documented command says otherwise.
