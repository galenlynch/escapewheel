"""Write the core registry from its TOML source.

`checkers/registry_source.py` says how a source directory assembles to a document, so an
extension outside the tree is assembled by the same code, copied into the validator.

    python assemble.py
"""

from pathlib import Path

from checkers.registry_source import RegistrySourceError, assemble, dumps

HERE = Path(__file__).resolve().parent
TREE = HERE.parent


def sources() -> dict[Path, Path]:
    """Return the core registry's source directory and the document built from it."""
    return {TREE / "source/core": TREE / "artifacts/logical_schemas.json"}


def main(targets: dict[Path, Path] | None = None) -> list[Path]:
    """Write each registry document from its source, by default the core registry."""
    written = []
    for directory, out in (sources() if targets is None else targets).items():
        out.write_text(dumps(assemble(directory)))
        written.append(out)
    return written


if __name__ == "__main__":
    try:
        for path in main():
            print(f"wrote {path.relative_to(TREE)}")
    except RegistrySourceError as error:
        raise SystemExit(str(error)) from None
