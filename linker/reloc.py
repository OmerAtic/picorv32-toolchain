# ============================================================
# linker/reloc.py - Relocation Patcher
# ============================================================
# Her relocation tipi icin instruction word'unu patchler.
# Cagiran kod: relocation listesi + image bytes + sembol tablosu.
# Bu modul tek bir relocation'i patcheliyor.
# ============================================================

from assembler import obj_format as oof


class RelocError(Exception):
    """Relocation sirasinda olusan hatalar."""
    pass


def read_word_le(image, addr):
    """image bytearray'inden 32-bit word okur (LE)."""
    return (image[addr+0]
            | (image[addr+1] << 8)
            | (image[addr+2] << 16)
            | (image[addr+3] << 24))


def write_word_le(image, addr, word):
    """image bytearray'ine 32-bit word yazar (LE)."""
    image[addr+0] = (word >>  0) & 0xFF
    image[addr+1] = (word >>  8) & 0xFF
    image[addr+2] = (word >> 16) & 0xFF
    image[addr+3] = (word >> 24) & 0xFF


def _signed(value, bits):
    """value'yu bits bit'lik signed olarak yorumla."""
    mask = (1 << bits) - 1
    v = value & mask
    if v & (1 << (bits - 1)):
        return v - (1 << bits)
    return v


# ============================================================
# Tip basina patch fonksiyonlari
# ============================================================

def patch_branch(image, instr_addr, target):
    """R_RISCV_BRANCH: 12-bit PC-rel signed offset, B-type bit yerlesimi.

    offset = target - instr_addr (cift sayi olmali)
    -4096..+4094 araligi.
    """
    offset = target - instr_addr
    if offset & 1:
        raise RelocError(f"Branch offset cift olmali: {offset}")
    if offset < -4096 or offset > 4094:
        raise RelocError(f"Branch offset 12-bit asti: {offset}")

    instr = read_word_le(image, instr_addr)
    # B-type immediate alanlarini sifirla
    instr &= ~((0x1 << 31) | (0x3F << 25) | (0xF << 8) | (0x1 << 7))

    imm = offset & 0x1FFF  # 13 bit (LSB her zaman 0)
    bit_11   = (imm >> 11) & 0x1
    bit_4_1  = (imm >> 1)  & 0xF
    bit_10_5 = (imm >> 5)  & 0x3F
    bit_12   = (imm >> 12) & 0x1

    instr |= (bit_11   << 7)
    instr |= (bit_4_1  << 8)
    instr |= (bit_10_5 << 25)
    instr |= (bit_12   << 31)
    write_word_le(image, instr_addr, instr & 0xFFFFFFFF)


def patch_jal(image, instr_addr, target):
    """R_RISCV_JAL: 20-bit PC-rel signed offset, J-type bit yerlesimi."""
    offset = target - instr_addr
    if offset & 1:
        raise RelocError(f"JAL offset cift olmali: {offset}")
    if offset < -1048576 or offset > 1048574:
        raise RelocError(f"JAL offset 20-bit asti: {offset}")

    instr = read_word_le(image, instr_addr)
    # J-type immediate alanini sifirla (bits 31, 30:21, 20, 19:12)
    instr &= ~(0xFFFFF << 12)

    imm = offset & 0x1FFFFF  # 21 bit (LSB her zaman 0)
    bit_19_12 = (imm >> 12) & 0xFF
    bit_11    = (imm >> 11) & 0x1
    bit_10_1  = (imm >> 1)  & 0x3FF
    bit_20    = (imm >> 20) & 0x1

    instr |= (bit_19_12 << 12)
    instr |= (bit_11    << 20)
    instr |= (bit_10_1  << 21)
    instr |= (bit_20    << 31)
    write_word_le(image, instr_addr, instr & 0xFFFFFFFF)


def patch_hi20(image, instr_addr, target):
    """R_RISCV_HI20: LUI absolute. imm20 = ((target + 0x800) >> 12) & 0xFFFFF.

    Sign-extension karsisi 0x800 ekleyerek dengeleme.
    """
    imm20 = ((target + 0x800) >> 12) & 0xFFFFF
    instr = read_word_le(image, instr_addr)
    instr &= 0xFFF  # opcode + rd kalsin (bits 0..11)
    instr |= (imm20 << 12)
    write_word_le(image, instr_addr, instr & 0xFFFFFFFF)


def patch_lo12_i(image, instr_addr, target):
    """R_RISCV_LO12_I: I-type 12-bit imm. imm12 = target & 0xFFF (signed)."""
    imm12 = target & 0xFFF
    instr = read_word_le(image, instr_addr)
    instr &= 0x000FFFFF  # bits 0..19 korunur, 20..31 sifirlanir
    instr |= (imm12 << 20)
    write_word_le(image, instr_addr, instr & 0xFFFFFFFF)


def patch_lo12_s(image, instr_addr, target):
    """R_RISCV_LO12_S: S-type 12-bit imm.

    [31:25] imm[11:5]
    [11:7]  imm[4:0]
    """
    imm12 = target & 0xFFF
    imm_low  = imm12 & 0x1F
    imm_high = (imm12 >> 5) & 0x7F

    instr = read_word_le(image, instr_addr)
    # imm bit'lerini sifirla
    instr &= ~((0x7F << 25) | (0x1F << 7))
    instr |= (imm_low  << 7)
    instr |= (imm_high << 25)
    write_word_le(image, instr_addr, instr & 0xFFFFFFFF)


def patch_pcrel_hi20(image, instr_addr, target):
    """R_RISCV_PCREL_HI20: AUIPC.

    imm20 = ((target - instr_addr + 0x800) >> 12) & 0xFFFFF
    """
    delta = target - instr_addr
    imm20 = ((delta + 0x800) >> 12) & 0xFFFFF
    instr = read_word_le(image, instr_addr)
    instr &= 0xFFF
    instr |= (imm20 << 12)
    write_word_le(image, instr_addr, instr & 0xFFFFFFFF)


def patch_pcrel_lo12_i(image, instr_addr, target):
    """R_RISCV_PCREL_LO12_I: JALR/ADDI sonrasi AUIPC.

    Onemli: Referans noktasi onceki AUIPC instruction'i (instr_addr - 4).
    imm12 = (target - (instr_addr - 4)) & 0xFFF
    """
    delta = target - (instr_addr - 4)
    imm12 = delta & 0xFFF
    instr = read_word_le(image, instr_addr)
    instr &= 0x000FFFFF
    instr |= (imm12 << 20)
    write_word_le(image, instr_addr, instr & 0xFFFFFFFF)


# ============================================================
# Dispatch
# ============================================================

def apply_reloc(image, reloc_type, instr_addr, target):
    """Bir relocation'i tipine gore uygular.

    Args:
        image: bytearray (full memory image)
        reloc_type: oof.R_* sabiti
        instr_addr: instruction'in image icindeki byte adresi
        target: hedef adres (sembol degeri + addend)
    """
    if reloc_type == oof.R_BRANCH:
        patch_branch(image, instr_addr, target)
    elif reloc_type == oof.R_JAL:
        patch_jal(image, instr_addr, target)
    elif reloc_type == oof.R_HI20:
        patch_hi20(image, instr_addr, target)
    elif reloc_type == oof.R_LO12_I:
        patch_lo12_i(image, instr_addr, target)
    elif reloc_type == oof.R_LO12_S:
        patch_lo12_s(image, instr_addr, target)
    elif reloc_type == oof.R_PCREL_HI20:
        patch_pcrel_hi20(image, instr_addr, target)
    elif reloc_type == oof.R_PCREL_LO12:
        patch_pcrel_lo12_i(image, instr_addr, target)
    else:
        raise RelocError(f"Desteklenmeyen reloc tipi: {reloc_type}")
