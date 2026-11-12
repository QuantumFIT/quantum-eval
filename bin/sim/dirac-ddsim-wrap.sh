#!/bin/bash
# dirac-ddsim-wrap.sh
# Usage: ./dirac-ddsim-wrap.sh <pre_file> <qasm_file>

PRE_FILE="$2"
QASM_FILE="$1"
DDSIM_EXE="../simulators/dirac-ddsim/ddsim_dirac.py"

if [[ ! -f "$PRE_FILE" || ! -f "$QASM_FILE" ]]; then
    echo "Usage: $0 <pre_file> <qasm_file>"
    exit 1
fi

OUTPUT=$(python3 "$DDSIM_EXE" "$QASM_FILE" "$PRE_FILE" -i 2>&1)
EXIT_CODE=$?
MEMORY_KB=$(echo "$OUTPUT" | grep -oP 'Peak memory usage: \K[0-9.]+' )
RUNTIME=$(echo "$OUTPUT" | grep -oP 'Simulation time: \K[0-9.]+' )

echo "###runtime:$RUNTIME"
echo "###memory:$MEMORY_KB"

exit "$EXIT_CODE"