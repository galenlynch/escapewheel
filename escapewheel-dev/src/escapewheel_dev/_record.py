"""The base of this library's records, whose missing attributes name the ones that exist."""

import dataclasses
from typing import TYPE_CHECKING


def field_names(record: type) -> tuple[str, ...]:
    """Return a record type's fields, then its public properties, in declaration order."""
    names = [field.name for field in dataclasses.fields(record)] if dataclasses.is_dataclass(record) else []
    for klass in reversed(record.__mro__):
        names += [name for name, value in vars(klass).items() if isinstance(value, property) and name[0] != "_"]
    return tuple(dict.fromkeys(names))


class Record:
    """A record whose missing attribute is reported with the names it has, so a guess fails informatively."""

    # Hidden from type checkers, which would otherwise accept any attribute name.
    if not TYPE_CHECKING:

        def __getattr__(self, name: str) -> object:
            if name.startswith("__"):
                raise AttributeError(name)
            raise AttributeError(
                f"{type(self).__name__} has no attribute {name!r}; it has {', '.join(field_names(type(self)))}"
            )
