# test_symbol.py - Symbol Table Testleri

from tables.symbol_table import SymbolTable


def test_sembol_ekleme():
    """Label'in symbol table'a dogru eklenmesini test eder."""
    st = SymbolTable()
    assert st.add_symbol("start", 0x00000000) == True
    assert st.add_symbol("loop", 0x0000000C) == True


def test_sembol_sorgulama():
    """Label adresinin dogru dondugunu test eder."""
    st = SymbolTable()
    st.add_symbol("start", 0)
    st.add_symbol("end", 100)
    assert st.get_address("start") == 0
    assert st.get_address("end") == 100


def test_duplicate_label():
    """Ayni label'in iki kez eklenmesinin reddedildigini test eder."""
    st = SymbolTable()
    assert st.add_symbol("loop", 0x10) == True
    assert st.add_symbol("loop", 0x20) == False  # Duplicate!


def test_tanimlanmamis_label():
    """Olmayan label sorgulandiginda None dondugunu test eder."""
    st = SymbolTable()
    assert st.get_address("yok") is None


def test_has_symbol():
    """has_symbol fonksiyonunun dogru calistigini test eder."""
    st = SymbolTable()
    st.add_symbol("test", 0x40)
    assert st.has_symbol("test") == True
    assert st.has_symbol("yok") == False


def test_get_all_symbols():
    """Tum sembollerin dict olarak dondugunu test eder."""
    st = SymbolTable()
    st.add_symbol("a", 0)
    st.add_symbol("b", 4)
    symbols = st.get_all_symbols()
    assert symbols == {"a": 0, "b": 4}
