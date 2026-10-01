"""The rows a build records about itself (Part 05 §7, §12).

- :func:`import_run` -- the import's processing run and its inputs.
- :func:`preferred_runs` -- a row per `preferred_run` entry of the recipe.
- :func:`source_roots` -- the roots a recipe's sources state.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from escapewheel_reader.resource_ids import CORE_PROCESSING_RUNS, CORE_SESSIONS
from escapewheel_validator import Level

from .alignment import alignment_parameters
from .amending import Held
from .errors import RecipeFault
from .recipe import Problem, Recipe, normalized_chosen_at, refusal
from .secrets import redacted
from .sources.compensations import describe
from .writer import PacketWriter

if TYPE_CHECKING:
    from .session import Context


def preferred_runs(recipe: Recipe, writer: PacketWriter, held: Held | None, session_id: str) -> list[dict[str, Any]]:
    """Return a `core.preferred_runs` row per `preferred_run` entry (Part 05 §12).

    Raises
    ------
    RecipeUnsound
        Naming each entry whose run neither the packet holds nor the build records, or whose run's
        activity or scope differs from the entry's.
    """
    runs = {str(r["processing_run_id"]): r for r in writer.rows(CORE_PROCESSING_RUNS)}
    if held is not None:
        for row in held.named_rows(CORE_PROCESSING_RUNS, writer.keys):
            runs.setdefault(str(row["processing_run_id"]), row)
    rows, problems = [], []
    for entry in recipe.preferred_runs:
        name = str(entry["processing_run_name"])
        run = runs.get(name)
        if run is None:
            problems.append(
                Problem(
                    Level.ERROR,
                    f"[[preferred_run]] {name} names no run the packet holds or this build records",
                    RecipeFault.PREFERRED_RUN_UNKNOWN,
                )
            )
            continue
        differs = [
            f"{column} {run.get(column)!r}, not {entry[column]!r}"
            for column in ("activity_type", "scope_kind", "scope")
            if str(run.get(column)) != str(entry[column])
        ]
        if differs:
            problems.append(
                Problem(
                    Level.ERROR,
                    f"[[preferred_run]] {name} names a run whose {', '.join(differs)}",
                    RecipeFault.PREFERRED_RUN_DIFFERS,
                )
            )
            continue
        rows.append(
            {
                "session_id": session_id,
                "activity_type": entry["activity_type"],
                "scope_kind": entry["scope_kind"],
                "scope": entry["scope"],
                "processing_run_id": name,
                "reason": entry["reason"],
                "chosen_at": normalized_chosen_at(entry["chosen_at"]) if "chosen_at" in entry else None,
            }
        )
    if problems:
        raise refusal(recipe, "refused (Part 05 §3.5): ", problems)
    return rows


def source_roots(recipe: Recipe) -> list[str]:
    """Return each distinct `root` the recipe's sources state, as written (Part 05 §7).

    As written rather than as this build resolved it: a relative root resolves against wherever
    the recipe sits, and recording that would make two builds of one recipe over the same bytes
    differ (Part 05 §11). A source stating no root states none to record.
    """
    stated = (entry.get("root") for entry in recipe.document.get("source", []))
    return list(dict.fromkeys(str(root) for root in stated if root is not None))


def import_run(
    recipe: Recipe, compensations: list[str] | None = None, context: Context | None = None
) -> dict[str, Any]:
    """Build the `core.processing_runs` row for this import, carrying the recipe as its parameters.

    Part 05 §4.3 wants normalization deterministic in declared parameters. Putting the recipe
    itself in `parameters` is what makes the run record answerable rather than merely present:
    a reader can see what produced the packet, and `code_uri` names the file it came from.

    The compensations go in beside it because a recipe alone does not determine the output: two
    runs of the same recipe against the same bytes differ if the importer's assumptions about
    those bytes changed. A packet that names them can be found again when a defect is fixed
    upstream.
    """
    from . import __version__

    return {
        "processing_run_id": f"import.{recipe.digest[:12]}",
        "session_id": recipe.session.get("session_id"),
        "activity_type": "import",
        # Part 01 §2.6: an import is session-wide, and a session-wide run names the session.
        "scope_kind": CORE_SESSIONS,
        "scope": recipe.session.get("session_id"),
        "software_name": "escapewheel-writer",
        "software_version": __version__,
        "code_uri": f"sha256:{recipe.digest}",
        "parameters": json.dumps(
            {
                # Redacted, because this lands in the packet: a recipe written before the
                # refusal existed carries a credential into every copy of it otherwise.
                "recipe": redacted(recipe.document),
                "compensations": describe(compensations or []),
                # Part 02 §12.6: what the terminal-anchor test withheld, and the measurement
                # that justifies mapping further than Part 01 §3.9's default.
                **alignment_parameters(context),
            },
            default=str,
            sort_keys=True,
        ),
        "started_at": datetime.now(UTC).isoformat(),
        "status": "succeeded",
    }


__all__ = ["import_run", "preferred_runs", "source_roots"]
