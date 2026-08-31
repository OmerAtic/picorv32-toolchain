# ============================================================
# symbol_table.py - Sembol Tablosu
# ============================================================
# Label (etiket) isimlerini adreslerle eslestirir.
# Pass 1'de doldurulur, Pass 2'de kullanilir.
# Veri yapisi: dict (hash table) -> O(1) insert ve lookup
# ============================================================


class SymbolTable:
    """Label-adres eslestirmesini yoneten sinif."""

    def __init__(self):
        # Sembol tablosu: {"label_adi": adres_degeri}
        self.symbols = {}

    def add_symbol(self, name, address):
        """Sembol tablosuna yeni bir label ekler.

        Args:
            name: Label adi (ornek: "loop", "start")
            address: Label'in bellekteki adresi (int)

        Returns:
            True: basariyla eklendi
            False: label zaten tanimli (duplicate)
        """
        if name in self.symbols:
            return False  # Duplicate label hatasi
        self.symbols[name] = address
        return True

    def get_address(self, name):
        """Label'in adresini dondurur.

        Bulunamazsa None dondurur (undefined symbol).
        """
        return self.symbols.get(name)

    def has_symbol(self, name):
        """Label tanimli mi kontrol eder."""
        return name in self.symbols

    def get_all_symbols(self):
        """Tum sembolleri dondurur (JSON ciktisi icin)."""
        return dict(self.symbols)

    def print_table(self):
        """Sembol tablosunu ekrana yazdirir (sunum/demo icin)."""
        print(f"\n{'='*40}")
        print(f"  SEMBOL TABLOSU ({len(self.symbols)} adet)")
        print(f"{'='*40}")
        print(f"  {'Label':<20} {'Adres':<15} {'Hex'}")
        print(f"  {'-'*20} {'-'*15} {'-'*10}")
        for name, address in self.symbols.items():
            print(f"  {name:<20} {address:<15} 0x{address:08X}")
        print(f"{'='*40}\n")
