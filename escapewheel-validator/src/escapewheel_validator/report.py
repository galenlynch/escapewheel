"""What validating a packet found, and the verdicts that composes.

- :class:`Report` -- the findings, evaluations and registry results of one validation, each bound
  registry's verdict and the packet's, and the JSON a report is written as.
- :class:`Finding` -- one finding: its level, check ID, message and first offending rows, and
  the resource, column and counts it concerns.
- :class:`Evaluation` -- one Tier 2 evaluation outcome of a bound registry.
- :class:`RegistryEvaluation` -- one registry document's conformance result.

A check adds its findings through :meth:`Report.add`, under an entry of :mod:`.check_table`;
:meth:`Report.add_about` adds one about a resource, for the registry declaring it.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, overload

from . import check_table
from .check_table import CheckEntry
from .registry_document import (
    CheckedRegistryContext,
    RegistryResult,
)
from .vocabulary import EvaluationStatus, Level, RegistryState, Verdict

#: Verdicts in increasing severity.
VERDICTS = tuple(Verdict)

#: Rows a finding keeps, and values a message lists, of however many a check found.
ROW_CAP = 5


def _worst(verdicts: Iterable[Verdict]) -> Verdict:
    return max(verdicts, key=VERDICTS.index, default=Verdict.PASSED)


@dataclass(frozen=True)
class Finding:
    """One validation finding.

    Attributes
    ----------
    level : Level
        ``error``, ``warning``, or ``info``.
    check : str
        Identifier of the check that produced it.
    message : str
        What went wrong.
    rows : tuple
        Offending rows, truncated. For SQL checks these are the query's result.
    registry : str or None
        The bound registry this finding belongs to, or None where it belongs to the packet
        (Part 05 §9.5). An extension's findings never count against core's verdict, nor core's
        against an extension's.
    resource : str or None
        The resource the finding concerns, or None where it concerns the packet, a registry or
        several resources.
    column : str or None
        The one column of `resource` the finding concerns, or None where it concerns none or several.
    counts : Mapping of str to int
        What the finding counted, by name, where its message states a count. A count is of everything
        the check found, where `rows` holds only the first.
    """

    level: Level
    check: str
    message: str
    rows: tuple[tuple[str, ...], ...] = ()
    registry: str | None = None
    resource: str | None = None
    column: str | None = None
    counts: Mapping[str, int] = field(default_factory=dict, hash=False)


@dataclass(frozen=True)
class Evaluation:
    """A registry-level Tier 2 evaluation outcome distinct from packet findings."""

    registry: str
    status: EvaluationStatus
    rule: str | None = None
    detail: str = ""


@dataclass(frozen=True)
class RegistryEvaluation:
    """A complete registry-document result and the external role it evaluated."""

    subject: str
    result: RegistryResult
    directs_checks: bool = False
    core: bool = False


@dataclass
class Report:
    """The outcome of validating a packet.

    Attributes
    ----------
    findings : list of Finding
        Every finding, in the order the layers ran.
    advisory : bool
        Whether advisory rules were run (Part 02 §10.2). Recorded because an empty advisory
        result is otherwise ambiguous between "none fired" and "not asked for".
    bound : tuple of str
        The registry IDs the manifest binds, each of which receives a verdict.
    """

    findings: list[Finding] = field(default_factory=list)
    evaluations: list[Evaluation] = field(default_factory=list)
    registries: list[RegistryEvaluation] = field(default_factory=list)
    advisory: bool = False
    bound: tuple[str, ...] = ()
    #: Declaration ID -> the bound registry holding it, for attributing a finding about an entry.
    declared_by: dict[str, str] = field(default_factory=dict)
    #: Resource ID -> declaration ID, from the manifest's entries.
    declarations: dict[str, str] = field(default_factory=dict)

    @property
    def errors(self) -> int:
        """How many error-level findings were produced, whatever their subject."""
        return sum(f.level == Level.ERROR for f in self.findings)

    @property
    def warnings(self) -> int:
        """How many warning-level findings were produced."""
        return sum(f.level == Level.WARNING for f in self.findings)

    def verdict(self, registry: str | None = None) -> Verdict:
        """Return one bound registry's verdict, or the packet's where `registry` is None (Part 05 §9.5).

        A registry passes only once its required evaluation is recorded complete, so a registry whose
        evaluation was withheld, or never reached, is ``incomplete`` rather than ``passed``. The
        packet's verdict is the worst of its own findings' and every bound registry's.

        Advisory rules cannot be ``error``, so no verdict depends on the ``advisory`` flag.
        """
        if registry is None:
            failed = any(f.level == Level.ERROR and f.registry is None for f in self.findings)
            own = Verdict.FAILED if failed else Verdict.PASSED
            return _worst([own, *(self.verdict(name) for name in self.bound)])
        if any(f.level == Level.ERROR and f.registry == registry for f in self.findings):
            return Verdict.FAILED
        states = {item.result.state for item in self.registries if item.subject == registry}
        statuses = {e.status for e in self.evaluations if e.registry == registry}
        if RegistryState.INVALID in states or EvaluationStatus.INVALID in statuses:
            return Verdict.FAILED
        if states != {RegistryState.VALID} or statuses != {EvaluationStatus.COMPLETE}:
            return Verdict.INCOMPLETE
        return Verdict.PASSED

    @property
    def passed(self) -> bool:
        """Whether the packet's verdict is ``passed``, the only one supporting a conformance claim."""
        return self.verdict() == Verdict.PASSED

    def attribute(self, declared_by: Mapping[str, str], entries: Iterable[Any]) -> None:
        """Record which registry holds each declaration, and which declaration each entry names."""
        self.declared_by = dict(declared_by)
        self.declarations = {entry.resource_id: entry.declaration_id for entry in entries}

    def owner(self, declaration_id: str) -> str | None:
        """Return the bound registry holding a declaration, or None where none holds it.

        A declaration no directing registry exposes is attributed by namespace to a bound extension,
        so a finding about a withheld extension's entry is still that extension's.
        """
        if (registry := self.declared_by.get(declaration_id)) is not None:
            return registry
        namespace = declaration_id.split(".", 1)[0]
        return namespace if namespace in self.bound and namespace != "core" else None

    def resource_owner(self, resource_id: str) -> str | None:
        """Return the registry declaring the resource an entry locates, or None for the packet."""
        declaration = self.declarations.get(resource_id, resource_id)
        return self.owner(declaration)

    def record_evaluation(
        self, registry: str, status: EvaluationStatus, *, rule: str | None = None, detail: str = ""
    ) -> None:
        """Record a Tier 2 outcome without turning validator inability into a finding."""
        self.evaluations.append(Evaluation(registry, EvaluationStatus(status), rule, detail))

    def complete(self, registry: str) -> None:
        """Record a registry's evaluation complete, unless an outcome recorded for it says otherwise.

        Called once every check the registry directs has run, since :meth:`verdict` passes a
        registry only where its evaluation is recorded complete.
        """
        if not any(e.registry == registry and e.status != EvaluationStatus.COMPLETE for e in self.evaluations):
            self.record_evaluation(registry, EvaluationStatus.COMPLETE)

    def record_registry(
        self, subject: str, context: CheckedRegistryContext, *, directs_checks: bool = False, core: bool = False
    ) -> None:
        """Retain a complete result, labelled by registry ID, and expose its invalid outcomes."""
        self.registries.append(RegistryEvaluation(subject, context.result, directs_checks, core))
        for outcome in context.result.findings:
            self.add(
                check_table.registry_outcome(outcome.id),
                f"{subject} registry {outcome.instance or '<root>'}: "
                f"{outcome.detail or outcome.reason or outcome.state}",
                registry=subject,
            )

    @overload
    def add(
        self,
        check: CheckEntry,
        message: str,
        /,
        rows: Iterable[Sequence[Any]] = (),
        registry: str | None = None,
        *,
        resource: str | None = None,
        column: str | None = None,
        counts: Mapping[str, int] | None = None,
    ) -> None: ...

    @overload
    def add(
        self,
        level: str,
        check: str,
        message: str,
        /,
        rows: Iterable[Sequence[Any]] = (),
        registry: str | None = None,
        *,
        resource: str | None = None,
        column: str | None = None,
        counts: Mapping[str, int] | None = None,
    ) -> None: ...

    def add(self, check: CheckEntry | str, *given: Any, **named: Any) -> None:
        """Record a finding under an entry of the check table, at the entry's level.

        A caller outside this package whose check the table does not hold gives a level and a check
        ID in the entry's place, as ``add(level, check, message, ...)``.

        Parameters
        ----------
        check : CheckEntry
            The check, from :mod:`.check_table`; `CheckEntry.at` gives it at another level.
        message : str
            What went wrong.
        rows : iterable, optional
            Offending rows; only the first `ROW_CAP` are kept.
        registry : str, optional
            The bound registry the finding belongs to; None for the packet.
        resource, column : str, optional
            The resource, and the one column of it, the finding concerns.
        counts : Mapping of str to int, optional
            What the finding counted, by name.
        """
        if isinstance(check, CheckEntry):
            self._record(check.level, check.id, *given, **named)
        else:
            self._record(Level(check), *given, **named)

    def _record(
        self,
        level: Level,
        check: str,
        message: str,
        rows: Iterable[Sequence[Any]] = (),
        registry: str | None = None,
        *,
        resource: str | None = None,
        column: str | None = None,
        counts: Mapping[str, int] | None = None,
    ) -> None:
        """Append one finding, keeping its first `ROW_CAP` rows as strings."""
        kept = tuple(tuple(str(v) for v in row) for row in itertools.islice(rows, ROW_CAP))
        self.findings.append(Finding(level, check, message, kept, registry, resource, column, dict(counts or {})))

    def add_about(
        self,
        resource_id: str,
        check: CheckEntry,
        message: str,
        rows: Iterable[Sequence[Any]] = (),
        *,
        column: str | None = None,
        counts: Mapping[str, int] | None = None,
    ) -> None:
        """Record a finding about one resource, for the registry declaring it.

        Parameters
        ----------
        resource_id : str
            The resource the finding concerns.
        check, message, rows, column, counts
            As :meth:`add` takes them.
        """
        self.add(
            check,
            message,
            rows,
            self.resource_owner(resource_id),
            resource=resource_id,
            column=column,
            counts=counts,
        )

    def to_dict(self, packet_id: str) -> dict[str, Any]:
        """Render the report as the JSON structure Part 05 describes.

        ``status`` is the packet's verdict and ``verdicts`` each bound registry's. A finding whose
        ``registry`` is null belongs to the packet. A finding's ``resource`` and ``column`` are null,
        and its ``counts`` empty, where it names none.

        Parameters
        ----------
        packet_id : str
            The packet this report concerns.

        Returns
        -------
        dict
            The report.
        """
        return {
            "packet_id": packet_id,
            "status": self.verdict(),
            "verdicts": {name: self.verdict(name) for name in self.bound},
            "advisory": self.advisory,
            "validator": {"name": "escapewheel_validator", "version": _version()},
            "summary": {"errors": self.errors, "warnings": self.warnings},
            "findings": [
                {
                    "level": f.level,
                    "check": f.check,
                    "message": f.message,
                    "rows": [list(r) for r in f.rows],
                    "registry": f.registry,
                    "resource": f.resource,
                    "column": f.column,
                    "counts": dict(f.counts),
                }
                for f in self.findings
            ],
            "evaluations": [
                {"registry": e.registry, "status": e.status, "rule": e.rule, "detail": e.detail}
                for e in self.evaluations
            ],
            "registries": [
                {
                    "subject": item.subject,
                    "core": item.core,
                    "directs_checks": item.directs_checks,
                    "result": item.result.to_dict(),
                }
                for item in self.registries
            ],
        }


def _version() -> str:
    from . import __version__

    return __version__


__all__ = ["Evaluation", "Finding", "RegistryEvaluation", "Report"]
