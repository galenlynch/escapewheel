"""Validate Escapewheel packets against the registries they bind (Part 05 §5).

:func:`validate` takes a packet opened by `escapewheel_reader` and returns a :class:`Report` of
findings and verdicts; ``escapewheel validate`` is the same call from the command line.
:func:`check_packet_manifest` runs the manifest phases alone, and :func:`check_registry_context`
checks a registry document with no packet in hand. :func:`manifest_schema` and
:func:`registry_meta_schema` are the two schemas those read. Every error the package raises on purpose is a
:class:`ValidatorError`. A finding's level, a verdict, an evaluation's status and a registry result's
state are members of :class:`Level`, :class:`Verdict`, :class:`EvaluationStatus` and
:class:`RegistryState`, each equal to the string a report's JSON carries. Every check a finding is
reported under is a :class:`CheckEntry` of :mod:`.check_table`, at a :class:`Scope`.

Its modules:

validator
    The layers over a packet.
report
    The findings, evaluations and registry results of a validation, and its verdicts.
registry_types
    What a registry document's column types and declarations mean to the layers reading them.
manifest
    Manifest conformance and registry binding (Part 04 §10).
declarations
    The manifest's entries against the declarations and the sources they name.
shim
    The checks of how a packet is stored, which no query over its tables can make.
generate
    Tier 1 checks generated from a registry's structure.
rules
    Running the generated checks and a registry's Tier 2 rules over the packet's tables.
registry_document, rule_language
    A registry document's own conformance, and the static check of its Tier 2 SQL.
amendment
    An amendment compared with the version it supersedes.
check_table
    Every check ID the package declares, with its level, its scope and whether a part names it.
errors
    Every exception the package raises on purpose.
stores
    Listings and digests of external resources, run only where a mode asks.
opaque
    Names in an opaque payload that some filesystem cannot hold.
vocabulary
    The levels, verdicts, evaluation statuses and registry states a report is written in.

A rule is SQL that returns offending rows, so the validator needs DuckDB where the reader does
not.

The names here are the user tier. A name another Escapewheel package needs is in the ``__all__`` of
the module that defines it, and is imported from that module.
"""

from importlib.metadata import PackageNotFoundError, version

from . import check_table
from .check_table import CheckEntry, Scope
from .errors import (
    FormatCheckUnavailable,
    OrderFault,
    OrderViolation,
    ReplacedPacketUnreadable,
    ResourceMissing,
    StoreUnreachable,
    UnknownAlgorithm,
    ValidatorError,
)
from .manifest import manifest_schema
from .registry_document import (
    CheckedRegistryContext,
    RegistryRejected,
    RegistryResult,
    check_registry_context,
    check_registry_context_bytes,
)
from .registry_types import registry_meta_schema
from .report import Evaluation, Finding, RegistryEvaluation, Report
from .validator import check_packet_manifest, validate
from .vocabulary import EvaluationStatus, Level, RegistryState, Verdict

try:
    __version__ = version("escapewheel-validator")
except PackageNotFoundError:  # pragma: no cover - only when running from a source tree
    __version__ = "0.0.0.dev0"

__all__ = [
    "CheckEntry",
    "CheckedRegistryContext",
    "Evaluation",
    "EvaluationStatus",
    "Finding",
    "FormatCheckUnavailable",
    "Level",
    "OrderFault",
    "OrderViolation",
    "RegistryEvaluation",
    "RegistryRejected",
    "RegistryResult",
    "RegistryState",
    "ReplacedPacketUnreadable",
    "Report",
    "ResourceMissing",
    "Scope",
    "StoreUnreachable",
    "UnknownAlgorithm",
    "ValidatorError",
    "Verdict",
    "__version__",
    "check_packet_manifest",
    "check_registry_context",
    "check_registry_context_bytes",
    "check_table",
    "manifest_schema",
    "registry_meta_schema",
    "validate",
]
