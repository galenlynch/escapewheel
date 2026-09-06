"""Validate Escapewheel packets against the registry they embed.

Rules are data, not code (R2 §7): Tier 1 checks are generated from each table's structure,
and Tier 2 rules are the SQL the registry carries inline. The execution contract is the whole
protocol -- a check's query returns offending rows, so empty is a pass and non-empty is a
failure whose rows are the finding.

Validation needs DuckDB because the rules are SQL. Reading does not, which is why this is a
separate package: `escapewheel_reader` opens a packet with PyArrow alone.
"""

from importlib.metadata import PackageNotFoundError, version

from .generate import Check, generate
from .validator import Finding, OrderViolation, Report, validate, verify_order

try:
    __version__ = version("escapewheel-validator")
except PackageNotFoundError:  # pragma: no cover - only when running from a source tree
    __version__ = "0.0.0.dev0"

__all__ = [
    "Check",
    "Finding",
    "OrderViolation",
    "Report",
    "__version__",
    "generate",
    "validate",
    "verify_order",
]
