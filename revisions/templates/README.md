# Revision templates

Copy the template matching the current stage; do not start from an old revision whose structure may
predate the current process.

| template | destination |
|---|---|
| `proposal.md` | `../proposals/<slug>.md` |
| `draft.md` | `../drafts/<slug>.md` |
| `accepted-revision.md` | `../accepted/R<N>-<slug>.md`, only during explicitly authorized acceptance and incorporation |
| `change-evidence.json` | `../evidence/R<N>.json`, created with the accepted revision |

The accepted-revision template is a final-shape checklist, not a separate authoring pass. An
accepted file should be the reviewed draft with its status and filename changed while the same
change incorporates it into the generated v0.2 specification.

Every open artifact records the full baseline commit. A draft and accepted revision also enumerate
their exact normative subsections in `Decision clauses`; the ledger reads that list rather than
inferring force from keywords. Preserve the completed impact inventory and evidence record through
acceptance. The JSON evidence manifest turns that record into checked paths and identifiers without
making implementations or tests authoritative.

All three stages follow the shared specification style in
`../../escapewheel_poc_docs_v0.2/CONTRIBUTING.md`; revision-specific guidance is in
`../CONTRIBUTING.md`.
