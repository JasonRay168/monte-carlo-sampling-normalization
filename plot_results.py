#!/usr/bin/env python3

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator


INPUT_CSV_PATH = Path("analysis_results.csv")
OUTPUT_DIR = Path("graphs")

ATTR_COLORS = {4: "#e74c3c", 5: "#f39c12", 6: "#2ecc71", 7: "#3498db", 8: "#9b59b6"}
ATTR_MARKERS = {4: "o", 5: "s", 6: "D", 7: "^", 8: "v"}
NF_COLORS = {
    "below_2nf_rate": "#d1495b",
    "2nf_rate": "#edae49",
    "3nf_rate": "#00798c",
    "bcnf_rate": "#30638e",
}
NF_LABELS = {
    "below_2nf_rate": "Below 2NF",
    "2nf_rate": "2NF",
    "3nf_rate": "3NF",
    "bcnf_rate": "BCNF",
}
NF_KEYS = ["below_2nf_rate", "2nf_rate", "3nf_rate", "bcnf_rate"]


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


def _group_by_attr(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row["num_attributes"]].append(row)
    for series in groups.values():
        series.sort(key=lambda r: r["sample_size"])
    return groups


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _save(fig, path: Path) -> None:
    for ext in (".svg", ".png"):
        fig.savefig(path.with_suffix(ext), dpi=220, bbox_inches="tight")
    plt.close(fig)


def _style(ax, title: str, x_label: str, y_label: str) -> None:
    ax.set_title(title, pad=14, fontsize=15, fontweight="semibold")
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.grid(True, which="major", linestyle="--", linewidth=0.6, alpha=0.35)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


# ── Graph 1: BCNF Rate vs Number of FDs ─────────────────────────────────────

def plot_bcnf_vs_num_fds(rows, out: Path):
    """The intuitive graph: at the same number of FDs, more attributes → lower BCNF."""
    groups = _group_by_attr(rows)
    fig, ax = plt.subplots(figsize=(12, 6.5))

    for n in sorted(groups):
        series = groups[n]
        x = [r["sample_size"] for r in series]
        y = [r["bcnf_rate"] for r in series]
        ax.plot(x, y, color=ATTR_COLORS[n], marker=ATTR_MARKERS[n],
                markersize=3.5, linewidth=1.8, label=f"n = {n}", alpha=0.9)

    _style(ax, "BCNF Rate vs Number of Sampled FDs", "Number of FDs", "BCNF Rate")
    ax.set_xscale("log")
    ax.set_xlim(left=0.8)
    ax.set_ylim(-0.02, 1.05)
    ax.axhline(0.5, color="grey", linestyle=":", linewidth=1, alpha=0.5)
    ax.legend(title="Attributes", frameon=False)
    _save(fig, out / "bcnf_vs_num_fds")


# ── Graph 2: NF Distribution at Fixed FD Count ──────────────────────────────

def plot_nf_at_fixed_fds(rows, out: Path):
    """Stacked bars at fixed sample sizes, comparing across attribute counts."""
    target_sizes = [1, 20]
    groups = _group_by_attr(rows)
    attr_values = sorted(groups)

    fig, axes = plt.subplots(1, len(target_sizes), figsize=(7 * len(target_sizes), 6.5))
    if len(target_sizes) == 1:
        axes = [axes]

    for ax, target in zip(axes, target_sizes):
        stack_rows = []
        for n in attr_values:
            candidates = groups[n]
            closest = min(candidates, key=lambda r: abs(r["sample_size"] - target))
            if abs(closest["sample_size"] - target) > target * 0.25 and target > 1:
                continue
            stack_rows.append(closest)

        x = list(range(len(stack_rows)))
        bottom = [0.0] * len(stack_rows)
        for key in NF_KEYS:
            heights = [r[key] for r in stack_rows]
            ax.bar(x, heights, width=0.6, bottom=bottom,
                   color=NF_COLORS[key], edgecolor="white", linewidth=0.5,
                   label=NF_LABELS[key])
            bottom = [b + h for b, h in zip(bottom, heights)]

        ax.set_xticks(x)
        ax.set_xticklabels([str(r["num_attributes"]) for r in stack_rows])
        actual = stack_rows[0]["sample_size"] if stack_rows else target
        _style(ax, f"NF Distribution at {actual} FDs",
               "Number of Attributes", "Share of FD Sets")
        ax.set_ylim(0, 1.25)
        ax.legend(loc="upper center", frameon=False, fontsize=9,
                  ncol=4, bbox_to_anchor=(0.5, 1.0))

    fig.tight_layout()
    _save(fig, out / "nf_at_fixed_fds")


# ── Graph 3: BCNF 50%/90% Threshold vs Attributes ───────────────────────────

def _find_threshold(series, target_rate):
    """Linear interpolation to find where bcnf_rate crosses target_rate."""
    for i in range(len(series) - 1):
        r0, r1 = series[i]["bcnf_rate"], series[i + 1]["bcnf_rate"]
        s0, s1 = series[i]["sample_size"], series[i + 1]["sample_size"]
        if r0 <= target_rate <= r1:
            frac = (target_rate - r0) / (r1 - r0) if r1 != r0 else 0
            return s0 + frac * (s1 - s0)
    return None


def plot_bcnf_threshold(rows, out: Path):
    """How many FDs are needed to reach 50% and 90% BCNF?"""
    groups = _group_by_attr(rows)
    fig, ax = plt.subplots(figsize=(10, 6.5))

    thresholds = [
        (0.1, "v:", "#95a5a6", "10% BCNF"),
        (0.3, "D-.", "#27ae60", "30% BCNF"),
        (0.5, "o-", "#2c3e50", "50% BCNF"),
        (0.7, "^-.", "#8e44ad", "70% BCNF"),
        (0.9, "s--", "#e67e22", "90% BCNF"),
    ]
    for target, style, color, label in thresholds:
        xs, ys = [], []
        for n in sorted(groups):
            thresh = _find_threshold(groups[n], target)
            if thresh is not None:
                xs.append(n)
                ys.append(thresh)
        ax.plot(xs, ys, style, linewidth=2.2, markersize=8,
                color=color, label=label)
        for x, y in zip(xs, ys):
            ax.annotate(f"{y:.0f}", (x, y), textcoords="offset points",
                        xytext=(8, 8), fontsize=9, alpha=0.8)

    _style(ax, "FDs Required to Reach BCNF Threshold",
           "Number of Attributes", "Number of FDs Needed")
    ax.set_xticks(sorted(groups))
    ax.set_yscale("log")
    ax.legend(frameon=False, fontsize=12)
    _save(fig, out / "bcnf_threshold")


# ── Graph 4: Reduction Ratio vs Number of FDs ───────────────────────────────

def plot_reduction_ratio(rows, out: Path):
    """Minimal cover size / sample size — shows FD redundancy scaling."""
    groups = _group_by_attr(rows)
    fig, ax = plt.subplots(figsize=(12, 6.5))

    for n in sorted(groups):
        series = groups[n]
        x = [r["sample_size"] for r in series]
        y = [r["minimal_cover_size"] / r["sample_size"] if r["sample_size"] > 0 else 0
             for r in series]
        ax.plot(x, y, color=ATTR_COLORS[n], marker=ATTR_MARKERS[n],
                markersize=3.5, linewidth=1.8, label=f"n = {n}", alpha=0.9)

    _style(ax, "Reduction Ratio vs Number of FDs",
           "Number of FDs", "Minimal Cover Size / Number of FDs")
    ax.set_xscale("log")
    ax.set_xlim(left=0.8)
    ax.set_ylim(bottom=0)
    ax.legend(title="Attributes", frameon=False)
    _save(fig, out / "reduction_ratio_vs_num_fds")


# ── Graph 5: Minimal Cover Size vs Number of FDs ────────────────────────────

def plot_cover_size(rows, out: Path):
    """Absolute minimal cover size growth."""
    groups = _group_by_attr(rows)
    fig, ax = plt.subplots(figsize=(12, 6.5))

    for n in sorted(groups):
        series = groups[n]
        x = [r["sample_size"] for r in series]
        y = [r["minimal_cover_size"] for r in series]
        ax.plot(x, y, color=ATTR_COLORS[n], marker=ATTR_MARKERS[n],
                markersize=3.5, linewidth=1.8, label=f"n = {n}", alpha=0.9)

    _style(ax, "Minimal Cover Size vs Number of FDs",
           "Number of FDs", "Avg Minimal Cover Size")
    ax.set_xscale("log")
    ax.set_xlim(left=0.8)
    ax.legend(title="Attributes", frameon=False)
    _save(fig, out / "cover_size_vs_num_fds")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    rows = load_rows(INPUT_CSV_PATH)
    if not rows:
        raise SystemExit("analysis_results.csv has no rows")

    ensure_dir(OUTPUT_DIR)

    print("Generating graphs...")
    plot_bcnf_vs_num_fds(rows, OUTPUT_DIR)
    plot_nf_at_fixed_fds(rows, OUTPUT_DIR)
    plot_bcnf_threshold(rows, OUTPUT_DIR)
    plot_reduction_ratio(rows, OUTPUT_DIR)
    plot_cover_size(rows, OUTPUT_DIR)
    print(f"Written graphs to: {OUTPUT_DIR.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
