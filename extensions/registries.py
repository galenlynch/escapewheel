"""Build or check the extension registries in one or more directories, each where it sits.

An extension is not a member of the specification, so its registry lies outside the tree. It is
assembled and checked by the tree's own checkers, which `escapewheel extension build` and
`escapewheel extension check` run outside this repository: see `checkers/extension_check.py`.

    python extensions/registries.py build extensions escapewheel-aind/extensions
    python extensions/registries.py check extensions escapewheel-aind/extensions
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TREE = ROOT / "spec"
sys.path.insert(0, str(TREE / "tools"))

import assemble
from checkers.extension_check import check_directory, contract_failures
from checkers.registry_document import check_registry_context_bytes
from checkers.registry_source import RegistrySourceError, extension_sources


def _check(directory: Path, core) -> list[str]:
    """Return every failure among the registries in `directory`."""
    checks, failures = check_directory(directory, core)
    for checked in checks:
        name = checked.path.stem
        failures += [f"{name}: {failure}" for failure in contract_failures(checked.context.result)]
        failures += [f"{name}: {failure}" for failure in checked.failures]
    print(f"{directory.relative_to(ROOT)}: {len(checks)} registries, {sum(c.tables for c in checks)} tables")
    return failures


def main() -> int:
    """Build or check each named directory; return the exit status."""
    parser = argparse.ArgumentParser(description="Build or check extension registries.")
    parser.add_argument("action", choices=("build", "check"))
    parser.add_argument("directories", nargs="+", type=Path)
    args = parser.parse_args()
    directories = [path.resolve() for path in args.directories]
    try:
        if args.action == "build":
            for directory in directories:
                for path in assemble.main(extension_sources(directory)):
                    print(f"wrote {path.relative_to(ROOT)}")
            return 0
        core = check_registry_context_bytes((TREE / "artifacts/logical_schemas.json").read_bytes())
        failures = [failure for directory in directories for failure in _check(directory, core)]
    except RegistrySourceError as error:
        print(error, file=sys.stderr)
        return 1
    for failure in failures:
        print(f"FAIL  {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
