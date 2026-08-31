# ============================================================
# error_handler.py - Hata Yonetim Modulu
# ============================================================
# Assembler surecinde olusan hatalari toplar ve raporlar.
# Tum diger moduller bu modulu kullanarak hata bildirir.
# Veri yapisi: liste (append O(1))
# ============================================================


class ErrorHandler:
    """Assembler hatalarini toplayan ve raporlayan sinif."""

    def __init__(self):
        # Hatalari saklayan liste
        # Her eleman: {"line": int, "type": str, "message": str}
        self.errors = []

    def add_error(self, line_number, error_type, message):
        """Hata listesine yeni bir hata ekler.

        Args:
            line_number: Hatanin olustugu satir numarasi
            error_type: Hata turu ("syntax", "semantic", "encoding", "directive")
            message: Hatanin aciklamasi
        """
        self.errors.append({
            "line": line_number,
            "type": error_type,
            "message": message
        })

    def has_errors(self):
        """Hata var mi kontrol eder."""
        return len(self.errors) > 0

    def get_errors(self):
        """Tum hatalari dondurur."""
        return self.errors

    def print_errors(self):
        """Hatalari ekrana yazdirir (sunum/demo icin)."""
        if not self.errors:
            print("Hata bulunamadi.")
            return

        print(f"\n{'='*50}")
        print(f"  HATALAR ({len(self.errors)} adet)")
        print(f"{'='*50}")
        for error in self.errors:
            print(f"  Satir {error['line']:>4} | [{error['type']}] {error['message']}")
        print(f"{'='*50}\n")

    def clear(self):
        """Hata listesini temizler (yeniden calistirma icin)."""
        self.errors = []
