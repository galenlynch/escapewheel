"""The result of checking one registry document, and the context binding it to its input."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import Any

RESULT_SCHEMA_ID = "https://escapewheel.org/schemas/registry-result/0.1.0"

PHASES = (
    "json",
    "schema_selection",
    "shape",
    "contract_selection",
    "semantic",
    "rule_static",
    "external_domain",
)


@dataclass(frozen=True)
class Outcome:
    """One non-passing check in the abstract registry result."""

    state: str
    id: str
    instance: str = ""
    owner: str | None = None
    reason: str | None = None
    schema_location: str | None = None
    detail: str | None = dataclass_field(default=None, compare=False)

    def to_dict(self) -> dict[str, Any]:
        """Return this outcome's portable Part 02 representation."""
        result: dict[str, Any] = {"state": self.state, "id": self.id, "instance": self.instance}
        for name in ("owner", "reason", "schema_location", "detail"):
            if (value := getattr(self, name)) is not None:
                result[name] = value
        return result


@dataclass(frozen=True)
class PhaseRecord:
    """The state and ordered non-passing outcomes of one contract phase."""

    phase: str
    state: str
    outcomes: tuple[Outcome, ...] = ()
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return this phase's portable Part 02 representation."""
        result: dict[str, Any] = {
            "phase": self.phase,
            "state": self.state,
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
        }
        if self.reason is not None:
            result["reason"] = self.reason
        return result


@dataclass(frozen=True)
class RegistryResult:
    """The complete language-neutral result for one registry document."""

    descriptor_id: str | None
    state: str
    phases: tuple[PhaseRecord, ...]

    @property
    def findings(self) -> tuple[Outcome, ...]:
        """Return exactly the invalid outcomes."""
        return tuple(outcome for phase in self.phases for outcome in phase.outcomes if outcome.state == "invalid")

    def to_dict(self) -> dict[str, Any]:
        """Return the portable representation incorporated by Part 02 §9.5."""
        return {
            "$schema": RESULT_SCHEMA_ID,
            "descriptor_id": self.descriptor_id,
            "state": self.state,
            "phases": [phase.to_dict() for phase in self.phases],
        }


def freeze(value: Any) -> Any:
    """Return `value` with each mapping read-only and each list a tuple."""
    if isinstance(value, Mapping):
        from types import MappingProxyType

        return MappingProxyType({key: freeze(child) for key, child in value.items()})
    if isinstance(value, list):
        return tuple(freeze(child) for child in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_thaw(child) for child in value]
    return value


@dataclass(frozen=True)
class CheckedRegistryContext(Mapping[str, Any]):
    """One registry result bound to immutable input and evaluation context."""

    input_kind: str
    exact_input: Any
    decoded: Any
    result: RegistryResult
    descriptors: tuple[str, ...]
    external_domains: tuple[str, ...]
    core: CheckedRegistryContext | None = None

    @property
    def document(self) -> Any:
        """Return an isolated ordinary-Python copy of the checked decoded value."""
        return _thaw(self.decoded)

    def __getitem__(self, key: str) -> Any:
        """Read one member from an isolated copy of the checked document."""
        document = self.document
        if not isinstance(document, Mapping):
            raise KeyError(key)
        return document[key]

    def __iter__(self) -> Iterator[str]:
        """Iterate the checked document's root member names."""
        document = self.document
        return iter(document if isinstance(document, Mapping) else {})

    def __len__(self) -> int:
        """Return the checked document's number of root members."""
        document = self.document
        return len(document) if isinstance(document, Mapping) else 0

    def __deepcopy__(self, memo: dict[int, Any]) -> Any:
        """Materialize a mutable copy without copying locks or mapping proxies."""
        del memo
        return self.document


class RegistryRejected(ValueError):
    """A production boundary received a non-valid registry context."""

    def __init__(self, subject: str, context: CheckedRegistryContext) -> None:
        self.subject = subject
        self.context = context
        self.result = context.result
        super().__init__(f"{subject} registry is {context.result.state}")


def json_pointer(parts: Iterable[Any]) -> str:
    """Return the JSON Pointer of `parts`, a `tables` path naming its resource's table payload."""
    parts = tuple(parts)
    if len(parts) >= 2 and parts[0] == "tables":
        parts = ("resources", parts[1], "table", *parts[2:])
    return "".join(f"/{str(part).replace('~', '~0').replace('/', '~1')}" for part in parts)


def invalid(invariant: str, pointer: str, owner: str | None, detail: str) -> Outcome:
    """Return an invalid outcome of `invariant` at `pointer`."""
    return Outcome("invalid", invariant, pointer, owner, detail=detail)


__all__ = [
    "PHASES",
    "RESULT_SCHEMA_ID",
    "CheckedRegistryContext",
    "Outcome",
    "PhaseRecord",
    "RegistryRejected",
    "RegistryResult",
    "freeze",
    "invalid",
    "json_pointer",
]
