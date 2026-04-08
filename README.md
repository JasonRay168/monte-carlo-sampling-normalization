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
python3 sampling.py <table_num> [--num-fds <N1> <N2> ...] [--num-samples <COUNT>] [--num-sets <COUNT>]
```

3. Check Normal Forms

```bash
python3 normal_form_check.py <list_of_files...>
```

## Testing Flow

Run the whole workflow with one Bash script. It generates the tables, runs sampling per table in parallel, then runs the normal-form checks in parallel while showing a live dashboard.

```bash
bash test.sh --jobs <NUM_PARALLEL> [--num-fds <N>]... [TABLES]
```

By default, the generator now builds tables 4 through 13. The test runner still defaults to tables 4 through 10. You can pass a subset and control the parallelism:

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

## Trend Analysis And Graphs

The workbook `CS4221 Project Results.xlsx` and `collated_results.csv` are merged into one cleaned dataset. When both contain the same `(Num Attributes, Sample Size)` pair, the workbook row is used.

Generate a cleaned merged dataset and a text summary of the strongest trends:

```bash
python3 analyze_results.py
```

This writes:

- `analysis_results.csv`
- `trend_report.txt`

Generate the graphs from the cleaned dataset:

```bash
python3 plot_results.py
```

This writes SVG graphs into `graphs/`.

The analysis scripts use these definitions:

- `FD Density = sample size / num fds`
- `Reduction Ratio = minimal cover size / num fds`

The analysis scripts use hardcoded file names and do not take CLI arguments.
For the report-facing merged dataset and figures, rows with `FD Density > 1` are excluded as oversampling artifacts.
Partially collated runs with missing normal-form counts are also excluded from the cleaned dataset.
The combined FD-density figures use one shared linear window up to `0.11` and select representative points nearest a common density ladder for a cleaner report-ready comparison across `n`.
