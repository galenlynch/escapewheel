"""What this package copies from the specification's tree, read from the copy map in `pyproject.toml`."""

import tomllib
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
#: A path in this package -> the path under `spec/` it copies.
COPIES: dict[str, str] = tomllib.loads((PACKAGE / "pyproject.toml").read_text())["tool"]["escapewheel"]["copies"]
#: Every copied file, which is edited at its source and never here.
COPIED_FILES = {PACKAGE / copy for copy in COPIES}
#: Each copied module's dotted name -> the path under `spec/` it copies.
COPIED_MODULES = {
    Path(copy).relative_to("src").with_suffix("").as_posix().replace("/", "."): source
    for copy, source in COPIES.items()
    if copy.endswith(".py")
}
