# ============================================================
# pseudo.py - Pseudo-Komut Donusturucusu
# ============================================================
# Kullanici dostu pseudo-komutlari gercek RV32I komutlarina
# donusturur. Encoder'dan ONCE calistirilir.
#
# Proje-1 pseudo'lari (geri uyumlu):
#   li rd, imm  -> addi rd, x0, imm  (kucuk) veya lui+addi (buyuk)
#   mv rd, rs   -> addi rd, rs, 0
#   j label     -> jal x0, label
#   nop         -> addi x0, x0, 0
#   ret         -> jalr x0, ra, 0
#   not rd, rs  -> xori rd, rs, -1
#   neg rd, rs  -> sub rd, x0, rs
#
# Proje-2 (linker icin) eklenenler:
#   la   rd, sym       -> lui rd, %hi(sym) + addi rd, rd, %lo(sym)
#   call func          -> auipc ra, %pcrel_hi(func) + jalr ra, ra, %pcrel_lo(func)
#   beqz rs, label     -> beq rs, x0, label
#   bnez rs, label     -> bne rs, x0, label
#   bgez rs, label     -> bge rs, x0, label
#   bltz rs, label     -> blt rs, x0, label
#   jr   rs            -> jalr x0, rs, 0
# ============================================================


PSEUDO_LIST = [
    # Proje-1
    "LI", "MV", "J", "NOP", "RET", "NOT", "NEG",
    # Proje-2 (linker icin)
    "LA", "CALL",
    "BEQZ", "BNEZ", "BGEZ", "BLTZ", "JR",
]


def is_pseudo(mnemonic):
    """Verilen komut bir pseudo-komut mu?"""
    if mnemonic is None:
        return False
    return mnemonic.upper() in PSEUDO_LIST


def expand_pseudo(token):
    """Pseudo-komutu gercek RV32I komut(lar)ina donusturur.

    Args:
        token: Lexer ciktisi {"line_num", "label", "mnemonic", "operands", ...}

    Returns:
        Gercek komut token listesi (1 veya 2 eleman)
    """
    mnemonic = token["mnemonic"].upper()
    operands = token["operands"]
    line_num = token["line_num"]

    expanded = []

    # ---- Proje-1 pseudo'lari ----
    if mnemonic == "NOP":
        expanded.append(_make_token(line_num, token["label"], "ADDI",
                                    ["x0", "x0", "0"]))

    elif mnemonic == "MV":
        if len(operands) >= 2:
            expanded.append(_make_token(line_num, token["label"], "ADDI",
                                        [operands[0], operands[1], "0"]))

    elif mnemonic == "J":
        # j label -> jal x0, label
        if len(operands) >= 1:
            expanded.append(_make_token(line_num, token["label"], "JAL",
                                        ["x0", operands[0]]))

    elif mnemonic == "RET":
        expanded.append(_make_token(line_num, token["label"], "JALR",
                                    ["x0", "ra", "0"]))

    elif mnemonic == "NOT":
        if len(operands) >= 2:
            expanded.append(_make_token(line_num, token["label"], "XORI",
                                        [operands[0], operands[1], "-1"]))

    elif mnemonic == "NEG":
        if len(operands) >= 2:
            expanded.append(_make_token(line_num, token["label"], "SUB",
                                        [operands[0], "x0", operands[1]]))

    elif mnemonic == "LI":
        if len(operands) >= 2:
            expanded = _expand_li(token)

    # ---- Proje-2 pseudo'lari ----
    elif mnemonic == "LA":
        # la rd, sym -> lui rd, %hi(sym) + addi rd, rd, %lo(sym)
        if len(operands) >= 2:
            rd = operands[0]
            sym = operands[1]
            expanded.append(_make_token(line_num, token["label"], "LUI",
                                        [rd, f"%hi({sym})"]))
            expanded.append(_make_token(line_num, None, "ADDI",
                                        [rd, rd, f"%lo({sym})"]))

    elif mnemonic == "CALL":
        # call func -> auipc ra, %pcrel_hi(func) + jalr ra, ra, %pcrel_lo(func)
        if len(operands) >= 1:
            func = operands[0]
            expanded.append(_make_token(line_num, token["label"], "AUIPC",
                                        ["ra", f"%pcrel_hi({func})"]))
            expanded.append(_make_token(line_num, None, "JALR",
                                        ["ra", "ra", f"%pcrel_lo({func})"]))

    elif mnemonic == "BEQZ":
        # beqz rs, label -> beq rs, x0, label
        if len(operands) >= 2:
            expanded.append(_make_token(line_num, token["label"], "BEQ",
                                        [operands[0], "x0", operands[1]]))

    elif mnemonic == "BNEZ":
        # bnez rs, label -> bne rs, x0, label
        if len(operands) >= 2:
            expanded.append(_make_token(line_num, token["label"], "BNE",
                                        [operands[0], "x0", operands[1]]))

    elif mnemonic == "BGEZ":
        # bgez rs, label -> bge rs, x0, label
        if len(operands) >= 2:
            expanded.append(_make_token(line_num, token["label"], "BGE",
                                        [operands[0], "x0", operands[1]]))

    elif mnemonic == "BLTZ":
        # bltz rs, label -> blt rs, x0, label
        if len(operands) >= 2:
            expanded.append(_make_token(line_num, token["label"], "BLT",
                                        [operands[0], "x0", operands[1]]))

    elif mnemonic == "JR":
        # jr rs -> jalr x0, rs, 0
        if len(operands) >= 1:
            expanded.append(_make_token(line_num, token["label"], "JALR",
                                        ["x0", operands[0], "0"]))

    return expanded


def _expand_li(token):
    """LI pseudo-komutunu genisletir (32-bit immediate destegi).

    Kucuk immediate (-2048..2047): sadece addi rd, x0, imm
    Buyuk immediate: lui rd, upper + addi rd, rd, lower

    DIKKAT: Sign-extension duzeltmesi gerekli!
    Eger lower 12-bit'in en ust biti (bit 11) set ise,
    addi'nin signed yorumlamasi nedeniyle lui'ya +1 eklenmelidir.

    32-bit signed aritmetik kullanilir (0xDEADBEEF gibi degerler icin).
    """
    rd = token["operands"][0]
    imm_str = token["operands"][1]
    line_num = token["line_num"]

    # Immediate parse
    try:
        if imm_str.startswith("0x") or imm_str.startswith("0X"):
            imm = int(imm_str, 16)
        elif imm_str.startswith("0b") or imm_str.startswith("0B"):
            imm = int(imm_str, 2)
        else:
            imm = int(imm_str)
    except ValueError:
        # Parse edemedi - asil hata encoder'da yakalanir
        return [_make_token(line_num, token["label"], "ADDI",
                            [rd, "x0", imm_str])]

    # 32-bit'e sigdir
    imm = imm & 0xFFFFFFFF

    # Signed 32-bit yorumla
    if imm & 0x80000000:
        imm_signed = imm - 0x100000000
    else:
        imm_signed = imm

    # 12-bit'e sigiyor mu? (-2048 .. 2047)
    if -2048 <= imm_signed <= 2047:
        return [_make_token(line_num, token["label"], "ADDI",
                            [rd, "x0", str(imm_signed)])]

    # Buyuk immediate: LUI + ADDI
    # Alt 12-bit (signed)
    lower = imm_signed & 0xFFF
    if lower & 0x800:
        # Signed: alt 12-bit negatif olacak, ust 20-bit'e +1 ekle
        lower_signed = lower - 0x1000
        upper = ((imm_signed - lower_signed) >> 12) & 0xFFFFF
    else:
        lower_signed = lower
        upper = (imm_signed >> 12) & 0xFFFFF

    expanded = []
    expanded.append(_make_token(line_num, token["label"], "LUI",
                                [rd, str(upper)]))
    expanded.append(_make_token(line_num, None, "ADDI",
                                [rd, rd, str(lower_signed)]))
    return expanded


def _make_token(line_num, label, mnemonic, operands):
    """Yeni bir token olusturur (genisletilmis komut icin)."""
    return {
        "line_num": line_num,
        "label": label,
        "mnemonic": mnemonic,
        "operands": operands,
        "original": f"  [expanded] {mnemonic} {', '.join(operands)}"
    }
