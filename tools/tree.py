"""Check the rules CONTRIBUTING.md states for the specification's tree and its tools.

- A copy of `spec/` alone, in an empty directory, regenerates every generated file and region
  byte for byte and passes its own checks, run in the environment its own lock declares.
- A tool in the tree imports only the standard library, the tree's own modules, and the libraries
  `spec/tools/pyproject.toml` declares; a test may also import the development group's.
- Every incorporated artifact is named by a tool in the tree, which is how a checked projection,
  consistency condition or schema conformance reaches one.
- No part or incorporated artifact gives a path under an entry of the repository outside the tree,
  which the tree's own path check cannot see.
"""

import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TREE = ROOT / "spec"
TOOLS = TREE / "tools"
sys.path.insert(0, str(TOOLS))

import specdoc

#: What regenerates the tree, then what checks it, each run from `tools/` in the copy.
GENERATE = (["build.py"], ["columns.py"], ["combine.py"])
CHECK = (["headings.py", "--check"], ["framework.py"], ["check.py"])

#: Import names of the declared distributions where they differ from the distribution's name.
IMPORT_NAMES = {"pytest": "pytest"}


def members() -> list[Path]:
    """Every file of the tree Git would commit, relative to it, including new ones."""
    listed = specdoc.tracked_files(ROOT, "spec")
    return sorted(path.relative_to(TREE) for path in (ROOT / name for name in listed) if path.is_file())


def regeneration_errors() -> list[str]:
    """Regenerate and check a copy of the tree alone, and report every difference."""
    errors = []
    files = members()
    with tempfile.TemporaryDirectory(prefix="escapewheel-tree-") as scratch:
        copy = Path(scratch) / "spec"
        for relative in files:
            (copy / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(TREE / relative, copy / relative)
        environment = {k: v for k, v in os.environ.items() if k not in {"VIRTUAL_ENV", "TMPDIR"}}
        for argv in (*GENERATE, *CHECK):
            done = subprocess.run(
                ["uv", "run", "--quiet", "--frozen", "--project", str(copy / "tools"), "python", *argv],
                cwd=copy / "tools",
                capture_output=True,
                text=True,
                env=environment,
                check=False,
            )
            if done.returncode:
                tail = (done.stdout + done.stderr).strip().splitlines()[-3:]
                errors.append(f"{' '.join(argv)} fails in a copy of the tree: {' | '.join(tail)}")
        for relative in files:
            if (copy / relative).read_bytes() != (TREE / relative).read_bytes():
                errors.append(f"{relative} differs once a copy of the tree regenerates it")
    return errors


def _local_modules() -> set[str]:
    return {path.stem for path in TOOLS.glob("*.py")} | {
        path.name for path in TOOLS.iterdir() if (path / "__init__.py").is_file()
    }


def import_errors() -> list[str]:
    """Report each import in a tree tool that is not stdlib, local, or declared and locked."""
    project = tomllib.loads((TOOLS / "pyproject.toml").read_text())
    locked = {entry["name"] for entry in tomllib.loads((TOOLS / "uv.lock").read_text())["package"]}

    def names(requirements: list[str]) -> set[str]:
        found = {re.match(r"[A-Za-z0-9._-]+", requirement).group(0) for requirement in requirements}
        missing = found - locked
        if missing:
            errors.append(f"declared but not locked: {', '.join(sorted(missing))}")
        return {IMPORT_NAMES.get(name, name.replace("-", "_")) for name in found}

    errors: list[str] = []
    runtime = names(project["project"]["dependencies"])
    development = runtime | names(
        [entry for entry in project.get("dependency-groups", {}).get("dev", []) if isinstance(entry, str)]
    )
    admitted = set(sys.stdlib_module_names) | _local_modules()
    for path in sorted(TOOLS.rglob("*.py")):
        if ".venv" in path.parts:
            continue
        libraries = development if "tests" in path.relative_to(TOOLS).parts else runtime
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported = [node.module]
            else:
                continue
            for name in imported:
                top = name.split(".")[0]
                if top not in admitted | libraries:
                    errors.append(f"{path.relative_to(ROOT)}:{node.lineno} imports {name}")
    return errors


def unchecked_artifacts() -> list[str]:
    """Report each incorporated artifact no tool in the tree names."""
    tools = "\n".join(
        path.read_text() for path in TOOLS.rglob("*.py") if ".venv" not in path.parts and "tests" not in path.parts
    )
    return [
        f"artifacts/{relative} is named by no tool in the tree"
        for relative in (path.relative_to(TREE / "artifacts") for path in sorted((TREE / "artifacts").rglob("*")))
        if (TREE / "artifacts" / relative).is_file() and relative.name not in tools
    ]


def outside_path_errors() -> list[str]:
    """Report each path a part or artifact gives under a repository entry outside the tree."""
    import framework

    outside = [path.name for path in ROOT.iterdir() if path.is_dir() and path != TREE and not path.name.startswith(".")]
    return framework.path_defects(framework._documents(), outside=outside)


def main() -> int:
    """Run the four checks; return non-zero where any fails."""
    report = specdoc.Reporter(shown=10)
    for label, check in (
        ("a tree tool imports only what the tree declares", import_errors),
        ("a tool in the tree names every incorporated artifact", unchecked_artifacts),
        ("no part gives a path under the repository outside the tree", outside_path_errors),
        ("a copy of the tree alone regenerates and checks itself", regeneration_errors),
    ):
        report(label, check())
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
