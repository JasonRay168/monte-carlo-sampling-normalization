#!/usr/bin/env bash

set -u
set -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

OUTPUT_FILE="${1:-collated_results.csv}"

python3 - "$ROOT_DIR" "$OUTPUT_FILE" <<'PY'
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

root = Path(sys.argv[1])
output_file = Path(sys.argv[2])

tables_path = root / "tables.json"
if not tables_path.exists():
    raise SystemExit("tables.json not found")

with tables_path.open("r", encoding="utf-8") as fh:
    tables = json.load(fh)

sample_files = sorted(root.glob("sample_table_*_size_*_set_*_*.json"))
groups = defaultdict(list)

for sample_file in sample_files:
    stem = sample_file.stem
    base = re.sub(r"_\d+$", "", stem)
    groups[base].append(sample_file)

sortable_rows = []

for base, files in sorted(groups.items()):
    match = re.search(r"sample_table_(\d+)_size_(\d+)_set_\d+", base)
    if not match:
        continue

    num_attrs = int(match.group(1))
    sample_size = int(match.group(2))
    table_key = f"table_{num_attrs}"
    table_rows = tables.get(table_key, [])
    no_fds = len(table_rows)

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

    normal_form_file = root / f"normal_form_counts_{base}.json"
    nf_counts = {"BCNF": "", "3NF": "", "2NF": "", "1NF": ""}
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

rows = [row for _, _, row in sorted(sortable_rows)]

fieldnames = [
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

with output_file.open("w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(fh, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Written: {output_file}")
PY
