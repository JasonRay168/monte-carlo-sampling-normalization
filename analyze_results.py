#!/usr/bin/env python3

from pathlib import Path

from results_dataset import group_by_attr, load_all_rows, write_cleaned_csv


CLEANED_CSV_PATH = Path("analysis_results.csv")
REPORT_PATH = Path("trend_report.txt")


def _fmt_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def _fmt_float(value: float) -> str:
    return f"{value:.6f}"


def build_report(rows):
    lines = []

    size_20_rows = sorted(
        [row for row in rows if row["sample_size"] == 20],
        key=lambda row: row["num_attributes"],
    )

    if size_20_rows:
        first = size_20_rows[0]
        last = size_20_rows[-1]
        lines.append("Trend 1: Attribute growth at fixed sample size 20")
        lines.append(
            f"- Minimal cover size rises from {_fmt_float(first['minimal_cover_size'])} at {first['num_attributes']} attributes "
            f"to {_fmt_float(last['minimal_cover_size'])} at {last['num_attributes']} attributes."
        )
        lines.append(
            f"- Reduction ratio (minimal cover size / num FDs) falls from {_fmt_float(first['reduction_ratio'])} "
            f"to {_fmt_float(last['reduction_ratio'])}, a {first['reduction_ratio'] / last['reduction_ratio']:.1f}x drop."
        )
        bcnf_collapse_row = next(
            (row for row in size_20_rows if row["bcnf_rate"] == 0.0),
            None,
        )
        if bcnf_collapse_row:
            lines.append(
                f"- BCNF rate falls from {_fmt_percent(first['bcnf_rate'])} to 0 by {bcnf_collapse_row['num_attributes']} attributes."
            )
        lines.append(
            f"- 3NF rate climbs from {_fmt_percent(first['3nf_rate'])} to {_fmt_percent(last['3nf_rate'])}."
        )
        lines.append("")

    groups = group_by_attr(rows)
    dense_groups = sorted(
        [
            [row for row in series if row["fd_density"] <= 1.0]
            for _, series in groups.items()
            if len([row for row in series if row["fd_density"] <= 1.0]) >= 2
        ],
        key=lambda series: series[0]["num_attributes"],
    )

    for series in dense_groups:
        start = series[0]
        end = series[-1]
        lines.append(f"Trend 2: Density sweep for attribute count {start['num_attributes']}")
        lines.append(
            f"- FD density increases from {_fmt_float(start['fd_density'])} to {_fmt_float(end['fd_density'])}."
        )
        lines.append(
            f"- BCNF rate changes from {_fmt_percent(start['bcnf_rate'])} to {_fmt_percent(end['bcnf_rate'])}."
        )
        lines.append(
            f"- 3NF rate changes from {_fmt_percent(start['3nf_rate'])} to {_fmt_percent(end['3nf_rate'])}."
        )
        lines.append(
            f"- Reduction ratio changes from {_fmt_float(start['reduction_ratio'])} to {_fmt_float(end['reduction_ratio'])}."
        )
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    rows = [row for row in load_all_rows() if row["fd_density"] <= 1.0]
    if not rows:
        raise SystemExit("No rows found in the hardcoded workbook/CSV sources.")

    write_cleaned_csv(rows, CLEANED_CSV_PATH)
    report = build_report(rows)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report, end="")
    print(f"Written cleaned dataset: {CLEANED_CSV_PATH.resolve()}")
    print(f"Written trend report: {REPORT_PATH.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
