#!/bin/bash
set -e

BASE_DIR=$(dirname "$(readlink -f "$0")")
# shellcheck disable=SC1091
source "$BASE_DIR/common.sh"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <tool-name> [ --sim-all | --eq-all | --all ]"
    echo "Available:"
    echo "Simulation: medusa-sylvan, medusa-motobuddy, medusa-motobuddy-inline, medusa-motobuddy-inline-lto, medusa-stabilizer, sliqsim, ddsim, quasimodo, autoq, dirac-ddsim, quokka, qsylvan, clue"
    echo "Equivalence: sliqec, autoq, quokka, qcec, feynman"
    exit 1
fi

uninstall_tool() {
    local tool="$1"
    TOOL_DIR="$BASE_DIR/../simulators/$tool"
    if [[ -d "$TOOL_DIR" ]]; then
        echo "Removing $tool folder..."
        rm -rf "$TOOL_DIR"
        echo "$tool uninstalled successfully."
    else
        echo "$tool not found, skipping."
    fi
}

if [[ "$1" == "--all" ]]; then
    for tools in medusa-sylvan medusa-motobuddy medusa-motobuddy-inline medusa-motobuddy-inline-lto sliqsim ddsim quasimodo autoq dirac-ddsim quokka qsylvan medusa-stabilizer clue sliqec qcec feynman; do
        uninstall_tool "$tools"
    done
elif [[ "$1" == "--sim-all" ]]; then
    for sim in medusa-sylvan medusa-motobuddy medusa-motobuddy-inline medusa-motobuddy-inline-lto sliqsim ddsim quasimodo autoq dirac-ddsim quokka qsylvan medusa-stabilizer clue; do
        uninstall_tool "$sim"
    done
elif [[ "$1" == "--eq-all" ]]; then
    for eq in sliqec autoq quokka qcec feynman; do
        uninstall_tool "$eq"
    done
else
    tool="$1"
    uninstall_tool "$tool"
fi
