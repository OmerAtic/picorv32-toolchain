#!/bin/bash
# ============================================================
# build_oss.sh - Acik kaynak Gowin akisi (yosys + nextpnr + apicula)
# ============================================================
# OSS CAD Suite ortamini kullanarak Tang Nano 9K bitstream'i uretir.
# Kullanim:  bash fpga/tangnano9k/build_oss.sh
# Cikti:     impl/loader.fs   (openFPGALoader ile karta yuklenir)
# ============================================================
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# OSS CAD Suite ortami (PATH'e yosys/nextpnr/gowin_pack/openFPGALoader ekler)
source "$HOME/fpga-tools/oss-cad-suite/environment"

mkdir -p impl

SRC="sim/picorv32.v fpga/uart_tx.v fpga/tangnano9k/uart_rx.v \
     fpga/tangnano9k/loader.v fpga/tangnano9k/soc_loader.v \
     fpga/tangnano9k/tangnano9k_top.v"

echo "### 1/3  Yosys sentez (synth_gowin)..."
yosys -q -p "read_verilog -sv $SRC; synth_gowin -top tangnano9k_top -json impl/loader.json"

echo "### 2/3  nextpnr-himbaechel yerlesim/yonlendirme..."
nextpnr-himbaechel \
    --json impl/loader.json \
    --write impl/loader_pnr.json \
    --device GW1NR-LV9QN88PC6/I5 \
    --vopt family=GW1N-9C \
    --vopt cst=fpga/tangnano9k/tangnano9k.cst \
    --vopt disable_gp_clock_routing

echo "### 3/3  gowin_pack bitstream..."
gowin_pack -d GW1N-9C -o impl/loader.fs impl/loader_pnr.json

echo
echo "### TAMAM -> impl/loader.fs"
echo "### Karta yukle:  openFPGALoader -b tangnano9k impl/loader.fs"
