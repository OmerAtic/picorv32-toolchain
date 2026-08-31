# ============================================================
# led_counter.s - GPIO uzerinden 8-bit sayac (LED demo)
# ============================================================
# PicoRV32'de calisir, GPIO'ya 0,1,2,3,... yazar (8-bit, 256'da overflow).
# Her artisi arasinda kucuk bir gecikme dongusu vardir.
# FPGA'da bu LED'lerde gozle gorulur titremeye dusurmek icin
# delay sayisi kullanilan board'un saatine gore artirilabilir.
#
# Memory map:
#   0x1000_0000 -> GPIO_OUT (write)
# ============================================================

.section .text
.global _start

_start:
    # Stack pointer: BRAM'in sonu - kucuk bir tampon
    li      sp, 0x1FF0

    # GPIO base
    li      s0, 0x10000000

    # Sayac
    li      s1, 0

main_loop:
    andi    a0, s1, 0xFF        # 8-bit maskele
    sw      a0, 0(s0)           # GPIO_OUT'a yaz

    # Delay
    li      a1, 50000
delay_loop:
    addi    a1, a1, -1
    bnez    a1, delay_loop

    addi    s1, s1, 1
    j       main_loop
