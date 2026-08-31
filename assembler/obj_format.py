# ============================================================
# obj_format.py - PicoRV32 Object Dosyasi Formati (PCO v1)
# ============================================================
# JSON tabanli, insan-okunabilir object dosyasi formati.
# Linker'in girdisi olan .o dosyalarini yazar/okur.
#
# Tam format spec'i:
# {
#   "magic":      "PICORV32-OBJ",       # sabit kimlik dizesi
#   "version":    1,                     # format surumu
#   "filename":   "math_lib.s",          # kaynak dosya adi
#   "timestamp":  "2026-05-09T15:30:00", # ISO 8601
#   "sections": [
#     {
#       "name":  ".text",
#       "addr":  0,                      # section'in BU dosya icindeki ofseti
#       "size":  144,
#       "data":  "0102deadbeef...",     # hex string, her byte 2 char (LE)
#       "align": 4,
#       "flags": ["EXEC", "ALLOC"]
#     },
#     {
#       "name":  ".data",
#       ...
#       "flags": ["WRITE", "ALLOC"]
#     }
#   ],
#   "symbols": [
#     {
#       "name":    "add_func",
#       "section": ".text",              # *UND* ise extern
#       "value":   0,                    # section ici offset
#       "size":    8,
#       "binding": "GLOBAL",             # LOCAL, GLOBAL, EXTERN
#       "type":    "NOTYPE",             # NOTYPE, FUNC, OBJECT
#       "line":    14
#     }
#   ],
#   "relocations": [
#     {
#       "section": ".text",
#       "offset":  20,                   # section ici offset (byte)
#       "type":    "R_RISCV_PCREL_HI20",
#       "symbol":  "add_func",
#       "addend":  0,
#       "line":    32
#     }
#   ]
# }
# ============================================================

import json
import datetime
import os


# Format sabitleri
PCO_MAGIC   = "PICORV32-OBJ"
PCO_VERSION = 1

# Sembol bagi (binding) tipleri
BIND_LOCAL  = "LOCAL"
BIND_GLOBAL = "GLOBAL"
BIND_EXTERN = "EXTERN"

# Sembol turu tipleri
SYM_NOTYPE = "NOTYPE"
SYM_FUNC   = "FUNC"
SYM_OBJECT = "OBJECT"

# Tanimsiz section (extern semboller icin)
SECTION_UNDEF = "*UND*"

# Relocation tipleri (RISC-V psABI uyumlu, alt-kume)
R_BRANCH      = "R_RISCV_BRANCH"        # B-type branch (12-bit PC-rel)
R_JAL         = "R_RISCV_JAL"           # J-type JAL (20-bit PC-rel)
R_HI20        = "R_RISCV_HI20"          # LUI absolute (la pseudo)
R_LO12_I      = "R_RISCV_LO12_I"        # ADDI/JALR/LW absolute
R_LO12_S      = "R_RISCV_LO12_S"        # SW/SH/SB absolute
R_PCREL_HI20  = "R_RISCV_PCREL_HI20"    # AUIPC (call pseudo)
R_PCREL_LO12  = "R_RISCV_PCREL_LO12_I"  # JALR (call pseudo)

ALL_RELOC_TYPES = [
    R_BRANCH, R_JAL,
    R_HI20, R_LO12_I, R_LO12_S,
    R_PCREL_HI20, R_PCREL_LO12,
]


# ============================================================
# Bytes <-> Hex string donusumleri
# ============================================================

def bytes_to_hex(data):
    """bytes -> hex string (lower case, LE byte order korunur).

    Ornek: b'\\x01\\x02\\xff' -> "0102ff"
    """
    if data is None:
        return ""
    return data.hex()


def hex_to_bytes(hex_str):
    """hex string -> bytes."""
    if hex_str is None or hex_str == "":
        return b""
    # Bosluklari ve newline'lari temizle
    s = ''.join(c for c in hex_str if c not in ' \t\n\r')
    return bytes.fromhex(s)


# ============================================================
# Object dosyasi yapilandirma yardimcilari
# ============================================================

def make_section(name, data=b"", align=4, flags=None):
    """Bos veya dolu bir section olusturur.

    Args:
        name:  ".text", ".data", vb.
        data:  bytes (icerik)
        align: hizalama (genellikle 4)
        flags: ["EXEC","ALLOC"] gibi listesi
    """
    if flags is None:
        if name == ".text":
            flags = ["EXEC", "ALLOC"]
        elif name == ".data":
            flags = ["WRITE", "ALLOC"]
        elif name == ".bss":
            flags = ["WRITE", "ALLOC", "NOBITS"]
        else:
            flags = ["ALLOC"]

    return {
        "name":  name,
        "addr":  0,
        "size":  len(data),
        "data":  bytes_to_hex(data),
        "align": align,
        "flags": flags,
    }


def make_symbol(name, section, value, size=0,
                binding=BIND_LOCAL, sym_type=SYM_NOTYPE, line=0):
    """Bir sembol kaydi olusturur."""
    return {
        "name":    name,
        "section": section,
        "value":   value,
        "size":    size,
        "binding": binding,
        "type":    sym_type,
        "line":    line,
    }


def make_relocation(section, offset, reloc_type, symbol, addend=0, line=0):
    """Bir relocation kaydi olusturur."""
    if reloc_type not in ALL_RELOC_TYPES:
        raise ValueError(f"Bilinmeyen relocation tipi: {reloc_type}")
    return {
        "section": section,
        "offset":  offset,
        "type":    reloc_type,
        "symbol":  symbol,
        "addend":  addend,
        "line":    line,
    }


def make_object(filename, sections=None, symbols=None, relocations=None):
    """Bir object dosyasi yapisi olusturur (henuz diske yazmaz).

    Returns: dict (PCO format)
    """
    return {
        "magic":       PCO_MAGIC,
        "version":     PCO_VERSION,
        "filename":    filename,
        "timestamp":   datetime.datetime.now().isoformat(timespec='seconds'),
        "sections":    sections    if sections    is not None else [],
        "symbols":     symbols     if symbols     is not None else [],
        "relocations": relocations if relocations is not None else [],
    }


# ============================================================
# Diske yazma / okuma
# ============================================================

def write_object_file(obj, filepath):
    """Object yapisini JSON olarak diske yazar."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def read_object_file(filepath):
    """JSON object dosyasini yukler ve magic+version dogrular.

    Returns: dict (PCO format)
    Raises:  ValueError eger magic veya version yanlissa
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Object dosyasi bulunamadi: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        obj = json.load(f)

    validate_object(obj, source=filepath)
    return obj


def validate_object(obj, source="<obj>"):
    """Bir object yapisinin format gecerligini dogrular.

    Hatalarda ValueError atar.
    """
    if not isinstance(obj, dict):
        raise ValueError(f"{source}: Object root bir dict olmali")

    if obj.get("magic") != PCO_MAGIC:
        raise ValueError(f"{source}: Hatali magic. Beklenen: {PCO_MAGIC}, "
                         f"alinan: {obj.get('magic')}")

    if obj.get("version") != PCO_VERSION:
        raise ValueError(f"{source}: Desteklenmeyen surum: {obj.get('version')} "
                         f"(beklenen: {PCO_VERSION})")

    if "sections" not in obj or not isinstance(obj["sections"], list):
        raise ValueError(f"{source}: 'sections' alani liste olmali")

    if "symbols" not in obj or not isinstance(obj["symbols"], list):
        raise ValueError(f"{source}: 'symbols' alani liste olmali")

    if "relocations" not in obj or not isinstance(obj["relocations"], list):
        raise ValueError(f"{source}: 'relocations' alani liste olmali")

    # Section data hex string mi?
    for sec in obj["sections"]:
        for k in ("name", "data", "align"):
            if k not in sec:
                raise ValueError(f"{source}: Section '{sec.get('name')}' "
                                 f"icin '{k}' eksik")

    # Sembol formati
    for sym in obj["symbols"]:
        for k in ("name", "section", "value", "binding"):
            if k not in sym:
                raise ValueError(f"{source}: Sembol '{sym.get('name')}' "
                                 f"icin '{k}' eksik")
        if sym["binding"] not in (BIND_LOCAL, BIND_GLOBAL, BIND_EXTERN):
            raise ValueError(f"{source}: Sembol '{sym['name']}' "
                             f"gecersiz binding: {sym['binding']}")

    # Reloc tipleri
    for rel in obj["relocations"]:
        for k in ("section", "offset", "type", "symbol"):
            if k not in rel:
                raise ValueError(f"{source}: Reloc icin '{k}' eksik")
        if rel["type"] not in ALL_RELOC_TYPES:
            raise ValueError(f"{source}: Bilinmeyen reloc tipi: {rel['type']}")

    return True


# ============================================================
# Yardimci sorgu fonksiyonlari
# ============================================================

def get_section_data(obj, section_name):
    """Bir section'in icerigini bytes olarak doner."""
    for sec in obj["sections"]:
        if sec["name"] == section_name:
            return hex_to_bytes(sec["data"])
    return None


def get_section_size(obj, section_name):
    """Bir section'in boyutu."""
    for sec in obj["sections"]:
        if sec["name"] == section_name:
            return sec["size"]
    return 0


def find_symbol(obj, name):
    """Sembol kaydini bulur, yoksa None."""
    for sym in obj["symbols"]:
        if sym["name"] == name:
            return sym
    return None


def get_global_symbols(obj):
    """Sadece GLOBAL bagli sembolleri donder."""
    return [s for s in obj["symbols"] if s["binding"] == BIND_GLOBAL]


def get_extern_symbols(obj):
    """Sadece EXTERN bagli sembolleri donder."""
    return [s for s in obj["symbols"] if s["binding"] == BIND_EXTERN]
