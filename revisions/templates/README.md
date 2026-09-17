# Revision templates

Copy the template matching the current stage; do not start from an old revision whose structure may
predate the current process.

| template | destination |
|---|---|
| `proposal.md` | `../proposals/<slug>.md` |
| `draft.md` | `../drafts/<slug>.md` |
| `accepted-revision.md` | `../R<N>-<slug>.md`, only during user-authorized acceptance and incorporation |

The accepted-revision template is a final-shape checklist, not a separate authoring pass. An
accepted file should be the reviewed draft with its status and filename changed while the same
change incorporates it into the generated v0.2 specification.

All three stages follow the shared specification style in
`../../escapewheel_poc_docs_v0.2/CONTRIBUTING.md`; revision-specific guidance is in
`../CONTRIBUTING.md`.
