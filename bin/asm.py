#!/usr/bin/env python3
# ============================================================
# bin/asm.py - PicoRV32 Assembler CLI
# ============================================================
# Bir .s assembly dosyasini PCO formatli .o dosyasina cevirir.
#
# Kullanim:
#   python bin/asm.py <input.s> [-o output.o] [--listing FILE]
# ============================================================

import argparse
import os
import sys

# Proje kok dizinini PYTHONPATH'e ekle (cli script icin)
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from assembler.assemble import assemble_file  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        prog="asm",
        description="PicoRV32 RV32I assembler (Proje-2 PCO v1 cikti)"
    )
    parser.add_argument("input",  help="kaynak .s dosyasi")
    parser.add_argument("-o", "--output",
                        help="cikti .o dosyasi (default: <input>.o)")
    parser.add_argument("--listing", default=None,
                        help="opsiyonel listing dosyasi (insan okunur)")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="sessiz mod (ozet basma)")

    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Hata: Kaynak dosya bulunamadi: {args.input}", file=sys.stderr)
        return 2

    out_path = args.output
    if out_path is None:
        base, _ = os.path.splitext(args.input)
        out_path = base + ".o"

    obj, errors = assemble_file(args.input, output_path=out_path,
                                listing_path=args.listing)

    if errors:
        print(f"=== Assembler Hatalari ({len(errors)} adet) ===", file=sys.stderr)
        for e in errors:
            print(f"  {args.input}:{e['line']}  [{e['type']}] {e['message']}",
                  file=sys.stderr)
        return 1

    if not args.quiet:
        sec_summary = ", ".join(f"{s['name']}={s['size']}B" for s in obj["sections"])
        n_global = sum(1 for s in obj["symbols"] if s["binding"] == "GLOBAL")
        n_extern = sum(1 for s in obj["symbols"] if s["binding"] == "EXTERN")
        n_reloc  = len(obj["relocations"])
        print(f"asm: {args.input} -> {out_path}")
        print(f"     sections: {sec_summary}")
        print(f"     symbols:  global={n_global}  extern={n_extern}")
        print(f"     reloc:    {n_reloc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
