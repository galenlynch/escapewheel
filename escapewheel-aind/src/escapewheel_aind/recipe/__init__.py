"""Draft a recipe for one AIND ecephys session from its public assets.

Its modules:

assets
    A session's assets, as DocDB and Code Ocean record them, and which of them a recipe reads.
facts
    The `[session]` and `[subject]` facts, from the raw asset's DocDB v2 record.
catalog
    The lookups: DocDB, Code Ocean, and one-level listings of known S3 prefixes.
draft
    The recipe's sources and their ownership, rendered as TOML.
cli
    ``escapewheel-aind-recipe``.

Its lookups need the ``recipe`` extra, which the adapters do not.
"""

__all__: list[str] = []
