#!/bin/bash

ABSOLUTE_SCRIPT_PATH=$(readlink -f "$0")
SCRIPT_DIR=$(dirname "${ABSOLUTE_SCRIPT_PATH}")

# Defaults
LOOP_MODE=0
PRECISION="f64"  # default precision
USE_CXX=0
EVAL_FLAG=""

# Parse flags
while [[ "$1" == -* ]]; do
    case "$1" in
        -s)
            LOOP_MODE=1
            shift
            ;;
        -p)
            PRECISION="$2"
            shift 2
            ;;
        -c)
            USE_CXX=1
            shift
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

# Validate precision
case "$PRECISION" in
    f32|f64|f80|f128) ;;
    *)
        echo "Invalid precision '$PRECISION'. Use: f32, f64, f80, f128" >&2
        exit 1
        ;;
esac

QASM_FILE="$1"

# Skip NL file
QASM_BASE=$(basename "$QASM_FILE")
if [[ "$QASM_BASE" == NL_* ]]; then
    echo "###runtime:NA"
    echo "###memory:NA"
    exit 1
fi

# Evaluated-angles variant: if present, use it instead
QASM_FILE_ABS=$(realpath "$QASM_FILE")
QASM_DIR=$(dirname "$QASM_FILE_ABS")
EVALUATED_ANGLES_FILE="$QASM_DIR/evaluated-angles/$QASM_BASE"
if [[ -f "$EVALUATED_ANGLES_FILE" ]]; then
    QASM_FILE="$EVALUATED_ANGLES_FILE"
fi

MEDUSA_C_DIR="../simulators/medusa-fp/"
MEDUSA_CXX_DIR="../simulators/medusa-fp-cpp/"

if [[ $USE_CXX -eq 1 ]]; then
    MEDUSA_DIR="$MEDUSA_CXX_DIR"
else
    MEDUSA_DIR="$MEDUSA_C_DIR"
fi

MEDUSA_EXE="${SCRIPT_DIR}/${MEDUSA_DIR}/MEDUSA_buddy_doubles_${PRECISION}"

if [[ ! -x "$MEDUSA_EXE" ]]; then
    echo "Executable not found or not executable: $MEDUSA_EXE" >&2
    exit 1
fi

# Run medusa with loop option if requested
if [[ $LOOP_MODE -eq 1 ]]; then
    MEDUSA_OUT=$("$MEDUSA_EXE" -i -s $EVAL_FLAG --file "$QASM_FILE" 2>&1)
else
    MEDUSA_OUT=$("$MEDUSA_EXE" -i $EVAL_FLAG --file "$QASM_FILE" 2>&1)
fi

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