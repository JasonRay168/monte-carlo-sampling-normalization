#!/usr/bin/env python3
"""
Generate plots for the Monte Carlo FD sampling experiments.

Reads collated_results.csv and produces:
  1. Experiment 1 plots (vary num_attributes, fixed num_fds=20)
  2. Experiment 2 plots (vary num_fds, fixed n=7)
  3. Experiment 3 plots (controlled FD density across n=5..8)

Usage:
    python3 plot.py [--csv PATH] [--out DIR]
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

NF_COLS = ["1NF", "2NF", "3NF", "BCNF"]
NF_COLORS = {"1NF": "#e74c3c", "2NF": "#f39c12", "3NF": "#3498db", "BCNF": "#2ecc71"}


def load(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["FD Density"] = df["Sample Size"] / df["No. Fds"]
    df["Reduction Ratio"] = df["Minimal Cover Size"] / df["Sample Size"]
    total = df[NF_COLS].sum(axis=1)
    for col in NF_COLS:
        df[f"{col} %"] = df[col] / total * 100
    return df


# ── Experiment 1: Vary num_attributes ────────────────────────────────────────

def plot_exp1(df: pd.DataFrame, out: Path):
    exp1 = df[df["Sample Size"] == 20].sort_values("Num Attributes")

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle("Experiment 1: Vary Num Attributes (num_fds = 20)", fontsize=14, y=1.02)

    # 1a: Minimal Cover Size
    ax = axes[0]
    ax.plot(exp1["Num Attributes"], exp1["Minimal Cover Size"], "o-", color="#2c3e50")
    ax.set_xlabel("Num Attributes")
    ax.set_ylabel("Avg Minimal Cover Size")
    ax.set_title("Minimal Cover Size")
    ax.grid(True, alpha=0.3)

    # 1b: Reduction Ratio
    ax = axes[1]
    ax.plot(exp1["Num Attributes"], exp1["Reduction Ratio"], "s-", color="#8e44ad")
    ax.set_xlabel("Num Attributes")
    ax.set_ylabel("Reduction Ratio (cover / num_fds)")
    ax.set_title("Reduction Ratio")
    ax.grid(True, alpha=0.3)

    # 1c: NF Distribution (stacked bar)
    ax = axes[2]
    bottoms = [0] * len(exp1)
    x = exp1["Num Attributes"].values
    for col in NF_COLS:
        vals = exp1[f"{col} %"].values
        ax.bar(x, vals, bottom=bottoms, label=col, color=NF_COLORS[col], width=0.6)
        bottoms = [b + v for b, v in zip(bottoms, vals)]
    ax.set_xlabel("Num Attributes")
    ax.set_ylabel("Percentage (%)")
    ax.set_title("Normal Form Distribution")
    ax.legend(loc="upper left", fontsize=8)
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3, axis="y")

    fig.tight_layout()
    fig.savefig(out / "exp1_vary_attributes.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out / 'exp1_vary_attributes.png'}")


# ── Experiment 2: Vary num_fds ───────────────────────────────────────────────

def plot_exp2(df: pd.DataFrame, out: Path):
    exp2 = df[df["Num Attributes"] == 7].sort_values("Sample Size")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Experiment 2: Vary Num FDs (n = 7, 441 total FDs)", fontsize=14, y=1.01)

    x = exp2["Sample Size"].values
    density = exp2["FD Density"].values * 100

    # 2a: Minimal Cover Size vs num_fds
    ax = axes[0, 0]
    ax.plot(x, exp2["Minimal Cover Size"], "o-", color="#2c3e50")
    ax.set_xlabel("Num FDs (Sample Size)")
    ax.set_ylabel("Avg Minimal Cover Size")
    ax.set_title("Minimal Cover Size vs Num FDs")
    ax.grid(True, alpha=0.3)

    # 2b: Reduction Ratio vs num_fds
    ax = axes[0, 1]
    ax.plot(x, exp2["Reduction Ratio"], "s-", color="#8e44ad")
    ax.set_xlabel("Num FDs (Sample Size)")
    ax.set_ylabel("Reduction Ratio")
    ax.set_title("Reduction Ratio vs Num FDs")
    ax.grid(True, alpha=0.3)

    # 2c: Minimal Cover Size vs FD Density
    ax = axes[1, 0]
    ax.plot(density, exp2["Minimal Cover Size"], "D-", color="#e67e22")
    ax.set_xlabel("FD Density (%)")
    ax.set_ylabel("Avg Minimal Cover Size")
    ax.set_title("Minimal Cover Size vs FD Density")
    ax.grid(True, alpha=0.3)

    # 2d: NF Distribution (stacked area)
    ax = axes[1, 1]
    pcts = [exp2[f"{col} %"].values for col in NF_COLS]
    ax.stackplot(x, *pcts, labels=NF_COLS,
                 colors=[NF_COLORS[c] for c in NF_COLS], alpha=0.85)
    ax.set_xlabel("Num FDs (Sample Size)")
    ax.set_ylabel("Percentage (%)")
    ax.set_title("Normal Form Distribution vs Num FDs")
    ax.legend(loc="center right", fontsize=8)
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3, axis="y")

    fig.tight_layout()
    fig.savefig(out / "exp2_vary_num_fds.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out / 'exp2_vary_num_fds.png'}")


# ── Experiment 3: Controlled FD Density ──────────────────────────────────────

EXP3_CONFIGS = {
    5: {0.05: 4, 0.10: 8, 0.20: 15},
    6: {0.05: 9, 0.10: 19, 0.20: 37},
    7: {0.05: 22, 0.10: 44, 0.20: 88},
    8: {0.05: 51, 0.10: 102, 0.20: 203},
}


def _get_exp3_row(df, n, num_fds):
    mask = (df["Num Attributes"] == n) & (df["Sample Size"] == num_fds)
    rows = df[mask]
    return rows.iloc[0] if len(rows) > 0 else None


def plot_exp3(df: pd.DataFrame, out: Path):
    target_densities = [0.05, 0.10, 0.20]
    tables = sorted(EXP3_CONFIGS.keys())

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))
    fig.suptitle("Experiment 3: Controlled FD Density (compare across num attributes)",
                 fontsize=14, y=1.02)

    markers = {5: "o", 6: "s", 7: "D", 8: "^"}
    table_colors = {5: "#e74c3c", 6: "#f39c12", 7: "#3498db", 8: "#2ecc71"}

    # 3a: Minimal Cover Size at each density, grouped by n
    ax = axes[0]
    for n in tables:
        densities_actual, covers = [], []
        for d in target_densities:
            row = _get_exp3_row(df, n, EXP3_CONFIGS[n][d])
            if row is not None:
                densities_actual.append(row["FD Density"] * 100)
                covers.append(row["Minimal Cover Size"])
        ax.plot(densities_actual, covers, f"{markers[n]}-", color=table_colors[n],
                label=f"n={n}", markersize=7)
    ax.set_xlabel("FD Density (%)")
    ax.set_ylabel("Avg Minimal Cover Size")
    ax.set_title("Minimal Cover Size")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 3b: Reduction Ratio at each density, grouped by n
    ax = axes[1]
    for n in tables:
        densities_actual, ratios = [], []
        for d in target_densities:
            row = _get_exp3_row(df, n, EXP3_CONFIGS[n][d])
            if row is not None:
                densities_actual.append(row["FD Density"] * 100)
                ratios.append(row["Reduction Ratio"])
        ax.plot(densities_actual, ratios, f"{markers[n]}-", color=table_colors[n],
                label=f"n={n}", markersize=7)
    ax.set_xlabel("FD Density (%)")
    ax.set_ylabel("Reduction Ratio")
    ax.set_title("Reduction Ratio")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 3c: NF Distribution grouped bar chart at ~10% density
    ax = axes[2]
    target_d = 0.10
    bar_width = 0.18
    x_positions = range(len(NF_COLS))
    for i, n in enumerate(tables):
        row = _get_exp3_row(df, n, EXP3_CONFIGS[n][target_d])
        if row is None:
            continue
        total = sum(row[c] for c in NF_COLS)
        pcts = [row[c] / total * 100 for c in NF_COLS]
        offsets = [p + (i - 1.5) * bar_width for p in x_positions]
        ax.bar(offsets, pcts, bar_width, label=f"n={n}", color=table_colors[n], alpha=0.85)
    ax.set_xticks(list(x_positions))
    ax.set_xticklabels(NF_COLS)
    ax.set_ylabel("Percentage (%)")
    ax.set_title("NF Distribution at ~10% Density")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    fig.tight_layout()
    fig.savefig(out / "exp3_controlled_density.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out / 'exp3_controlled_density.png'}")


# ── Combined NF heatmap ─────────────────────────────────────────────────────

def plot_nf_heatmap(df: pd.DataFrame, out: Path):
    """BCNF percentage heatmap: num_attributes vs num_fds for all data points."""
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.suptitle("BCNF Percentage Across All Configurations", fontsize=14)

    scatter = ax.scatter(
        df["Num Attributes"], df["Sample Size"],
        c=df["BCNF %"], cmap="RdYlGn", s=120, edgecolors="black", linewidths=0.5,
        vmin=0, vmax=100,
    )
    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label("BCNF %")

    for _, row in df.iterrows():
        ax.annotate(f'{row["BCNF %"]:.0f}%',
                     (row["Num Attributes"], row["Sample Size"]),
                     textcoords="offset points", xytext=(6, 4), fontsize=7, alpha=0.8)

    ax.set_xlabel("Num Attributes")
    ax.set_ylabel("Num FDs (Sample Size)")
    ax.set_title("BCNF % by (Num Attributes, Num FDs)")
    ax.grid(True, alpha=0.2)

    fig.tight_layout()
    fig.savefig(out / "bcnf_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out / 'bcnf_heatmap.png'}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Plot experiment results")
    parser.add_argument("--csv", default="collated_results.csv", help="Input CSV path")
    parser.add_argument("--out", default="plots", help="Output directory for PNGs")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    out = Path(args.out)
    out.mkdir(exist_ok=True)

    df = load(csv_path)

    print("Generating plots...")
    plot_exp1(df, out)
    plot_exp2(df, out)
    plot_exp3(df, out)
    plot_nf_heatmap(df, out)
    print("Done.")


if __name__ == "__main__":
    main()
