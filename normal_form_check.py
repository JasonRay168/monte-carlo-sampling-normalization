import glob
import json
import re
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm

from dbis_functional_dependencies import fds, fdcheck


def _concat_attributes(attrs):
	"""Concatenate mapped attribute symbols (e.g. ['0','2'] -> '02')."""
	return "".join(str(a) for a in attrs)


def _attribute_universe_from_filename(file_path):
	"""Extract attribute universe from filename segment table_<N>."""
	match = re.search(r"table_(\d+)", Path(file_path).name)
	if not match:
		raise ValueError(
			f"Could not extract table size from filename: {Path(file_path).name}. "
			"Expected pattern containing 'table_<N>'."
		)

	num_attrs = int(match.group(1))
	return "".join(str(i) for i in range(num_attrs))


def _fdset_from_json_entry(fd_entry, attribute_universe):
	"""Build a FunctionalDependencySet from one sampled FD set entry."""
	fdset = fdcheck.FunctionalDependencySet(attribute_universe)

	for lhs, rhs in fd_entry:
		lhs_str = _concat_attributes(lhs)
		rhs_str = _concat_attributes(rhs)
		fdset.add_dependency(lhs_str, rhs_str)

	return fdset


def _highest_normal_form(fdset):
	"""Classify by highest satisfied normal form for exclusive counting."""
	if fdset.isBCNF():
		return "BCNF"
	if fdset.is3NF():
		return "3NF"
	if fdset.is2NF():
		return "2NF"
	return "below_2NF"


def _sample_type(file_path):
	"""Return the base type of a sample file by stripping the trailing _<N> set number."""
	stem = Path(file_path).stem  # e.g. sample_table_5_size_10_set_10000_1
	return re.sub(r"_\d+$", "", stem)  # -> sample_table_5_size_10_set_10000


def _analyze_file_group(file_paths, attribute_universe):
	"""Analyze a list of files sharing the same sample type and return aggregated counts."""
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
			fdset = _fdset_from_json_entry(fd_entry, attribute_universe)
			nf = _highest_normal_form(fdset)
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


def analyze_sample_files_normal_forms(input_pattern="sample_*.json"):
	"""
	Read every sample_*.json file, group by sample type (stripping trailing _<N>),
	classify each FD set by highest normal form, and write one JSON per group.
	"""
	matched_files = sorted(glob.glob(input_pattern))
	if not matched_files:
		raise FileNotFoundError(f"No files matched pattern: {input_pattern}")

	# Group files by their base type name
	groups = defaultdict(list)
	for file_path in matched_files:
		groups[_sample_type(file_path)].append(file_path)

	all_results = {}
	for sample_type, file_paths in sorted(groups.items()):
		attribute_universe = _attribute_universe_from_filename(file_paths[0])
		results = _analyze_file_group(file_paths, attribute_universe)

		output_file = f"normal_form_counts_{sample_type}.json"
		with open(output_file, "w", encoding="utf-8") as f:
			json.dump(results, f, indent=2)
		print(f"Written: {output_file}")

		all_results[sample_type] = results

	return all_results


if __name__ == "__main__":
	all_results = analyze_sample_files_normal_forms()
	for sample_type, results in all_results.items():
		print(f"\n{sample_type}:")
		print(json.dumps(results["total"], indent=2))
