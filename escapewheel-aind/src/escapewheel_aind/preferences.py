"""Which resources these adapters win when a build has more than one producer for them.

A preference names the source that knows most about a resource (Part 05 §3.4), and it is declared
by whoever ships that source: the writer cannot check a preference naming a kind it can neither
import nor see produce the resource. It reaches a build through the `escapewheel.preferences`
entry-point group, which `escapewheel_writer.recipe.preferences` merges with its own.
"""

from __future__ import annotations

#: `subject.json` is the record `general/subject` is a projection of: it carries a
#: `background_strain` key the projection lacks and a date of birth with no timezone. Safe to
#: declare because Part 05 §3.4 refuses a build where preferring it drops a fact the NWB stated --
#: so the preference costs nothing where the NWB knows more, and is refused rather than silent.
PREFERRED: dict[str, str] = {
    "core.subjects": "session",
}

__all__ = ["PREFERRED"]
