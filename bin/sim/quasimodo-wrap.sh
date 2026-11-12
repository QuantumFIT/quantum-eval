#!/bin/bash

ABSOLUTE_SCRIPT_PATH=$(readlink -f "$0")
SCRIPT_DIR=$(dirname "${ABSOLUTE_SCRIPT_PATH}")

QUASIMODO_BACKEND='CFLOBDD'

if [[ "$1" == "-t" ]]; then
    QUASIMODO_BACKEND="$2"
    shift
    shift
fi

QASM_FILE="$1"

# finding NL (no-loop) version as Quasimodo does not support for {...} syntax
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
QUASIMODO_EXE="LD_LIBRARY_PATH=${SCRIPT_DIR}/../simulators/quasimodo/Quasimodo:$LD_LIBRARY_PATH ${SCRIPT_DIR}/../simulators/quasimodo/QuasimodoSim"
QUASIMODO_OUT=$(eval "$QUASIMODO_EXE -t $QUASIMODO_BACKEND -i -f $QASM_FILE 2>&1")

EXIT_CODE=$?

RUNTIME=$(echo "$QUASIMODO_OUT" | grep -oP 'Time=\s*\K[0-9.e+-]+')

MEMORY_KB=$(echo "$QUASIMODO_OUT" | grep -oP 'Peak Memory Usage=\s*\K[0-9]+' || echo "NA")


# Print in pycobench format
echo "###runtime:$RUNTIME"
echo "###memory:$MEMORY_KB"

exit $EXIT_CODE