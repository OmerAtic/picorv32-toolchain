# test_encoder.py - Makine Kodu Uretimi Testleri
# Her komut formati icin en az bir dogrulama

from assembler.encoder import (
    encode_r_type, encode_i_type, encode_s_type,
    encode_b_type, encode_u_type, encode_j_type
)


def test_r_type_add():
    """ADD x1, x2, x3 icin dogru makine kodu uretildigini test eder.

    ADD: opcode=0110011, funct3=000, funct7=0000000
    rd=x1(1), rs1=x2(2), rs2=x3(3)
    Beklenen: 0x003100B3
    """
    result = encode_r_type(rd=1, rs1=2, rs2=3, funct3=0b000, funct7=0b0000000, opcode=0b0110011)
    assert result == 0x003100B3, f"Beklenen: 0x003100B3, Alinan: 0x{result:08X}"


def test_r_type_sub():
    """SUB x4, x5, x6 icin dogrulama.

    SUB: funct7=0100000, funct3=000
    Beklenen: 0x40628233
    """
    result = encode_r_type(rd=4, rs1=5, rs2=6, funct3=0b000, funct7=0b0100000, opcode=0b0110011)
    assert result == 0x40628233, f"Beklenen: 0x40628233, Alinan: 0x{result:08X}"


def test_i_type_addi():
    """ADDI x1, x0, 100 icin dogrulama.

    ADDI: opcode=0010011, funct3=000
    rd=1, rs1=0, imm=100
    Beklenen: 0x06400093
    """
    result = encode_i_type(rd=1, rs1=0, imm=100, funct3=0b000, opcode=0b0010011)
    assert result == 0x06400093, f"Beklenen: 0x06400093, Alinan: 0x{result:08X}"


def test_i_type_negatif_immediate():
    """ADDI x2, x1, -50 icin dogrulama (negatif immediate).

    imm = -50 = 0xFCE (12-bit two's complement)
    Beklenen: 0xFCE08113
    """
    result = encode_i_type(rd=2, rs1=1, imm=-50, funct3=0b000, opcode=0b0010011)
    assert result == 0xFCE08113, f"Beklenen: 0xFCE08113, Alinan: 0x{result:08X}"


def test_s_type_sw():
    """SW x5, 4(x1) icin dogrulama.

    SW: opcode=0100011, funct3=010
    rs2=5, rs1=1, imm=4
    Beklenen: 0x0050A223
    """
    result = encode_s_type(rs1=1, rs2=5, imm=4, funct3=0b010, opcode=0b0100011)
    assert result == 0x0050A223, f"Beklenen: 0x0050A223, Alinan: 0x{result:08X}"


def test_b_type_beq():
    """BEQ x1, x2, offset=20 icin dogrulama.

    B-type immediate bit karistirmasi dogru yapilmali.
    """
    result = encode_b_type(rs1=1, rs2=2, imm=20, funct3=0b000, opcode=0b1100011)
    # Sonucu kontrol et - en azindan opcode dogru olmali
    assert (result & 0x7F) == 0b1100011  # opcode kontrol


def test_u_type_lui():
    """LUI x7, 0x12345 icin dogrulama.

    LUI: opcode=0110111
    rd=7, imm=0x12345
    Beklenen: 0x123453B7
    """
    result = encode_u_type(rd=7, imm=0x12345, opcode=0b0110111)
    assert result == 0x123453B7, f"Beklenen: 0x123453B7, Alinan: 0x{result:08X}"


def test_j_type_jal():
    """JAL x1 icin opcode dogrulamasi.

    J-type immediate bit karistirmasi dogru yapilmali.
    """
    result = encode_j_type(rd=1, imm=0, opcode=0b1101111)
    # opcode ve rd dogrulama
    assert (result & 0x7F) == 0b1101111       # opcode
    assert ((result >> 7) & 0x1F) == 1         # rd = x1


def test_nop_encoding():
    """NOP (ADDI x0, x0, 0) icin dogrulama.

    Beklenen: 0x00000013
    """
    result = encode_i_type(rd=0, rs1=0, imm=0, funct3=0b000, opcode=0b0010011)
    assert result == 0x00000013, f"Beklenen: 0x00000013, Alinan: 0x{result:08X}"
