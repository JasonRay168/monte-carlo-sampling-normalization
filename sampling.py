import argparse
import random
import json
import os
import time
from tqdm import tqdm
from generate import generate_table
from functional_dependencies import *


def sample_table_fix_prob(table, probability=0.5):
    sample = []
    for row in table:
        coin_flip = random.random()
        if coin_flip < probability:
            sample.append(row)
    return sample


def sample_table_fix_size(table, size):
    total_rows = len(table)
    sample = []
    for row in table:
        coin_flip = random.random()
        if coin_flip < size / total_rows:
            sample.append(row)
    return sample


def convert_sample(sample):
    fdset = FDSet()
    for row in sample:
        lhs = set()
        rhs = set()

        for idx, value in enumerate(row):
            if value == 1:
                lhs.add(f"{idx}")
            elif value == -1:
                rhs.add(f"{idx}")

        fdset.add(FD(lhs, rhs))

    return fdset.basis()


def fd_set_to_json(fd_set):
    return [(list(fd.lhs), list(fd.rhs)) for fd in fd_set]


def test_conversion():
    sample = [[1, 0, -1, 0], [0, 1, -1, 0], [1, 1, -1, 0], [-1, -1, 0, 1]]
    converted = convert_sample(sample)
    print(converted)


def create_samples_fix_size(table, table_name, sample_size, num_samples=10000):
    set_num = 1
    while os.path.exists(
        f"sample_table_{table_name}_size_{sample_size}_set_{num_samples}_{set_num}.json"
    ):
        set_num += 1

    samples = [
        sample_table_fix_size(table, sample_size)
        for _ in tqdm(
            range(num_samples),
            desc=f"Sampling table {table_name} (size={sample_size})",
            unit="sample",
        )
    ]
    fdsets = [
        convert_sample(sample)
        for sample in tqdm(
            samples,
            desc=f"Converting table {table_name} (size={sample_size})",
            unit="sample",
        )
    ]

    filename = (
        f"sample_table_{table_name}_size_{sample_size}_set_{num_samples}_{set_num}.json"
    )
    json_fdsets = [fd_set_to_json(fdset) for fdset in fdsets]
    with open(filename, "w") as f:
        json.dump(json_fdsets, f)

    return fdsets


def create_samples_fix_prob(table, table_name, probability, num_samples=10000):
    set_num = 1
    while os.path.exists(
        f"sample_table_{table_name}_prob_{probability}_set_{num_samples}_{set_num}.json"
    ):
        set_num += 1

    samples = [
        sample_table_fix_prob(table, probability)
        for _ in tqdm(
            range(num_samples),
            desc=f"Sampling table {table_name} (prob={probability})",
            unit="sample",
        )
    ]
    fdsets = [
        convert_sample(sample)
        for sample in tqdm(
            samples,
            desc=f"Converting table {table_name} (prob={probability})",
            unit="sample",
        )
    ]

    filename = (
        f"sample_table_{table_name}_prob_{probability}_set_{num_samples}_{set_num}.json"
    )
    json_fdsets = [fd_set_to_json(fdset) for fdset in fdsets]
    with open(filename, "w") as f:
        json.dump(json_fdsets, f)

    return fdsets


if __name__ == "__main__":
    if not os.path.exists("tables.json"):
        print("tables.json not found!")
        exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument("table", type=int, help="Table number e.g. 7 for table_7")
    parser.add_argument(
        "--num-fds",
        type=int,
        nargs="+",
        default=None,
        help="One or more FD sample sizes (default: run 20, 40, and 60)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible sampling",
    )
    args = parser.parse_args()

    table_number = args.table

    if args.seed is not None:
        random.seed(args.seed)

    print(f"tables.json already exists. Loading table {table_number}...")

    with open("tables.json", "r") as f:
        data = json.load(f)

    start = time.time()

    sample_sizes = args.num_fds if args.num_fds is not None else [20, 40, 60]
    if any(size <= 0 for size in sample_sizes):
        parser.error("--num-fds values must be positive integers")

    print(f"FD sample sizes: {sample_sizes}")
    if args.seed is not None:
        print(f"Sampling seed: {args.seed}")

    for size in sample_sizes:
        for i in range(3):  # Create 3 sets for each size
            fdsample_size = create_samples_fix_size(
                data[f"table_{table_number}"],
                f"{table_number}",
                sample_size=size,
                num_samples=10000,
            )

    elapsed = time.time() - start
    print(f"Time elapsed: {elapsed:.4f} seconds")
