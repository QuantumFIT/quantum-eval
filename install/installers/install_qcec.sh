#!/bin/bash
set -e
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../common.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../configs/qcec.conf"

log "Installing QCEC..."

# Check dependencies
for dep in "${DEPS[@]}"; do
    if ! dpkg -s "$dep" >/dev/null 2>&1; then
        log "Installing $dep"
        sudo apt-get install -y "$dep"
    else
        log "$dep is already installed"
    fi
done

# QCEC has no C++ CLI, it is used through the Python package
for pipdep in "${PIPDEPS[@]}"; do
    pip install "$pipdep"
done

# Clone repo (source reference, place for the wrapper helper)
clone_repo "$REPO" "$DIR"

# Record which wheel version is actually used
{
    echo "mqt.qcec=$(pip show mqt.qcec 2>/dev/null | grep '^Version:' | cut -d' ' -f2)"
    echo "installed_at=$(date -Iseconds)"
} >"$DIR/BUILD_INFO.txt"
log "Wrote $DIR/BUILD_INFO.txt"

log "QCEC installation completed!"
