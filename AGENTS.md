# Agent instructions for Escapewheel

These instructions apply throughout the monorepo. A nested `AGENTS.md` may add narrower guidance.

## Required context

- For architecture, behavior, or schema work, first read the authority model in `README.md`, then
  read `spec/README.md` and the relevant numbered parts in `spec/parts/`.
- Before editing a specification part, read `spec/CONTRIBUTING.md`.
- For registry, generation, or tree-tool work, read `CONTRIBUTING.md`.
- For package work, read that package's `README.md` and `CONTRIBUTING.md`.
- For specification change work, read `revisions/CONTRIBUTING.md` in full.
- Answer a question about the current specification, registries, schemas or packets with
  `escapewheel-dev` rather than `grep`, `sed` or an inline script over `spec/`. From the root,
  `uv run --project escapewheel-dev escapewheel-dev` then: `section 9 5.7` reads a section,
  `requirements 12 | grep <word>` finds a rule, `schema recipe` prints a schema, `table <resource>`
  shows a declaration; `--help` lists the rest, and its `README.md` the Python API.

## Agent-specific safeguards

- Keep agent instruction files short and agent-specific. Put explanations and developer workflows
  in a `README.md` or `CONTRIBUTING.md`, and normative requirements in the specification.
- Do not accept, number, or incorporate a revision without explicit user direction. Agents may
  prepare change documents.
- Do not edit generated artifacts directly. Follow the source and generator documented in
  `CONTRIBUTING.md` or the applicable package guide.
- Preserve unrelated working-tree changes and run repository commands from the monorepo root unless
  a documented command says otherwise.
- In a restricted agent sandbox, use `tools/gate.py --changed` for the in-sandbox gate: it runs
  `verify.py --quick` and the suite of each changed package and its dependents. A full run needs
  the thread wakeups, Zarr round trip, and Unix-domain socket checked by
  `tools/runtime_capabilities.py`; if that preflight rejects the sandbox, rerun the unchanged full
  verifier with an unrestricted execution permission. Do not retry it in the same sandbox, skip
  the writer suite, or treat the capability failure as a writer defect.
