"""What the specification's tools share.

Only the standard library is imported, so a tool outside the tree's environment can import this.
"""


class GenerationError(Exception):
    """A source a generator cannot produce its output from; the message names it and says why."""
