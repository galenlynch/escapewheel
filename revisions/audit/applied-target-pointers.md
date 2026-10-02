# Ledger targets the audit would change

The [audit of the ledger's applied targets](applied-targets.md) found 140 `applied` clauses whose
recorded targets differ from the sections that state them. Nothing here has been applied to
`revisions/applied.toml`, and no row has had a second reading.

The third column lists 167 sections, over 115 clauses, that state a rule of the clause and that the
ledger does not name for it. The fourth lists 58 recorded targets, over 46 clauses, that state none
of the clause. Twenty-one clauses appear in both columns.

| clause | recorded targets | sections that state it, unrecorded | recorded targets that state none of it |
|---|---|---|---|
| R1 §2 | Part 05 `ew-validation-shim` | Part 00 §3.3; Part 03 §1 | Part 05 `ew-validation-shim` |
| R2 §2 | Part 02 §6 | Part 02 §1 | Part 02 §6 |
| R2 §3 | Part 02 §9.1 | Part 02 §2.3 |  |
| R2 §6 | Part 02 §2; Part 02 §7; Part 03 §5.3 | Part 02 §10.1 | Part 03 §5.3 |
| R2 §8 | Part 02 `ew-registry-self-description` | Part 02 §9.1; Part 04 §8 |  |
| R2 §9 | Part 02 `ew-registry-self-description` | Part 02 §9.4 |  |
| R3 §2.1 | Part 03 `ew-parquet-reader-floor` | Part 02 §5.1; Part 02 §5.2; Part 02 §5.3; Part 02 §6 |  |
| R3 §5.1 | Part 03 §6.2 | Part 03 §6.5 |  |
| R3 §6 | Part 02 §8.1.1 | Part 05 §5.3 |  |
| R3 §7.1 | Part 03 §6.1 | Part 03 §6.2 |  |
| R6 §2 | Part 01 §3.9 | Part 03 §5.5 |  |
| R8 §4 | Part 02 `ew-registry-vocabularies` | Part 01 §3.17 |  |
| R14 §2.2 | Part 03 `ew-array-codecs` | Part 05 §5.3 |  |
| R14 §2.3 | Part 04 §5.1 | Part 04 §4.1 |  |
| R15 §2 | Part 03 `ew-array-codecs` | Part 03 §6.1 | Part 03 `ew-array-codecs` |
| R15 §3 | Part 04 §3 |  | Part 04 §3 |
| R17 §2 | Part 09 §5.1 | Part 09 §5.2; Part 09 §6.1 |  |
| R21 §3.3 | Part 03 `ew-array-codecs` | Part 03 §6.1 |  |
| R22 §4 | Part 05 §5.2 |  | Part 05 §5.2 |
| R25 §4 | Part 01 §2.2 | Part 01 §2.3 | Part 01 §2.2 |
| R27 §3 | Part 01 §3.9 |  | Part 01 §3.9 |
| R27 §6 | Part 01 §3.9 | Part 01 §2.2 |  |
| R30 §3.1 | Part 03 §5.4 |  | Part 03 §5.4 |
| R30 §3.2 | Part 03 §5.4 | Part 05 §5.3 |  |
| R32 §4 | Part 05 `ew-superseded-manifest-retention`; Part 03 `ew-portable-amendment` | Part 04 §1 |  |
| R32 §5 | Part 05 `ew-incremental-revalidation` | Part 05 §6 |  |
| R35 §2 | Part 05 `ew-incremental-revalidation` | Part 05 §8 |  |
| R36 §2.1 | Part 04 `ew-prefix-resources` | Part 04 §4.3 | Part 04 `ew-prefix-resources` |
| R36 §2.3 | Part 04 `ew-external-resource-verification` | Part 04 §4.3 |  |
| R37 §3.1 | Part 01 §3.9 |  | Part 01 §3.9 |
| R38 §2.3 | Part 01 §2.2 | Part 01 §2.3 | Part 01 §2.2 |
| R40 §2.2 | Part 02 `ew-clock-alignment-record` | Part 01 §3.9 |  |
| R41 §2.2 | Part 01 §3.20 | Part 01 §2.6 | Part 01 §3.20 |
| R41 §2.3 | Part 01 §2.4 |  | Part 01 §2.4 |
| R41 §2.4 | Part 01 §2.4 | Part 01 §2.6 | Part 01 §2.4 |
| R44 §2.2 | Part 01 §2.4 | Part 01 §2.6 | Part 01 §2.4 |
| R44 §2.3 | Part 01 §2.4 | Part 01 §2.6 | Part 01 §2.4 |
| R45 §2.1 | Part 01 §2.3 | Part 05 §4.3 |  |
| R45 §2.5 | Part 01 §3.9 | Part 01 §2.2 |  |
| R51 §2.1 | Part 04 `ew-prefix-resources` | Part 04 §4.3 |  |
| R52 §2.3 | Part 03 `ew-owned-resource-digests`; Part 04 `ew-external-resource-verification` |  | Part 03 `ew-owned-resource-digests` |
| R52 §2.4 | Part 05 `ew-incremental-revalidation` | Part 03 §8.1; Part 04 §4.3 | Part 05 `ew-incremental-revalidation` |
| R56 §2.5 | Part 02 §8.4 | Part 01 §2.2 |  |
| R57 §2.1 | Part 02 `ew-registry-self-description` |  | Part 02 `ew-registry-self-description` |
| R62 §2.2 | Part 04 §3 | Part 03 §3.3 |  |
| R71 §2.1 | Part 00 `ew-packet-content-classes` | Part 06 §2 |  |
| R71 §2.2 | Part 05 `ew-error-policy` | Part 00 §4.1; Part 09 §3 | Part 05 `ew-error-policy` |
| R72 §2.4 | Part 05 `ew-verdict-composition` | Part 09 §5.4 |  |
| R79 §2.3 | Part 05 §10 |  | Part 05 §10 |
| R80 §2.4 | Part 04 `ew-source-resolution` | Part 04 §5.3 |  |
| R81 §2.2 | Part 02 `ew-unit-identity` | Part 05 §11 |  |
| R81 §2.4 | Part 03 §5.3; Part 03 §5.4; Part 02 §9 |  | Part 02 §9 |
| R81 §2.5 | Part 02 §9 | Part 02 §12.1 | Part 02 §9 |
| R84 §2.2 | Part 00 `ew-physical-profile`; Part 03 `ew-portable-profile-scope`; Part 04 §3; Part 04 `ew-source-resolution` | Part 01 §1; Part 02 §1 |  |
| R86 §2.1 | Part 00 `ew-packet` | Part 02 §7.1 | Part 00 `ew-packet` |
| R86 §2.2 | Part 00 `ew-packet` | Part 05 §13.1 | Part 00 `ew-packet` |
| R86 §2.3 | Part 00 `ew-packet` | Part 05 §13.1 | Part 00 `ew-packet` |
| R88 §2.4 | Part 02 §12.3 | Part 02 §8.2 |  |
| R90 §3.9 | Part 02 `ew-discriminator-semantics`; Part 00 `ew-packet-content-classes` |  | Part 00 `ew-packet-content-classes` |
| R92 §2.2 | Part 03 §5.3 | Part 02 §8.5 |  |
| R93 §3.1 | Part 02 §5.3 | Part 00 §7.3 |  |
| R93 §3.4 | Part 10 §1 | Part 00 §8 |  |
| R95 §3.3 | Part 05 `ew-validation-shim`; Part 07 `ew-reference-object-model` |  | Part 07 `ew-reference-object-model` |
| R97 §3.3 | Part 02 §8.6 | Part 07 §4 |  |
| R102 §3.1 | Part 01 §3.17 |  | Part 01 §3.17 |
| R105 §3.3 | Part 01 §3.8 | Part 02 §12.7 |  |
| R107 §3.1 | Part 02 `ew-column-declaration` |  | Part 02 `ew-column-declaration` |
| R109 §3.2 | Part 09 §5.7 | Part 05 §3.5 |  |
| R111 §3.5 | Part 00 `ew-core-content-requirements`; Part 00 `ew-analysis-content-requirements`; Part 00 `ew-later-physical-profiles`; Part 01 §3.5; Part 01 §3.8; Part 01 §3.9; Part 02 §4; Part 02 §5.2; Part 02 §8.1.1; Part 02 §8.2; Part 02 `ew-discriminator-semantics`; Part 02 §8.6; Part 02 §8.7; Part 02 §10.3; Part 03 §4; Part 03 `ew-parquet-reader-floor`; Part 03 §6.2; Part 03 §8.1; Part 05 `ew-incremental-revalidation`; Part 05 `ew-packet-cleanup`; Part 05 `ew-amendment-definition`; Part 04 `ew-prefix-resources`; Part 04 `ew-source-resolution`; Part 05 §2; Part 05 §3.2; Part 05 `ew-source-declarations`; Part 05 `ew-recipe-check`; Part 05 `ew-import-delivery`; Part 05 §4.3; Part 05 `ew-validation-shim`; Part 05 §5.4; Part 05 §10; Part 05 `ew-writer-acceptance-criteria`; Part 06 §2; Part 06 §4; Part 09 §5.2; Part 09 §5.4; Part 09 §5.7; Part 12 `ew-adapter-run-report`; Part 09 §8; Part 09 §8.1 | Part 02 §12.8 | Part 00 `ew-analysis-content-requirements`; Part 00 `ew-core-content-requirements`; Part 01 §3.8; Part 01 §3.9; Part 02 `ew-discriminator-semantics`; Part 05 §10; Part 05 §2; Part 05 §5.4; Part 09 §5.4; Part 12 `ew-adapter-run-report` |
| R112 §3.1 | Part 00 `ew-numbered-part-ownership` | the revision guide §5.3 | Part 00 `ew-numbered-part-ownership` |
| R114 §3 | Part 02 §7 | Part 09 §5.1 |  |
| R115 §3.1 | Part 12 `ew-build-supplied-values`; Part 05 `ew-source-declarations` | Part 05 §3.5 |  |
| R115 §3.10 | Part 05 §4.4; Part 12 `ew-arrow-ipc-floor` | Part 12 §5 |  |
| R115 §3.11 | Part 05 §4.4; Part 05 §3.7; Part 12 `ew-adapter-run-report` | Part 12 §8 |  |
| R115 §3.2 | Part 05 `ew-recipe-ownership` | Part 05 §3.4 |  |
| R115 §3.3 | Part 12 `ew-protocol-groups`; Part 09 §5.7 | Part 12 §4; Part 12 §6; Part 12 §7 |  |
| R115 §3.8 | Part 12 `ew-referenced-resource-delivery` | Part 12 §2 |  |
| R119 §3.4 | Part 12 `ew-adapter-declaration-document`; Part 05 `ew-source-declarations`; Part 05 `ew-recipe-check` | Part 07 §4 | Part 05 `ew-source-declarations` |
| R120 §3.1 | the revision guide `ew-decision-domains` | the revision guide §1; the revision guide §8.1 |  |
| R120 §3.6 | the revision guide `ew-citation-context` | Part 00 §2.1 |  |
| R120 §3.7 | the revision guide `ew-current-owner-ledger` | the revision guide §11; the revision guide §12; the revision guide §8.4; the revision guide §9 |  |
| R120 §3.8 | the revision guide `ew-process-incorporation-boundary` | the revision guide §5.3 |  |
| R122 §3.5 | Part 00 `ew-architecture-classifications` | Part 00 §8 |  |
| R122 §3.8 | Part 00 `ew-specification-candidate` | Part 00 §2.3; Part 00 §8 |  |
| R123 §3.1 | Part 01 `ew-unit-concept`; Part 02 `ew-unit-identity`; Part 05 `ew-reader-unit-selection` |  | Part 05 `ew-reader-unit-selection` |
| R123 §3.6 | Part 00 `ew-numbered-part-ownership` | Part 00 §2 |  |
| R124 §3.3 | Part 00 `ew-normative-references`; Part 03 `ew-portable-profile-scope`; Part 03 `ew-portable-profile-normative-references`; Part 04 `ew-packet-catalog-scope`; Part 04 `ew-packet-catalog-normative-references` |  | Part 03 `ew-portable-profile-scope`; Part 04 `ew-packet-catalog-scope` |
| R125 §3.1 | Part 00 `ew-numbered-part-ownership`; Part 02 `ew-registry-document`; Part 11 `ew-tier-2-language-selection` | Part 11 §9 |  |
| R125 §3.11 | Part 02 `ew-registry-self-description` | Part 02 §9.1; Part 11 §1 |  |
| R125 §3.2 | Part 11 `ew-tier-2-query-profile` | Part 11 §1; Part 11 §4 |  |
| R125 §3.3 | Part 11 `ew-tier-2-relation-environment` | Part 11 §2 |  |
| R125 §3.4 | Part 11 `ew-tier-2-type-binding` | Part 11 §2; Part 11 §3 |  |
| R125 §3.5 | Part 11 `ew-tier-2-deterministic-semantics` | Part 11 §2 |  |
| R125 §3.8 | Part 05 `ew-incomplete-validation`; Part 09 `ew-extension-verdicts`; Part 11 `ew-tier-2-evaluation-outcomes` | Part 05 §9.5 |  |
| R125 §3.9 | Part 05 `ew-validation-shim` | Part 11 §3 |  |
| R126 §3.1 | Part 02 `ew-core-logical-schema-scope`; Part 09 `ew-extension-definition` | Part 00 §2.1; Part 00 §2.2; Part 00 §8; Part 02 §2; Part 02 §9.4; Part 09 §5.5 |  |
| R126 §3.2 | Part 02 `ew-registry-document`; Part 09 `ew-extension-namespacing`; Part 09 `ew-core-extension-reference-direction` | Part 02 §2; Part 02 §9.2; Part 02 §9.4 |  |
| R126 §3.4 | Part 02 `ew-column-declaration`; Part 02 `ew-registry-conformance` | Part 02 §1; Part 02 §9.1 |  |
| R126 §3.5 | Part 02 `ew-registry-conformance`; Part 09 `ew-extension-definition` |  | Part 09 `ew-extension-definition` |
| R126 §3.6 | Part 02 `ew-table-resource-requirements`; Part 02 `ew-logical-references`; Part 02 `ew-identifier-semantics`; Part 02 `ew-registry-conformance` | Part 02 §8.3; Part 02 §8.4; Part 02 §8.6; Part 02 §9.3 |  |
| R126 §3.8 | Part 02 `ew-logical-column-naming`; Part 02 `ew-registry-conformance` | Part 02 §3 | Part 02 `ew-registry-conformance` |
| R126 §3.9 | Part 02 `ew-unit-and-clock-context`; Part 02 `ew-registry-conformance`; Part 02 `ew-logical-schema-normative-references` | Part 00 §2.2; Part 02 §9.3 |  |
| R127 §3.3 | Part 05 `ew-registry-conformance-boundary` | Part 02 §9.4 |  |
| R127 §3.5 | Part 05 `ew-registry-producer-boundary` | Part 05 §14.6 |  |
| R127 §3.6 | Part 05 `ew-validator-registry-boundary` | Part 05 §9.4 |  |
| R128 §3.1 | Part 02 `ew-resource-common-fields`; Part 02 `ew-registry-document`; Part 09 `ew-extension-definition` | Part 02 §2; Part 09 §5.2 |  |
| R128 §3.3 | Part 00 `ew-logical-standard`; Part 01 `ew-array-asset-concept`; Part 01 `ew-media-asset-concept`; Part 02 `ew-resource-kind` | Part 00 §3.1 |  |
| R128 §3.4 | Part 02 `ew-resource-instance-model` | Part 02 §2.3; Part 02 §2.6; Part 04 §4.1; Part 04 §8 |  |
| R128 §3.5 | Part 00 `ew-core-content-requirements`; Part 02 `ew-resource-presence`; Part 02 `ew-logical-references` | Part 02 §9.4; Part 04 §10 |  |
| R128 §3.6 | Part 02 `ew-resource-catalog-binding` | Part 04 §10 |  |
| R128 §3.7 | Part 02 `ew-resource-provenance-policy`; Part 06 `ew-analysis-rules` | Part 02 §2.1; Part 02 §2.2; Part 04 §10; Part 04 §4.1; Part 05 §14.5; Part 06 §5 |  |
| R128 §3.8 | Part 00 `ew-packet-catalog`; Part 04 `ew-packet-resource-entry-fields` | Part 04 §1; Part 04 §3; Part 04 §4.2; Part 04 §9; Part 05 §10; Part 05 §2; Part 05 §5.3; Part 12 §1; Part 12 §5 |  |
| R128 §3.9 | Part 02 `ew-registry-self-description`; Part 02 `ew-registry-conformance` | Part 04 §10; Part 05 §14.3; Part 05 §5.3 |  |
| R129 §3.1 | Part 03 `ew-portable-profile-scope` | Part 00 §2.3 |  |
| R129 §3.2 | Part 03 `ew-portable-profile-technologies` | Part 03 §1 |  |
| R129 §3.3 | Part 03 `ew-table-encoding`; Part 03 `ew-parquet-reader-floor` | Part 04 §6 |  |
| R129 §3.4 | Part 03 `ew-array-version`; Part 03 `ew-array-codecs` | Part 03 §12 |  |
| R129 §3.5 | Part 03 `ew-portable-profile-technologies` | Part 03 §6.4 |  |
| R129 §3.6 | Part 04 `ew-packet-identifiers`; Part 04 `ew-packet-resource-entry-fields`; Part 04 `ew-packet-codecs` | Part 05 §3.8 |  |
| R129 §3.7 | Part 05 `ew-reader-registry-independence` | Part 03 §6.1 |  |
| R129 §3.8 | Part 04 `ew-external-resource-verification`; Part 05 `ew-validation-shim` | Part 03 §6.4 |  |
| R129 §3.9 | Part 03 `ew-portable-profile-technologies` | Part 04 §5.3 |  |
| R130 §3.11 | Part 02 `ew-registry-self-description`; Part 02 `ew-registry-conformance` | Part 04 §10 |  |
| R130 §3.2 | Part 04 `ew-packet-identifiers`; Part 04 `ew-packet-resource-entry-fields`; Part 04 `ew-packet-validation-block` | Part 04 §7 |  |
| R130 §3.7 | Part 02 `ew-resource-provenance-policy`; Part 04 `ew-resource-lineage`; Part 06 `ew-analysis-rules`; Part 06 `ew-analysis-spike-events`; Part 06 `ew-analysis-materialization-provenance`; Part 05 `ew-conformance-classes`; Part 00 `ew-analysis-content-requirements` | Part 02 §2.2 |  |
| R134 §3.1 | Part 12 `ew-adapter-declaration-document`; Part 07 `ew-reference-object-model` |  | Part 07 `ew-reference-object-model` |
| R136 §3.3 | Part 04 `ew-packet-catalog-scope`; Part 04 `ew-packet-resource-entry-fields`; Part 04 `ew-prefix-resources`; Part 04 `ew-packet-manifest-conformance` | Part 12 §1 |  |
| R141 §3.4 | Part 00 `ew-packet-content-classes`; Part 02 `ew-resource-content-class` |  | Part 00 `ew-packet-content-classes` |
| R142 §3.1 | Part 12 `ew-build-supplied-values`; Part 12 `ew-adapter-declaration-document`; Part 05 `ew-source-declarations`; Part 05 `ew-recipe-check`; Part 07 `ew-reference-object-model` |  | Part 05 `ew-source-declarations` |
| R144 §3.1 | Part 12 `ew-adapter-interface-scope`; Part 12 `ew-adapter-declaration-document` | Part 00 §8; Part 12 §9 |  |
| R144 §3.4 | Part 12 `ew-adapter-run-report` | Part 12 §1 |  |
| R146 §3.1 | Part 05 `ew-validation-import-scope`; Part 05 `ew-conformance-classes`; Part 05 `ew-writer-acceptance-criteria` | Part 00 §2.4 |  |
| R146 §3.5 | Part 10 `ew-materialization-measurements`; Part 07 `ew-reference-performance-notes` | Part 06 §4 |  |
| R146 §3.8 | Part 05 `ew-validation-shim` | Part 02 §8.6 |  |
| R147 §3.8 | Part 02 `ew-registry-self-description`; Part 02 `ew-registry-conformance`; Part 02 `ew-core-logical-schema-scope` |  | Part 02 `ew-core-logical-schema-scope` |
| R148 §3.4 | Part 02 `ew-registry-self-description` |  | Part 02 `ew-registry-self-description` |
| R149 §3.3 | Part 11 `ew-tier-2-language-selection` | Part 02 §9.2 |  |
| R149 §3.4 | Part 02 `ew-registry-self-description`; Part 02 `ew-registry-conformance`; Part 02 `ew-core-logical-schema-scope` |  | Part 02 `ew-core-logical-schema-scope` |
| R150 §3.10 | Part 02 `ew-core-logical-schema-scope`; Part 02 `ew-registry-self-description`; Part 02 `ew-registry-conformance`; Part 05 `ew-recipe-purpose` |  | Part 02 `ew-core-logical-schema-scope`; Part 02 `ew-registry-conformance`; Part 05 `ew-recipe-purpose` |
| R151 §3.2 | Part 02 `ew-registry-self-description` |  | Part 02 `ew-registry-self-description` |
