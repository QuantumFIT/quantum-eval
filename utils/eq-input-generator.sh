#!/bin/bash
OUTPUT_DIR="../bench"
EQ_DIR="../circuits/eq"

# name:base folder:partner folder
PAIRS=(
    "exact-opt:exact:exact_opt"
    "exact-rm1:exact:exact_opt_1removed"
    "exact-rm3:exact:exact_opt_3removed"
    "approx-opt:approx:approx_opt"
    "approx-shift4:approx:approx_opt_shift1e-4"
    "approx-shift7:approx:approx_opt_shift1e-7"
)

for p in "${PAIRS[@]}"; do
    IFS=: read -r name base partner <<< "$p"
    input_file="$OUTPUT_DIR/eq_$name.input"
    : > "$input_file"
    (cd "$EQ_DIR/$base" && find . -type f -name "*.qasm" | sort) | while read -r rel; do
        rel=${rel#./}
        [ -f "$EQ_DIR/$partner/$rel" ] || { echo "missing partner: $partner/$rel" >&2; continue; }
        echo "$EQ_DIR/$base/$rel;$EQ_DIR/$partner/$rel" >> "$input_file"
    done
    echo "Created $input_file ($(wc -l < "$input_file") pairs)"
done
