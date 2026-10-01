API Reference
=============

.. currentmodule:: escapewheel_validator

Every name here is importable from ``escapewheel_validator``. Open a packet with
``escapewheel_reader.open_packet`` and pass it to :func:`validate`.

Validating a packet
-------------------

.. autosummary::
   :toctree: generated

   validate
   check_packet_manifest
   Report
   Finding
   Evaluation
   RegistryEvaluation

Checking a registry document
----------------------------

.. autosummary::
   :toctree: generated

   check_registry_context
   check_registry_context_bytes
   CheckedRegistryContext
   RegistryResult
   RegistryRejected

Generated checks and physical order
-----------------------------------

.. autosummary::
   :toctree: generated

   generate
   Check
   verify_order
   manifest_schema

Errors
------

.. autosummary::
   :toctree: generated

   ValidatorError
   StoreUnreachable
   ResourceMissing
   OrderViolation
   OrderFault

Modules
-------

Each module's page lists what it holds beyond the names above.

.. autosummary::
   :toctree: generated

   validator
   manifest
   generate
   registry_document
   rule_language
   amendment
   errors
   stores
   opaque
