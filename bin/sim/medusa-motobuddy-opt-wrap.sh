#!/bin/bash
# Wrapper for MEDUSA MoToBuddy PR #24 builds (inlined hot wrappers ± LTO).
#
# Usage:
#   medusa-motobuddy-opt-wrap.sh -v inline|inline-lto [-s] [-p f32|f64|f80|f128] [-e] QASM
#
# -v  build variant (required): inline (LTO=0) or inline-lto (LTO=1)
# -s  loop / symbolic mode (-s passed to MEDUSA)
# -p  float precision; omit to use algebraic MEDUSA_buddy_gmp
# -e  evaluated-angles / -e flag

ABSOLUTE_SCRIPT_PATH=$(readlink -f "$0")
SCRIPT_DIR=$(dirname "${ABSOLUTE_SCRIPT_PATH}")

VARIANT=""
LOOP_MODE=0
PRECISION=""
EVAL_FLAG=""

while [[ $# -gt 0 && "$1" == -* ]]; do
    case "$1" in
        -v)
            VARIANT="$2"
            shift 2
            ;;
        -s)
            LOOP_MODE=1
            shift
            ;;
        -p)
            PRECISION="$2"
            shift 2
            ;;
        -e)
            EVAL_FLAG="-e"
            shift
            ;;
        *)
            echo "Unknown flag: $1" >&2
            exit 1
            ;;
    esac
done

case "$VARIANT" in
    inline)
        MEDUSA_DIR="${SCRIPT_DIR}/../simulators/medusa-motobuddy-inline"
        ;;
    inline-lto)
        MEDUSA_DIR="${SCRIPT_DIR}/../simulators/medusa-motobuddy-inline-lto"
        ;;
    *)
        echo "Invalid or missing -v variant. Use: inline | inline-lto" >&2
        exit 1
        ;;
esac

if [[ -n "$PRECISION" ]]; then
    case "$PRECISION" in
        f32|f64|f80|f128) ;;
        *)
            echo "Invalid precision '$PRECISION'. Use: f32, f64, f80, f128" >&2
            exit 1
            ;;
    esac
    MEDUSA_EXE="${MEDUSA_DIR}/MEDUSA_buddy_doubles_${PRECISION}"
else
    MEDUSA_EXE="${MEDUSA_DIR}/MEDUSA_buddy_gmp"
fi

QASM_FILE="$1"
if [[ -z "$QASM_FILE" ]]; then
    echo "Usage: $0 -v inline|inline-lto [-s] [-p f32|f64|f80|f128] [-e] QASM" >&2
    exit 1
fi

QASM_BASE=$(basename "$QASM_FILE")
if [[ "$QASM_BASE" == NL_* ]]; then
    echo "###runtime:NA"
    echo "###memory:NA"
    exit 1
fi

# Prefer evaluated-angles sibling when present (same as fp wrap).
QASM_FILE_ABS=$(realpath "$QASM_FILE")
QASM_DIR=$(dirname "$QASM_FILE_ABS")
EVALUATED_ANGLES_FILE="$QASM_DIR/evaluated-angles/$QASM_BASE"
if [[ -f "$EVALUATED_ANGLES_FILE" ]]; then
    QASM_FILE="$EVALUATED_ANGLES_FILE"
fi

if [[ ! -x "$MEDUSA_EXE" ]]; then
    echo "Executable not found or not executable: $MEDUSA_EXE" >&2
    echo "Install with: ./install/install.sh medusa-motobuddy-${VARIANT}" >&2
    exit 1
fi

if [[ $LOOP_MODE -eq 1 ]]; then
    # shellcheck disable=SC2086
    MEDUSA_OUT=$("$MEDUSA_EXE" -i -s $EVAL_FLAG --file "$QASM_FILE" 2>&1)
else
    # shellcheck disable=SC2086
    MEDUSA_OUT=$("$MEDUSA_EXE" -i $EVAL_FLAG --file "$QASM_FILE" 2>&1)
fi

EXIT_CODE=$?

RUNTIME=$(echo "$MEDUSA_OUT" | grep -oP 'Time=\K[0-9.]+' || true)
MEMORY_KB=$(echo "$MEDUSA_OUT" | grep -oP 'Peak Memory Usage=\K[0-9]+' || true)

echo "###runtime:${RUNTIME:-NA}"
echo "###memory:${MEMORY_KB:-NA}"

[[ -f "res.dot" ]] && rm -f "res.dot"
[[ -f "res-vars.txt" ]] && rm -f "res-vars.txt"

exit $EXIT_CODE
