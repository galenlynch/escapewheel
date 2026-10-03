"""Where the working tree this library reads is."""

import importlib
import sys
from pathlib import Path
from types import ModuleType

#: The monorepo root. The package is installed editable, so this is the checkout it was installed from.
ROOT = Path(__file__).resolve().parents[3]


def spec_tool(name: str) -> ModuleType:
    """Import one of the specification tree's tools, which are scripts on a path rather than a package."""
    tools = str(ROOT / "spec" / "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    return importlib.import_module(name)
