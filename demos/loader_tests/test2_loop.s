# ============================================================
# test2_loop.s - TEST 2: Dongu / sayac -> LED
# ============================================================
# Amac: 0,1,2,... diye artan bir sayaci LED'lerde gosterir.
# Her adimda bir gecikme dongusu vardir; FPGA'da LED'ler
# gozle gorulur sekilde sayar (ikili sayac).
#
# Zorluk: dongu (loop) + dallanma (branch) + gecikme.
# Memory map: GPIO_OUT (LED) = 0x1000_0000
# ============================================================

.section .text
.global _start

_start:
    li      sp, 0x1FF0
    li      s0, 0x10000000      # GPIO_OUT (LED)
    li      s1, 0               # sayac = 0

count_loop:
    andi    a0, s1, 0x3F        # alt 6 bit (6 LED)
    sw      a0, 0(s0)           # LED'lere yaz

    li      a1, 300000          # gecikme miktari (27 MHz icin gozle gorunur)
delay:
    addi    a1, a1, -1
    bnez    a1, delay

    addi    s1, s1, 1           # sayaci arttir
    j       count_loop
