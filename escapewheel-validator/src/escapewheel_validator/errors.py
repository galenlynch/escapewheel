"""Every exception this package raises on purpose; each derives from :class:`ValidatorError`.

- :class:`ValidatorError` -- the base, under the reader's `EscapewheelError`.
- :class:`StoreUnreachable`, :class:`ResourceMissing` -- a store could not be reached, or was
  reached and holds nothing under the URI.
- :class:`OrderViolation` -- a stream of batches leaves its declared order or repeats a key.
- :class:`_Unmappable` -- a tick reaches no value on another clock; raised and caught inside the
  time-origin check.

:exc:`~escapewheel_validator.registry_document.RegistryRejected` and
:exc:`~escapewheel_validator.rule_language.RuleProfileError` are defined in the modules copied
from the specification's tree, outside this taxonomy.
"""

from __future__ import annotations

from escapewheel_reader import EscapewheelError


class ValidatorError(EscapewheelError):
    """Base class for every error raised by this package."""


class StoreUnreachable(ValidatorError):
    """A store could not be reached, which says nothing about whether the packet is valid."""


class ResourceMissing(StoreUnreachable):
    """The store was reached and holds nothing under the URI."""


class OrderViolation(ValidatorError):
    """A stream of batches is not in the order it declares, or repeats a key."""


class _Unmappable(ValidatorError):
    """A tick has no defined value on the clock it is being carried to."""
