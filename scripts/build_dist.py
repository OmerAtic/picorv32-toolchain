#!/usr/bin/env python3
# ============================================================
# scripts/build_dist.py - Teslim paketi olusturucu
# ============================================================
# Hocaya teslim edilecek artifact'lari ureten kucuk script.
# Her demo icin:
#    - input .s dosyalari
#    - .o dosyalari (PCO v1)
#    - .hex (Verilog $readmemh)
#    - .bin (raw binary)
#    - .ihex (Intel HEX)
#    - .map (memory map)
# tek bir dist/ klasorunde toplar.
#
# Kullanim:
#    python3 scripts/build_dist.py
# ============================================================

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIST = os.path.join(ROOT, "dist")
DEMOS = os.path.join(ROOT, "demos")

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from assembler.assemble import assemble_file
from linker.linker import link_objects
from assembler import obj_format as oof


# Demo tanimlari: (klasor, [.s dosyalari], cikti adi)
DEMOS_INFO = [
    ("led_counter",  ["led_counter.s"],            "led_counter"),
    ("multi_file",   ["main.s", "math_lib.s"],     "multi_file"),
    ("uart_hello",   ["main.s", "uart_lib.s"],     "uart_hello"),
]


def _build_one(demo_name, asm_files, out_name):
    src_dir = os.path.join(DEMOS, demo_name)
    out_dir = os.path.join(DIST, demo_name)
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n=== {demo_name} ===")

    # 1) Kaynak .s dosyalarini dist'e kopyala
    for asm in asm_files:
        shutil.copy2(os.path.join(src_dir, asm), os.path.join(out_dir, asm))

    # 2) Assemble
    obj_paths = []
    for asm in asm_files:
        obj_path = os.path.join(out_dir, asm.replace(".s", ".o"))
        _, errs = assemble_file(os.path.join(src_dir, asm), output_path=obj_path)
        if errs:
            print(f"  HATA ({asm}):")
            for e in errs:
                print(f"    {asm}:{e['line']}  [{e['type']}] {e['message']}")
            return False
        obj = oof.read_object_file(obj_path)
        secs = ", ".join(f"{s['name']}={s['size']}B" for s in obj["sections"])
        print(f"  asm: {asm:<14} -> {os.path.basename(obj_path):<14} ({secs})")
        obj_paths.append(obj_path)

    # 3) Link (her cikti format)
    hex_path  = os.path.join(out_dir, f"{out_name}.hex")
    bin_path  = os.path.join(out_dir, f"{out_name}.bin")
    ihex_path = os.path.join(out_dir, f"{out_name}.ihex")
    map_path  = os.path.join(out_dir, f"{out_name}.map")

    result = link_objects(
        obj_paths,
        script_path=os.path.join(ROOT, "scripts", "picorv_unified.ld.json"),
        hex_output=hex_path,
        map_output=map_path,
        bin_output=bin_path,
        ihex_output=ihex_path,
    )
    print(f"  link -> {os.path.basename(hex_path)}, .bin, .ihex, .map  "
          f"(entry=0x{result['entry']:08x}, "
          f"globals={len(result['global_table'])})")
    return True


def _write_readme():
    readme = os.path.join(DIST, "README.md")
    with open(readme, 'w', encoding='utf-8') as f:
        f.write("""# Teslim Paketi (Proje-2)

Bu klasorde hocanin sartnamesinde istenen tum kod artifactlari yer alir:
en az 2 farkli .o dosyasi + bunlarin linklenmis HEX ciktisi.

## Klasor Icerigi

Her demo icin ayri alt klasor:

```
dist/
  led_counter/
      led_counter.s         # kaynak
      led_counter.o         # PCO v1 object dosyasi
      led_counter.hex       # Verilog $readmemh formati (BRAM init)
      led_counter.bin       # raw binary (LE)
      led_counter.ihex      # Intel HEX
      led_counter.map       # memory map raporu

  multi_file/               # math_lib + main (linker demosu, 2 dosya)
      main.s, math_lib.s
      main.o, math_lib.o    # 2 farkli object dosyasi
      multi_file.hex        # linklenmis cikti
      multi_file.bin
      multi_file.ihex
      multi_file.map

  uart_hello/               # uart_lib + main (UART demosu, 2 dosya)
      ...
```

## Beklenen Davranislar (iverilog simulasyonunda dogrulandi)

| Demo         | Beklenen Cikti                                                |
| ------------ | ------------------------------------------------------------- |
| led_counter  | GPIO_OUT 0,1,2,3,... yazar (8-bit overflow)                   |
| multi_file   | GPIO 22, 8, 42, 314, 0xDEADBEEF (sirasiyla)                   |
| uart_hello   | UART: "Hello, FPGA from PicoRV32!\\ncounter = 0xdeadbeef\\n" |

## FPGA Yukleme

`*.hex` dosyalari Vivado'da `$readmemh` ile BRAM'e yuklenir.
`fpga/build_vivado.tcl` scripti hex dosyasini otomatik kopyalar:

```bash
vivado -mode batch -source fpga/build_vivado.tcl \\
       -tclargs dist/multi_file/multi_file.hex
```

## Tekrar Uretim

Bu klasor bilgisayardan silinirse asagidaki komutla yeniden uretilir:

```bash
python3 scripts/build_dist.py
```
""")
    print(f"\nREADME yazildi: {readme}")


def main():
    if os.path.isdir(DIST):
        print(f"Eski {DIST} siliniyor...")
        shutil.rmtree(DIST)
    os.makedirs(DIST, exist_ok=True)

    ok = True
    for demo_name, asm_files, out_name in DEMOS_INFO:
        if not _build_one(demo_name, asm_files, out_name):
            ok = False

    if not ok:
        print("\nHATA: bazi demolar derlenemedi.")
        return 1

    _write_readme()

    # Ozet
    print(f"\n{'='*60}")
    print(f"TESLIM PAKETI HAZIR: {DIST}")
    print(f"{'='*60}")
    for demo_name, _, out_name in DEMOS_INFO:
        d = os.path.join(DIST, demo_name)
        files = sorted(os.listdir(d))
        print(f"  {demo_name}/")
        for fn in files:
            size = os.path.getsize(os.path.join(d, fn))
            print(f"      {fn:<26} {size:>6} B")

    return 0


if __name__ == "__main__":
    sys.exit(main())
