#!/usr/bin/env python3

import csv
from collections import defaultdict
from pathlib import Path
from statistics import median

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize
from matplotlib.ticker import MaxNLocator


INPUT_CSV_PATH = Path("analysis_results.csv")
OUTPUT_DIR = Path("graphs")
STACK_COLORS = {
    "below_2nf_rate": "#d1495b",
    "2nf_rate": "#edae49",
    "3nf_rate": "#00798c",
    "bcnf_rate": "#30638e",
}


def load_rows(path: Path):
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            parsed = {}
            for key, value in row.items():
                if key in {
                    "sample_size",
                    "num_attributes",
                    "num_fds",
                    "total_fd_sets",
                    "below_2nf_count",
                    "2nf_count",
                    "3nf_count",
                    "bcnf_count",
                }:
                    parsed[key] = int(value)
                else:
                    parsed[key] = float(value)
            rows.append(parsed)
    return rows


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _save_figure(fig, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _style_axis(ax, title: str, x_label: str, y_label: str) -> None:
    ax.set_title(title, pad=14, fontsize=15, fontweight="semibold")
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.grid(True, which="major", linestyle="--", linewidth=0.6, alpha=0.35)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def _balanced_offsets(count: int, spread: float = 0.28):
    if count <= 1:
        return [0.0]
    return [(-spread + (2 * spread * index / (count - 1))) for index in range(count)]


def draw_grouped_line_chart(path: Path, title: str, y_label: str, rows, y_key: str):
    groups = defaultdict(list)
    for row in rows:
        groups[row["num_attributes"]].append(row)

    attr_values = sorted(groups)
    color_map = plt.get_cmap("tab10", len(attr_values))

    fig, ax = plt.subplots(figsize=(11.8, 6.4))

    for index, num_attributes in enumerate(attr_values):
        series = sorted(groups[num_attributes], key=lambda row: row["fd_density"])
        x_values = [row["fd_density"] for row in series]
        y_values = [row[y_key] for row in series]
        ax.plot(
            x_values,
            y_values,
            color=color_map(index),
            linewidth=2.0,
            marker="o",
            markersize=4.0,
            label=f"n={num_attributes}",
        )

    _style_axis(ax, title, "FD Density", y_label)
    ax.set_xlim(left=0)
    if rows:
        ax.set_xlim(0, max(row["fd_density"] for row in rows) * 1.03)
    ax.legend(loc="upper left", ncol=2, frameon=False, title="Attributes")
    _save_figure(fig, path)


def draw_stacked_bar_chart(path: Path, title: str, rows):
    keys = ["below_2nf_rate", "2nf_rate", "3nf_rate", "bcnf_rate"]
    labels = {
        "below_2nf_rate": "Below 2NF",
        "2nf_rate": "2NF",
        "3nf_rate": "3NF",
        "bcnf_rate": "BCNF",
    }

    aggregated = defaultdict(
        lambda: {
            "below_2nf_count": 0,
            "2nf_count": 0,
            "3nf_count": 0,
            "bcnf_count": 0,
            "total_fd_sets": 0,
        }
    )
    for row in rows:
        bucket = aggregated[row["num_attributes"]]
        bucket["below_2nf_count"] += row["below_2nf_count"]
        bucket["2nf_count"] += row["2nf_count"]
        bucket["3nf_count"] += row["3nf_count"]
        bucket["bcnf_count"] += row["bcnf_count"]
        bucket["total_fd_sets"] += row["total_fd_sets"]

    attr_values = sorted(aggregated)
    stack_rows = []
    for num_attributes in attr_values:
        bucket = aggregated[num_attributes]
        total = bucket["total_fd_sets"] or 1
        stack_rows.append(
            {
                "num_attributes": num_attributes,
                "below_2nf_rate": bucket["below_2nf_count"] / total,
                "2nf_rate": bucket["2nf_count"] / total,
                "3nf_rate": bucket["3nf_count"] / total,
                "bcnf_rate": bucket["bcnf_count"] / total,
            }
        )

    fig, ax = plt.subplots(figsize=(11.8, 6.4))
    _style_axis(ax, title, "Number of Attributes", "Share of FD Sets")
    ax.set_ylim(0, 1.0)
    ax.yaxis.set_major_locator(MaxNLocator(6))

    bottom = [0.0] * len(stack_rows)
    bar_width = 0.68
    x_positions = list(range(len(stack_rows)))

    for key in keys:
        heights = [row[key] for row in stack_rows]
        ax.bar(
            x_positions,
            heights,
            width=bar_width,
            bottom=bottom,
            color=STACK_COLORS[key],
            label=labels[key],
            edgecolor="white",
            linewidth=0.5,
        )
        bottom = [current + height for current, height in zip(bottom, heights)]

    ax.set_xticks(x_positions)
    ax.set_xticklabels([str(row["num_attributes"]) for row in stack_rows])
    ax.legend(loc="upper right", frameon=False)
    _save_figure(fig, path)


def draw_density_scatter(path: Path, title: str, y_label: str, rows, y_key: str):
    density_values = [row["fd_density"] for row in rows]
    attr_values = [row["num_attributes"] for row in rows]
    density_norm = Normalize(vmin=min(attr_values), vmax=max(attr_values))
    density_cmap = plt.get_cmap("plasma")

    fig, ax = plt.subplots(figsize=(11.8, 6.4))
    for row in rows:
        ax.scatter(
            row["fd_density"],
            row[y_key],
            s=44,
            color=density_cmap(density_norm(row["num_attributes"])),
            alpha=0.86,
            edgecolors="white",
            linewidths=0.45,
        )

    _style_axis(ax, title, "FD Density", y_label)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.xaxis.set_major_locator(MaxNLocator(8))
    ax.yaxis.set_major_locator(MaxNLocator(8))

    if density_values:
        max_density = max(density_values)
        if max_density > 0.0:
            ax.set_xlim(0, max_density * 1.03)

    colorbar = fig.colorbar(
        cm.ScalarMappable(norm=density_norm, cmap=density_cmap),
        ax=ax,
        pad=0.02,
    )
    colorbar.set_label("Number of Attributes")
    _save_figure(fig, path)


def main() -> int:
    rows = load_rows(INPUT_CSV_PATH)
    if not rows:
        raise SystemExit("analysis_results.csv has no rows")

    ensure_dir(OUTPUT_DIR)

    draw_grouped_line_chart(
        OUTPUT_DIR / "attrs_vs_min_cover_size.svg",
        "Minimal Cover Size vs FD Density",
        "Minimal Cover Size",
        rows,
        "minimal_cover_size",
    )
    draw_grouped_line_chart(
        OUTPUT_DIR / "attrs_vs_reduction_ratio.svg",
        "Reduction Ratio vs FD Density",
        "Reduction Ratio",
        rows,
        "reduction_ratio",
    )
    draw_stacked_bar_chart(
        OUTPUT_DIR / "attrs_vs_nf_distribution.svg",
        "Normal Form Distribution vs Number of Attributes",
        rows,
    )
    draw_density_scatter(
        OUTPUT_DIR / "fd_density_vs_bcnf_rate.svg",
        "BCNF Rate vs FD Density",
        "BCNF Rate",
        rows,
        "bcnf_rate",
    )
    draw_density_scatter(
        OUTPUT_DIR / "fd_density_vs_reduction_ratio.svg",
        "Reduction Ratio vs FD Density",
        "Reduction Ratio",
        rows,
        "reduction_ratio",
    )

    print(f"Written graphs to: {OUTPUT_DIR.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
