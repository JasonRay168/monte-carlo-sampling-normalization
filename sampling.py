import random
import json
import os
import time
from generate import generate_table

def sample_table_fix_prob(table, probability=0.5):
    sample = []
    for row in table:
        coin_flip = random.random()
        if coin_flip < probability:
            sample.append(row)
    return sample

def sample_table_fix_size(table, size=10):
    total_rows = len(table)
    sample = []
    for row in table:
        coin_flip = random.random()
        if coin_flip < size/total_rows:
            sample.append(row)
    return sample

def convert_sample(sample):
    return 

def create_samples(table, table_name, num_samples=10000, num_iterations=2):
    set_num = 1
    while os.path.exists(f"sample_{num_samples}_table_{table_name}_set_{set_num}.json"):
        set_num += 1

    for _ in range(num_iterations):
        samples = [sample_table(table) for _ in range(num_samples)]
        filename = f"sample_{num_samples}_table_{table_name}_set_{set_num}.json"
        with open(filename, 'w') as f:
            json.dump(samples, f)
        print(f"Saved {num_samples} samples to {filename}")
        set_num += 1

if __name__ == "__main__":
    if not os.path.exists("tables.json"):
        print("tables.json not found!")
    else:
        print("tables.json already exists. Loading tables...")
        with open("tables.json", 'r') as f:
            data = json.load(f)
            table_8 = data["table_8"]

        start = time.time()

        create_samples(table_8, "8", num_samples=1000, num_iterations=1)

        elapsed = time.time() - start
        print(f"Time elapsed: {elapsed:.4f} seconds")