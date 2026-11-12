#!/bin/bash
set -e
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../common.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../configs/autoq.conf"

log "Installing AutoQ..."

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

# Build ANTLR C++ runtime (static only)
log "Building ANTLR $ANTLR_VERSION C++ runtime..."
clone_repo "$ANTLR_REPO" "$ANTLR_DIR" "$ANTLR_VERSION"
cmake -S "$ANTLR_DIR/runtime/Cpp" -B "$ANTLR_DIR/build" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$ANTLR_PREFIX" \
    -DCMAKE_INSTALL_LIBDIR=lib \
    -DANTLR_BUILD_SHARED=OFF \
    -DANTLR_BUILD_STATIC=ON \
    -DANTLR_BUILD_CPP_TESTS=OFF
cmake --build "$ANTLR_DIR/build" -j"$(nproc)"
cmake --install "$ANTLR_DIR/build"

# Build AutoQ (same as `make release`, but linking our ANTLR runtime)
cd "$DIR"
log "Building AutoQ release..."
rm -rf build
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_EXE_LINKER_FLAGS="-L$ANTLR_PREFIX/lib"
cmake --build build -j"$(nproc)"
log "AutoQ built"
