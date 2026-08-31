# ============================================
# branch_test.asm - Dongu ve Branch Ornegi
# 1'den 10'a kadar toplama yapan program
# ============================================

.text

        ADDI x1, x0, 0        # x1 = toplam = 0
        ADDI x2, x0, 1        # x2 = sayac = 1
        ADDI x3, x0, 11       # x3 = sinir = 11

loop:   ADD  x1, x1, x2       # toplam += sayac
        ADDI x2, x2, 1        # sayac++
        BLT  x2, x3, loop     # sayac < 11 ise donguye don

        # Sonuc: x1 = 1+2+3+...+10 = 55
done:   ADDI x0, x0, 0        # NOP - program sonu
