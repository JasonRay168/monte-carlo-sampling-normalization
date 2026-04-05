#!/usr/bin/env bash
#
# Runs the three Monte Carlo experiments:
#   1) Vary num_attributes  (fix num_fds=20, n=4..13)
#   2) Vary num_fds          (fix n=7)
#   3) Controlled FD density (5%, 10%, 20% across n=5..8)
#
# Usage:
#   bash run_experiment.sh [1|2|3|all]   (default: all)

set -u
set -o pipefail
shopt -s nullglob

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

EXPERIMENT="${1:-all}"

run() {
  echo "────────────────────────────────────────"
  echo "  $1"
  echo "────────────────────────────────────────"
  shift
  bash test.sh --no-dashboard "$@"
}

python3 generate.py

case "$EXPERIMENT" in
  1)
    # Experiment 1: vary num_attributes, fix num_fds=20
    # n=4..13, density ranges from 71% (n=4) to 0.04% (n=13)
    run "Exp 1: vary num_attributes (num_fds=20)" --num-fds 20
    ;;

  2)
    # Experiment 2: vary num_fds, fix n=7 (441 total FDs)
    # density ranges from 1.1% to 45.4%
    run "Exp 2: vary num_fds (n=7)" 7 --num-fds 5 10 20 40 60 80 100 150 200
    ;;

  3)
    # Experiment 3: controlled FD density across n=5..8
    # ≈5% density
    run "Exp 3: ~5% density, n=5"  5 --num-fds 4
    run "Exp 3: ~5% density, n=6"  6 --num-fds 9
    run "Exp 3: ~5% density, n=7"  7 --num-fds 22
    run "Exp 3: ~5% density, n=8"  8 --num-fds 51

    # ≈10% density
    run "Exp 3: ~10% density, n=5" 5 --num-fds 8
    run "Exp 3: ~10% density, n=6" 6 --num-fds 19
    run "Exp 3: ~10% density, n=7" 7 --num-fds 44
    run "Exp 3: ~10% density, n=8" 8 --num-fds 102

    # ≈20% density
    run "Exp 3: ~20% density, n=5" 5 --num-fds 15
    run "Exp 3: ~20% density, n=6" 6 --num-fds 37
    run "Exp 3: ~20% density, n=7" 7 --num-fds 88
    run "Exp 3: ~20% density, n=8" 8 --num-fds 203
    ;;

  all)
    run "Exp 1: vary num_attributes (num_fds=20)" --num-fds 20

    run "Exp 2: vary num_fds (n=7)" 7 --num-fds 5 10 20 40 60 80 100 150 200

    run "Exp 3: ~5% density, n=5"  5 --num-fds 4
    run "Exp 3: ~5% density, n=6"  6 --num-fds 9
    run "Exp 3: ~5% density, n=7"  7 --num-fds 22
    run "Exp 3: ~5% density, n=8"  8 --num-fds 51
    run "Exp 3: ~10% density, n=5" 5 --num-fds 8
    run "Exp 3: ~10% density, n=6" 6 --num-fds 19
    run "Exp 3: ~10% density, n=7" 7 --num-fds 44
    run "Exp 3: ~10% density, n=8" 8 --num-fds 102
    run "Exp 3: ~20% density, n=5" 5 --num-fds 15
    run "Exp 3: ~20% density, n=6" 6 --num-fds 37
    run "Exp 3: ~20% density, n=7" 7 --num-fds 88
    run "Exp 3: ~20% density, n=8" 8 --num-fds 203
    ;;

  *)
    echo "Usage: bash run_experiment.sh [1|2|3|all]" >&2
    exit 1
    ;;
esac

echo
echo "Done. Results in collated_results.csv"
