# ============================================================
# test1_math.s - TEST 1: Basit matematik -> LED
# ============================================================
# Amac: Loader ile yuklenip FPGA'de calisinca, birkac aritmetik
# islem yapip sonucu LED'lerde gosterir.
#   (15 + 7) = 22 ; 22 << 1 = 44 ; 44 - 2 = 42
# Sonuc 42 = 0b101010 -> LED'lerde bir-atla desen gorunur.
#
# Memory map: GPIO_OUT (LED) = 0x1000_0000
# ============================================================

.section .text
.global _start

_start:
    li      sp, 0x1FF0          # stack pointer
    li      s0, 0x10000000      # GPIO_OUT (LED) adresi

    li      t0, 15              # ilk sayi
    li      t1, 7               # ikinci sayi
    add     t2, t0, t1          # t2 = 22
    slli    t2, t2, 1           # t2 = 44
    addi    t2, t2, -2          # t2 = 42
    andi    a0, t2, 0x3F        # alt 6 bit (6 LED)

    sw      a0, 0(s0)           # sonucu LED'lere yaz

hold:
    j       hold                # burada kal (sonuc LED'de sabit)
