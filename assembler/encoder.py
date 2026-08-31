# ============================================================
# encoder.py - Makine Kodu Uretici
# ============================================================
# Assembly komutlarini 32-bit makine koduna donusturur.
# Her komut formati (R, I, S, B, U, J) icin ayri encoding
# fonksiyonu bulunur. Bit shift ve mask islemleri ile
# 32-bit instruction word olusturulur.
#
# RV32I Instruction Formatlari:
#   R-Type: [funct7 | rs2 | rs1 | funct3 | rd | opcode]
#   I-Type: [imm[11:0]        | rs1 | funct3 | rd | opcode]
#   S-Type: [imm[11:5] | rs2 | rs1 | funct3 | imm[4:0] | opcode]
#   B-Type: [imm[12|10:5] | rs2 | rs1 | funct3 | imm[4:1|11] | opcode]
#   U-Type: [imm[31:12]                       | rd | opcode]
#   J-Type: [imm[20|10:1|11|19:12]            | rd | opcode]
# ============================================================

from tables.opcode_table import get_instruction_info, get_register_number
from assembler.parser import parse_memory_operand, parse_immediate


def encode_r_type(rd, rs1, rs2, funct3, funct7, opcode):
    """R-Type komut formatini encode eder.

    Bit yapisi (32 bit):
    [31:25] funct7 | [24:20] rs2 | [19:15] rs1 | [14:12] funct3 | [11:7] rd | [6:0] opcode
    """
    instruction = 0
    instruction |= (opcode & 0x7F)         # bit [6:0]
    instruction |= (rd & 0x1F) << 7        # bit [11:7]
    instruction |= (funct3 & 0x7) << 12    # bit [14:12]
    instruction |= (rs1 & 0x1F) << 15      # bit [19:15]
    instruction |= (rs2 & 0x1F) << 20      # bit [24:20]
    instruction |= (funct7 & 0x7F) << 25   # bit [31:25]
    return instruction


def encode_i_type(rd, rs1, imm, funct3, opcode):
    """I-Type komut formatini encode eder.

    Bit yapisi (32 bit):
    [31:20] imm[11:0] | [19:15] rs1 | [14:12] funct3 | [11:7] rd | [6:0] opcode

    imm 12-bit signed: -2048 .. 2047
    """
    # 12-bit signed immediate -> unsigned bit patterni
    imm_bits = imm & 0xFFF

    instruction = 0
    instruction |= (opcode & 0x7F)         # bit [6:0]
    instruction |= (rd & 0x1F) << 7        # bit [11:7]
    instruction |= (funct3 & 0x7) << 12    # bit [14:12]
    instruction |= (rs1 & 0x1F) << 15      # bit [19:15]
    instruction |= (imm_bits & 0xFFF) << 20  # bit [31:20]
    return instruction


def encode_s_type(rs1, rs2, imm, funct3, opcode):
    """S-Type komut formatini encode eder.

    Bit yapisi (32 bit):
    [31:25] imm[11:5] | [24:20] rs2 | [19:15] rs1 | [14:12] funct3 | [11:7] imm[4:0] | [6:0] opcode

    imm 12-bit signed: -2048 .. 2047
    Immediate iki parcaya bolunur: ust 7 bit ve alt 5 bit
    """
    imm_bits = imm & 0xFFF
    imm_low = imm_bits & 0x1F          # bit [4:0]
    imm_high = (imm_bits >> 5) & 0x7F  # bit [11:5]

    instruction = 0
    instruction |= (opcode & 0x7F)         # bit [6:0]
    instruction |= (imm_low & 0x1F) << 7   # bit [11:7]
    instruction |= (funct3 & 0x7) << 12    # bit [14:12]
    instruction |= (rs1 & 0x1F) << 15      # bit [19:15]
    instruction |= (rs2 & 0x1F) << 20      # bit [24:20]
    instruction |= (imm_high & 0x7F) << 25 # bit [31:25]
    return instruction


def encode_b_type(rs1, rs2, imm, funct3, opcode):
    """B-Type komut formatini encode eder.

    Bit yapisi (32 bit):
    [31] imm[12] | [30:25] imm[10:5] | [24:20] rs2 | [19:15] rs1 |
    [14:12] funct3 | [11:8] imm[4:1] | [7] imm[11] | [6:0] opcode

    imm 13-bit signed (en dusuk bit her zaman 0, 2'nin katlari):
    -4096 .. 4094 (cift sayilar)

    DIKKAT: B-type'da immediate bitleri karisik siralanir!
    """
    imm_bits = imm & 0x1FFF  # 13 bit

    # Bit parcalarini ayir
    bit_11  = (imm_bits >> 11) & 0x1    # imm[11]
    bit_4_1 = (imm_bits >> 1) & 0xF     # imm[4:1]
    bit_10_5 = (imm_bits >> 5) & 0x3F   # imm[10:5]
    bit_12  = (imm_bits >> 12) & 0x1    # imm[12]

    instruction = 0
    instruction |= (opcode & 0x7F)           # bit [6:0]
    instruction |= (bit_11 & 0x1) << 7       # bit [7]    = imm[11]
    instruction |= (bit_4_1 & 0xF) << 8      # bit [11:8] = imm[4:1]
    instruction |= (funct3 & 0x7) << 12      # bit [14:12]
    instruction |= (rs1 & 0x1F) << 15        # bit [19:15]
    instruction |= (rs2 & 0x1F) << 20        # bit [24:20]
    instruction |= (bit_10_5 & 0x3F) << 25   # bit [30:25] = imm[10:5]
    instruction |= (bit_12 & 0x1) << 31      # bit [31]    = imm[12]
    return instruction


def encode_u_type(rd, imm, opcode):
    """U-Type komut formatini encode eder.

    Bit yapisi (32 bit):
    [31:12] imm[31:12] | [11:7] rd | [6:0] opcode

    imm ust 20 bit (alt 12 bit sifir kabul edilir)
    """
    instruction = 0
    instruction |= (opcode & 0x7F)                # bit [6:0]
    instruction |= (rd & 0x1F) << 7               # bit [11:7]
    instruction |= ((imm & 0xFFFFF) << 12)        # bit [31:12]
    return instruction


def encode_i_shift(rd, rs1, shamt, funct3, funct7, opcode):
    """I-Shift komutu (SLLI/SRLI/SRAI) encode'u.

    Bit yapisi I-type ile ayni; ama imm[11:0] = (funct7 << 5) | (shamt & 0x1F).
    shamt 0..31 araliginda olmali.
    """
    imm = ((funct7 & 0x7F) << 5) | (shamt & 0x1F)
    return encode_i_type(rd, rs1, imm & 0xFFF, funct3, opcode)


def encode_j_type(rd, imm, opcode):
    """J-Type komut formatini encode eder.

    Bit yapisi (32 bit):
    [31] imm[20] | [30:21] imm[10:1] | [20] imm[11] | [19:12] imm[19:12] |
    [11:7] rd | [6:0] opcode

    imm 21-bit signed (en dusuk bit 0, 2'nin katlari):
    -1048576 .. 1048574

    DIKKAT: J-type'da da immediate bitleri karisik siralanir!
    """
    imm_bits = imm & 0x1FFFFF  # 21 bit

    # Bit parcalarini ayir
    bit_19_12 = (imm_bits >> 12) & 0xFF    # imm[19:12]
    bit_11    = (imm_bits >> 11) & 0x1     # imm[11]
    bit_10_1  = (imm_bits >> 1) & 0x3FF    # imm[10:1]
    bit_20    = (imm_bits >> 20) & 0x1     # imm[20]

    instruction = 0
    instruction |= (opcode & 0x7F)               # bit [6:0]
    instruction |= (rd & 0x1F) << 7              # bit [11:7]
    instruction |= (bit_19_12 & 0xFF) << 12      # bit [19:12] = imm[19:12]
    instruction |= (bit_11 & 0x1) << 20          # bit [20]    = imm[11]
    instruction |= (bit_10_1 & 0x3FF) << 21      # bit [30:21] = imm[10:1]
    instruction |= (bit_20 & 0x1) << 31          # bit [31]    = imm[20]
    return instruction


def encode_instruction(token, current_pc, symbol_table, error_handler):
    """Tek bir instruction token'ini 32-bit makine koduna donusturur.

    Args:
        token: Parser ciktisi {"mnemonic", "operands", "line_num", ...}
        current_pc: Bu instruction'in adresi
        symbol_table: Label adreslerini iceren SymbolTable nesnesi
        error_handler: Hata yoneticisi

    Returns:
        32-bit integer (makine kodu) veya None (hata durumunda)
    """
    mnemonic = token["mnemonic"].upper()
    operands = token["operands"]
    line_num = token["line_num"]

    # Opcode tablosundan komut bilgisini al
    info = get_instruction_info(mnemonic)
    if info is None:
        error_handler.add_error(line_num, "encoding",
                                f"Bilinmeyen komut: '{mnemonic}'")
        return None

    inst_type = info["type"]
    opcode = info["opcode"]
    funct3 = info["funct3"]
    funct7 = info["funct7"]

    # ---- R-Type: ADD rd, rs1, rs2 ----
    if inst_type == "R":
        if len(operands) != 3:
            error_handler.add_error(line_num, "syntax",
                                    f"{mnemonic} komutu 3 operand gerektirir (rd, rs1, rs2)")
            return None

        rd = get_register_number(operands[0])
        rs1 = get_register_number(operands[1])
        rs2 = get_register_number(operands[2])

        if rd is None or rs1 is None or rs2 is None:
            for i, op in enumerate(operands):
                if get_register_number(op) is None:
                    error_handler.add_error(line_num, "syntax",
                                            f"Gecersiz register: '{op}'")
            return None

        return encode_r_type(rd, rs1, rs2, funct3, funct7, opcode)

    # ---- I-Type: ADDI rd, rs1, imm  veya  LW rd, offset(rs1) ----
    elif inst_type == "I":
        # Load komutlari icin ozel format: LW rd, offset(rs1)
        if mnemonic in ["LW", "LH", "LB"]:
            if len(operands) != 2:
                error_handler.add_error(line_num, "syntax",
                                        f"{mnemonic} komutu 2 operand gerektirir: rd, offset(rs1)")
                return None

            rd = get_register_number(operands[0])
            if rd is None:
                error_handler.add_error(line_num, "syntax",
                                        f"Gecersiz register: '{operands[0]}'")
                return None

            mem = parse_memory_operand(operands[1])
            if mem is None:
                error_handler.add_error(line_num, "syntax",
                                        f"Gecersiz bellek adresi formati: '{operands[1]}'")
                return None

            rs1 = get_register_number(mem["register"])
            if rs1 is None:
                error_handler.add_error(line_num, "syntax",
                                        f"Gecersiz register: '{mem['register']}'")
                return None

            imm = mem["offset"]

        # JALR: jalr rd, rs1, imm
        elif mnemonic == "JALR":
            if len(operands) != 3:
                error_handler.add_error(line_num, "syntax",
                                        f"JALR komutu 3 operand gerektirir: rd, rs1, imm")
                return None

            rd = get_register_number(operands[0])
            rs1 = get_register_number(operands[1])
            if rd is None or rs1 is None:
                error_handler.add_error(line_num, "syntax",
                                        f"Gecersiz register operand")
                return None

            imm = parse_immediate(operands[2])
            if imm is None:
                error_handler.add_error(line_num, "syntax",
                                        f"Gecersiz immediate deger: '{operands[2]}'")
                return None

        # Diger I-type: ADDI rd, rs1, imm
        else:
            if len(operands) != 3:
                error_handler.add_error(line_num, "syntax",
                                        f"{mnemonic} komutu 3 operand gerektirir: rd, rs1, imm")
                return None

            rd = get_register_number(operands[0])
            rs1 = get_register_number(operands[1])
            if rd is None or rs1 is None:
                for op in [operands[0], operands[1]]:
                    if get_register_number(op) is None:
                        error_handler.add_error(line_num, "syntax",
                                                f"Gecersiz register: '{op}'")
                return None

            imm = parse_immediate(operands[2])
            if imm is None:
                error_handler.add_error(line_num, "syntax",
                                        f"Gecersiz immediate deger: '{operands[2]}'")
                return None

        # Immediate sinir kontrolu (12-bit signed: -2048 .. 2047)
        if imm < -2048 or imm > 2047:
            error_handler.add_error(line_num, "encoding",
                                    f"Immediate deger 12-bit sinirini asiyor: {imm} (sinir: -2048..2047)")
            return None

        return encode_i_type(rd, rs1, imm, funct3, opcode)

    # ---- S-Type: SW rs2, offset(rs1) ----
    elif inst_type == "S":
        if len(operands) != 2:
            error_handler.add_error(line_num, "syntax",
                                    f"{mnemonic} komutu 2 operand gerektirir: rs2, offset(rs1)")
            return None

        rs2 = get_register_number(operands[0])
        if rs2 is None:
            error_handler.add_error(line_num, "syntax",
                                    f"Gecersiz register: '{operands[0]}'")
            return None

        mem = parse_memory_operand(operands[1])
        if mem is None:
            error_handler.add_error(line_num, "syntax",
                                    f"Gecersiz bellek adresi formati: '{operands[1]}'")
            return None

        rs1 = get_register_number(mem["register"])
        if rs1 is None:
            error_handler.add_error(line_num, "syntax",
                                    f"Gecersiz register: '{mem['register']}'")
            return None

        imm = mem["offset"]
        if imm < -2048 or imm > 2047:
            error_handler.add_error(line_num, "encoding",
                                    f"Offset deger 12-bit sinirini asiyor: {imm}")
            return None

        return encode_s_type(rs1, rs2, imm, funct3, opcode)

    # ---- B-Type: BEQ rs1, rs2, label ----
    elif inst_type == "B":
        if len(operands) != 3:
            error_handler.add_error(line_num, "syntax",
                                    f"{mnemonic} komutu 3 operand gerektirir: rs1, rs2, label/offset")
            return None

        rs1 = get_register_number(operands[0])
        rs2 = get_register_number(operands[1])
        if rs1 is None or rs2 is None:
            for op in [operands[0], operands[1]]:
                if get_register_number(op) is None:
                    error_handler.add_error(line_num, "syntax",
                                            f"Gecersiz register: '{op}'")
            return None

        # 3. operand: label adi veya sayi (offset)
        imm = parse_immediate(operands[2])
        if imm is None:
            # Label olabilir - symbol table'dan adresini bul
            label_addr = symbol_table.get_address(operands[2])
            if label_addr is None:
                error_handler.add_error(line_num, "semantic",
                                        f"Tanimlanmamis label: '{operands[2]}'")
                return None
            # Offset hesapla: hedef_adres - mevcut_adres
            imm = label_addr - current_pc

        # B-type offset 13-bit signed, cift sayi olmali
        if imm < -4096 or imm > 4094:
            error_handler.add_error(line_num, "encoding",
                                    f"Branch offset siniri asildi: {imm} (sinir: -4096..4094)")
            return None

        return encode_b_type(rs1, rs2, imm, funct3, opcode)

    # ---- U-Type: LUI rd, imm ----
    elif inst_type == "U":
        if len(operands) != 2:
            error_handler.add_error(line_num, "syntax",
                                    f"{mnemonic} komutu 2 operand gerektirir: rd, imm")
            return None

        rd = get_register_number(operands[0])
        if rd is None:
            error_handler.add_error(line_num, "syntax",
                                    f"Gecersiz register: '{operands[0]}'")
            return None

        imm = parse_immediate(operands[1])
        if imm is None:
            error_handler.add_error(line_num, "syntax",
                                    f"Gecersiz immediate deger: '{operands[1]}'")
            return None

        # U-type immediate: 20-bit (0..1048575)
        if imm < 0 or imm > 0xFFFFF:
            error_handler.add_error(line_num, "encoding",
                                    f"U-type immediate 20-bit sinirini asiyor: {imm}")
            return None

        return encode_u_type(rd, imm, opcode)

    # ---- J-Type: JAL rd, label ----
    elif inst_type == "J":
        if len(operands) != 2:
            error_handler.add_error(line_num, "syntax",
                                    f"{mnemonic} komutu 2 operand gerektirir: rd, label/offset")
            return None

        rd = get_register_number(operands[0])
        if rd is None:
            error_handler.add_error(line_num, "syntax",
                                    f"Gecersiz register: '{operands[0]}'")
            return None

        # 2. operand: label adi veya sayi (offset)
        imm = parse_immediate(operands[1])
        if imm is None:
            # Label olabilir
            label_addr = symbol_table.get_address(operands[1])
            if label_addr is None:
                error_handler.add_error(line_num, "semantic",
                                        f"Tanimlanmamis label: '{operands[1]}'")
                return None
            imm = label_addr - current_pc

        # J-type offset 21-bit signed, cift sayi
        if imm < -1048576 or imm > 1048574:
            error_handler.add_error(line_num, "encoding",
                                    f"Jump offset siniri asildi: {imm}")
            return None

        return encode_j_type(rd, imm, opcode)

    return None
