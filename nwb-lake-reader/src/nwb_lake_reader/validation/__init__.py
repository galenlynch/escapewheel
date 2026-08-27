"""Packet validation.

Requires the ``validate`` extra, which brings in DuckDB because Tier 1 and Tier 2 checks are
SQL. A packet can be read without it — see :mod:`nwb_lake_reader.packet`.
"""

from __future__ import annotations

from .generate import Check, generate
from .validator import Finding, Report, validate

__all__ = ["Check", "Finding", "Report", "generate", "validate"]
