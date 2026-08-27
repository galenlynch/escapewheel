"""Packet validation.

Requires the ``validate`` extra, which brings in DuckDB. Reading a packet does not.
"""

from __future__ import annotations

from .generate import Check, generate
from .validator import Finding, Report, validate

__all__ = ["Check", "Finding", "Report", "generate", "validate"]
