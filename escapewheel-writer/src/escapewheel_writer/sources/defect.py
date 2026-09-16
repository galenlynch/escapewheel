"""What a source cannot proceed past.

Here rather than in any one adapter because it is raised by all of them and by the build: a source
kind nothing can import, a root nothing supplied, a command that is not an argument list, a declared
Parquet file that is absent, an NWB holding no units group. It lived in `nwb.py` while six adapters
and two build modules imported it from there, which read as though a failure to open a Harp stream
were an NWB's.
"""

from __future__ import annotations


class SourceDefect(ValueError):
    """A source cannot supply what it was asked for, and the build cannot proceed past it.

    Carried as an exception rather than a note because it stops a build (Part 05 §4.4), where what
    an adapter worked around goes in the run's report (Part 09 §5.8).
    """


__all__ = ["SourceDefect"]
