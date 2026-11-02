#!/bin/bash
set -e
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../common.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../configs/sliqec.conf"

log "Installing SliQEC..."

# Check dependencies
for dep in "${DEPS[@]}"; do
    if ! dpkg -s "$dep" >/dev/null 2>&1; then
        log "Installing $dep"
        sudo apt-get install -y "$dep"
    else
        log "$dep is already installed"
    fi
done

# Clone repo
clone_repo "$REPO" "$DIR"

# Build SliQEC
cd "$DIR"
log "Configuring CUDD..."
cd cudd

# Some bits in the repo should be executable but aren't
chmod +x configure build-aux/*
touch aclocal.m4 && sleep 1 && touch configure Makefile.in config.h.in

./configure --enable-dddmp --enable-obj --enable-shared --enable-static
cd ..
log "Making SliQEC..."
make
log "SliQEC installation completed!"
