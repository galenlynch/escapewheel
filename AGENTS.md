# Agent instructions for Escapewheel

These instructions apply throughout the monorepo. A nested `AGENTS.md` may add narrower guidance.

## Required context

- For architecture, behavior, or schema work, first read the authority model in `README.md`, then
  read `spec/README.md` and the relevant numbered parts in `spec/parts/`.
- Before editing a specification part, read `spec/CONTRIBUTING.md`.
- For registry, generation, or tree-tool work, read `CONTRIBUTING.md`.
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
- In a restricted agent sandbox, use `verify.py --quick` for the in-sandbox gate. A full run needs
  the thread wakeups, Zarr round trip, and Unix-domain socket checked by
  `tools/runtime_capabilities.py`; if that preflight rejects the sandbox, rerun the unchanged full
  verifier with an unrestricted execution permission. Do not retry it in the same sandbox, skip
  the writer suite, or treat the capability failure as a writer defect.
