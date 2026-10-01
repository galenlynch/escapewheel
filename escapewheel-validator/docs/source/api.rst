API Reference
=============

.. currentmodule:: escapewheel_validator

Two tiers of names are public. The user tier is importable from ``escapewheel_validator``: open a
packet with ``escapewheel_reader.open_packet`` and pass it to :func:`validate`. The support tier is
for another Escapewheel package, and each of its names is imported from the module shown. A name
this page does not list is the validator's own and may change without notice.

Validating a packet
-------------------

.. autosummary::
   :toctree: generated

   validate
   Verification
   check_packet_manifest
   Report
   Finding
   Evaluation
   RegistryEvaluation

Vocabularies
------------

Each is a string enumeration whose members equal the strings a report's JSON carries.

.. autosummary::
   :toctree: generated

   Level
   Verdict
   EvaluationStatus
   RegistryState

Check IDs
---------

Every check ID the package declares is an entry of :mod:`check_table`: a constant for each fixed
ID, and a function for each family whose IDs are built from a resource or a column.
:meth:`Report.add` takes an entry.

.. autosummary::
   :toctree: generated

   check_table
   CheckEntry
   Scope

Checking a registry document
----------------------------

.. autosummary::
   :toctree: generated

   check_registry_context
   check_registry_context_bytes
   CheckedRegistryContext
   RegistryResult
   RegistryRejected

Schemas
-------

.. autosummary::
   :toctree: generated

   manifest_schema
   registry_meta_schema

Errors
------

.. autosummary::
   :toctree: generated

   ValidatorError
   StoreUnreachable
   ResourceMissing
   UnknownAlgorithm
   ReplacedPacketUnreadable
   FormatCheckUnavailable
   OrderViolation
   OrderFault

Support tier
------------

For the writer and an adapter package. Every user-tier name is also importable from the module
that defines it.

.. autosummary::
   :toctree: generated

   shim.ordering.verify_order
   generate.adjacency_settles_uniqueness
   amendment.IDENTITY
   amendment.PREFERENCES
   amendment.DERIVED
   amendment.PROVENANCE
   amendment.Version
   amendment.absent
   amendment.chain_reaches
   amendment.semver
   manifest.format_checker
   stores.listing
   stores.Listing
   stores.Member
   stores.StoreDigest
   stores.store_digest
   stores.listing_digest
   stores.digest
   stores.digest_resource
   stores.Digested
   scripts.cli.register

The two checkers copied from the specification's tree are in the support tier whole, each with the
names its source exports. ``registry_document`` exports the result model it takes from
``registry_result``; that module, ``registry_invariants`` and ``registry_phases`` are what it is
built from, and are copied with it for its own use.

.. autosummary::
   :toctree: generated

   registry_document
   rule_language

Modules
-------

Each module's page lists what it holds beyond the names above.

.. autosummary::
   :toctree: generated

   validator
   report
   registry_types
   manifest
   generate
   amendment
   errors
   stores
   vocabulary
   verification
   shim.ordering
   scripts.cli
