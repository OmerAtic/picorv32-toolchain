# ============================================
# error_test.asm - Hata Ayiklama Testi
# ============================================
# Bilerek hatali yazilmis assembly kodu.
# Assembler'in hatalari yakalayip yakalmadigini test eder.
# ============================================

.text

# Dogru komut (karsilastirma icin)
        ADDI x1, x0, 10

# HATA 1: Bilinmeyen komut
        ADDX x1, x2, x3

# HATA 2: Gecersiz register adi
        ADD x1, x50, x3

# HATA 3: Eksik operand
        ADD x1, x2

# HATA 4: Tanimlanmamis label
        BEQ x1, x2, yok_label

# HATA 5: Immediate sinir asimi (12-bit max: 2047)
        ADDI x1, x0, 5000

# HATA 6: Gecersiz bellek formati
        LW x1, x2

# Dogru komut (hata sonrasi da devam ettigini gostermek icin)
done:   ADDI x0, x0, 0
