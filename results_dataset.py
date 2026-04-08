#!/usr/bin/env python3

import csv
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List
from zipfile import ZipFile


XML_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
WORKBOOK_PATH = Path("CS4221 Project Results.xlsx")
REPO_COLLATED_PATH = Path("collated_results.csv")


def _as_float(value: str) -> float:
    return float(value) if value not in ("", None) else 0.0


def _rate(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _normalize_row(
    sample_size: float,
    num_attributes: float,
    num_fds: float,
    minimal_cover_size: float,
    total_fd_sets: float,
    count_2nf: float,
    count_3nf: float,
    count_bcnf: float,
) -> Dict[str, float | str]:
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


def load_workbook_rows(path: Path = WORKBOOK_PATH) -> List[Dict[str, float | str]]:
    records: List[Dict[str, float | str]] = []

    with ZipFile(path) as workbook_zip:
        shared_strings: List[str] = []
        if "xl/sharedStrings.xml" in workbook_zip.namelist():
            shared_root = ET.fromstring(workbook_zip.read("xl/sharedStrings.xml"))
            for item in shared_root.findall("m:si", XML_NS):
                text = "".join(node.text or "" for node in item.iterfind(".//m:t", XML_NS))
                shared_strings.append(text)

        sheet_root = ET.fromstring(workbook_zip.read("xl/worksheets/sheet1.xml"))
        rows = sheet_root.findall(".//m:sheetData/m:row", XML_NS)
        for row in rows[1:]:
            values: List[str] = []
            for cell in row.findall("m:c", XML_NS):
                value_node = cell.find("m:v", XML_NS)
                if value_node is None:
                    values.append("")
                    continue

                raw_value = value_node.text or ""
                if cell.attrib.get("t") == "s":
                    values.append(shared_strings[int(raw_value)])
                else:
                    values.append(raw_value)

            if len(values) < 10:
                continue

            records.append(
                _normalize_row(
                    sample_size=_as_float(values[0]),
                    num_attributes=_as_float(values[1]),
                    num_fds=_as_float(values[2]),
                    minimal_cover_size=_as_float(values[4]),
                    total_fd_sets=_as_float(values[6]),
                    count_2nf=_as_float(values[7]),
                    count_3nf=_as_float(values[8]),
                    count_bcnf=_as_float(values[9]),
                )
            )

    return records


def load_repo_collated_rows(path: Path = REPO_COLLATED_PATH) -> List[Dict[str, float | str]]:
    records: List[Dict[str, float | str]] = []
    if not path.exists():
        return records

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            # Skip partially collated runs that do not yet have complete
            # normal-form counts. Treating blanks as zero would distort the
            # report-facing trends and graphs.
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


def load_all_rows() -> List[Dict[str, float | str]]:
    merged: Dict[tuple[int, int], Dict[str, float | str]] = {}

    for row in load_repo_collated_rows():
        merged[(row["num_attributes"], row["sample_size"])] = row

    if WORKBOOK_PATH.exists():
        for row in load_workbook_rows():
            merged[(row["num_attributes"], row["sample_size"])] = row

    return sorted(merged.values(), key=lambda row: (row["num_attributes"], row["sample_size"]))


def write_cleaned_csv(rows: Iterable[Dict[str, float | str]], path: Path) -> None:
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


def group_by_attr(rows: Iterable[Dict[str, float | str]]) -> Dict[int, List[Dict[str, float | str]]]:
    groups: Dict[int, List[Dict[str, float | str]]] = defaultdict(list)
    for row in rows:
        groups[row["num_attributes"]].append(row)

    for series in groups.values():
        series.sort(key=lambda row: row["sample_size"])

    return groups
