#!/usr/bin/env bash
# ============================================================
# sim/run_sim.sh - iverilog ile bir hex dosyasini simule et
# ============================================================
# Kullanim:
#   sim/run_sim.sh <hex_dosyasi> [cycles] [max_gpio]
#
# Hex dosyasinin yolu mutlak olarak alinir, cunku iverilog
# build dizinine cd ediyor; bagil yol verilirse $readmemh yolu
# bulamaz.
# ============================================================

set -euo pipefail

HEX_PATH="${1:?usage: run_sim.sh <hex_file> [cycles] [max_gpio]}"
CYCLES="${2:-200000}"
MAX_GPIO="${3:-0}"

# Mutlak yola cevir
if [[ "$HEX_PATH" != /* ]]; then
    HEX_PATH="$(pwd)/$HEX_PATH"
fi

if [[ ! -f "$HEX_PATH" ]]; then
    echo "run_sim: hex dosyasi bulunamadi: $HEX_PATH" >&2
    exit 1
fi

SIM_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$(cd "$SIM_DIR/.." && pwd)/build/sim"
mkdir -p "$BUILD_DIR"

OUT="$BUILD_DIR/sim.out"

if ! command -v iverilog >/dev/null 2>&1; then
    echo "run_sim: iverilog kurulu degil." >&2
    echo "  macOS: brew install icarus-verilog"
    echo "  Linux: sudo apt install iverilog"
    exit 2
fi

iverilog -g2012 -o "$OUT" \
    "$SIM_DIR/picorv32.v" "$SIM_DIR/soc.v" "$SIM_DIR/tb.v"

cd "$BUILD_DIR"
vvp "$OUT" "+hex=$HEX_PATH" "+cycles=$CYCLES" "+max_gpio=$MAX_GPIO"
