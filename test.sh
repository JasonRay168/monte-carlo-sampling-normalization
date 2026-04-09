#!/usr/bin/env bash

set -u
set -o pipefail

shopt -s nullglob

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

DEFAULT_TABLES=(6)
MAX_JOBS=$(sysctl -n hw.logicalcpu)
SHOW_DASHBOARD=1
DENSITY_BASED=1
DENSITY_MAX=1.0
DENSITY_STEP=0.05
FD_CHUNK_SIZE=120
SIZE_PARALLEL_JOBS=$MAX_JOBS
NUM_SAMPLES=10000
NUM_SETS=3
RUN_GENERATE=0
HAS_SAMPLE_NUM_FDS=0
DEFAULT_SAMPLE_SIZES=(20 40 60)
declare -a SAMPLE_NUM_FDS=()
TABLES=()

usage() {
  cat <<'EOF'
Usage: bash test.sh [options] [table ...]

Options:
  -j, --jobs N        Maximum number of parallel jobs (default: number of CPU cores)
  --num-fds N         FD sample size to include (repeatable, overrides density-based mode)
  --generate          Regenerate tables with generate.py before sampling (default: off)
  --no-full-density   Disable density-based auto-scheduling and fall back to sampling.py defaults
  --density-max X     Maximum FD density for auto-scheduling (default: 1.0)
  --density-step X    Density ladder step for auto-scheduling (default: 0.05)
  --size-jobs N       Max parallel sampling.py jobs per table across sizes (default: number of CPU cores)
  --num-samples N     Number of sampled FD sets per generated JSON file (default: 10000)
  --num-sets N        Number of JSON files to generate for each FD sample size (default: 3)
  --no-dashboard      Disable the live terminal dashboard
  -h, --help          Show this help message

Arguments:
  table               One or more table numbers to process.
                      If omitted, the script runs table 6.
EOF
}

is_number() {
  [[ "$1" =~ ^[0-9]+$ ]]
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    -j|--jobs)
      [ "$#" -ge 2 ] || { echo "Missing value for $1" >&2; exit 1; }
      MAX_JOBS="$2"
      shift 2
      ;;
    --num-fds)
      [ "$#" -ge 2 ] || { echo "Missing value for $1" >&2; exit 1; }
      SAMPLE_NUM_FDS+=("$2")
      HAS_SAMPLE_NUM_FDS=1
      shift 2
      ;;
    --generate)
      RUN_GENERATE=1
      shift
      ;;
    --no-full-density)
      DENSITY_BASED=0
      shift
      ;;
    --density-max)
      [ "$#" -ge 2 ] || { echo "Missing value for $1" >&2; exit 1; }
      DENSITY_MAX="$2"
      shift 2
      ;;
    --density-step)
      [ "$#" -ge 2 ] || { echo "Missing value for $1" >&2; exit 1; }
      DENSITY_STEP="$2"
      shift 2
      ;;
    --fd-chunk-size)
      [ "$#" -ge 2 ] || { echo "Missing value for $1" >&2; exit 1; }
      FD_CHUNK_SIZE="$2"
      shift 2
      ;;
    --size-jobs)
      [ "$#" -ge 2 ] || { echo "Missing value for $1" >&2; exit 1; }
      SIZE_PARALLEL_JOBS="$2"
      shift 2
      ;;
    --num-samples)
      [ "$#" -ge 2 ] || { echo "Missing value for $1" >&2; exit 1; }
      NUM_SAMPLES="$2"
      shift 2
      ;;
    --num-sets)
      [ "$#" -ge 2 ] || { echo "Missing value for $1" >&2; exit 1; }
      NUM_SETS="$2"
      shift 2
      ;;
    --no-dashboard)
      SHOW_DASHBOARD=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      while [ "$#" -gt 0 ]; do
        TABLES+=("$1")
        shift
      done
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      TABLES+=("$1")
      shift
      ;;
  esac
done

if [ "${#TABLES[@]}" -eq 0 ]; then
  TABLES=("${DEFAULT_TABLES[@]}")
fi

if ! is_number "$MAX_JOBS" || [ "$MAX_JOBS" -lt 1 ]; then
  echo "--jobs must be a positive integer" >&2
  exit 1
fi

if ! is_number "$FD_CHUNK_SIZE" || [ "$FD_CHUNK_SIZE" -lt 1 ]; then
  echo "--fd-chunk-size must be a positive integer" >&2
  exit 1
fi
if ! is_number "$SIZE_PARALLEL_JOBS" || [ "$SIZE_PARALLEL_JOBS" -lt 1 ]; then
  echo "--size-jobs must be a positive integer" >&2
  exit 1
fi
if ! is_number "$NUM_SAMPLES" || [ "$NUM_SAMPLES" -lt 1 ]; then
  echo "--num-samples must be a positive integer" >&2
  exit 1
fi
if ! is_number "$NUM_SETS" || [ "$NUM_SETS" -lt 1 ]; then
  echo "--num-sets must be a positive integer" >&2
  exit 1
fi

if ! [[ "$DENSITY_MAX" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
  echo "--density-max must be a non-negative number" >&2
  exit 1
fi
if ! [[ "$DENSITY_STEP" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
  echo "--density-step must be a positive number" >&2
  exit 1
fi

if [ "$HAS_SAMPLE_NUM_FDS" -eq 1 ]; then
  for n in "${SAMPLE_NUM_FDS[@]}"; do
    if ! is_number "$n" || [ "$n" -lt 1 ]; then
      echo "--num-fds values must be positive integers" >&2
      exit 1
    fi
  done
fi

for table in "${TABLES[@]}"; do
  if ! is_number "$table"; then
    echo "Invalid table number: $table" >&2
    exit 1
  fi
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found in PATH" >&2
  exit 1
fi

if [ "$RUN_GENERATE" -eq 0 ] && [ ! -f "tables.json" ]; then
  if [ "$HAS_SAMPLE_NUM_FDS" -eq 0 ] && [ "$DENSITY_BASED" -eq 1 ]; then
    echo "tables.json not found. Density-based scheduling needs table FD counts." >&2
    echo "Provide tables.json, or run once with --generate, or pass explicit --num-fds values." >&2
    exit 1
  fi

  echo "tables.json not found. sampling.py requires tables.json for table loading." >&2
  echo "Provide tables.json or run once with --generate." >&2
  exit 1
fi

LOG_DIR="$(mktemp -d "${TMPDIR:-/tmp}/monte-carlo-flow.XXXXXX")"

declare -a SAMPLE_STATUS
declare -a SAMPLE_PID
declare -a SAMPLE_LOG
declare -a NF_STATUS
declare -a NF_PID
declare -a NF_LOG

for idx in "${!TABLES[@]}"; do
  SAMPLE_STATUS[$idx]="pending"
  SAMPLE_PID[$idx]=""
  SAMPLE_LOG[$idx]="$LOG_DIR/table_${TABLES[$idx]}_sampling.log"
  NF_STATUS[$idx]="pending"
  NF_PID[$idx]=""
  NF_LOG[$idx]="$LOG_DIR/table_${TABLES[$idx]}_normal_form.log"
done

cleanup() {
  for pid in "${SAMPLE_PID[@]}" "${NF_PID[@]}"; do
    if [ -n "${pid:-}" ] && kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
    fi
  done
}
trap cleanup EXIT INT TERM

count_running() {
  local running=0
  local idx
  for idx in "${!TABLES[@]}"; do
    [ "${SAMPLE_STATUS[$idx]}" = "running" ] && running=$((running + 1))
    [ "${NF_STATUS[$idx]}" = "running" ] && running=$((running + 1))
  done
  printf '%s' "$running"
}

all_done() {
  local idx
  for idx in "${!TABLES[@]}"; do
    [ "${SAMPLE_STATUS[$idx]}" = "done" ] || return 1
    [ "${NF_STATUS[$idx]}" = "done" ] || return 1
  done
  return 0
}

progress_done=0
progress_total=$((RUN_GENERATE + 2 * ${#TABLES[@]}))

render_bar() {
  local width=30
  local filled empty
  filled=$((progress_done * width / progress_total))
  empty=$((width - filled))
  printf '%*s' "$filled" '' | tr ' ' '#'
  printf '%*s' "$empty" '' | tr ' ' '.'
}

read_full_log() {
  local log_file="$1"
  if [ -f "$log_file" ]; then
    # show recent log content with tqdm progress converted to visible lines,
    # then collapse sampling/converting progress to one line per task label.
    # Use tail -n to get complete lines (not byte-bounded) to avoid truncating long progress bars
    LC_ALL=C tail -n 1000 "$log_file" 2>/dev/null | LC_ALL=C tr '\r' '\n' | \
      LC_ALL=C awk '
        {
          if ($0 ~ /^(Sampling table|Converting table) /) {
            key = $0
            sub(/: .*/, "", key)
            if (!(key in seen)) {
              seen[key] = 1
              order[++order_count] = key
            }
            latest[key] = $0
            next
          }

          # Keep any non-empty line that is not a progress line
          if (length($0) > 0) {
            other[++other_count] = $0
          }
        }
        END {
          for (i = 1; i <= other_count; i++) {
            print other[i]
          }
          for (i = 1; i <= order_count; i++) {
            print latest[order[i]]
          }
        }
      '
  fi
}

draw_dashboard() {
  if [ "$SHOW_DASHBOARD" -ne 1 ] || [ ! -t 1 ]; then
    return
  fi

  printf '\033[H\033[2J'
  printf 'Monte Carlo Sampling Normalization\n'
  printf 'Progress [%s] %d/%d\n' "$(render_bar)" "$progress_done" "$progress_total"
  printf 'Parallel jobs: %s\n\n' "$MAX_JOBS"

  local idx table log_file log_content
  for idx in "${!TABLES[@]}"; do
    table="${TABLES[$idx]}"
    if [ "${NF_STATUS[$idx]}" = "running" ] || [ "${NF_STATUS[$idx]}" = "done" ] || [ "${NF_STATUS[$idx]}" = "ready" ]; then
      log_file="${NF_LOG[$idx]}"
    else
      log_file="${SAMPLE_LOG[$idx]}"
    fi
    printf '\n--- Table %s [Sampling: %s | NormalForm: %s] ---\n' "$table" "${SAMPLE_STATUS[$idx]}" "${NF_STATUS[$idx]}"
    log_content="$(read_full_log "$log_file")"
    if [ -n "$log_content" ]; then
      printf '%s\n' "$log_content" | tail -n 20
    else
      printf '(no log yet)\n'
    fi
  done
}

run_generate() {
  echo "[generate] python3 generate.py"
  python3 generate.py
}

start_sampling() {
  local idx="$1"
  local table="${TABLES[$idx]}"
  local log_file="${SAMPLE_LOG[$idx]}"
  SAMPLE_STATUS[$idx]="running"

  (
    set -euo pipefail

    get_fd_count() {
      local t="$1"
      python3 - "$t" <<'PY'
import json, sys
n = int(sys.argv[1])
with open("tables.json", "r", encoding="utf-8") as fh:
    data = json.load(fh)
print(len(data[f"table_{n}"]))
PY
    }



    run_sampling_for_table() {
      local table_num="$1"
      local requested_sizes=()
      local pending_sizes=()
      local pending_sets=()

      size_needs_sampling() {
        local size="$1"
        local existing_files=(sample_table_${table_num}_size_${size}_set_${NUM_SAMPLES}_*.json)
        local existing_count="${#existing_files[@]}"
        [ "$existing_count" -lt "$NUM_SETS" ]
      }

      size_sets_needed() {
        local size="$1"
        local existing_files=(sample_table_${table_num}_size_${size}_set_${NUM_SAMPLES}_*.json)
        local existing_count="${#existing_files[@]}"
        local needed=$((NUM_SETS - existing_count))
        if [ "$needed" -lt 0 ]; then
          needed=0
        fi
        printf '%s' "$needed"
      }

      build_pending_sizes() {
        local size
        local needed_sets
        pending_sizes=()
        pending_sets=()
        for size in "${requested_sizes[@]}"; do
          needed_sets="$(size_sets_needed "$size")"
          if [ "$needed_sets" -gt 0 ]; then
            pending_sizes+=("$size")
            pending_sets+=("$needed_sets")
          fi
        done
      }

      run_sizes_in_parallel() {
        local total_sizes="${#pending_sizes[@]}"
        local next_index=0
        local -a job_pids=()
        local -a job_sizes=()
        local -a job_sets=()
        local i pid size sets rc

        if [ "$total_sizes" -eq 0 ]; then
          echo "[table $table_num] all requested sample sizes already exist; skipping sampling"
          return 0
        fi

        while :; do
          while [ "${#job_pids[@]}" -lt "$SIZE_PARALLEL_JOBS" ] && [ "$next_index" -lt "$total_sizes" ]; do

            size="${pending_sizes[$next_index]}"
            sets="${pending_sets[$next_index]}"
            echo "[table $table_num] sampling size $size (remaining sets: $sets)"

            python3 sampling.py "$table_num" \
              --num-fds "$size" \
              --num-samples "$NUM_SAMPLES" \
              --num-sets "$sets" &

            job_pids+=("$!")
            job_sizes+=("$size")
            job_sets+=("$sets")
            next_index=$((next_index + 1))
          done

          if [ "${#job_pids[@]}" -eq 0 ] && [ "$next_index" -ge "$total_sizes" ]; then
            break
          fi

          i=0
          while [ "$i" -lt "${#job_pids[@]}" ]; do
            pid="${job_pids[$i]}"
            if ! kill -0 "$pid" >/dev/null 2>&1; then
              if wait "$pid"; then
                echo "[table $table_num] completed size ${job_sizes[$i]}"
              else
                rc="$?"
                echo "[table $table_num] failed size ${job_sizes[$i]} with exit code $rc" >&2
                for pid in "${job_pids[@]}"; do
                  kill "$pid" >/dev/null 2>&1 || true
                done
                for pid in "${job_pids[@]}"; do
                  wait "$pid" >/dev/null 2>&1 || true
                done
                return "$rc"
              fi

              unset 'job_pids[$i]' 'job_sizes[$i]' 'job_sets[$i]'
              job_pids=("${job_pids[@]}")
              job_sizes=("${job_sizes[@]}")
              job_sets=("${job_sets[@]}")
              continue
            fi
            i=$((i + 1))
          done

          sleep 1
        done

        return 0
      }

      if [ "$HAS_SAMPLE_NUM_FDS" -eq 1 ]; then
        requested_sizes=("${SAMPLE_NUM_FDS[@]}")
        build_pending_sizes
        run_sizes_in_parallel
        return $?
      fi

      if [ "$DENSITY_BASED" -eq 0 ]; then
        requested_sizes=("${DEFAULT_SAMPLE_SIZES[@]}")
        build_pending_sizes
        if [ "${#pending_sizes[@]}" -eq 0 ]; then
          echo "[table $table_num] default sample sizes already exist; skipping sampling"
          return 0
        fi
        python3 sampling.py "$table_num" \
          --num-fds "${pending_sizes[@]}" \
          --num-samples "$NUM_SAMPLES" \
          --num-sets "$NUM_SETS"
        return $?
      fi

      local fd_count
      fd_count="$(get_fd_count "$table_num")"
      echo "[table $table_num] density-based mode: max density $DENSITY_MAX step $DENSITY_STEP"

      density_sizes_str="$(python3 - "$fd_count" "$DENSITY_MAX" "$DENSITY_STEP" <<'PY'
import math
import sys

num_fds = int(sys.argv[1])
dmax = float(sys.argv[2])
dstep = float(sys.argv[3])

if dstep <= 0:
    dstep = 0.02

max_density = min(max(dmax, 0.0), 1.0)
steps = int(math.floor(max_density / dstep + 1e-9))

sizes = {1, num_fds}
for i in range(1, steps + 1):
    density = i * dstep
    size = int(round(density * num_fds))
    size = max(1, min(num_fds, size))
    sizes.add(size)

print(" ".join(str(v) for v in sorted(sizes)))
PY
)"

      if [ -z "$density_sizes_str" ]; then
        echo "[table $table_num] no density sizes produced" >&2
        return 1
      fi

      density_sizes=()
      for size in $density_sizes_str; do
        density_sizes+=("$size")
      done

      requested_sizes=("${density_sizes[@]}")
      build_pending_sizes
      run_sizes_in_parallel
      return $?
    }

    printf '[table %s] sampling started at %s\n' "$table" "$(date '+%H:%M:%S')"
    run_sampling_for_table "$table"
    printf '[table %s] sampling finished at %s\n' "$table" "$(date '+%H:%M:%S')"
  ) >"$log_file" 2>&1 &

  SAMPLE_PID[$idx]="$!"
}

start_normal_form() {
  local idx="$1"
  local table="${TABLES[$idx]}"
  local log_file="${NF_LOG[$idx]}"
  local files=(sample_table_${table}_size_*_set_${NUM_SAMPLES}_*.json)
  local pending_files=()
  local bases=()
  local incomplete_bases=()
  local extra_bases=()
  local base_files=()
  local selected_base_files=()
  local sample_file file_name base_name count_file
  local known_base base_seen base_count selected_count extra_count item

  if [ "${#files[@]}" -eq 0 ]; then
    echo "[table $table] no sample files found for normal-form analysis" >"$log_file"
    NF_STATUS[$idx]="failed"
    return 1
  fi

  # Build unique sample bases for this table and num-samples bucket.
  for sample_file in "${files[@]}"; do
    file_name="$(basename "$sample_file")"
    base_name="${file_name%.json}"
    base_name="${base_name%_[0-9]*}"

    base_seen=0
    for known_base in "${bases[@]-}"; do
      if [ "$known_base" = "$base_name" ]; then
        base_seen=1
        break
      fi
    done
    if [ "$base_seen" -eq 0 ]; then
      bases+=("$base_name")
    fi
  done

  # Only process bases that have complete sampling sets.
  for base_name in "${bases[@]}"; do
    base_files=($(printf '%s\n' ${base_name}_*.json | sort -V))
    base_count="${#base_files[@]}"
    if [ "$base_count" -lt "$NUM_SETS" ]; then
      incomplete_bases+=("${base_name}:${base_count}/${NUM_SETS}")
      continue
    fi

    selected_base_files=("${base_files[@]:0:NUM_SETS}")
    selected_count="${#selected_base_files[@]}"
    extra_count=$((base_count - selected_count))
    if [ "$extra_count" -gt 0 ]; then
      extra_bases+=("${base_name}:${extra_count} extra ignored")
    fi

    count_file="normal_form_counts_${base_name}.json"
    if [ ! -f "$count_file" ]; then
      pending_files+=("${selected_base_files[@]}")
    fi
  done

  NF_STATUS[$idx]="running"
  (
    if [ "${#incomplete_bases[@]}" -gt 0 ]; then
      printf '[table %s] waiting on complete test sets before normal-form:\n' "$table"
      for item in "${incomplete_bases[@]}"; do
        printf '  - %s\n' "$item"
      done
    fi

    if [ "${#extra_bases[@]}" -gt 0 ]; then
      printf '[table %s] found more than %s sets; using first %s only:\n' "$table" "$NUM_SETS" "$NUM_SETS"
      for item in "${extra_bases[@]}"; do
        printf '  - %s\n' "$item"
      done
    fi

    if [ "${#pending_files[@]}" -eq 0 ]; then
      printf '[table %s] normal_form_check skipped; no complete pending bases\n' "$table"
      exit 0
    fi
    printf '[table %s] normal_form_check started at %s\n' "$table" "$(date '+%H:%M:%S')"
    python3 normal_form_check.py "${pending_files[@]}"
    printf '[table %s] normal_form_check finished at %s\n' "$table" "$(date '+%H:%M:%S')"
  ) >"$log_file" 2>&1 &
  NF_PID[$idx]="$!"
}

if [ "$RUN_GENERATE" -eq 1 ]; then
  run_generate
  progress_done=1
fi

draw_dashboard

failed=0

while :; do
  for idx in "${!TABLES[@]}"; do
    if [ "${SAMPLE_STATUS[$idx]}" = "running" ]; then
      pid="${SAMPLE_PID[$idx]}"
      if ! kill -0 "$pid" >/dev/null 2>&1; then
        if wait "$pid"; then
          SAMPLE_STATUS[$idx]="done"
          progress_done=$((progress_done + 1))
          NF_STATUS[$idx]="ready"
        else
          rc="$?"
          SAMPLE_STATUS[$idx]="failed"
          failed=1
        fi
      fi
    fi

    if [ "${NF_STATUS[$idx]}" = "running" ]; then
      pid="${NF_PID[$idx]}"
      if ! kill -0 "$pid" >/dev/null 2>&1; then
        if wait "$pid"; then
          NF_STATUS[$idx]="done"
          progress_done=$((progress_done + 1))
        else
          NF_STATUS[$idx]="failed"
          failed=1
        fi
      fi
    fi
  done

  if [ "$failed" -ne 0 ]; then
    draw_dashboard
    echo
    echo "Flow failed. Check the logs under $LOG_DIR" >&2
    exit 1
  fi

  while [ "$(count_running)" -lt "$MAX_JOBS" ]; do
    launched=0

    for idx in "${!TABLES[@]}"; do
      if [ "${NF_STATUS[$idx]}" = "ready" ]; then
        if start_normal_form "$idx"; then
          launched=1
        else
          failed=1
        fi
        break
      fi
    done

    if [ "$launched" -eq 1 ]; then
      continue
    fi

    for idx in "${!TABLES[@]}"; do
      if [ "${SAMPLE_STATUS[$idx]}" = "pending" ]; then
        start_sampling "$idx"
        launched=1
        break
      fi
    done

    if [ "$launched" -eq 0 ]; then
      break
    fi
  done

  draw_dashboard

  if all_done; then
    break
  fi

  sleep 1
done

draw_dashboard

echo
echo "All stages completed successfully."
echo "Dashboard logs: $LOG_DIR"

python3 collate.py
