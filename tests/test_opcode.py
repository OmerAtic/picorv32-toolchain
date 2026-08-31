# test_opcode.py - Opcode Table Testleri

from tables.opcode_table import get_instruction_info, get_register_number


def test_r_type_komutlar():
    """R-Type komutlarin opcode tablosunda dogru tanimlandigini test eder."""
    info = get_instruction_info("ADD")
    assert info is not None
    assert info["type"] == "R"
    assert info["opcode"] == 0b0110011
    assert info["funct3"] == 0b000
    assert info["funct7"] == 0b0000000

    info = get_instruction_info("SUB")
    assert info["funct7"] == 0b0100000  # SUB'in farkli funct7'si


def test_i_type_komutlar():
    """I-Type komutlarin opcode tablosunda dogru oldugunu test eder."""
    info = get_instruction_info("ADDI")
    assert info is not None
    assert info["type"] == "I"
    assert info["opcode"] == 0b0010011
    assert info["funct3"] == 0b000


def test_s_type_komutlar():
    """S-Type komutlarin dogru tanimlandigini test eder."""
    info = get_instruction_info("SW")
    assert info is not None
    assert info["type"] == "S"
    assert info["funct3"] == 0b010


def test_b_type_komutlar():
    """B-Type komutlarin dogru tanimlandigini test eder."""
    info = get_instruction_info("BEQ")
    assert info is not None
    assert info["type"] == "B"
    assert info["opcode"] == 0b1100011


def test_u_type_komutlar():
    """U-Type komutlarin dogru tanimlandigini test eder."""
    info = get_instruction_info("LUI")
    assert info is not None
    assert info["type"] == "U"
    assert info["opcode"] == 0b0110111


def test_j_type_komutlar():
    """J-Type komutlarin dogru tanimlandigini test eder."""
    info = get_instruction_info("JAL")
    assert info is not None
    assert info["type"] == "J"
    assert info["opcode"] == 0b1101111


def test_buyuk_kucuk_harf():
    """Buyuk/kucuk harf farki gozetmeden komut bulunabildigini test eder."""
    assert get_instruction_info("add") is not None
    assert get_instruction_info("ADD") is not None
    assert get_instruction_info("Add") is not None


def test_bilinmeyen_komut():
    """Olmayan komut icin None donuldugunu test eder."""
    assert get_instruction_info("ADDX") is None
    assert get_instruction_info("MUL") is None


def test_register_numaralari():
    """Register isimlerinin dogru numaralara eslendigini test eder."""
    assert get_register_number("x0") == 0
    assert get_register_number("x31") == 31
    assert get_register_number("zero") == 0
    assert get_register_number("ra") == 1
    assert get_register_number("sp") == 2
    assert get_register_number("t0") == 5
    assert get_register_number("a0") == 10
    assert get_register_number("s0") == 8
    assert get_register_number("fp") == 8  # fp = s0


def test_gecersiz_register():
    """Gecersiz register ismi icin None donuldugunu test eder."""
    assert get_register_number("x32") is None
    assert get_register_number("abc") is None
