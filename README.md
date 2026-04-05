# Monte Carlo Sampling Normalization

> For CS4221 coursework

## Environment

Versions:
- Python 3.12.13 (Tested by @jloh02)

```bash
pip install -r requirements.txt
```

## Steps

1. Generate Tables

```bash
python3 generate.py
```

2. Sample Tables

```bash
python3 sampling.py <table_num>
```

3. Check Normal Forms

```bash
python3 normal_form_check.py <list_of_files...>
```

## Testing Flow

Run the whole workflow with one Bash script. It generates the tables, runs sampling per table in parallel, then runs the normal-form checks in parallel while showing a live dashboard.

```bash
bash test.sh --jobs <NUM_PARALLEL> [TABLES]
```

By default, the script processes tables 4 through 10. You can pass a subset and control the parallelism:

```bash
bash test.sh --jobs 4 4 5 6
```

The runner also writes a collated CSV summary at the end of the flow.

## CSV Collation

Generate the CSV summary directly from the existing sample and normal-form output files

**NOTE:** Uses all result json files, remember to delete when you change the run

```bash
python3 collate.py
```

This writes `collated_results.csv` with these columns:

- Sample Size
- Num Attributes
- No. Fds
- FD Density
- Minimal Cover Size
- Reduction Ratio
- 1NF
- 2NF
- 3NF
- BCNF

`FD Density` and `Reduction Ratio` are intentionally left blank so you can fill them in with Excel formulas later.