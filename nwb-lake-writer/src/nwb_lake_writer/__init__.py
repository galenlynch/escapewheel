"""Tools to write NWB lakes."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("nwb-lake-writer")
except PackageNotFoundError:
    __version__ = "0.0.0.dev0"
