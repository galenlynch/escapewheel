"""Draw SUMMARY.md's figures from the result files it quotes.

uv run python figures.py --session 776259 --out figures/
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import NullFormatter

RESULTS = Path(__file__).parent / "results"
COLOURS = {
    "Escapewheel": "#1b7837",
    "pynwb, Zarr": "#762a83",
    "pynwb, HDF5": "#c2a5cf",
    "lazynwb, Zarr": "#e08214",
    "lazynwb, HDF5": "#fdb863",
    "eager": "#8c8c8c",
    "lazy": "#1b7837",
}
HDF5 = " HDF5"


def cells(*names: str, suffix: str = "") -> dict[tuple[str, str], dict]:
    """Each measured cell of the named result files, keyed by (reader or arm, operation), later files winning.

    `suffix` is appended to each reader or arm, so an NWB-HDF5 run's cells sit beside the NWB-Zarr run's.
    """
    found: dict[tuple[str, str], dict] = {}
    for name in names:
        path = RESULTS / name
        if not path.exists():
            raise SystemExit(f"missing result file: {path}")
        for cell in json.loads(path.read_text())["cells"]:
            if cell.get("runs"):
                found[((cell.get("reader") or cell["arm"]) + suffix, cell.get("operation") or cell["analysis"])] = cell
    return found


def fastest(found: dict[tuple[str, str], dict], arms: list[str], op: str) -> dict | None:
    """The fastest of `arms`' cells for `op`, as a summary column reports a reader."""
    options = [found[(arm, op)] for arm in arms if (arm, op) in found]
    return min(options, key=lambda cell: cell["seconds"]) if options else None


def number(v: float) -> str:
    return f"{v:,.0f}" if v >= 100 else f"{v:.2g}" if v < 0.1 else f"{v:.3g}"


def annotate(ax, y, values: list[float | None]) -> None:
    """Write each bar's value past its end."""
    for yy, v in zip(y, values, strict=True):
        if v is not None:
            ax.text(v * 1.15, yy, number(v), va="center", fontsize=6)


def widen(ax, values: list[float | None]) -> None:
    """Fit every bar and the label past it on a log axis, without minor tick labels."""
    shown = [v for v in values if v is not None]
    ax.set_xscale("log")
    ax.set_xlim(min(shown) / 2, max(shown) * 8)
    ax.xaxis.set_minor_formatter(NullFormatter())


def bars(ax, labels: list[str], series: dict[str, list[float | None]], unit: str) -> None:
    """Horizontal grouped bars on a log axis, each bar annotated; the caller orders the shared y axis."""
    rows = np.arange(len(labels))
    height = 0.84 / len(series)
    for offset, (name, values) in enumerate(series.items()):
        y = rows + (offset - (len(series) - 1) / 2) * height
        shown = [np.nan if v is None else v for v in values]
        ax.barh(y, shown, height, color=COLOURS[name], label=name)
        annotate(ax, y, values)
    widen(ax, [v for values in series.values() for v in values])
    ax.set_yticks(rows, labels)
    ax.set_xlabel(unit)
    ax.grid(axis="x", which="major", alpha=0.3)
    ax.set_axisbelow(True)


def value(cell: dict | None, field: str = "seconds", scale: float = 1.0) -> float | None:
    return None if cell is None or cell.get(field) is None else cell[field] / scale


def panels(fig_title: str, labels: list[str], stores: list[tuple[str, dict, str, float]], series, out: Path) -> None:
    """One panel per (unit, cells, field, scale), sharing the questions on the y axis and the legend."""
    fig, axes = plt.subplots(1, len(stores), figsize=(6 * len(stores), 0.62 * len(labels) + 1.6), sharey=True)
    for ax, (unit, found, field, scale) in zip(axes, stores, strict=True):
        bars(ax, labels, series(found, field, scale), unit)
    axes[0].invert_yaxis()
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper right", ncols=5, fontsize=8)
    fig.suptitle(fig_title, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(out, dpi=150)
    plt.close(fig)


READER_QUESTIONS = [
    ("open", "open"),
    ("list tables", "list tables"),
    ("list", "full tree"),
    ("units 5 cols", "units, five columns"),
    ("trials", "trials"),
    ("every spike", "every spike"),
    ("10 s window", "10 s window"),
    ("one train", "one train"),
    ("region units", "units in MD"),
    ("unit positions", "unit positions"),
    ("MD waveforms", "MD waveforms"),
]
READERS = {
    "Escapewheel": ["packet", "packet-sql"],
    "pynwb, Zarr": ["pynwb"],
    "pynwb, HDF5": ["pynwb" + HDF5],
    "lazynwb, Zarr": ["lazynwb"],
    "lazynwb, HDF5": ["lazynwb" + HDF5],
}


def reader_cells(session: str) -> tuple[dict, dict]:
    """The NVMe and S3 cells SUMMARY.md's reader tables quote, Zarr and HDF5 side by side."""
    run = f"readers-{session}-r164"
    local = cells(f"2026-10-04-{run}-local.json", f"2026-10-04-{run}-local-positions.json")
    local |= cells(f"2026-10-04-{run}-local-hdf5.json", suffix=HDF5)
    remote = cells(
        f"2026-10-02-{run}-s3.json",
        f"2026-10-02-{run}-s3-lazynwb.json",
        f"2026-10-03-{run}-s3-list.json",
        f"2026-10-03-{run}-s3-list-lazynwb.json",
        f"2026-10-03-{run}-s3-final.json",
        f"2026-10-03-{run}-s3-region.json",
        f"2026-10-03-{run}-s3-natural.json",
        f"2026-10-04-{run}-s3-contents.json",
        f"2026-10-04-{run}-s3-units.json",
        f"2026-10-04-{run}-s3-waveforms.json",
    ) | cells(f"2026-10-04-{run}-s3-hdf5.json", suffix=HDF5)
    return local, remote


def readers(session: str, out: Path) -> None:
    local, remote = reader_cells(session)

    def series(found, field, scale):
        return {
            name: [value(fastest(found, arms, op), field, scale) for op, _ in READER_QUESTIONS]
            for name, arms in READERS.items()
        }

    panels(
        f"{session}: one question at a time, cold; each reader's fastest arm",
        [label for _, label in READER_QUESTIONS],
        [
            ("seconds, NVMe", local, "seconds", 1.0),
            ("seconds, S3", remote, "seconds", 1.0),
            ("MB received, S3", remote, "received_bytes", 1e6),
        ],
        series,
        out / f"readers-{session}.png",
    )


ANALYSES = [
    ("go-cue rasters", "go-cue rasters"),
    ("condition psth", "condition PSTH"),
    ("cross-correlograms", "cross-correlograms"),
]


def analysis_cells(session: str) -> tuple[dict, dict]:
    """The NVMe and S3 cells of the go-cue rasters and the population tests, Zarr and HDF5 side by side."""
    local, remote = {}, {}
    for found, store in ((local, ""), (remote, "-s3")):
        found |= cells(
            f"2026-10-04-trials-{session}-r164{store}-grouped.json", f"2026-10-04-population-{session}-r164{store}.json"
        )
        found |= cells(
            f"2026-10-04-trials-{session}-r164{store}-hdf5.json",
            f"2026-10-04-population-{session}-r164{store}-hdf5.json",
            suffix=HDF5,
        )
    return local, remote


def analyses(session: str, out: Path) -> None:
    local, remote = analysis_cells(session)

    def series(found, field, scale):
        def arms(prefix: str, suffix: str) -> list[str]:
            return [arm for arm, _ in found if arm.startswith(prefix + " ") and arm.endswith(suffix)]

        readers = {
            "Escapewheel": arms("packet", ""),
            "pynwb, Zarr": [arm for arm in arms("pynwb", "") if not arm.endswith(HDF5)],
            "pynwb, HDF5": arms("pynwb", HDF5),
            "lazynwb, Zarr": [arm for arm in arms("lazynwb", "") if not arm.endswith(HDF5)],
            "lazynwb, HDF5": arms("lazynwb", HDF5),
        }
        return {
            name: [value(fastest(found, names, op), field, scale) for op, _ in ANALYSES]
            for name, names in readers.items()
        }

    panels(
        f"{session}: whole-session analyses, cold; each reader's fastest arm",
        [label for _, label in ANALYSES],
        [
            ("seconds, NVMe", local, "seconds", 1.0),
            ("seconds, S3", remote, "seconds", 1.0),
            ("MB received, S3", remote, "received_bytes", 1e6),
        ],
        series,
        out / f"analyses-{session}.png",
    )


LAZY_OPERATIONS = [
    ("first rows", "first 10,000 spikes"),
    ("good region window", "MD single units, 60 s"),
    ("one session", "one packet of two"),
    ("duckdb window", "DuckDB, 60 s window"),
    ("polars window", "Polars, 60 s window"),
    ("rate on clock", "every spike on the clock"),
    ("spikes per unit", "spikes per unit"),
]


def lazy(session: str, out: Path) -> None:
    local = cells(
        *(f"2026-10-03-lazy-{session}-r164{tag}.json" for tag in ("", "-good", "-natural")),
        f"2026-10-04-lazy-{session}-r164-clock2.json",
    )
    remote = cells(
        *(f"2026-10-03-lazy-{session}-r164-s3{tag}.json" for tag in ("", "-good", "-natural")),
        f"2026-10-04-lazy-{session}-r164-s3-clock2.json",
    )

    def series(found, field, scale):
        return {
            arm: [value(found.get((arm, op)), field, scale) for op, _ in LAZY_OPERATIONS] for arm in ("eager", "lazy")
        }

    panels(
        f"{session}: each question read whole, then filtered (eager), or narrowed before reading (lazy)",
        [label for _, label in LAZY_OPERATIONS],
        [
            ("seconds, NVMe", local, "seconds", 1.0),
            ("peak RSS GiB, NVMe", local, "peak_mib", 1024.0),
            ("seconds, S3", remote, "seconds", 1.0),
            ("MB received, S3", remote, "received_bytes", 1e6),
        ],
        series,
        out / f"lazy-{session}.png",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Draw SUMMARY.md's figures from the result files it quotes.")
    parser.add_argument("--session", default="776259", choices=["776259", "786867"])
    parser.add_argument("--out", type=Path, required=True, help="directory for the PNG files")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    readers(args.session, args.out)
    analyses(args.session, args.out)
    lazy(args.session, args.out)


if __name__ == "__main__":
    main()
