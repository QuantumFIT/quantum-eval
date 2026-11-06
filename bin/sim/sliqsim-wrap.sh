#!/bin/bash

ABSOLUTE_SCRIPT_PATH=$(readlink -f "$0")
SCRIPT_DIR=$(dirname "${ABSOLUTE_SCRIPT_PATH}")

QASM_FILE="$1"

# finding NL (no-loop) version as SliQSim does not support for {...} syntax
QASM_DIR=$(dirname "$QASM_FILE")
QASM_BASE=$(basename "$QASM_FILE")

# skip if the file is NL already
if [[ "$QASM_BASE" == NL_* ]]; then
    echo "###runtime:NA"
    echo "###memory:NA"
    exit 1
fi

QASM_NL_FILE="$QASM_DIR/NL_${QASM_BASE}"

# if such file exists, use it
if [ -f "$QASM_NL_FILE" ]; then
    QASM_FILE="$QASM_NL_FILE"
fi

# No-MCX variant: look in no-mcx subdirectory relative to the original file
NOMCX_FILE="$QASM_DIR/no-mcx/$QASM_BASE"
if [ -f "$NOMCX_FILE" ]; then
    QASM_FILE="$NOMCX_FILE"
fi

SLIQSIM_EXE="${SCRIPT_DIR}/SliQSim"

SLIQSIM_OUT=$("$SLIQSIM_EXE" --print_info --type 1 --sim_qasm "$QASM_FILE" 2>&1)

EXIT_CODE=$?

# treat warnings as errors
if echo "$SLIQSIM_OUT" | grep -qi "warning"; then
    echo "###runtime:NA"
    echo "###memory:NA"
    exit 1
fi

RUNTIME=$(echo "$SLIQSIM_OUT" | grep -oP 'Runtime:\s*\K[0-9.]+' || echo "NA")

MEMORY_BYTES=$(echo "$SLIQSIM_OUT" | grep -oP 'Peak memory usage:\s*\K[0-9]+' || echo "NA")

if [ "$MEMORY_BYTES" != "NA" ]; then
    MEMORY_KB=$(awk "BEGIN {print int($MEMORY_BYTES/1024)}")
else
    MEMORY_KB="NA"
fi

# Print in pycobench format
echo "###runtime:$RUNTIME"
echo "###memory:$MEMORY_KB"

exit $EXIT_CODE