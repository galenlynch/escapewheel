# Part 09 — Metadata Minimalism and Extensions

Normative.

## 1. Scope

This part defines how much metadata core requires, where richer metadata belongs, and how an extension declares it.

## 2. Tiers

| tier | contents | location |
|---|---|---|
| 1 | packet-level facts | the manifest |
| 2 | facts needed to interpret, validate, join, or reproduce | core tables |
| 3 | domain-rich, lab-specific facts | an extension's tables |
| 4 | human-readable context | `docs/` sidecars |
| 3-4 | such facts stated about one row, in the source's own vocabulary | that table's `metadata` column |

## 3. Core inclusion rule

A field belongs in core only if common interpretation, validation, joining, or analysis would break without it.

A field SHOULD be in core when it is needed to interpret units, clocks, channels, arrays, or spike times; to validate a required relationship; to join tables; to filter or group a common analysis; to reproduce processing or curation; or to trace provenance.

A field SHOULD be in an extension or a sidecar when it is institutional, administrative, lab-specific, rarely queried, free-form, procedural but not required for analysis, or biologically rich but not required to interpret the recording.

## 4. Required minimum

A conforming packet requires only what is needed to identify, interpret, validate, query, and reproduce. The registry states the minimum per resource; this part does not restate it.

An import MUST NOT fail because optional extension metadata is absent.

## 5. Extensions

<a id="ew-extension-definition" data-spec-anchor="canonical"></a>
### 5.1 What an extension is

An extension is a registry document in the extension class defined by Part 02 §9.1. Its
`extension_id` is its namespace, and its full `logical_standard_version` selects the core context
against which core-dependent invariants run. It declares logical resources of any Part 02 kind,
including table columns, references, and rules where the kind is `table`, on the same applicable
terms as core.

An extension needs no code. Its registry document supplies the logical contract; physical-profile
support determines how a particular payload is read or written. Neither imports anything of the
reference implementation.

<a id="ew-extension-namespacing" data-spec-anchor="canonical"></a>
### 5.2 Namespacing

Every declaration identifier in an extension registry MUST begin with the namespace equal to its
`extension_id`. The extension owns only that namespace. An extension namespace MUST NOT be `core`,
`analysis`, or `nwb`.

<a id="ew-extension-registration" data-spec-anchor="canonical"></a>
### 5.3 Registration

A packet carrying extension resources MUST bind each extension registry that declares them with a
registry descriptor whose role is `extension`, under
[Part 04 §8](04_packet_catalog.md#ew-packet-registry-bindings).
[Part 04 §10](04_packet_catalog.md#ew-packet-manifest-conformance) owns the checks of that
binding. A validator MUST NOT require an extension registry in order to validate core.

<a id="ew-extension-verdicts" data-spec-anchor="canonical"></a>
### 5.4 Separate verdicts

An extension is validated on core's terms under
[Part 05 §5.4](05_validation_and_import.md#ew-validation-extensions), and its verdict and core's are
composed under [Part 05 §9.5](05_validation_and_import.md#ew-verdict-composition), so an extension's
findings never change core's verdict and core's findings never change an extension's. A consumer
MAY read core from a packet whose extension fails, and MUST NOT read that packet's verdict as though
the failure were external to it.

<a id="ew-extension-versioning" data-spec-anchor="canonical"></a>
### 5.5 Independent versioning

An extension's `registry_version` is that extension registry's own version. It advances
independently of the core registry's `registry_version`; the core specification neither selects
nor assigns it.

<a id="ew-code-free-extension-handling" data-spec-anchor="canonical"></a>
### 5.6 A writer requires no code of an extension

A writer MUST be able to interpret every extension logical declaration from the registry document
without extension plugin code. It MUST be able to build extension tables given that document and
their rows as files. This requirement does not grant generic physical support for every possible
opaque payload or adapter protocol; those capabilities remain profile and adapter concerns. A
writer MUST NOT require the extension itself to be installed, importable, or resolvable in the
writer's environment.

A writer MAY accept an extension that ships code — an adapter registered under an entry-point group, or a registry document loaded from an installed distribution — and MUST NOT treat either as the ordinary case. That is what turns §5.1's "needs no code" from a possibility into a promise.

### 5.7 How an extension's document and rows reach a build

An extension delivers a registry document in the format of Part 02 and, per table it declares, rows. Parquet written under the `delivery_root` a build supplies (`files-v0.1`) is one way and remains the route every implementation supports; an extension MAY deliver over any protocol of the group its profile names (Part 12 §3), since what the requirement rests on is a dependency closure that must not become the writer's and the process boundary is what answers that. Where a raw source needs converting first, a recipe names a command: an argument list carried as a list and run in the source's own root, never a shell line (Part 05 §3.7), so an extension isolates its dependencies however it likes and a build states no opinion about how.

An extension's registry document and Part 12 §7's declaration document are different things for different readers, and neither substitutes for the other: the first declares logical resources, while the second declares what the adapter carrying them produces, states, needs, and speaks.

Rows arrive carrying identifiers as the names their source used, and a writer numbers them, so an extension neither knows nor needs the packet's numbering.

How the registry document is produced is the extension's business, but an extension MUST NOT derive it from the rows it delivers for the packet being built. A declaration derived from one packet's data cannot disagree with that data, so it declares nothing, and two packets whose extensions each derived one no longer share a schema. Part 02 §5's three presence states are what carry the difference between a column this run did not compute and one the extension does not have.

An extension's command MUST produce the same rows from the same inputs, and MUST NOT let wall-clock time, an unfixed random seed, or iteration over an unordered collection reach a value it writes. Which program the command resolves to is the recipe author's: pinning library versions so two runs agree byte for byte is a build property, and a validator MUST NOT judge a packet non-conforming for lacking one. An extension that cannot be a function of its inputs delivers a file produced beforehand rather than a command the build runs.

## 6. Direction of reference

<a id="ew-core-extension-reference-direction" data-spec-anchor="canonical"></a>
### 6.1 Core does not reference an extension

A core registry reference or declaration dependency MUST target the core registry. An extension
registry reference, dependency, or catalog binding MUST target either its selected core context or
the same extension registry. A core table MUST NOT declare a foreign key into an extension table,
and an extension MUST NOT reference another extension.

The reasons are separable verdicts (§5.4) and independent versioning (§5.5). "Interpretable when no extension is present" is *not* among them: a packet embeds its extension registries, so they are present whenever the resources are.

<a id="ew-core-extension-discrimination" data-spec-anchor="canonical"></a>
### 6.2 Core may name an extension

A core table MAY name an extension resource through a `discriminator` column (Part 02 §8.3). A
consumer resolves a value by reading the named registry resource, taking its primary key, and
applying the declared discriminator shape.

**A discriminator names without depending.** It creates neither a shared verdict nor a version coupling, which is why it is the one mechanism core is allowed.

## 7. Promotion

A field moves from an extension into core through a revision of this specification, not by a writer deciding to emit it. Promotion is justified by §3's rule and by evidence that more than one producer needs it.

## 8. Anti-patterns

A reader MUST NOT make an extension's schema required in order to open core tables or arrays.

A writer MUST NOT:

- hide analysis-critical metadata inside free-form JSON;
- use an object path as the only way to identify a resource;
- treat the manifest as a store for all metadata.

A build MUST NOT block an import because optional institutional metadata is incomplete.

### 8.1 Untyped accretion

Core MUST NOT contain a table whose purpose is to hold arbitrary name-value pairs.

Nothing constrains the name, type, or meaning of what accretes in such a table, so two packets cannot be compared and neither can be checked. `core.trial_tags` was the one place this format permitted it and is withdrawn.

An extension needing a multi-valued attribute declares its own typed child table, as Part 02 §5.2 requires of everything else.
