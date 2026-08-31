# ============================================================
# opcode_table.py - RV32I Komut Sozlugu
# ============================================================
# Desteklenen tum RV32I komutlarinin opcode, funct3, funct7
# ve format bilgilerini icerir.
# Veri yapisi: dict (hash table) -> O(1) lookup
# ============================================================


# --- RV32I Komut Tablosu ---
# Her komut icin: opcode, funct3, funct7 (varsa), format tipi
# Format tipleri: R, I, S, B, U, J

OPCODE_TABLE = {
    # ---- R-Type Komutlar (register-register islemleri) ----
    "ADD":  {"opcode": 0b0110011, "funct3": 0b000, "funct7": 0b0000000, "type": "R"},
    "SUB":  {"opcode": 0b0110011, "funct3": 0b000, "funct7": 0b0100000, "type": "R"},
    "AND":  {"opcode": 0b0110011, "funct3": 0b111, "funct7": 0b0000000, "type": "R"},
    "OR":   {"opcode": 0b0110011, "funct3": 0b110, "funct7": 0b0000000, "type": "R"},
    "XOR":  {"opcode": 0b0110011, "funct3": 0b100, "funct7": 0b0000000, "type": "R"},
    "SLL":  {"opcode": 0b0110011, "funct3": 0b001, "funct7": 0b0000000, "type": "R"},
    "SRL":  {"opcode": 0b0110011, "funct3": 0b101, "funct7": 0b0000000, "type": "R"},
    "SRA":  {"opcode": 0b0110011, "funct3": 0b101, "funct7": 0b0100000, "type": "R"},
    "SLT":  {"opcode": 0b0110011, "funct3": 0b010, "funct7": 0b0000000, "type": "R"},
    "SLTU": {"opcode": 0b0110011, "funct3": 0b011, "funct7": 0b0000000, "type": "R"},

    # ---- I-Type Komutlar (immediate islemleri) ----
    "ADDI":  {"opcode": 0b0010011, "funct3": 0b000, "funct7": None, "type": "I"},
    "SLTI":  {"opcode": 0b0010011, "funct3": 0b010, "funct7": None, "type": "I"},
    "SLTIU": {"opcode": 0b0010011, "funct3": 0b011, "funct7": None, "type": "I"},
    "XORI":  {"opcode": 0b0010011, "funct3": 0b100, "funct7": None, "type": "I"},
    "ORI":   {"opcode": 0b0010011, "funct3": 0b110, "funct7": None, "type": "I"},
    "ANDI":  {"opcode": 0b0010011, "funct3": 0b111, "funct7": None, "type": "I"},

    # ---- I-Shift Komutlari (shift amount immediate, 5-bit) ----
    "SLLI":  {"opcode": 0b0010011, "funct3": 0b001, "funct7": 0b0000000, "type": "I_SHIFT"},
    "SRLI":  {"opcode": 0b0010011, "funct3": 0b101, "funct7": 0b0000000, "type": "I_SHIFT"},
    "SRAI":  {"opcode": 0b0010011, "funct3": 0b101, "funct7": 0b0100000, "type": "I_SHIFT"},

    # ---- I-Type Load Komutlari (bellekten okuma) ----
    "LW":   {"opcode": 0b0000011, "funct3": 0b010, "funct7": None, "type": "I"},
    "LH":   {"opcode": 0b0000011, "funct3": 0b001, "funct7": None, "type": "I"},
    "LB":   {"opcode": 0b0000011, "funct3": 0b000, "funct7": None, "type": "I"},

    # ---- I-Type JALR (register uzerinden atlama) ----
    "JALR": {"opcode": 0b1100111, "funct3": 0b000, "funct7": None, "type": "I"},

    # ---- S-Type Komutlar (bellege yazma) ----
    "SW":   {"opcode": 0b0100011, "funct3": 0b010, "funct7": None, "type": "S"},
    "SH":   {"opcode": 0b0100011, "funct3": 0b001, "funct7": None, "type": "S"},
    "SB":   {"opcode": 0b0100011, "funct3": 0b000, "funct7": None, "type": "S"},

    # ---- B-Type Komutlar (kosullu dallanma) ----
    "BEQ":  {"opcode": 0b1100011, "funct3": 0b000, "funct7": None, "type": "B"},
    "BNE":  {"opcode": 0b1100011, "funct3": 0b001, "funct7": None, "type": "B"},
    "BLT":  {"opcode": 0b1100011, "funct3": 0b100, "funct7": None, "type": "B"},
    "BGE":  {"opcode": 0b1100011, "funct3": 0b101, "funct7": None, "type": "B"},
    "BLTU": {"opcode": 0b1100011, "funct3": 0b110, "funct7": None, "type": "B"},
    "BGEU": {"opcode": 0b1100011, "funct3": 0b111, "funct7": None, "type": "B"},

    # ---- U-Type Komutlar (ust immediate) ----
    "LUI":   {"opcode": 0b0110111, "funct3": None, "funct7": None, "type": "U"},
    "AUIPC": {"opcode": 0b0010111, "funct3": None, "funct7": None, "type": "U"},

    # ---- J-Type Komutlar (kosulsuz atlama) ----
    "JAL":  {"opcode": 0b1101111, "funct3": None, "funct7": None, "type": "J"},
}


# --- Register Tablosu ---
# x0-x31 ve ABI isimleri -> register numarasi eslesmesi
# Assembler hem "x5" hem "t0" kabul etmeli

REGISTER_TABLE = {
    # x0-x31 numaralari
    "x0": 0,   "x1": 1,   "x2": 2,   "x3": 3,
    "x4": 4,   "x5": 5,   "x6": 6,   "x7": 7,
    "x8": 8,   "x9": 9,   "x10": 10, "x11": 11,
    "x12": 12, "x13": 13, "x14": 14, "x15": 15,
    "x16": 16, "x17": 17, "x18": 18, "x19": 19,
    "x20": 20, "x21": 21, "x22": 22, "x23": 23,
    "x24": 24, "x25": 25, "x26": 26, "x27": 27,
    "x28": 28, "x29": 29, "x30": 30, "x31": 31,

    # ABI isimleri
    "zero": 0,
    "ra": 1,
    "sp": 2,
    "gp": 3,
    "tp": 4,
    "t0": 5,  "t1": 6,  "t2": 7,
    "s0": 8,  "fp": 8,  # s0 ve fp ayni register
    "s1": 9,
    "a0": 10, "a1": 11, "a2": 12, "a3": 13,
    "a4": 14, "a5": 15, "a6": 16, "a7": 17,
    "s2": 18, "s3": 19, "s4": 20, "s5": 21,
    "s6": 22, "s7": 23, "s8": 24, "s9": 25,
    "s10": 26, "s11": 27,
    "t3": 28, "t4": 29, "t5": 30, "t6": 31,
}


def get_instruction_info(mnemonic):
    """Komut isminden opcode bilgilerini getirir.

    Buyuk/kucuk harf farki gozetmez.
    Bulunamazsa None dondurur.
    """
    return OPCODE_TABLE.get(mnemonic.upper())


def get_register_number(name):
    """Register adini (x0, ra, sp, t0 vb.) numaraya cevirir.

    Bulunamazsa None dondurur.
    """
    return REGISTER_TABLE.get(name.lower())
