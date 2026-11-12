#!/bin/bash

ABSOLUTE_SCRIPT_PATH=$(readlink -f "$0")
SCRIPT_DIR=$(dirname "${ABSOLUTE_SCRIPT_PATH}")

QASM_FILE="$1"
# skip NL file
QASM_BASE=$(basename "$QASM_FILE")

if [[ "$QASM_BASE" == NL_* ]]; then
    echo "###runtime:NA"
    echo "###memory:NA"
    exit 1
fi


MEDUSA_SYLVAN_EXE="${SCRIPT_DIR}/../simulators/medusa-stabilizer/stabilizer"

MEDUSA_OUT=$("$MEDUSA_SYLVAN_EXE" -i --file "$QASM_FILE" 2>&1)

EXIT_CODE=$?

# Extract runtime (seconds)
RUNTIME=$(echo "$MEDUSA_OUT" | grep -oP 'Time=\K[0-9.]+')

# Extract peak memory usage
MEMORY_KB=$(echo "$MEDUSA_OUT" | grep -oP 'Peak Memory Usage=\K[0-9]+')

# Print in pycobench format
echo "###runtime:$RUNTIME"
echo "###memory:$MEMORY_KB"

[[ -f "res.dot" ]] && rm -f "res.dot"
[[ -f "res-vars.txt" ]] && rm -f "res-vars.txt"

exit $EXIT_CODE