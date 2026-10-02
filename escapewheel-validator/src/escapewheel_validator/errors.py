"""Every exception this package raises on purpose; each derives from :class:`ValidatorError`.

- :class:`ValidatorError` -- the base, under the reader's `EscapewheelError`.
- :class:`StoreUnreachable`, :class:`ResourceMissing` -- a store could not be reached, or was
  reached and holds nothing under the URI.
- :class:`UnknownAlgorithm` -- a digest was asked for in an algorithm that is not admitted.
- :class:`ReplacedPacketUnreadable` -- a path given as a replaced packet holds no published
  manifest that can be read.
- :class:`FormatCheckUnavailable` -- the installation cannot assert a format the manifest schema
  requires.
- :class:`LoweringFailed` -- a Tier 2 query cannot be given to the engine so that it evaluates as
  its language defines it.
- :class:`OrderViolation` -- a stream of batches leaves its declared order or repeats a key, as
  one :class:`OrderFault`.
- :class:`_Unmappable` -- a tick reaches no value on another clock; raised and caught inside the
  time-origin check.

:exc:`~escapewheel_validator.registry_result.RegistryRejected` and
:exc:`~escapewheel_validator.rule_language.RuleProfileError` are defined in the modules copied
from the specification's tree, outside this taxonomy.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from escapewheel_reader import EscapewheelError


class ValidatorError(EscapewheelError):
    """Base class for every error raised by this package."""


class StoreUnreachable(ValidatorError):
    """A store could not be reached, which says nothing about whether the packet is valid.

    Attributes
    ----------
    uri : str
        What was being reached.
    key : str or None
        The member being read, relative to `uri`; None where the failure concerns everything
        under the URI.
    """

    def __init__(self, message: str, *, uri: str, key: str | None = None) -> None:
        super().__init__(message)
        self.uri = uri
        self.key = key


class ResourceMissing(StoreUnreachable):
    """The store was reached and holds nothing under the URI."""


class UnknownAlgorithm(ValidatorError, ValueError):
    """A digest was asked for in an algorithm that is not admitted.

    Attributes
    ----------
    algorithm : str
        The name given.
    """

    def __init__(self, message: str, *, algorithm: str) -> None:
        super().__init__(message)
        self.algorithm = algorithm


class ReplacedPacketUnreadable(ValidatorError, FileNotFoundError):
    """A path given as a replaced packet holds no published manifest that can be read.

    Attributes
    ----------
    path : pathlib.Path
        The path given.
    """

    def __init__(self, message: str, *, path: Path) -> None:
        super().__init__(message)
        self.path = path


class FormatCheckUnavailable(ValidatorError):
    """The installation cannot assert a format the manifest schema requires.

    A fault in the environment and none in a packet: a format no checker is registered for
    passes every value.
    """


class LoweringFailed(ValidatorError):
    """A Tier 2 query cannot be given to the engine so that it evaluates as its language defines it.

    A limit of the lowering and no defect of the rule, whose evaluation is then incomplete
    (Part 11 §8).

    Attributes
    ----------
    expression : str or None
        The expression the lowering stops at, or None where it is the whole query.
    """

    def __init__(self, message: str, *, expression: str | None = None) -> None:
        super().__init__(message if expression is None else f"{message}: {expression}")
        self.expression = expression


class OrderFault(StrEnum):
    """How a row departs from the order its table declares."""

    #: The row sorts before the row above it.
    DESCENT = "descent"
    #: The row repeats the key of the row above it.
    REPEAT = "repeat"


class OrderViolation(ValidatorError):
    """A stream of batches is not in the order it declares, or repeats a key.

    Attributes
    ----------
    kind : OrderFault
        Which departure the row makes.
    row : int
        Index of the offending row in the stream. The message gives its position, which starts
        at 1.
    resource_id : str or None
        The table the stream is for, or None until a caller that knows it says so.
    """

    def __init__(self, kind: OrderFault, row: int, detail: str, *, resource_id: str | None = None) -> None:
        super().__init__(detail)
        self.kind = kind
        self.row = row
        self.resource_id = resource_id

    def __str__(self) -> str:
        """Name the table where it is known, then the row by position and what it does."""
        table = "" if self.resource_id is None else f"{self.resource_id}: "
        return f"{table}row {self.row + 1} {self.args[0]}"


class _Unmappable(ValidatorError):
    """A tick has no defined value on the clock it is being carried to."""


__all__ = [
    "FormatCheckUnavailable",
    "LoweringFailed",
    "OrderFault",
    "OrderViolation",
    "ReplacedPacketUnreadable",
    "ResourceMissing",
    "StoreUnreachable",
    "UnknownAlgorithm",
    "ValidatorError",
]
