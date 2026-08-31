# ============================================================
# directive.py - Direktif Islemcisi
# ============================================================
# Eski direktifler (Proje-1):
#   .data, .text, .word, .byte, .org, .end
# Linker icin eklenen yeni direktifler (Proje-2):
#   .global / .globl  - sembol global olarak isaretlenir
#   .extern           - sembol baska dosyadan beklenir
#   .section .text/.data - section degistirir
#   .string / .asciz  - null-terminator'lu ASCII metin
#   .ascii            - terminator'siz ASCII metin
#   .space / .skip    - belirli sayida sifir byte
#   .half             - 2 byte
#   .align            - hizalama
# ============================================================

from assembler.parser import parse_immediate


# Tum tanidigimiz direktifler (yeni + eski)
ALL_DIRECTIVES = [
    # Eski (Proje-1 ile uyumlu)
    ".data", ".text", ".word", ".byte", ".org", ".end",
    # Yeni (linker icin)
    ".global", ".globl", ".extern",
    ".section",
    ".string", ".asciz", ".ascii",
    ".space", ".skip",
    ".half",
    ".align",
]


def is_directive(mnemonic):
    """Verilen string bir direktif mi kontrol eder."""
    if mnemonic is None:
        return False
    return mnemonic.lower() in ALL_DIRECTIVES


def process_directive(token, current_pc, data_memory, error_handler):
    """Eski (Proje-1) direktif islemcisi - geri uyumluluk icin korunur.

    Sadece .text, .data, .word, .byte, .org, .end isler.
    Yeni direktifleri (.global, .extern, .section, .string vb.)
    section-aware assembler (assembler/assemble.py) icinde isler.

    Returns: Yeni PC degeri
    """
    directive = token["mnemonic"].lower()
    operands = token["operands"]
    line_num = token["line_num"]

    if directive == ".text":
        return current_pc

    elif directive == ".data":
        return current_pc

    elif directive == ".word":
        if len(operands) == 0:
            error_handler.add_error(line_num, "directive",
                                    ".word direktifi bir deger gerektirir")
            return current_pc
        value = parse_immediate(operands[0])
        if value is None:
            error_handler.add_error(line_num, "directive",
                                    f".word icin gecersiz deger: '{operands[0]}'")
            return current_pc
        data_memory[current_pc] = value & 0xFFFFFFFF
        return current_pc + 4

    elif directive == ".byte":
        if len(operands) == 0:
            error_handler.add_error(line_num, "directive",
                                    ".byte direktifi bir deger gerektirir")
            return current_pc
        value = parse_immediate(operands[0])
        if value is None:
            error_handler.add_error(line_num, "directive",
                                    f".byte icin gecersiz deger: '{operands[0]}'")
            return current_pc
        data_memory[current_pc] = value & 0xFF
        return current_pc + 1

    elif directive == ".org":
        if len(operands) == 0:
            error_handler.add_error(line_num, "directive",
                                    ".org direktifi bir adres gerektirir")
            return current_pc
        address = parse_immediate(operands[0])
        if address is None:
            error_handler.add_error(line_num, "directive",
                                    f".org icin gecersiz adres: '{operands[0]}'")
            return current_pc
        return address

    elif directive == ".end":
        return current_pc

    # Yeni direktifler bu fonksiyonda islenmez (assemble.py'da islenir)
    # Burada sadece "biliniyor" olarak gecilir, PC degismez
    elif directive in [".global", ".globl", ".extern", ".section",
                       ".string", ".asciz", ".ascii",
                       ".space", ".skip", ".half", ".align"]:
        # Bu direktifler section-aware assembler tarafindan islenir.
        # Eski main.py akisinda gorulurse sessizce gec (PC etkilenmez).
        return current_pc

    else:
        error_handler.add_error(line_num, "directive",
                                f"Bilinmeyen direktif: '{directive}'")
        return current_pc


def parse_string_literal(raw):
    """Tirnak icindeki string'i Python string'ine cevirir.

    Escape karakterler: \\n \\t \\r \\0 \\\\ \\"
    Ornek giris:  '"Hello\\n"'
    Ornek cikti:  bytes  b'Hello\\n'

    None doner: gecersiz string ise.
    """
    s = raw.strip()
    if len(s) < 2 or s[0] != '"' or s[-1] != '"':
        return None

    inner = s[1:-1]
    result = bytearray()
    i = 0
    while i < len(inner):
        c = inner[i]
        if c == '\\' and i + 1 < len(inner):
            nxt = inner[i + 1]
            if   nxt == 'n':  result.append(0x0A)
            elif nxt == 't':  result.append(0x09)
            elif nxt == 'r':  result.append(0x0D)
            elif nxt == '0':  result.append(0x00)
            elif nxt == '\\': result.append(0x5C)
            elif nxt == '"':  result.append(0x22)
            else:
                # Tanimsiz escape - oldugu gibi birak
                result.append(ord(c))
                result.append(ord(nxt))
            i += 2
        else:
            result.append(ord(c))
            i += 1
    return bytes(result)


def split_string_operand(rest):
    """Bir satirin operand kismini "string" olarak yakalar.

    Lexer normalde virgule gore bolerken string icindeki virgulleri bozar.
    Ornek: '.string "Hello, World"' -> '"Hello, World"' donmeli.

    rest: lexer'in operand[0] degeri DEGIL, orijinal satirdan ayrilmis
          ham string parcasi (ornek: '"Hello, World\\n"')
    """
    s = rest.strip()
    if not s.startswith('"'):
        return None
    # Sondaki tirnagi bul (escape edilmemis)
    i = 1
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            i += 2
            continue
        if s[i] == '"':
            return s[:i + 1]
        i += 1
    return None
