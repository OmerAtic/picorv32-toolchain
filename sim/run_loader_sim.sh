#!/bin/bash
# ============================================================
# run_loader_sim.sh - Loader uctan uca simulasyonu (iverilog)
# ============================================================
# Gercek donanima gerek kalmadan Loader'in dogrulugunu kanitlar.
# Kullanim: sim/run_loader_sim.sh
# ============================================================
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

OUT=build/tb_loader.out
mkdir -p build

iverilog -g2012 -o "$OUT" \
    sim/picorv32.v \
    fpga/tangnano9k/uart_rx.v \
    fpga/uart_tx.v \
    fpga/tangnano9k/loader.v \
    fpga/tangnano9k/soc_loader.v \
    sim/tb_loader.v

vvp "$OUT"
