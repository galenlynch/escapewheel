"""Compare the cleaned registry contract with the pre-cleanup declarations.

The comparison removes only repository-history fields, the two identifiers deliberately changed
by R121, and revision-only wording. Everything else—including keys, references, roles, rule SQL,
levels, execution modes, and table placement—must remain byte-for-byte equal as JSON values.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "41aad8a15b7c8c3415f6c52b3c12e64114658718"

CORE = "registry/logical_schemas.json"
RULES = "registry/rules.json"
EXTENSIONS = tuple(
    str(path.relative_to(ROOT))
    for path in sorted((ROOT / "registry/extensions").glob("*.json"))
)

_PARENTHETICAL_REVISION = re.compile(
    r" \((?:R\d+(?: §?[0-9.]+)?(?:, §[0-9.]+)?(?:, )?)+\)"
)


def _at_baseline(path: str) -> Any:
    """Load one JSON document from the reviewed bootstrap commit."""
    result = subprocess.run(
        ["git", "show", f"{BASELINE}:{path}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def _current(path: str) -> Any:
    """Load one JSON document from the working tree."""
    return json.loads((ROOT / path).read_text())


def _text(value: str) -> str:
    """Remove revision-only wording while retaining the statement it annotated."""
    value = _PARENTHETICAL_REVISION.sub("", value)
    value = value.replace("R27 5.3's default", "the default")
    value = value.replace(
        "as part of R90 " + "§3.5's shared key", "as part of the shared key"
    )
    value = value.replace("A narrow exception to R9 " + "§4: the ", "The ")
    value = value.replace(", which is the reading R23 " + "§2 gives a stream", "")
    value = value.replace(
        ": R89 " + "§1.2 measures 133 and 302 days between them",
        "; measured examples differ by 133 and 302 days",
    )
    value = value.replace(
        ": an equality join on a float64 is not safe, which is why R47 could strike "
        "`interval_index` and this stays",
        ": an equality join on a float64 is not safe, so the key uses an explicit sequence "
        "position",
    )
    value = value.replace(
        "Tier 2 validation rules (R2 7.2):", "Tier 2 validation rules:"
    )
    value = value.replace("pass (R2 7.3)", "pass")
    return value


def _normalize(value: Any, *, core: bool = False, root: bool = True) -> Any:
    """Remove only the reviewed R121 differences from a JSON value."""
    if isinstance(value, list):
        return [_normalize(item, core=core, root=False) for item in value]
    if not isinstance(value, dict):
        return _text(value) if isinstance(value, str) else value

    cleaned = {}
    for key, item in value.items():
        if key in {"derived_from", "since"}:
            continue
        if root and key == "$schema":
            continue
        if root and core and key == "registry_version":
            continue
        cleaned[key] = _normalize(item, core=core, root=False)
    return cleaned


def defects() -> list[str]:
    """Return each declaration or rule set changed beyond the reviewed cleanup."""
    found = []
    if _normalize(_at_baseline(CORE), core=True) != _normalize(
        _current(CORE), core=True
    ):
        found.append(CORE)
    for path in EXTENSIONS:
        if _normalize(_at_baseline(path)) != _normalize(_current(path)):
            found.append(path)
    if _normalize(_at_baseline(RULES)) != _normalize(_current(RULES)):
        found.append(RULES)
    return found


def main() -> int:
    """Report the normalized comparison."""
    changed = defects()
    if changed:
        for path in changed:
            print(f"FAIL  {path}")
        return 1
    print("ok    history cleanup preserves declarations and rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
