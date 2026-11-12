#!/bin/bash

OUTPUT_DIR="../bench"
mkdir -p "$OUTPUT_DIR"

BASE_DIR="../circuits/no-measure" # base dir of categories

for category in "$BASE_DIR"/*; do
    if [ -d "$category" ]; then
        category_name=$(basename "$category")
        input_file="$OUTPUT_DIR/no-measure_$category_name.input"
        
        # list all .qasm files recursively in that category
        find "$category" -type f -name "*.qasm" | sort > "$input_file"
        echo "Created $input_file"
    fi
done
