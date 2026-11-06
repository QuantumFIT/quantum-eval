#!/bin/bash

show_help() {
	echo "Usage:"
	echo "run_eq_bench.sh [options] [BENCHMARK1 BENCHMARK2 ...]"
	echo ""
	echo "Runs the given equivalence checker on the specified benchmarks (eq/<BENCHMARK>.input)."
	echo "If no benchmark is given, all suites are run:"
	echo "  eq_exact-opt, eq_exact-rm1, eq_exact-rm3,"
	echo "  eq_approx-opt, eq_approx-shift4, eq_approx-shift7"
	echo ""
	echo "Options:"
	echo "  -h        Show this help message"
	echo "  -t TOOL   Which tool to run (default=sliqec)"
	echo "  -j N      How many processes to run in parallel (default=4; always 1 for qcec-parallel)"
	echo "  -m N      Memory limit of each process in GB (default=3)"
	echo "  -s N      Timeout for each process in seconds (default=300)"

	echo "Note: positional arguments are treated as benchmark names and are not"
	echo "expanded into groups. Provide multiple benchmark names to run them all."
}

# input files contain paths relative to bench/
cd "$(dirname "$(readlink -f "$0")")" || exit 1

CONFIG="eq/quantum-eq.yaml"

tool="sliqec"
j_value="4"
m_value="3"
s_value="300"
while getopts "ht:j:m:s:" option; do
    case $option in
        h)
            show_help
            exit 0
            ;;
        t)
            tool=$OPTARG
            ;;
        j)
            j_value=$OPTARG
            ;;
        m)
            m_value=$OPTARG
            ;;
        s)
            s_value=$OPTARG
            ;;
        *)
            echo "Invalid option: -$OPTARG"
            show_help
            exit 1
            ;;
    esac
done

# Shift the option index so that $1 refers to the first positional argument
shift $((OPTIND - 1))

# qcec-parallel uses all cores itself, so only one pair may run at a time
if [ "$tool" = "qcec-parallel" ] && [ "$j_value" != "1" ]; then
    echo "qcec-parallel runs multithreaded: using -j 1 instead of -j $j_value"
    j_value="1"
fi

if [ ! -f "$CONFIG" ]; then
    echo "Config $CONFIG not found"
    exit 1
fi

benchmarks=()

# If no benchmark is given, run all equivalence suites
if [ -z "$1" ]; then
  benchmarks=("eq_exact-opt" "eq_exact-rm1" "eq_exact-rm3" "eq_approx-opt" "eq_approx-shift4" "eq_approx-shift7")
else
  # treat each positional argument as a benchmark name (no grouping)
  for BENCH_NAME in "$@"; do
    benchmarks+=("$BENCH_NAME")
  done
fi

tasks_files=()

CUR_DATE=$(date +%Y-%m-%d-%H-%M)
for benchmark in "${benchmarks[@]}"; do
	if [ ! -f "eq/$benchmark.input" ]; then
		echo "Skipping $benchmark: eq/$benchmark.input not found"
		continue
	fi
	echo "Running benchmark $benchmark"
	FILE_PREFIX="$benchmark-to${s_value}-$tool-$CUR_DATE"
	TASKS_FILE="$FILE_PREFIX.tasks"
	cat "eq/$benchmark.input" | ./pycobench -c "$CONFIG" -j $j_value -t $s_value --memout $m_value -m "$tool" -o "$TASKS_FILE"
	tasks_files+=("$TASKS_FILE")
	echo "$TASKS_FILE" >> tasks_names.txt
done

for tasks_file in "${tasks_files[@]}"; do
	echo "$tasks_file"
done
