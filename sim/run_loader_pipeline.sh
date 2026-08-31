#!/bin/bash
# ============================================================
# run_loader_pipeline.sh - Tam zincir otomatik testi
# ============================================================
#   .s --(asm)--> .o --(ld)--> .bin --(host_send --emit-frames)
#      --> cerceveler --(tb_loader_file)--> Loader --> PicoRV32
#
# Gercek toolchain ciktisinin FPGA Loader'da dogru calistigini
# (iverilog simulasyonunda) ucdan uca kanitlar.
# ============================================================
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p build/loader_tests

VFILES="sim/picorv32.v fpga/tangnano9k/uart_rx.v fpga/uart_tx.v \
        fpga/tangnano9k/loader.v fpga/tangnano9k/soc_loader.v sim/tb_loader_file.v"

echo "### Loader file-replay TB derleniyor..."
iverilog -g2012 -o build/tbl_file.out $VFILES

# build_run <isim> <expect> [btn]
build_run () {
    local name="$1" expect="$2" btn="$3"
    echo
    echo "### TEST: $name  (beklenen GPIO=$expect${btn:+, btn=$btn})"
    python3 bin/asm.py demos/loader_tests/$name.s -o build/loader_tests/$name.o   >/dev/null
    python3 bin/ld.py  build/loader_tests/$name.o -o build/loader_tests/$name.hex \
            --bin build/loader_tests/$name.bin                                    >/dev/null
    python3 host/host_send.py --file build/loader_tests/$name.bin \
            --emit-frames build/loader_tests/$name.frames | tail -1
    vvp build/tbl_file.out +frames=build/loader_tests/$name.frames \
            +expect=$expect ${btn:+ +btn=$btn} 2>/dev/null | grep -E "cerceve|GPIO|==="
}

build_run test1_math      42
build_run test2_loop      -1          # sayac: yuklenmeyi dogrula (GPIO=0 baslangic)
build_run test3_func_btn   3   0      # buton bos -> 3
build_run test3_func_btn  15   1      # buton basili -> topla() -> 15

echo
echo "### Pipeline testleri tamam."
