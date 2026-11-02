#!/bin/bash
set -e
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../common.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../configs/feynman.conf"

log "Installing Feynman..."

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

# Local Haskell toolchain (GHCup) inside $DIR, independent of ~/.ghcup and ~/.cabal
export GHCUP_INSTALL_BASE_PREFIX="$DIR"
export CABAL_DIR="$DIR/.cabal"
export PATH="$DIR/.ghcup/bin:$PATH"
if [[ ! -x "$DIR/.ghcup/bin/ghcup" ]]; then
    log "Downloading GHCup..."
    mkdir -p "$DIR/.ghcup/bin"
    curl --proto '=https' --tlsv1.2 -sSfL "$GHCUP_URL" -o "$DIR/.ghcup/bin/ghcup"
    chmod +x "$DIR/.ghcup/bin/ghcup"
fi
log "Installing GHC ($GHC_VERSION) and cabal ($CABAL_VERSION)..."
ghcup install ghc "$GHC_VERSION" --set
ghcup install cabal "$CABAL_VERSION" --set

# Build Feynman (feynver, feynopt, ...) into $DIR/bin
cd "$DIR"
log "Building Feynman..."
cabal update
cabal build "${CABAL_FLAGS[@]}"
cabal install "${CABAL_FLAGS[@]}" --installdir="$DIR/bin" --install-method=copy --overwrite-policy=always
log "Feynman installation completed!"
