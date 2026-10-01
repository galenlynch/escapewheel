"""The exception for a source defect that stops a build.

- :exc:`SourceDefect` -- a source cannot supply what it was asked for, which stops the build.

Every adapter and the build raise it, so it has a module of its own.
"""

from __future__ import annotations


class SourceDefect(ValueError):
    """A source cannot supply what it was asked for, and the build cannot proceed past it.

    Carried as an exception rather than a note because it stops a build (Part 05 §4.4), where what
    an adapter worked around goes in the run's report (Part 12 §9).
    """


__all__ = ["SourceDefect"]
