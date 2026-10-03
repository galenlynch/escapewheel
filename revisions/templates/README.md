# Revision templates

Copy the template for the document being written; do not start from an old revision whose
structure may predate the current process.

| template | destination |
|---|---|
| `change.md` | `../changes/<slug>.md`, opened Open or, where no question needs answering, Ready |
| `accepted-revision.md` | `../accepted/R<N>-<slug>.md`, only during explicitly authorized acceptance and incorporation |
| `change-evidence.json` | `../evidence/R<N>.json`, created with the accepted revision |

The accepted-revision template is a final-shape checklist, not a separate authoring pass. An
accepted file should be the Ready document with its status and filename changed while the same
change incorporates it into the generated v0.2 specification.

A change document records its full baseline commit and declares no decision domain. A Ready
document and an accepted revision also declare an ordinary or structural change form and
enumerate their exact normative subsections in `Decision clauses`; the ledger reads that list rather
than inferring force from keywords. Preserve the completed impact inventory and evidence record
through acceptance. The JSON evidence manifest turns that record into checked paths and identifiers
without making implementations or tests authoritative.

Every document follows the shared specification style in `../../spec/CONTRIBUTING.md`;
revision-specific rules and guidance are in `../CONTRIBUTING.md`.
