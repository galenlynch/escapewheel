# Agent instructions for escapewheel-validator

The root `AGENTS.md` also applies. Before changing this package, read `CONTRIBUTING.md`; read
`README.md` when public behavior or examples may change.

- Resolve behavioral questions using the root authority model and the registry embedded by the
  packet under validation.
- Follow `../CONTRIBUTING.md` for generated inputs. Do not hand-edit the vendored registry schema.
- Preserve the SQL-versus-storage-shim boundary documented in `CONTRIBUTING.md`; report a format
  defect instead of inventing a package-local rule.
