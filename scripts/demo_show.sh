#!/usr/bin/env bash
# ============================================================
# scripts/demo_show.sh - Hocaya canli gosterim scripti
# ============================================================
# Sirayla:
#   1. Multi-file demonun .s kaynaklari
#   2. Assemble (asm.py): .s -> .o
#   3. Object dump (sembol tablosu, extern/global, relocation)
#   4. Link (ld.py): coklu .o -> hex + map
#   5. Memory map raporu
#   6. HEX cikti
#   7. PicoRV32 (iverilog) simulasyonu
#   8. Hata senaryolari (multiple def, undefined ref, overflow)
#   9. Tum test paketi
# ============================================================

set -e
cd "$(dirname "$0")/.."

bar() { echo; echo "============================================================"; echo " $*"; echo "============================================================"; }

bar "1) MULTI-FILE DEMO KAYNAK DOSYALARI"
echo "--- demos/multi_file/main.s (ana program) ---"
cat demos/multi_file/main.s
echo
echo "--- demos/multi_file/math_lib.s (kutuphane) ---"
cat demos/multi_file/math_lib.s

bar "2) ASSEMBLE: .s -> .o (PCO v1 object dosyasi)"
mkdir -p build
python3 bin/asm.py demos/multi_file/main.s     -o build/main.o
python3 bin/asm.py demos/multi_file/math_lib.s -o build/math_lib.o

bar "3) OBJECT DUMP: sembol tablosu + extern + relocation"
echo "--- main.o (extern semboller + reloc'lar) ---"
python3 bin/objdump.py build/main.o --header --symbols --reloc
echo "--- math_lib.o (global semboller, .data icerigi) ---"
python3 bin/objdump.py build/math_lib.o --symbols --data

bar "4) LINK: 2 farkli .o -> tek HEX + memory map"
python3 bin/ld.py build/main.o build/math_lib.o \
    -o build/multi.hex --bin build/multi.bin --ihex build/multi.ihex --map build/multi.map

bar "5) MEMORY MAP RAPORU (linker'in sembol cozumu)"
cat build/multi.map

bar "6) VERILOG \$readmemh CIKTISI (ilk 12 satir)"
head -12 build/multi.hex

bar "7) PICORV32 (IVERILOG) SIMULASYONU"
echo "Beklenen GPIO: 22 (15+7), 8 (15-7), 42 (7*6), 314 (pi_x100), 0xDEADBEEF"
echo
sim/run_sim.sh build/multi.hex 200000 6 2>&1 | grep -E '\[gpio|sim_done|readmemh' | head -10

bar "8) HATA SENARYOLARI (linker savunmasi)"

echo "--- 8a) Multiple definition (ayni .global iki dosyada) ---"
python3 - <<'PY' 2>&1 | head -10
from assembler.assemble import assemble_source
from assembler import obj_format as oof
from linker.linker import link_objects, LinkError
o1, _ = assemble_source(".section .text\n.global foo\nfoo: ret\n", "f1.s")
o2, _ = assemble_source(".section .text\n.global foo\nfoo: ret\n", "f2.s")
oof.write_object_file(o1, "build/dup1.o")
oof.write_object_file(o2, "build/dup2.o")
try:
    link_objects(["build/dup1.o", "build/dup2.o"])
    print("HATA YAKALANMADI")
except LinkError as e:
    print(f"  [BEKLENEN HATA] {e}")
PY

echo
echo "--- 8b) Undefined reference (extern sembol cozulemiyor) ---"
python3 - <<'PY' 2>&1 | head -10
from assembler.assemble import assemble_source
from assembler import obj_format as oof
from linker.linker import link_objects, LinkError
src = ".section .text\n.global _start\n.extern noluyo\n_start:\n  call noluyo\n"
o, _ = assemble_source(src, "u.s")
oof.write_object_file(o, "build/undef.o")
try:
    link_objects(["build/undef.o"])
    print("HATA YAKALANMADI")
except LinkError as e:
    print(f"  [BEKLENEN HATA] {e}")
PY

echo
echo "--- 8c) Memory overflow (8 KB BRAM'a 9 KB sigmaz) ---"
python3 - <<'PY' 2>&1 | head -10
from assembler.assemble import assemble_source
from assembler import obj_format as oof
from linker.linker import link_objects, LinkError
src = """
.section .data
.global blob
blob:
    .space 9000
.section .text
.global _start
_start:
    nop
"""
o, _ = assemble_source(src, "ovf.s")
oof.write_object_file(o, "build/ovf.o")
try:
    link_objects(["build/ovf.o"])
    print("HATA YAKALANMADI")
except LinkError as e:
    print(f"  [BEKLENEN HATA] {e}")
PY

bar "9) TUM TEST PAKETI"
python3 -m pytest tests/ -q 2>&1 | tail -3

echo
echo "============================================================"
echo " DEMO TAMAM. Tum cikti yukarida hocaya canli gosterilebilir."
echo "============================================================"
