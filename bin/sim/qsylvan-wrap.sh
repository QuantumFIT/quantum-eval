#!/bin/bash

ABSOLUTE_SCRIPT_PATH=$(readlink -f "$0")
SCRIPT_DIR=$(dirname "$ABSOLUTE_SCRIPT_PATH")

QSYLVAN_BACKEND="qmdd"

# Optional backend flag
if [[ "$1" == "-t" ]]; then
    QSYLVAN_BACKEND="$2"
    shift 2
fi

QASM_FILE="$1"

if [ -z "$QASM_FILE" ]; then
    echo "Usage: $0 [-t backend] <qasm_file>"
    exit 1
fi

QASM_DIR=$(dirname "$QASM_FILE")
QASM_BASE=$(basename "$QASM_FILE")

# Skip if already NL version
if [[ "$QASM_BASE" == NL_* ]]; then
    echo "###runtime:NA"
    echo "###memory:NA"
    exit 0
fi

# Prefer NL version if it exists because Q-Sylvan does not support loops
QASM_NL_FILE="$QASM_DIR/NL_${QASM_BASE}"
if [ -f "$QASM_NL_FILE" ]; then
    QASM_FILE="$QASM_NL_FILE"
fi

QSYLVAN_EXE="$SCRIPT_DIR/../simulators/qsylvan/build/qasm/run_qasm_on_${QSYLVAN_BACKEND}"

# Run with /usr/bin/time to measure memory + runtime
TIME_OUTPUT=$( /usr/bin/time -f "MAXMEM=%M\nRUNTIME=%e" \
    "$QSYLVAN_EXE" "$QASM_FILE" --state-vector \
    2>&1 >/tmp/qsylvan_stdout.$$ )

EXIT_CODE=${PIPESTATUS[0]}

# Read actual program output (JSON)
QSYLVAN_OUT=$(cat /tmp/qsylvan_stdout.$$)
rm /tmp/qsylvan_stdout.$$

# Extract runtime from JSON
RUNTIME=$(echo "$QSYLVAN_OUT" | grep -oP '"simulation_time"\s*:\s*\K[0-9.e+-]+')

# Fallback to /usr/bin/time runtime if JSON missing
if [ -z "$RUNTIME" ]; then
    RUNTIME=$(echo "$TIME_OUTPUT" | grep 'RUNTIME=' | cut -d'=' -f2)
fi

# Extract memory_kb from time output as JSON does not have it
MEMORY_KB=$(echo "$TIME_OUTPUT" | grep 'MAXMEM=' | cut -d'=' -f2)

echo "###runtime:$RUNTIME"
echo "###memory:$MEMORY_KB"

exit "$EXIT_CODE"
