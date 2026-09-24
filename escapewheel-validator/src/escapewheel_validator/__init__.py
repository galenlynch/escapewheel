"""Validate Escapewheel packets against the registries they bind.

Rules are data, not code: Tier 1 checks are generated from each table's structure, and Tier 2
rules are parsed against the registry's versioned portable language before execution. A completed
query returns a typed bag of offending rows; invalid, unsupported, and incomplete evaluation are
reported separately from packet findings.

Validation needs DuckDB because the rules are SQL. Reading does not, which is why this is a
separate package: `escapewheel_reader` opens a packet with PyArrow alone.
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
