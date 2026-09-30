"""Write each package's copies from the specification's tree, or check them with `--check`.

A package lists its copies under `[tool.escapewheel.copies]` in its `pyproject.toml`. The check
also requires a package copying a checker to declare each library the checker imports, with a
bound admitting the version the tree's `uv.lock` holds, so the copy runs against a library the
tree's own tests ran it against.
"""

import argparse
import ast
import sys
from pathlib import Path

import tomllib
from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parent
TREE = ROOT / "spec"
PACKAGES = ("escapewheel-reader", "escapewheel-validator", "escapewheel-writer")


def copies(package: str) -> dict[Path, Path]:
    """Return each copy in `package` and the tree file it copies."""
    project = tomllib.loads((ROOT / package / "pyproject.toml").read_text())
    table = project["tool"]["escapewheel"]["copies"]
    return {ROOT / package / copy: TREE / source for copy, source in table.items()}


def _locked() -> dict[str, str]:
    lock = tomllib.loads((TREE / "tools/uv.lock").read_text())
    return {entry["name"]: entry["version"] for entry in lock["package"]}


def _imports(path: Path) -> set[str]:
    """Top-level names of the absolute imports in a Python file."""
    names = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            names |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def admission_errors(package: str) -> list[str]:
    """Where `package` fails to admit the tree's locked version of a library a copied checker imports."""
    declared = tomllib.loads((TREE / "tools/pyproject.toml").read_text())["project"]["dependencies"]
    tree_libraries = {Requirement(entry).name for entry in declared}
    locked = _locked()
    project = tomllib.loads((ROOT / package / "pyproject.toml").read_text())["project"]
    requirements = {Requirement(entry).name: Requirement(entry) for entry in project["dependencies"]}
    errors = []
    imported = set().union(*(_imports(source) for source in copies(package).values() if source.suffix == ".py"))
    for library in sorted(imported & tree_libraries):
        requirement = requirements.get(library)
        if requirement is None:
            errors.append(f"{package}: copies a checker importing {library} but does not declare it")
        elif not requirement.specifier.contains(locked[library], prereleases=True):
            errors.append(f"{package}: {requirement} does not admit the tree's locked {library} {locked[library]}")
    return errors


def main() -> int:
    """Write or check every package's copies; return the exit status."""
    parser = argparse.ArgumentParser(description="Write or check the packages' copies from spec/.")
    parser.add_argument("--check", action="store_true", help="report disagreement instead of writing")
    args = parser.parse_args()
    errors = []
    for package in PACKAGES:
        for copy, source in copies(package).items():
            if args.check:
                if not copy.is_file() or copy.read_bytes() != source.read_bytes():
                    errors.append(f"{copy.relative_to(ROOT)} differs from {source.relative_to(ROOT)}")
            elif not copy.is_file() or copy.read_bytes() != source.read_bytes():
                copy.parent.mkdir(parents=True, exist_ok=True)
                copy.write_bytes(source.read_bytes())
                print(f"wrote {copy.relative_to(ROOT)}")
        if args.check:
            errors += admission_errors(package)
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
