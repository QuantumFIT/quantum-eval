#!/bin/bash
# Usage: feynman-eq-wrap.sh <circuit1.qasm> <circuit2.qasm>
# Prints ###runtime, ###memory and ###result:eq|neq|unknown|error
# feynver reads only .qc, the conversion is not included in the measured time.

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
FEYNVER_EXE="$SCRIPT_DIR/../../simulators/feynman/bin/feynver"

CIRC1="$1"
CIRC2="$2"

if [[ ! -f "$CIRC1" || ! -f "$CIRC2" ]]; then
    echo "Usage: $0 <circuit1.qasm> <circuit2.qasm>" >&2
    exit 1
fi

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

if ! python3 "$SCRIPT_DIR/helpers/qasm2qc.py" "$CIRC1" "$TMP_DIR/c1.qc" >&2 || \
   ! python3 "$SCRIPT_DIR/helpers/qasm2qc.py" "$CIRC2" "$TMP_DIR/c2.qc" >&2; then
    echo "###runtime:NA"
    echo "###memory:NA"
    echo "###result:error"
    exit 1
fi

OUTPUT=$( /usr/bin/time -f "%e %M" -o "$TMP_DIR/time" "$FEYNVER_EXE" -ignore-global-phase "$TMP_DIR/c1.qc" "$TMP_DIR/c2.qc" 2>&1 )
RUNTIME=$(awk '{print $1}' "$TMP_DIR/time")
MEMORY_KB=$(awk '{print $2}' "$TMP_DIR/time")

# "Equal (took ...)", "Not equal (took ...)", "Inconclusive (took ...)"
if echo "$OUTPUT" | grep -q "^Not equal"; then
    RESULT="neq"
elif echo "$OUTPUT" | grep -q "^Equal"; then
    RESULT="eq"
elif echo "$OUTPUT" | grep -q "^Inconclusive"; then
    RESULT="unknown"
else
    RESULT="error"
fi

echo "###runtime:${RUNTIME:-NA}"
echo "###memory:${MEMORY_KB:-NA}"
echo "###result:$RESULT"

[[ "$RESULT" == "error" ]] && exit 1
exit 0
