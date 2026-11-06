#!/bin/bash

ABSOLUTE_SCRIPT_PATH=$(readlink -f "$0")
SCRIPT_DIR=$(dirname "$ABSOLUTE_SCRIPT_PATH")

QASM_FILE="$1"

if [ -z "$QASM_FILE" ]; then
    echo "Usage: $0 <qasm_file>"
    exit 1
fi

QASM_DIR=$(dirname "$QASM_FILE")
QASM_BASE=$(basename "$QASM_FILE")

if [[ "$QASM_BASE" == NL_* ]]; then
    echo "###runtime:NA"
    echo "###memory:NA"
    exit 0
fi

QASM_NL_FILE="$QASM_DIR/NL_${QASM_BASE}"

if [ -f "$QASM_NL_FILE" ]; then
    QASM_FILE="$QASM_NL_FILE"
fi

DDSIM_EXE="${SCRIPT_DIR}/../simulators/ddsim/build/apps/mqt-ddsim-simple"

TIME_OUTPUT=$( /usr/bin/time -f "MAXMEM=%M\nRUNTIME=%e" "$DDSIM_EXE" --ps --simulate_file "$QASM_FILE" 2>&1 >/dev/null )
EXIT_CODE=${PIPESTATUS[0]} 
RUNTIME=$(echo "$TIME_OUTPUT" | grep 'RUNTIME=' | cut -d'=' -f2)
MEMORY_KB=$(echo "$TIME_OUTPUT" | grep 'MAXMEM=' | cut -d'=' -f2)

echo "###runtime:$RUNTIME"
echo "###memory:$MEMORY_KB"

exit "$EXIT_CODE"