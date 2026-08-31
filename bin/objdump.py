#!/usr/bin/env python3
# ============================================================
# bin/objdump.py - PCO Object Dosyasi Inceleyici
# ============================================================
# Bir .o (PCO v1) dosyasinin icerigini insan okunur formatta yazar.
#
# Kullanim:
#   python bin/objdump.py <obj.o> [--all|--header|--symbols|--reloc|--data]
# ============================================================

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from assembler import obj_format as oof  # noqa: E402


def _print_header(obj):
    print("== Header ==")
    print(f"  magic:     {obj['magic']}")
    print(f"  version:   {obj['version']}")
    print(f"  filename:  {obj['filename']}")
    print(f"  timestamp: {obj['timestamp']}")
    print()
    print("== Sections ==")
    print(f"  {'Name':<10} {'Size':>8} {'Align':>6}  Flags")
    for s in obj["sections"]:
        flags = ",".join(s.get("flags", []))
        print(f"  {s['name']:<10} {s['size']:>8} {s['align']:>6}  {flags}")
    print()


def _print_symbols(obj):
    print("== Symbols ==")
    print(f"  {'Binding':<8} {'Type':<8} {'Section':<10} {'Value':>10}  {'Size':>4}  Name")
    for s in obj["symbols"]:
        print(f"  {s['binding']:<8} {s.get('type','NOTYPE'):<8} "
              f"{s['section']:<10} 0x{s['value']:08x}  "
              f"{s.get('size',0):>4}  {s['name']}")
    print()


def _print_reloc(obj):
    print("== Relocations ==")
    if not obj["relocations"]:
        print("  (yok)")
        print()
        return
    print(f"  {'Section':<10} {'Offset':>10}  {'Type':<24} {'Addend':>6}  Symbol")
    for r in obj["relocations"]:
        print(f"  {r['section']:<10} 0x{r['offset']:08x}  "
              f"{r['type']:<24} {r.get('addend',0):>6}  {r['symbol']}")
    print()


def _print_data(obj):
    print("== Section Data ==")
    for sec in obj["sections"]:
        print(f"-- {sec['name']} ({sec['size']} bytes) --")
        data = oof.hex_to_bytes(sec["data"])
        # 16 byte/satir
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hex_part = " ".join(f"{b:02x}" for b in chunk)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            print(f"  {i:08x}  {hex_part:<47}  |{ascii_part}|")
        print()


def main():
    parser = argparse.ArgumentParser(
        prog="objdump",
        description="PicoRV32 PCO object dosyasi inceleyici"
    )
    parser.add_argument("object", help=".o dosyasi")
    parser.add_argument("--all",     action="store_true", help="tum bolumler")
    parser.add_argument("--header",  action="store_true", help="header + section listesi")
    parser.add_argument("--symbols", action="store_true", help="sembol tablosu")
    parser.add_argument("--reloc",   action="store_true", help="relocation listesi")
    parser.add_argument("--data",    action="store_true", help="section icerikleri (hex dump)")

    args = parser.parse_args()

    if not os.path.isfile(args.object):
        print(f"objdump: dosya bulunamadi: {args.object}", file=sys.stderr)
        return 2

    try:
        obj = oof.read_object_file(args.object)
    except (ValueError, FileNotFoundError) as e:
        print(f"objdump: hata: {e}", file=sys.stderr)
        return 1

    show_all = args.all or not (args.header or args.symbols or args.reloc or args.data)

    if show_all or args.header:
        _print_header(obj)
    if show_all or args.symbols:
        _print_symbols(obj)
    if show_all or args.reloc:
        _print_reloc(obj)
    if show_all or args.data:
        _print_data(obj)
    return 0


if __name__ == "__main__":
    sys.exit(main())
