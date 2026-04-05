#!/usr/bin/env bash

set -u
set -o pipefail

shopt -s nullglob

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

DEFAULT_TABLES=(4 5 6 7 8 9 10)
MAX_JOBS=$(sysctl -n hw.logicalcpu) #use number of CPU cores by default
SHOW_DASHBOARD=1
declare -a SAMPLE_NUM_FDS=()
TABLES=()

usage() {
  cat <<'EOF'
Usage: bash test.sh [options] [table ...]

Options:
  -j, --jobs N        Maximum number of parallel jobs (default: number of CPU cores)
  --num-fds N         FD sample size to include (repeatable, default: sampling.py default)
  --no-dashboard      Disable the live terminal dashboard
  -h, --help          Show this help message

Arguments:
  table               One or more table numbers to process.
                      If omitted, the script runs tables 4 through 10.
EOF
}

is_number() {
  [[ "$1" =~ ^[0-9]+$ ]]
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    -j|--jobs)
      if [ "$#" -lt 2 ]; then
        echo "Missing value for $1" >&2
        exit 1
      fi
      MAX_JOBS="$2"
      shift 2
      ;;
    --num-fds)
      if [ "$#" -lt 2 ]; then
        echo "Missing value for $1" >&2
        exit 1
      fi
      SAMPLE_NUM_FDS+=("$2")
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

for n in "${SAMPLE_NUM_FDS[@]}"; do
  if ! is_number "$n" || [ "$n" -lt 1 ]; then
    echo "--num-fds values must be positive integers" >&2
    exit 1
  fi
done

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
progress_total=$((1 + 2 * ${#TABLES[@]}))

render_bar() {
  local width=30
  local filled empty
  filled=$((progress_done * width / progress_total))
  empty=$((width - filled))
  printf '%*s' "$filled" '' | tr ' ' '#'
  printf '%*s' "$empty" '' | tr ' ' '.'
}

latest_log_line() {
  local log_file="$1"
  if [ -f "$log_file" ]; then
    tail -n 1 "$log_file" 2>/dev/null | tr -d '\r' | cut -c1-70
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
  printf '%-8s %-10s %-12s %s\n' 'Table' 'Sampling' 'NormalForm' 'Latest log'
  printf '%s\n' '------------------------------------------------------------------------'

  local idx table line log_file
  for idx in "${!TABLES[@]}"; do
    table="${TABLES[$idx]}"
    log_file=""
    if [ "${NF_STATUS[$idx]}" = "running" ] || [ "${NF_STATUS[$idx]}" = "done" ] || [ "${NF_STATUS[$idx]}" = "ready" ]; then
      log_file="${NF_LOG[$idx]}"
    else
      log_file="${SAMPLE_LOG[$idx]}"
    fi
    line="$(latest_log_line "$log_file")"
    printf '%-8s %-10s %-12s %s\n' "$table" "${SAMPLE_STATUS[$idx]}" "${NF_STATUS[$idx]}" "$line"
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
    printf '[table %s] sampling started at %s\n' "$table" "$(date '+%H:%M:%S')"
    if [ "${#SAMPLE_NUM_FDS[@]}" -gt 0 ]; then
      python3 sampling.py "$table" --num-fds "${SAMPLE_NUM_FDS[@]}"
    else
      python3 sampling.py "$table"
    fi
    printf '[table %s] sampling finished at %s\n' "$table" "$(date '+%H:%M:%S')"
  ) >"$log_file" 2>&1 &
  SAMPLE_PID[$idx]="$!"
}

start_normal_form() {
  local idx="$1"
  local table="${TABLES[$idx]}"
  local log_file="${NF_LOG[$idx]}"
  local files=(sample_table_${table}_size_*_set_10000_*.json)
  if [ "${#files[@]}" -eq 0 ]; then
    echo "[table $table] no sample files found for normal-form analysis" >"$log_file"
    NF_STATUS[$idx]="failed"
    return 1
  fi

  NF_STATUS[$idx]="running"
  (
    printf '[table %s] normal_form_check started at %s\n' "$table" "$(date '+%H:%M:%S')"
    python3 normal_form_check.py "${files[@]}"
    printf '[table %s] normal_form_check finished at %s\n' "$table" "$(date '+%H:%M:%S')"
  ) >"$log_file" 2>&1 &
  NF_PID[$idx]="$!"
}

run_generate
progress_done=1
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
