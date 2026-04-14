#!/usr/bin/env python3

from pathlib import Path
import csv

REPO_COLLATED_PATH = Path("collated_results.csv")


def _as_float(value):
    return float(value) if value not in ("", None) else 0.0


def _rate(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def _normalize_row(
    sample_size,
    num_attributes,
    num_fds,
    minimal_cover_size,
    total_fd_sets,
    count_2nf,
    count_3nf,
    count_bcnf,
):
    below_2nf = max(total_fd_sets - count_2nf - count_3nf - count_bcnf, 0.0)
    return {
        "sample_size": int(round(sample_size)),
        "num_attributes": int(round(num_attributes)),
        "num_fds": int(round(num_fds)),
        "fd_density": _rate(sample_size, num_fds),
        "minimal_cover_size": minimal_cover_size,
        "reduction_ratio": _rate(minimal_cover_size, num_fds),
        "total_fd_sets": int(round(total_fd_sets)),
        "below_2nf_count": int(round(below_2nf)),
        "2nf_count": int(round(count_2nf)),
        "3nf_count": int(round(count_3nf)),
        "bcnf_count": int(round(count_bcnf)),
        "below_2nf_rate": _rate(below_2nf, total_fd_sets),
        "2nf_rate": _rate(count_2nf, total_fd_sets),
        "3nf_rate": _rate(count_3nf, total_fd_sets),
        "bcnf_rate": _rate(count_bcnf, total_fd_sets),
    }


def load_repo_collated_rows(
    path=REPO_COLLATED_PATH,
):
    records = []
    if not path.exists():
        return records

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if any(row[key] in ("", None) for key in ("1NF", "2NF", "3NF", "BCNF")):
                continue

            records.append(
                _normalize_row(
                    sample_size=_as_float(row["Sample Size"]),
                    num_attributes=_as_float(row["Num Attributes"]),
                    num_fds=_as_float(row["No. Fds"]),
                    minimal_cover_size=_as_float(row["Minimal Cover Size"]),
                    total_fd_sets=_as_float(row["1NF"]),
                    count_2nf=_as_float(row["2NF"]),
                    count_3nf=_as_float(row["3NF"]),
                    count_bcnf=_as_float(row["BCNF"]),
                )
            )

    return records


def load_all_rows():
    merged = {}

    for row in load_repo_collated_rows():
        merged[(row["num_attributes"], row["sample_size"])] = row

    return sorted(
        merged.values(), key=lambda row: (row["num_attributes"], row["sample_size"])
    )


def write_cleaned_csv(rows, path) -> None:
    fieldnames = [
        "sample_size",
        "num_attributes",
        "num_fds",
        "fd_density",
        "minimal_cover_size",
        "reduction_ratio",
        "total_fd_sets",
        "below_2nf_count",
        "2nf_count",
        "3nf_count",
        "bcnf_count",
        "below_2nf_rate",
        "2nf_rate",
        "3nf_rate",
        "bcnf_rate",
    ]

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


CLEANED_CSV_PATH = Path("analysis_results.csv")
MIN_NUM_ATTRIBUTES = 4
MAX_NUM_ATTRIBUTES = 8


def main():
    rows = [
        row
        for row in load_all_rows()
        if row["fd_density"] <= 1.0
        and MIN_NUM_ATTRIBUTES <= row["num_attributes"] <= MAX_NUM_ATTRIBUTES
    ]
    if not rows:
        return 1

    write_cleaned_csv(rows, CLEANED_CSV_PATH)
    print(f"Written cleaned dataset: {CLEANED_CSV_PATH.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
