#!/bin/bash
# Usage: qcec-eq-wrap.sh [-p] <circuit1.qasm> <circuit2.qasm>
#   -p  run QCEC's checkers in parallel (one thread per core) instead of sequentially
# Prints ###runtime, ###memory and ###result:eq|neq|unknown|error

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

PARALLEL=()
if [[ "$1" == "-p" ]]; then
    PARALLEL=(--parallel)
    shift
fi

CIRC1="$1"
CIRC2="$2"

if [[ ! -f "$CIRC1" || ! -f "$CIRC2" ]]; then
    echo "Usage: $0 [-p] <circuit1.qasm> <circuit2.qasm>" >&2
    exit 1
fi

TIME_FILE=$(mktemp)
OUTPUT=$( /usr/bin/time -f "%e %M" -o "$TIME_FILE" python3 "$SCRIPT_DIR/helpers/qcec-eq.py" "${PARALLEL[@]}" "$CIRC1" "$CIRC2" 2>&1 )
EXIT_CODE=$?
RUNTIME=$(awk '{print $1}' "$TIME_FILE")
MEMORY_KB=$(awk '{print $2}' "$TIME_FILE")
rm -f "$TIME_FILE"

RESULT=$(echo "$OUTPUT" | grep -oP '^result:\K\w+')
[[ $EXIT_CODE -ne 0 || -z "$RESULT" ]] && RESULT="error"

echo "###runtime:${RUNTIME:-NA}"
echo "###memory:${MEMORY_KB:-NA}"
echo "###result:$RESULT"

[[ "$RESULT" == "error" ]] && exit 1
exit 0
