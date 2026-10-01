"""Validate Escapewheel packets against the registries they bind (Part 05 §5).

:func:`validate` takes a packet opened by `escapewheel_reader` and returns a :class:`Report` of
findings and verdicts; ``escapewheel validate`` is the same call from the command line.
:func:`check_packet_manifest` runs the manifest phases alone, and :func:`check_registry_context`
checks a registry document with no packet in hand.

Its modules:

validator
    The layers over a packet, and the report they fill.
manifest
    Manifest conformance and registry binding (Part 04 §10).
generate
    Tier 1 checks generated from a registry's structure.
registry_document, rule_language
    A registry document's own conformance, and the static check of its Tier 2 SQL.
amendment
    An amendment compared with the version it supersedes.
stores
    Listings and digests of external resources, run only where a mode asks.
opaque
    Names in an opaque payload that some filesystem cannot hold.

A rule is SQL that returns offending rows, so the validator needs DuckDB where the reader does
not.
"""

from importlib.metadata import PackageNotFoundError, version

from .generate import Check, generate
from .manifest import manifest_schema
from .registry_document import (
    CheckedRegistryContext,
    RegistryRejected,
    RegistryResult,
    check_registry_context,
    check_registry_context_bytes,
)
from .validator import (
    Evaluation,
    Finding,
    OrderViolation,
    RegistryEvaluation,
    Report,
    check_packet_manifest,
    validate,
    verify_order,
)

try:
    __version__ = version("escapewheel-validator")
except PackageNotFoundError:  # pragma: no cover - only when running from a source tree
    __version__ = "0.0.0.dev0"

__all__ = [
    "Check",
    "CheckedRegistryContext",
    "Evaluation",
    "Finding",
    "OrderViolation",
    "RegistryEvaluation",
    "RegistryRejected",
    "RegistryResult",
    "Report",
    "__version__",
    "check_packet_manifest",
    "check_registry_context",
    "check_registry_context_bytes",
    "generate",
    "manifest_schema",
    "validate",
    "verify_order",
]
