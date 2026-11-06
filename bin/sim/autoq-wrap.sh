#!/bin/bash
# autoq-wrap.sh
# Usage: ./autoq-wrap.sh <pre_file> <qasm_file>

PRE_FILE="$2"
QASM_FILE="$1"
AUTOQ_EXE="../simulators/autoq/build/cli/autoq"  # <-- relative path without leading /

if [[ ! -f "$PRE_FILE" || ! -f "$QASM_FILE" ]]; then
    echo "Usage: $0 <pre_file> <qasm_file>"
    exit 1
fi

if [[ ! -x "$AUTOQ_EXE" ]]; then
    echo "Error: autoq executable not found at $AUTOQ_EXE or is not executable"
    exit 1
fi

TIME_OUTPUT=$( /usr/bin/time -f "%e %M" "$AUTOQ_EXE" ex "$PRE_FILE" "$QASM_FILE" 2>&1 1>/dev/null )
EXIT_CODE=${PIPESTATUS[0]} 
RUNTIME=$(echo "$TIME_OUTPUT" | awk '{print $1}')
MEMORY_KB=$(echo "$TIME_OUTPUT" | awk '{print $2}')

echo "###runtime:$RUNTIME"
echo "###memory:$MEMORY_KB"

exit "$EXIT_CODE"