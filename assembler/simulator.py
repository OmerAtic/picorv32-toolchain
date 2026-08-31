# ============================================================
# simulator.py - Basit RV32I Simulatoru
# ============================================================
# Assemble edilen komutlari sirayla calistirir ve
# register degerlerini gosterir.
# 32 register + basit bellek simulasyonu yapar.
# ============================================================

from tables.opcode_table import get_instruction_info, get_register_number
from assembler.parser import parse_memory_operand, parse_immediate


def simulate(tokens, symbol_table, data_memory, max_steps=1000):
    """Assembly komutlarini simule eder.

    Args:
        tokens: Genisletilmis token listesi
        symbol_table: SymbolTable nesnesi
        data_memory: Direktiflerden gelen bellek degerleri
        max_steps: Sonsuz dongu korumasi

    Returns:
        registers: 32 elemanli register dizisi
    """
    # 32 register (x0 her zaman 0)
    registers = [0] * 32

    # Bellek simulasyonu (dict tabanli)
    memory = dict(data_memory)

    # Sadece instruction olan tokenlari filtrele
    instructions = []
    for token in tokens:
        if token["mnemonic"] is None:
            continue
        info = get_instruction_info(token["mnemonic"])
        if info is not None:
            instructions.append(token)

    # Program Counter (instruction index olarak)
    pc = 0
    step = 0

    while pc < len(instructions) and step < max_steps:
        token = instructions[pc]
        mnemonic = token["mnemonic"].upper()
        operands = token["operands"]
        info = get_instruction_info(mnemonic)
        inst_type = info["type"]

        next_pc = pc + 1  # Varsayilan: siradaki komut

        # ---- R-Type ----
        if inst_type == "R" and len(operands) == 3:
            rd = get_register_number(operands[0])
            rs1 = get_register_number(operands[1])
            rs2 = get_register_number(operands[2])
            if rd is not None and rs1 is not None and rs2 is not None:
                v1 = registers[rs1]
                v2 = registers[rs2]

                if mnemonic == "ADD":
                    result = v1 + v2
                elif mnemonic == "SUB":
                    result = v1 - v2
                elif mnemonic == "AND":
                    result = v1 & v2
                elif mnemonic == "OR":
                    result = v1 | v2
                elif mnemonic == "XOR":
                    result = v1 ^ v2
                elif mnemonic == "SLL":
                    result = v1 << (v2 & 0x1F)
                elif mnemonic == "SRL":
                    result = (v1 & 0xFFFFFFFF) >> (v2 & 0x1F)
                elif mnemonic == "SRA":
                    result = v1 >> (v2 & 0x1F)
                elif mnemonic == "SLT":
                    result = 1 if v1 < v2 else 0
                elif mnemonic == "SLTU":
                    result = 1 if (v1 & 0xFFFFFFFF) < (v2 & 0xFFFFFFFF) else 0
                else:
                    result = 0

                # 32-bit'e sigdir
                result = _to_signed_32(result)
                if rd != 0:  # x0 her zaman 0
                    registers[rd] = result

        # ---- I-Type ----
        elif inst_type == "I":
            if mnemonic in ["LW", "LH", "LB"]:
                # Load: rd, offset(rs1)
                if len(operands) == 2:
                    rd = get_register_number(operands[0])
                    mem = parse_memory_operand(operands[1])
                    if rd is not None and mem is not None:
                        rs1 = get_register_number(mem["register"])
                        if rs1 is not None:
                            addr = registers[rs1] + mem["offset"]
                            value = memory.get(addr, 0)
                            if rd != 0:
                                registers[rd] = _to_signed_32(value)

            elif mnemonic == "JALR":
                # jalr rd, rs1, imm
                if len(operands) == 3:
                    rd = get_register_number(operands[0])
                    rs1 = get_register_number(operands[1])
                    imm = parse_immediate(operands[2])
                    if rd is not None and rs1 is not None and imm is not None:
                        if rd != 0:
                            registers[rd] = _to_signed_32((pc + 1) * 4)
                        target_addr = (registers[rs1] + imm) & ~1
                        # Adresten instruction index'e cevir
                        next_pc = target_addr // 4

            else:
                # ADDI, ANDI, ORI, XORI, SLTI
                if len(operands) == 3:
                    rd = get_register_number(operands[0])
                    rs1 = get_register_number(operands[1])
                    imm = parse_immediate(operands[2])
                    if rd is not None and rs1 is not None and imm is not None:
                        v1 = registers[rs1]

                        if mnemonic == "ADDI":
                            result = v1 + imm
                        elif mnemonic == "ANDI":
                            result = v1 & imm
                        elif mnemonic == "ORI":
                            result = v1 | imm
                        elif mnemonic == "XORI":
                            result = v1 ^ imm
                        elif mnemonic == "SLTI":
                            result = 1 if v1 < imm else 0
                        else:
                            result = 0

                        result = _to_signed_32(result)
                        if rd != 0:
                            registers[rd] = result

        # ---- S-Type ----
        elif inst_type == "S":
            if len(operands) == 2:
                rs2 = get_register_number(operands[0])
                mem = parse_memory_operand(operands[1])
                if rs2 is not None and mem is not None:
                    rs1 = get_register_number(mem["register"])
                    if rs1 is not None:
                        addr = registers[rs1] + mem["offset"]
                        memory[addr] = registers[rs2] & 0xFFFFFFFF

        # ---- B-Type ----
        elif inst_type == "B":
            if len(operands) == 3:
                rs1 = get_register_number(operands[0])
                rs2 = get_register_number(operands[1])
                if rs1 is not None and rs2 is not None:
                    v1 = registers[rs1]
                    v2 = registers[rs2]
                    branch = False

                    if mnemonic == "BEQ":
                        branch = (v1 == v2)
                    elif mnemonic == "BNE":
                        branch = (v1 != v2)
                    elif mnemonic == "BLT":
                        branch = (v1 < v2)
                    elif mnemonic == "BGE":
                        branch = (v1 >= v2)
                    elif mnemonic == "BLTU":
                        branch = ((v1 & 0xFFFFFFFF) < (v2 & 0xFFFFFFFF))
                    elif mnemonic == "BGEU":
                        branch = ((v1 & 0xFFFFFFFF) >= (v2 & 0xFFFFFFFF))

                    if branch:
                        # Label'dan hedef adresi bul
                        target = parse_immediate(operands[2])
                        if target is None:
                            label_addr = symbol_table.get_address(operands[2])
                            if label_addr is not None:
                                next_pc = label_addr // 4
                        else:
                            next_pc = pc + (target // 4)

        # ---- U-Type ----
        elif inst_type == "U":
            if len(operands) == 2:
                rd = get_register_number(operands[0])
                imm = parse_immediate(operands[1])
                if rd is not None and imm is not None:
                    if mnemonic == "LUI":
                        result = imm << 12
                    elif mnemonic == "AUIPC":
                        result = (pc * 4) + (imm << 12)
                    else:
                        result = 0
                    result = _to_signed_32(result)
                    if rd != 0:
                        registers[rd] = result

        # ---- J-Type ----
        elif inst_type == "J":
            if len(operands) == 2:
                rd = get_register_number(operands[0])
                if rd is not None:
                    if rd != 0:
                        registers[rd] = _to_signed_32((pc + 1) * 4)
                    # Label'dan hedef bul
                    target = parse_immediate(operands[1])
                    if target is None:
                        label_addr = symbol_table.get_address(operands[1])
                        if label_addr is not None:
                            next_pc = label_addr // 4
                    else:
                        next_pc = pc + (target // 4)

        # x0 her zaman 0 olmali
        registers[0] = 0

        pc = next_pc
        step += 1

    return registers, memory, step


def print_registers(registers):
    """Sadece degeri olan registerlari yazdirir."""
    abi_names = [
        "zero", "ra", "sp", "gp", "tp", "t0", "t1", "t2",
        "s0/fp", "s1", "a0", "a1", "a2", "a3", "a4", "a5",
        "a6", "a7", "s2", "s3", "s4", "s5", "s6", "s7",
        "s8", "s9", "s10", "s11", "t3", "t4", "t5", "t6"
    ]

    print(f"\n{'='*60}")
    print(f"  REGISTER DURUMU (Simulasyon Sonucu)")
    print(f"{'='*60}")

    found = False
    for i in range(32):
        val = registers[i]
        if val != 0:
            unsigned_val = val & 0xFFFFFFFF
            print(f"  x{i:<4} ({abi_names[i]:<5})  =  {val:<12} (0x{unsigned_val:08X})")
            found = True

    if not found:
        print("  Tum registerlar 0.")

    print(f"{'='*60}")


def print_memory(memory):
    """Bellek icerigini yazdirir (sadece kullanilan adresler)."""
    if not memory:
        return

    print(f"\n{'='*55}")
    print(f"  BELLEK DURUMU")
    print(f"{'='*55}")
    print(f"  {'Adres':<14} {'Deger (Hex)':<16} {'Deger (Dec)'}")
    print(f"  {'-'*14} {'-'*16} {'-'*14}")

    for addr in sorted(memory.keys()):
        val = memory[addr]
        print(f"  0x{addr:08X}   0x{val:08X}       {val}")

    print(f"{'='*55}")


def _to_signed_32(value):
    """Degeri 32-bit signed integer'a cevirir."""
    value = value & 0xFFFFFFFF
    if value & 0x80000000:
        return value - 0x100000000
    return value
