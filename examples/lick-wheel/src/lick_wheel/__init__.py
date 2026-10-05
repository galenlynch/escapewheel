"""A worked Escapewheel source adapter for a lick-and-wheel task."""

from pathlib import Path

from .source import LickWheelSource

#: The declaration document `escapewheel declare lick_wheel` writes, for a build that does not
#: install this package and so cannot read the class (Part 12 §7).
DECLARATION = Path(__file__).with_name("declaration.json")

__all__ = ["DECLARATION", "LickWheelSource"]
