# ============================================================
# parser.py - Yapisal Ayristirma (Parser)
# ============================================================
# Lexer ciktisini alarak her satirin turunu belirler ve
# operandlari yapisal olarak ayristirir.
# Ozellikle S-Type (store) komutlarinda offset(register)
# formatini parcalar: "0(x2)" -> offset=0, register="x2"
#
# Proje-2 eklentisi: Relocation ifadelerini taniyor:
#   %hi(sym), %lo(sym), %pcrel_hi(sym), %pcrel_lo(sym)
# ============================================================

import re
from tables.opcode_table import get_instruction_info, get_register_number


# Desteklenen direktifler (Proje-1 + Proje-2)
DIRECTIVES = [
    ".data", ".text", ".word", ".byte", ".org", ".end",
    ".global", ".globl", ".extern",
    ".section",
    ".string", ".asciz", ".ascii",
    ".space", ".skip",
    ".half",
    ".align",
]


# Pseudo komut listesi (pseudo.py ile senkron)
PSEUDO_INSTRUCTIONS = [
    "LI", "MV", "J", "NOP", "RET", "NOT", "NEG",
    "LA", "CALL",
    "BEQZ", "BNEZ", "BGEZ", "BLTZ", "JR",
]


# Relocation ifade regex'i: %hi(symbol), %lo(symbol) vb.
_RELOC_RE = re.compile(
    r'^%(hi|lo|pcrel_hi|pcrel_lo)\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)$'
)


def classify_line(token):
    """Satirin turunu belirler.

    Returns: "instruction", "directive", "label_only", "pseudo", "unknown"
    """
    if token["mnemonic"] is None:
        return "label_only"

    mnemonic = token["mnemonic"]

    # Direktif (. ile baslar)
    if mnemonic.startswith('.'):
        return "directive"

    # Pseudo
    if mnemonic.upper() in PSEUDO_INSTRUCTIONS:
        return "pseudo"

    # Normal instruction
    if get_instruction_info(mnemonic) is not None:
        return "instruction"

    return "unknown"


def parse_immediate(value_str):
    """Immediate (sabit) degeri parse eder.

    Desteklenen formatlar:
        - Decimal: 100, -50
        - Hexadecimal: 0x1A, 0xFF
        - Binary: 0b1010
        - Karakter: 'A' -> 65

    Bulunamazsa None doner (label veya reloc ifadesi olabilir).
    """
    if value_str is None:
        return None
    s = value_str.strip()

    # Karakter literal: 'A' -> 65
    if len(s) >= 3 and s[0] == "'" and s[-1] == "'":
        inner = s[1:-1]
        if len(inner) == 1:
            return ord(inner)
        # Escape
        if len(inner) == 2 and inner[0] == '\\':
            esc = inner[1]
            mapping = {'n': 10, 't': 9, 'r': 13, '0': 0, '\\': 92, "'": 39, '"': 34}
            if esc in mapping:
                return mapping[esc]

    try:
        if s.startswith("0x") or s.startswith("0X"):
            return int(s, 16)
        elif s.startswith("0b") or s.startswith("0B"):
            return int(s, 2)
        else:
            return int(s)
    except ValueError:
        return None


def parse_memory_operand(operand):
    """S-Type ve Load komutlari icin offset(register) formatini parcalar.

    Ornek: "0(x2)"   -> {"offset": 0, "register": "x2"}
    Ornek: "-4(sp)"  -> {"offset": -4, "register": "sp"}
    Ornek: "%lo(sym)(x2)" -> {"offset_expr": ("lo","sym"), "register": "x2"}
    """
    operand = operand.strip()

    if '(' not in operand or ')' not in operand:
        return None

    # En sondaki parantez ciftini bul (reloc ifadesinde de paranteze var)
    paren_end = operand.rfind(')')
    # Eslesen acilis parantezini bul
    paren_start = _find_matching_open(operand, paren_end)
    if paren_start is None:
        return None

    offset_str = operand[:paren_start].strip()
    register_str = operand[paren_start + 1:paren_end].strip()

    if offset_str == '':
        return {"offset": 0, "register": register_str}

    # Reloc ifadesi mi? (%lo(sym) vb.)
    reloc = parse_reloc_expr(offset_str)
    if reloc is not None:
        return {"offset_expr": reloc, "register": register_str}

    offset = parse_immediate(offset_str)
    if offset is None:
        return None

    return {"offset": offset, "register": register_str}


def _find_matching_open(s, close_idx):
    """Belirli bir kapama parantezinin esi olan acilis parantezini bul."""
    depth = 0
    for i in range(close_idx, -1, -1):
        if s[i] == ')':
            depth += 1
        elif s[i] == '(':
            depth -= 1
            if depth == 0:
                return i
    return None


def parse_reloc_expr(token_str):
    """Relocation ifadesini parse eder.

    Ornek: "%hi(my_symbol)"      -> ("hi", "my_symbol")
    Ornek: "%lo(data_addr)"      -> ("lo", "data_addr")
    Ornek: "%pcrel_hi(func)"     -> ("pcrel_hi", "func")
    Ornek: "%pcrel_lo(call_lbl)" -> ("pcrel_lo", "call_lbl")

    Returns: (kind, symbol) tuple veya None
    """
    if token_str is None:
        return None
    m = _RELOC_RE.match(token_str.strip())
    if m is None:
        return None
    return (m.group(1), m.group(2))


def is_reloc_expr(token_str):
    """Token bir reloc ifadesi mi?"""
    return parse_reloc_expr(token_str) is not None


def validate_register(name, error_handler, line_num):
    """Register adinin gecerli olup olmadigini kontrol eder.

    Gecerliyse register numarasini dondurur, degilse hata ekler.
    """
    reg_num = get_register_number(name)
    if reg_num is None:
        error_handler.add_error(line_num, "syntax",
                                f"Gecersiz register adi: '{name}'")
        return None
    return reg_num
