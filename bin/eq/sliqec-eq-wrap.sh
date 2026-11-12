#!/bin/bash
# Usage: sliqec-eq-wrap.sh <circuit1.qasm> <circuit2.qasm>
# Prints ###runtime, ###memory and ###result:eq|neq|error

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
SLIQEC_EXE="$SCRIPT_DIR/../../simulators/sliqec/SliQEC"

CIRC1="$1"
CIRC2="$2"

if [[ ! -f "$CIRC1" || ! -f "$CIRC2" ]]; then
    echo "Usage: $0 <circuit1.qasm> <circuit2.qasm>" >&2
    exit 1
fi

TIME_FILE=$(mktemp)
OUTPUT=$( /usr/bin/time -f "%e %M" -o "$TIME_FILE" "$SLIQEC_EXE" --circuit1 "$CIRC1" --circuit2 "$CIRC2" 2>&1 )
EXIT_CODE=$?
RUNTIME=$(awk '{print $1}' "$TIME_FILE")
MEMORY_KB=$(awk '{print $2}' "$TIME_FILE")
rm -f "$TIME_FILE"

# SliQEC skips unsupported lines with only a warning -> the result would be wrong
if echo "$OUTPUT" | grep -q "is not supported"; then
    RESULT="error"
elif echo "$OUTPUT" | grep -q "Is equivalent? Yes"; then
    RESULT="eq"
elif echo "$OUTPUT" | grep -q "Is equivalent? No"; then
    RESULT="neq"
else
    RESULT="error"
fi

echo "###runtime:${RUNTIME:-NA}"
echo "###memory:${MEMORY_KB:-NA}"
echo "###result:$RESULT"

[[ "$RESULT" == "error" ]] && exit 1
exit 0
