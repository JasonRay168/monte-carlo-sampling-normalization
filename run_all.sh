#!/usr/bin/env zsh
# Efficient single-pass runner for all 3 experiments.
# Uses zsh (default macOS shell) for associative array support.
set -uo pipefail

cd "$(dirname "${0:A}")"
source .venv/bin/activate

MAX_JOBS=$(sysctl -n hw.logicalcpu 2>/dev/null || echo 4)
LOG_DIR="$(mktemp -d "${TMPDIR:-/tmp}/mc-all.XXXXXX")"

echo "=== Phase 0: Generate tables ==="
python3 generate.py

# Collect all (table:num_fds) pairs, deduplicating
typeset -A SEEN
UNIQUE_JOBS=()

add_job() {
  local key="$1:$2"
  if [[ -z "${SEEN[$key]:-}" ]]; then
    SEEN[$key]=1
    UNIQUE_JOBS+=("$key")
  fi
}

# Experiment 1: vary num_attributes, fix num_fds=20
for t in 4 5 6 7 8 9 10 11 12 13; do add_job $t 20; done

# Experiment 2: vary num_fds, fix n=7
for nf in 5 10 20 40 60 80 100 150 200; do add_job 7 $nf; done

# Experiment 3: controlled FD density (~5%, ~10%, ~20%) across n=5..8
for pair in 5:4 6:9 7:22 8:51 5:8 6:19 7:44 8:102 5:15 6:37 7:88 8:203; do
  add_job ${pair%%:*} ${pair##*:}
done

echo "=== Phase 1: Sampling (${#UNIQUE_JOBS[@]} configs, $MAX_JOBS parallel) ==="

pids=()
pid_labels=()
done_count=0
total=${#UNIQUE_JOBS[@]}

reap_one() {
  # Wait for any one child to finish
  while true; do
    for i in {1..${#pids[@]}}; do
      local p=${pids[$i]}
      if ! kill -0 "$p" 2>/dev/null; then
        wait "$p" || { echo "\nFAILED: ${pid_labels[$i]}"; exit 1; }
        done_count=$((done_count + 1))
        printf '\r  [%d/%d] %s done          ' "$done_count" "$total" "${pid_labels[$i]}"
        pids[$i]=()
        pid_labels[$i]=()
        pids=("${(@)pids:#}")
        pid_labels=("${(@)pid_labels:#}")
        return
      fi
    done
    sleep 0.5
  done
}

for j in "${UNIQUE_JOBS[@]}"; do
  t="${j%%:*}"
  nf="${j##*:}"

  log="$LOG_DIR/sample_${t}_${nf}.log"
  python3 sampling.py "$t" --num-fds "$nf" >"$log" 2>&1 &
  pids+=($!)
  pid_labels+=("table=$t nf=$nf")

  if (( ${#pids[@]} >= MAX_JOBS )); then
    reap_one
  fi
done

while (( ${#pids[@]} > 0 )); do
  reap_one
done
echo

# Figure out which tables were used
typeset -A NF_TABLES
for j in "${UNIQUE_JOBS[@]}"; do
  NF_TABLES[${j%%:*}]=1
done
TABLES=(${(kon)NF_TABLES})

echo "=== Phase 2: Normal form checking (${#TABLES[@]} tables) ==="

pids=()
pid_labels=()
done_count=0
total=${#TABLES[@]}

for t in "${TABLES[@]}"; do
  files=(sample_table_${t}_size_*_set_10000_*.json(N))
  if (( ${#files[@]} == 0 )); then
    echo "  [table $t] no sample files, skipping"
    done_count=$((done_count + 1))
    continue
  fi

  log="$LOG_DIR/nf_${t}.log"
  python3 normal_form_check.py "${files[@]}" >"$log" 2>&1 &
  pids+=($!)
  pid_labels+=("table=$t (${#files[@]} files)")

  if (( ${#pids[@]} >= MAX_JOBS )); then
    reap_one
  fi
done

while (( ${#pids[@]} > 0 )); do
  reap_one
done
echo

echo "=== Phase 3: Collate ==="
python3 collate.py

echo
echo "All done. Results: collated_results.csv"
echo "Logs: $LOG_DIR"
