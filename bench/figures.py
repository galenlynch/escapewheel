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
COLOURS = {"Escapewheel": "#1b7837", "pynwb": "#762a83", "lazynwb": "#e08214", "eager": "#8c8c8c", "lazy": "#1b7837"}


def cells(*names: str) -> dict[tuple[str, str], dict]:
    """Each measured cell of the named result files, keyed by (reader or arm, operation), later files winning."""
    found: dict[tuple[str, str], dict] = {}
    for name in names:
        path = RESULTS / name
        if not path.exists():
            raise SystemExit(f"missing result file: {path}")
        for cell in json.loads(path.read_text())["cells"]:
            if cell.get("runs"):
                found[(cell.get("reader") or cell["arm"], cell.get("operation") or cell["analysis"])] = cell
    return found


def number(v: float) -> str:
    return f"{v:,.0f}" if v >= 100 else f"{v:.3g}"


def annotate(ax, y, values: list[float | None]) -> None:
    """Write each bar's value past its end."""
    for yy, v in zip(y, values, strict=True):
        if v is not None:
            ax.text(v * 1.15, yy, number(v), va="center", fontsize=7)


def widen(ax, values: list[float | None]) -> None:
    """Fit every bar and the label past it on a log axis, without minor tick labels."""
    shown = [v for v in values if v is not None]
    ax.set_xscale("log")
    ax.set_xlim(min(shown) / 2, max(shown) * 6)
    ax.xaxis.set_minor_formatter(NullFormatter())


def bars(ax, labels: list[str], series: dict[str, list[float | None]], unit: str) -> None:
    """Horizontal grouped bars on a log axis, each bar annotated; the caller orders the shared y axis."""
    rows = np.arange(len(labels))
    height = 0.8 / len(series)
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


READER_QUESTIONS = [
    ("open", "open"),
    ("list", "list the full tree"),
    ("units 5 cols", "units, five columns"),
    ("trials", "trials"),
    ("every spike", "every spike"),
    ("10 s window", "every unit, 10 s"),
    ("one train", "one unit's train"),
    ("region units", "units in MD, with trains"),
]


def readers(session: str, out: Path) -> None:
    day, nwb_day = "2026-10-03", "2026-10-02"
    local = cells(
        f"{nwb_day}-readers-{session}-r164-rerun.json",
        f"{day}-readers-{session}-r164-list.json",
        *([f"{day}-readers-{session}-r164-list-packet.json"] if session == "776259" else []),
        f"{day}-readers-{session}-r164-final.json",
        f"{day}-readers-{session}-r164-region.json",
    )
    remote = cells(
        f"{nwb_day}-readers-{session}-r164-s3.json",
        f"{nwb_day}-readers-{session}-r164-s3-lazynwb.json",
        f"{day}-readers-{session}-r164-s3-list.json",
        f"{day}-readers-{session}-r164-s3-list-lazynwb.json",
        f"{day}-readers-{session}-r164-s3-final.json",
        f"{day}-readers-{session}-r164-s3-region.json",
    )

    def packet(found, op):
        """The faster of the Escapewheel PyArrow and DuckDB paths."""
        options = [c for c in (found.get(("packet", op)), found.get(("packet-sql", op))) if c]
        return min(options, key=lambda c: c["seconds"]) if options else None

    labels = [label for _, label in READER_QUESTIONS]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.5), sharey=True)
    panels = [
        (axes[0], local, "seconds", 1.0, "seconds, local NVMe"),
        (axes[1], remote, "seconds", 1.0, "seconds, S3"),
        (axes[2], remote, "received_bytes", 1e6, "MB received, S3"),
    ]
    for ax, found, field, scale, unit in panels:
        series = {
            "Escapewheel": [value(packet(found, op), field, scale) for op, _ in READER_QUESTIONS],
            "pynwb": [value(found.get(("pynwb", op)), field, scale) for op, _ in READER_QUESTIONS],
            "lazynwb": [value(found.get(("lazynwb", op)), field, scale) for op, _ in READER_QUESTIONS],
        }
        bars(ax, labels, series, unit)
    axes[0].invert_yaxis()
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper right", ncols=3, fontsize=8)
    fig.suptitle(f"{session}: one question at a time, cold (Escapewheel: faster of PyArrow and DuckDB)")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(out / f"readers-{session}.png", dpi=150)


GO_CUE_ARMS = [
    ("packet aligned_spikes", "Escapewheel", "Escapewheel: aligned_spikes"),
    ("packet duckdb", "Escapewheel", "Escapewheel: DuckDB"),
    ("packet dataset", "Escapewheel", "Escapewheel: PyArrow dataset"),
    ("packet polars", "Escapewheel", "Escapewheel: Polars"),
    ("packet pandas", "Escapewheel", "Escapewheel: pandas"),
    ("lazynwb intervals", "lazynwb", "lazynwb: intervals"),
    ("lazynwb polars", "lazynwb", "lazynwb: Polars"),
    ("lazynwb pandas", "lazynwb", "lazynwb: pandas"),
    ("lazynwb sql", "lazynwb", "lazynwb: SQL"),
    ("pynwb pandas", "pynwb", "pynwb: pandas"),
    ("pynwb duckdb", "pynwb", "pynwb: DuckDB"),
]


def go_cue(session: str, out: Path) -> None:
    analysis = "go-cue spikes"
    stores = {
        "seconds, local NVMe": cells(
            f"2026-10-03-trials-{session}-r164.json", f"2026-10-03-trials-{session}-r164-final.json"
        ),
        "seconds, S3": cells(
            f"2026-10-03-trials-{session}-r164-s3.json", f"2026-10-03-trials-{session}-r164-s3-final.json"
        ),
    }
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    rows = np.arange(len(GO_CUE_ARMS))
    for ax, (unit, found) in zip(axes, stores.items(), strict=True):
        times = [value(found.get((arm, analysis))) for arm, _, _ in GO_CUE_ARMS]
        ax.barh(rows, [np.nan if t is None else t for t in times], color=[COLOURS[k] for _, k, _ in GO_CUE_ARMS])
        annotate(ax, rows, times)
        widen(ax, times)
        ax.set_yticks(rows, [label for _, _, label in GO_CUE_ARMS])
        ax.set_xlabel(unit)
        ax.grid(axis="x", alpha=0.3)
        ax.set_axisbelow(True)
    axes[0].invert_yaxis()
    fig.suptitle(f"{session}: every unit's spikes within [-1, +2] s of each go cue, cold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(out / f"go-cue-{session}.png", dpi=150)


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
    local = cells(f"2026-10-03-lazy-{session}-r164.json", f"2026-10-03-lazy-{session}-r164-good.json")
    remote = cells(f"2026-10-03-lazy-{session}-r164-s3.json", f"2026-10-03-lazy-{session}-r164-s3-good.json")
    labels = [label for _, label in LAZY_OPERATIONS]
    fig, axes = plt.subplots(1, 4, figsize=(18, 4.8), sharey=True)
    panels = [
        (axes[0], local, "seconds", 1.0, "seconds, local NVMe"),
        (axes[1], local, "peak_mib", 1024.0, "peak RSS GiB, local NVMe"),
        (axes[2], remote, "seconds", 1.0, "seconds, S3"),
        (axes[3], remote, "received_bytes", 1e6, "MB received, S3"),
    ]
    for ax, found, field, scale, unit in panels:
        series = {
            arm: [value(found.get((arm, op)), field, scale) for op, _ in LAZY_OPERATIONS] for arm in ("eager", "lazy")
        }
        bars(ax, labels, series, unit)
    axes[0].invert_yaxis()
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper right", ncols=2, fontsize=8)
    fig.suptitle(f"{session}: the same question read whole, then filtered (eager), or narrowed before reading (lazy)")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(out / f"lazy-{session}.png", dpi=150)


def main() -> None:
    parser = argparse.ArgumentParser(description="Draw SUMMARY.md's figures from the result files it quotes.")
    parser.add_argument("--session", default="776259", choices=["776259", "786867"])
    parser.add_argument("--out", type=Path, required=True, help="directory for the PNG files")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    readers(args.session, args.out)
    go_cue(args.session, args.out)
    lazy(args.session, args.out)


if __name__ == "__main__":
    main()
