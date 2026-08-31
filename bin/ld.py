#!/usr/bin/env python3
# ============================================================
# bin/ld.py - PicoRV32 Linker CLI
# ============================================================
# Birden fazla PCO .o dosyasini birlestirip Verilog $readmemh
# formatinda hex dosyasi uretir. Opsiyonel olarak memory map raporu yazar.
#
# Kullanim:
#   python bin/ld.py <obj1.o> <obj2.o> [...] [-o output.hex]
#                    [--map output.map] [-T script.json]
# ============================================================

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from linker.linker import link_objects, LinkError  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        prog="ld",
        description="PicoRV32 linker (PCO v1 -> Verilog hex)"
    )
    parser.add_argument("objects", nargs="+", help="bir veya daha fazla .o dosyasi")
    parser.add_argument("-o", "--hex", default="a.hex",
                        help="Verilog $readmemh cikti (default: a.hex)")
    parser.add_argument("--bin", default=None,
                        help="raw binary cikti (LE byte order)")
    parser.add_argument("--ihex", default=None,
                        help="Intel HEX cikti")
    parser.add_argument("--map", default=None,
                        help="memory map raporu cikti dosyasi")
    parser.add_argument("-T", "--script", default=None,
                        help="linker script JSON (default: scripts/picorv_unified.ld.json)")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="sessiz mod (ozet basma)")

    args = parser.parse_args()

    # Default scripti otomatik bul
    script_path = args.script
    if script_path is None:
        candidate = os.path.join(_ROOT, "scripts", "picorv_unified.ld.json")
        if os.path.isfile(candidate):
            script_path = candidate

    try:
        result = link_objects(
            args.objects,
            script_path=script_path,
            hex_output=args.hex,
            map_output=args.map,
            bin_output=args.bin,
            ihex_output=args.ihex,
        )
    except (LinkError, FileNotFoundError, ValueError) as e:
        print(f"ld: hata: {e}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"ld: {len(args.objects)} object linklendi -> {args.hex}")
        print(f"     entry:    0x{result['entry']:08x}")
        print(f"     globals:  {len(result['global_table'])}")
        if args.map:  print(f"     map:      {args.map}")
        if args.bin:  print(f"     bin:      {args.bin}")
        if args.ihex: print(f"     ihex:     {args.ihex}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
