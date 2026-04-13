import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm

from dbis_functional_dependencies import fdcheck


def attribute_universe_from_filename(file_path):
    match = re.search(r"table_(\d+)", Path(file_path).name)
    if not match:
        return

    num_attrs = int(match.group(1))
    return "".join(str(i) for i in range(num_attrs))


def fdset_from_json_entry(fd_entry, attribute_universe):
    fdset = fdcheck.FunctionalDependencySet(attribute_universe)

    for lhs, rhs in fd_entry:
        lhs_str = "".join(str(a) for a in lhs)
        rhs_str = "".join(str(a) for a in rhs)
        fdset.add_dependency(lhs_str, rhs_str)

    return fdset


def identify_sample_type(file_path):
    # e.g. sample_table_5_size_10_set_10000_1 -> sample_table_5_size_10_set_10000
    stem = Path(file_path).stem
    return re.sub(r"_\d+$", "", stem)


def analyze_file_group(file_paths, attribute_universe):
    results = {
        "files_processed": [Path(p).name for p in file_paths],
        "per_file": {},
        "total": {
            "BCNF": 0,
            "3NF": 0,
            "2NF": 0,
            "below_2NF": 0,
            "fd_sets_processed": 0,
        },
    }

    for file_path in file_paths:
        with open(file_path, "r", encoding="utf-8") as f:
            fd_sets = json.load(f)

        counts = defaultdict(int)
        file_name = Path(file_path).name
        for fd_entry in tqdm(fd_sets, desc=f"Analysing {file_name}", unit="set"):
            fdset = fdset_from_json_entry(fd_entry, attribute_universe)
            if fdset.isBCNF():
                nf = "BCNF"
            elif fdset.is3NF():
                nf = "3NF"
            elif fdset.is2NF():
                nf = "2NF"
            else:
                nf = "below_2NF"
            counts[nf] += 1
            counts["fd_sets_processed"] += 1

        file_counts = {
            "BCNF": counts["BCNF"],
            "3NF": counts["3NF"],
            "2NF": counts["2NF"],
            "below_2NF": counts["below_2NF"],
            "fd_sets_processed": counts["fd_sets_processed"],
        }
        results["per_file"][file_name] = file_counts

        for k in ("BCNF", "3NF", "2NF", "below_2NF", "fd_sets_processed"):
            results["total"][k] += file_counts[k]

    return results


def analyze_sample_files_normal_forms(files):
    if not files:
        return

    groups = defaultdict(list)
    for file_path in files:
        groups[identify_sample_type(file_path)].append(file_path)

    all_results = {}
    for sample_type, file_paths in sorted(groups.items()):
        attribute_universe = attribute_universe_from_filename(file_paths[0])
        results = analyze_file_group(file_paths, attribute_universe)

        output_file = f"normal_form_counts_{sample_type}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Written: {output_file}")

        all_results[sample_type] = results

    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "files", nargs="+", help="List of sample_*.json files to analyze"
    )
    args = parser.parse_args()

    all_results = analyze_sample_files_normal_forms(args.files)
    for sample_type, results in all_results.items():
        print(f"\n{sample_type}:")
        print(json.dumps(results["total"], indent=2))
