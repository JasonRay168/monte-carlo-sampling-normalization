#!/usr/bin/env python3

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm


FIELDNAMES = [
    "Sample Size",
    "Num Attributes",
    "No. Fds",
    "FD Density",
    "Minimal Cover Size",
    "Reduction Ratio",
    "1NF",
    "2NF",
    "3NF",
    "BCNF",
]


def collate(workspace: Path, output_file: Path) -> None:
    tables_path = workspace / "tables.json"
    if not tables_path.exists():
        raise FileNotFoundError("tables.json not found")

    with tables_path.open("r", encoding="utf-8") as fh:
        tables = json.load(fh)

    sample_files = sorted(workspace.glob("sample_table_*_size_*_set_*_*.json"))
    groups = defaultdict(list)

    for sample_file in sample_files:
        stem = sample_file.stem
        base = re.sub(r"_\d+$", "", stem)
        groups[base].append(sample_file)

    sortable_rows = []

    grouped_items = sorted(groups.items())
    for base, files in tqdm(
        grouped_items,
        desc="Collating sample groups",
        unit="group",
    ):
        match = re.search(r"sample_table_(\d+)_size_(\d+)_set_\d+", base)
        if not match:
            continue

        num_attrs = int(match.group(1))
        sample_size = int(match.group(2))
        table_key = f"table_{num_attrs}"
        no_fds = len(tables.get(table_key, []))

        total_fd_sets = 0
        total_min_cover_size = 0

        for sample_file in files:
            with sample_file.open("r", encoding="utf-8") as fh:
                fd_sets = json.load(fh)
            for fd_set in fd_sets:
                total_fd_sets += 1
                total_min_cover_size += len(fd_set)

        avg_min_cover_size = ""
        if total_fd_sets:
            avg_min_cover_size = f"{total_min_cover_size / total_fd_sets:.6f}"

        normal_form_file = workspace / f"normal_form_counts_{base}.json"
        nf_counts = {"1NF": "", "2NF": "", "3NF": "", "BCNF": ""}

        if normal_form_file.exists():
            with normal_form_file.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            total = data.get("total", {})
            processed = total.get("fd_sets_processed", "")
            if processed != "":
                nf_counts["1NF"] = processed
            nf_counts["2NF"] = total.get("2NF", "")
            nf_counts["3NF"] = total.get("3NF", "")
            nf_counts["BCNF"] = total.get("BCNF", "")

        if nf_counts["1NF"] == "":
            nf_counts["1NF"] = total_fd_sets

        sortable_rows.append(
            (
                num_attrs,
                sample_size,
                {
                    "Sample Size": sample_size,
                    "Num Attributes": num_attrs,
                    "No. Fds": no_fds,
                    "FD Density": "",
                    "Minimal Cover Size": avg_min_cover_size,
                    "Reduction Ratio": "",
                    "1NF": nf_counts["1NF"],
                    "2NF": nf_counts["2NF"],
                    "3NF": nf_counts["3NF"],
                    "BCNF": nf_counts["BCNF"],
                },
            )
        )

    merged_rows = {}
    for num_attrs, sample_size, row in sortable_rows:
        key = (num_attrs, sample_size)
        if key not in merged_rows:
            merged_rows[key] = row
            continue

        current = merged_rows[key]
        current_1nf = int(current["1NF"]) if str(current["1NF"]).isdigit() else -1
        new_1nf = int(row["1NF"]) if str(row["1NF"]).isdigit() else -1

        # Prefer the row with more processed FD sets when duplicate keys exist.
        if new_1nf > current_1nf:
            merged_rows[key] = row

    rows = [merged_rows[key] for key in sorted(merged_rows)]

    with output_file.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collate sample and normal-form results into CSV."
    )
    parser.add_argument(
        "-o",
        "--output",
        default="collated_results.csv",
        help="Output CSV path (default: collated_results.csv)",
    )
    parser.add_argument(
        "-w",
        "--workspace",
        default=".",
        help="Workspace directory containing tables.json and sample files (default: .)",
    )
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    output_file = Path(args.output)
    if not output_file.is_absolute():
        output_file = workspace / output_file

    collate(workspace, output_file)
    print(f"Written: {output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
