#!/bin/bash
# Usage: autoq-eq-wrap.sh <circuit1.qasm> <circuit2.qasm>
# Prints ###runtime, ###memory and ###result:eq|neq|error

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
AUTOQ_EXE="$SCRIPT_DIR/../../simulators/autoq/build/cli/autoq"

CIRC1="$1"
CIRC2="$2"

if [[ ! -f "$CIRC1" || ! -f "$CIRC2" ]]; then
    echo "Usage: $0 <circuit1.qasm> <circuit2.qasm>" >&2
    exit 1
fi

TIME_FILE=$(mktemp)
OUTPUT=$( /usr/bin/time -f "%e %M" -o "$TIME_FILE" "$AUTOQ_EXE" eq "$CIRC1" "$CIRC2" 2>&1 )
EXIT_CODE=$?
RUNTIME=$(awk '{print $1}' "$TIME_FILE")
MEMORY_KB=$(awk '{print $2}' "$TIME_FILE")
rm -f "$TIME_FILE"

# "The two quantum programs are verified to be [equal|unequal] ..."
if [[ $EXIT_CODE -ne 0 ]]; then
    RESULT="error"
elif echo "$OUTPUT" | grep -q "verified to be \[equal\]"; then
    RESULT="eq"
elif echo "$OUTPUT" | grep -q "verified to be \[unequal\]"; then
    RESULT="neq"
else
    RESULT="error"
fi

echo "###runtime:${RUNTIME:-NA}"
echo "###memory:${MEMORY_KB:-NA}"
echo "###result:$RESULT"

[[ "$RESULT" == "error" ]] && exit 1
exit 0
