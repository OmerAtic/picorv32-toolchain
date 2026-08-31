# test_parser.py - Parser ve Lexer Testleri

from assembler.lexer import tokenize_line, tokenize_file
from assembler.parser import classify_line, parse_immediate, parse_memory_operand


def test_basit_satir_tokenize():
    """Basit bir instruction satirinin dogru tokenize edildigini test eder."""
    token = tokenize_line("ADD x1, x2, x3", 1)
    assert token["mnemonic"] == "ADD"
    assert token["operands"] == ["x1", "x2", "x3"]
    assert token["label"] is None


def test_label_ile_tokenize():
    """Label iceren satirin dogru parcalandigini test eder."""
    token = tokenize_line("loop: ADD x1, x2, x3", 5)
    assert token["label"] == "loop"
    assert token["mnemonic"] == "ADD"
    assert token["operands"] == ["x1", "x2", "x3"]


def test_sadece_label():
    """Sadece label olan satirin dogru islendigini test eder."""
    token = tokenize_line("start:", 1)
    assert token["label"] == "start"
    assert token["mnemonic"] is None


def test_yorum_temizleme():
    """Yorumlu satirin dogru temizlendigini test eder."""
    token = tokenize_line("ADDI x1, x0, 10  # sayi yukle", 1)
    assert token["mnemonic"] == "ADDI"
    assert token["operands"] == ["x1", "x0", "10"]


def test_bos_satir():
    """Bos satirin None dondugunu test eder."""
    assert tokenize_line("", 1) is None
    assert tokenize_line("   ", 1) is None
    assert tokenize_line("# sadece yorum", 1) is None


def test_satir_siniflandirma():
    """classify_line fonksiyonunun satir turlerini dogru belirlemesini test eder."""
    token_inst = {"mnemonic": "ADD", "operands": ["x1", "x2", "x3"], "label": None, "line_num": 1}
    assert classify_line(token_inst) == "instruction"

    token_dir = {"mnemonic": ".text", "operands": [], "label": None, "line_num": 1}
    assert classify_line(token_dir) == "directive"

    token_label = {"mnemonic": None, "operands": [], "label": "start", "line_num": 1}
    assert classify_line(token_label) == "label_only"


def test_immediate_parse():
    """Farkli sayi formatlarinin dogru parse edildigini test eder."""
    assert parse_immediate("100") == 100
    assert parse_immediate("-50") == -50
    assert parse_immediate("0xFF") == 255
    assert parse_immediate("0b1010") == 10
    assert parse_immediate("abc") is None  # Gecersiz


def test_memory_operand_parse():
    """S-Type ve Load formatinin dogru parcalandigini test eder."""
    result = parse_memory_operand("0(x2)")
    assert result["offset"] == 0
    assert result["register"] == "x2"

    result = parse_memory_operand("-4(sp)")
    assert result["offset"] == -4
    assert result["register"] == "sp"

    result = parse_memory_operand("4(x1)")
    assert result["offset"] == 4
    assert result["register"] == "x1"


def test_gecersiz_memory_operand():
    """Gecersiz bellek formati icin None dondugunu test eder."""
    assert parse_memory_operand("x1") is None
    assert parse_memory_operand("100") is None
