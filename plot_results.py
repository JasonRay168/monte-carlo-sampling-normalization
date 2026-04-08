#!/usr/bin/env python3

import csv
import html
from pathlib import Path


WIDTH = 960
HEIGHT = 540
MARGIN_LEFT = 80
MARGIN_RIGHT = 40
MARGIN_TOP = 50
MARGIN_BOTTOM = 70
PLOT_WIDTH = WIDTH - MARGIN_LEFT - MARGIN_RIGHT
PLOT_HEIGHT = HEIGHT - MARGIN_TOP - MARGIN_BOTTOM

PALETTE = ["#00798c", "#d1495b", "#edae49", "#30638e", "#66a182", "#6b4e71"]
STACK_COLORS = {
    "below_2nf_rate": "#d1495b",
    "2nf_rate": "#edae49",
    "3nf_rate": "#00798c",
    "bcnf_rate": "#30638e",
}
INPUT_CSV_PATH = Path("analysis_results.csv")
OUTPUT_DIR = Path("graphs")
DENSITY_GRAPH_MAX = 0.11
TARGET_DENSITIES = [0.01, 0.02, 0.04, 0.06, 0.08, 0.10]


def load_rows(path: Path):
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            parsed = {}
            for key, value in row.items():
                if key in {"sample_size", "num_attributes", "num_fds", "total_fd_sets", "below_2nf_count", "2nf_count", "3nf_count", "bcnf_count"}:
                    parsed[key] = int(value)
                else:
                    parsed[key] = float(value)
            rows.append(parsed)
    return rows


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _scale_x(x, xmin, xmax):
    if xmax == xmin:
        return MARGIN_LEFT + PLOT_WIDTH / 2
    return MARGIN_LEFT + (x - xmin) / (xmax - xmin) * PLOT_WIDTH


def _scale_y(y, ymin, ymax):
    if ymax == ymin:
        return MARGIN_TOP + PLOT_HEIGHT / 2
    return MARGIN_TOP + (1 - (y - ymin) / (ymax - ymin)) * PLOT_HEIGHT


def _polyline_points(series, xmin, xmax, ymin, ymax):
    return " ".join(
        f"{_scale_x(row['x'], xmin, xmax):.2f},{_scale_y(row['y'], ymin, ymax):.2f}"
        for row in series
    )


def _svg_frame(title, x_label, y_label):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<rect width="100%" height="100%" fill="#f7f3e8"/>',
        f'<text x="{WIDTH / 2:.1f}" y="28" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="22" fill="#1f2933">{html.escape(title)}</text>',
        f'<line x1="{MARGIN_LEFT}" y1="{MARGIN_TOP + PLOT_HEIGHT}" x2="{MARGIN_LEFT + PLOT_WIDTH}" y2="{MARGIN_TOP + PLOT_HEIGHT}" stroke="#334e68" stroke-width="2"/>',
        f'<line x1="{MARGIN_LEFT}" y1="{MARGIN_TOP}" x2="{MARGIN_LEFT}" y2="{MARGIN_TOP + PLOT_HEIGHT}" stroke="#334e68" stroke-width="2"/>',
        f'<text x="{WIDTH / 2:.1f}" y="{HEIGHT - 20}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="16" fill="#1f2933">{html.escape(x_label)}</text>',
        f'<text x="24" y="{HEIGHT / 2:.1f}" text-anchor="middle" transform="rotate(-90 24 {HEIGHT / 2:.1f})" font-family="Helvetica, Arial, sans-serif" font-size="16" fill="#1f2933">{html.escape(y_label)}</text>',
    ]


def write_svg(path: Path, lines):
    path.write_text("\n".join(lines + ["</svg>"]) + "\n", encoding="utf-8")


def draw_line_chart(path: Path, title: str, x_label: str, y_label: str, series_map):
    all_points = [point for series in series_map.values() for point in series]
    xmin = min(point["x"] for point in all_points)
    xmax = max(point["x"] for point in all_points)
    ymin = min(point["y"] for point in all_points)
    ymax = max(point["y"] for point in all_points)
    if ymin > 0:
        ymin = 0.0

    lines = _svg_frame(title, x_label, y_label)

    for tick_index in range(6):
        tick_y_value = ymin + (ymax - ymin) * tick_index / 5 if ymax != ymin else ymin
        tick_y = _scale_y(tick_y_value, ymin, ymax)
        lines.append(
            f'<line x1="{MARGIN_LEFT}" y1="{tick_y:.2f}" x2="{MARGIN_LEFT + PLOT_WIDTH}" y2="{tick_y:.2f}" stroke="#d9e2ec" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{MARGIN_LEFT - 10}" y="{tick_y + 5:.2f}" text-anchor="end" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#486581">{tick_y_value:.3f}</text>'
        )

    x_ticks = sorted({point["x"] for point in all_points})
    for tick_value in x_ticks:
        tick_x = _scale_x(tick_value, xmin, xmax)
        lines.append(
            f'<line x1="{tick_x:.2f}" y1="{MARGIN_TOP}" x2="{tick_x:.2f}" y2="{MARGIN_TOP + PLOT_HEIGHT}" stroke="#eef2f6" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{tick_x:.2f}" y="{MARGIN_TOP + PLOT_HEIGHT + 22}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#486581">{tick_value:g}</text>'
        )

    legend_y = MARGIN_TOP + 18
    legend_x = MARGIN_LEFT + 10
    for index, (label, series) in enumerate(series_map.items()):
        color = PALETTE[index % len(PALETTE)]
        lines.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{_polyline_points(series, xmin, xmax, ymin, ymax)}"/>'
        )
        for point in series:
            cx = _scale_x(point["x"], xmin, xmax)
            cy = _scale_y(point["y"], ymin, ymax)
            lines.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="4" fill="{color}"/>')

        ly = legend_y + index * 20
        lines.append(f'<rect x="{legend_x}" y="{ly - 10}" width="14" height="14" fill="{color}"/>')
        lines.append(
            f'<text x="{legend_x + 22}" y="{ly + 2}" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#1f2933">{html.escape(label)}</text>'
        )

    write_svg(path, lines)


def draw_stacked_bar_chart(path: Path, title: str, rows):
    keys = ["below_2nf_rate", "2nf_rate", "3nf_rate", "bcnf_rate"]
    labels = {
        "below_2nf_rate": "Below 2NF",
        "2nf_rate": "2NF",
        "3nf_rate": "3NF",
        "bcnf_rate": "BCNF",
    }
    lines = _svg_frame(title, "Number of Attributes", "Share of FD Sets")

    for tick_index in range(6):
        tick_value = tick_index / 5
        tick_y = _scale_y(tick_value, 0.0, 1.0)
        lines.append(
            f'<line x1="{MARGIN_LEFT}" y1="{tick_y:.2f}" x2="{MARGIN_LEFT + PLOT_WIDTH}" y2="{tick_y:.2f}" stroke="#d9e2ec" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{MARGIN_LEFT - 10}" y="{tick_y + 5:.2f}" text-anchor="end" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#486581">{tick_value:.1f}</text>'
        )

    bar_width = PLOT_WIDTH / max(len(rows), 1) * 0.65
    for index, row in enumerate(rows):
        center_x = MARGIN_LEFT + (index + 0.5) * (PLOT_WIDTH / len(rows))
        base_y = MARGIN_TOP + PLOT_HEIGHT
        for key in keys:
            height = row[key] * PLOT_HEIGHT
            y = base_y - height
            lines.append(
                f'<rect x="{center_x - bar_width / 2:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{height:.2f}" fill="{STACK_COLORS[key]}"/>'
            )
            base_y = y
        lines.append(
            f'<text x="{center_x:.2f}" y="{MARGIN_TOP + PLOT_HEIGHT + 22}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#486581">{row["num_attributes"]}</text>'
        )

    legend_x = MARGIN_LEFT + 10
    legend_y = MARGIN_TOP + 18
    for index, key in enumerate(keys):
        ly = legend_y + index * 20
        lines.append(f'<rect x="{legend_x}" y="{ly - 10}" width="14" height="14" fill="{STACK_COLORS[key]}"/>')
        lines.append(
            f'<text x="{legend_x + 22}" y="{ly + 2}" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#1f2933">{labels[key]}</text>'
        )

    write_svg(path, lines)


def choose_best_size_20_rows(rows):
    return sorted([row for row in rows if row["sample_size"] == 20], key=lambda row: row["num_attributes"])


def choose_density_series(rows):
    groups = {}
    for row in rows:
        if row["fd_density"] <= DENSITY_GRAPH_MAX:
            groups.setdefault(row["num_attributes"], []).append(row)

    series_map = {}
    for num_attributes, series in sorted(groups.items()):
        series = sorted(series, key=lambda row: row["fd_density"])
        selected = []
        used_sample_sizes = set()
        for target_density in TARGET_DENSITIES:
            candidate = min(
                series,
                key=lambda row: (
                    abs(row["fd_density"] - target_density),
                    row["sample_size"],
                ),
            )
            if candidate["sample_size"] in used_sample_sizes:
                continue
            selected.append(candidate)
            used_sample_sizes.add(candidate["sample_size"])

        if not selected:
            continue

        label = f"n={num_attributes}"
        series_map[label] = sorted(selected, key=lambda row: row["fd_density"])
    return series_map


def draw_density_window_chart(path: Path, title: str, y_label: str, series_map, y_key: str):
    all_points = [point for series in series_map.values() for point in series]
    xmin = 0.0
    xmax = DENSITY_GRAPH_MAX
    ymin = 0.0
    ymax = max(point[y_key] for point in all_points)
    if ymax == 0.0:
        ymax = 1.0

    def scale_x(value):
        return MARGIN_LEFT + (value - xmin) / (xmax - xmin) * PLOT_WIDTH

    lines = _svg_frame(title, "FD Density", y_label)

    for tick_index in range(6):
        tick_y_value = ymin + (ymax - ymin) * tick_index / 5
        tick_y = _scale_y(tick_y_value, ymin, ymax)
        lines.append(
            f'<line x1="{MARGIN_LEFT}" y1="{tick_y:.2f}" x2="{MARGIN_LEFT + PLOT_WIDTH}" y2="{tick_y:.2f}" stroke="#d9e2ec" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{MARGIN_LEFT - 10}" y="{tick_y + 5:.2f}" text-anchor="end" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#486581">{tick_y_value:.3f}</text>'
        )

    tick_values = [0.0, 0.02, 0.04, 0.06, 0.08, 0.10]
    for tick_value in tick_values:
        tick_x = scale_x(tick_value)
        lines.append(
            f'<line x1="{tick_x:.2f}" y1="{MARGIN_TOP}" x2="{tick_x:.2f}" y2="{MARGIN_TOP + PLOT_HEIGHT}" stroke="#eef2f6" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{tick_x:.2f}" y="{MARGIN_TOP + PLOT_HEIGHT + 22}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#486581">{tick_value:.2f}</text>'
        )

    legend_y = MARGIN_TOP + 18
    legend_x = MARGIN_LEFT + 10
    for index, (label, series) in enumerate(series_map.items()):
        color = PALETTE[index % len(PALETTE)]
        points = " ".join(f"{scale_x(point['fd_density']):.2f},{_scale_y(point[y_key], ymin, ymax):.2f}" for point in series)
        lines.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{points}"/>')
        for point in series:
            cx = scale_x(point["fd_density"])
            cy = _scale_y(point[y_key], ymin, ymax)
            lines.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="4" fill="{color}"/>')

        ly = legend_y + index * 20
        lines.append(f'<rect x="{legend_x}" y="{ly - 10}" width="14" height="14" fill="{color}"/>')
        lines.append(
            f'<text x="{legend_x + 22}" y="{ly + 2}" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#1f2933">{html.escape(label)}</text>'
        )

    write_svg(path, lines)


def main() -> int:
    rows = load_rows(INPUT_CSV_PATH)
    ensure_dir(OUTPUT_DIR)

    size_20_rows = choose_best_size_20_rows(rows)
    draw_line_chart(
        OUTPUT_DIR / "attrs_vs_min_cover_size.svg",
        "Minimal Cover Size vs Number of Attributes",
        "Number of Attributes",
        "Minimal Cover Size",
        {
            "sample size = 20": [
                {"x": row["num_attributes"], "y": row["minimal_cover_size"]}
                for row in size_20_rows
            ]
        },
    )
    draw_line_chart(
        OUTPUT_DIR / "attrs_vs_reduction_ratio.svg",
        "Reduction Ratio vs Number of Attributes",
        "Number of Attributes",
        "Reduction Ratio",
        {
            "sample size = 20": [
                {"x": row["num_attributes"], "y": row["reduction_ratio"]}
                for row in size_20_rows
            ]
        },
    )
    draw_stacked_bar_chart(
        OUTPUT_DIR / "attrs_vs_nf_distribution.svg",
        "Normal Form Distribution vs Number of Attributes",
        size_20_rows,
    )

    density_series = choose_density_series(rows)
    draw_density_window_chart(
        OUTPUT_DIR / "fd_density_vs_bcnf_rate.svg",
        "BCNF Rate vs FD Density",
        "BCNF Rate",
        density_series,
        "bcnf_rate",
    )
    draw_density_window_chart(
        OUTPUT_DIR / "fd_density_vs_reduction_ratio.svg",
        "Reduction Ratio vs FD Density",
        "Reduction Ratio",
        density_series,
        "reduction_ratio",
    )

    print(f"Written graphs to: {OUTPUT_DIR.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
