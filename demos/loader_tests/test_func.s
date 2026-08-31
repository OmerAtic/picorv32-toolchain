# test_func.s - Fonksiyon cagrisini KARTTA net gosterir (butona ihtiyac yok)
# add_func(10,5)=15 -> 15 = 0b001111 -> LED0,1,2,3 yanar (4 LED yan yana)
.section .text
.global _start
_start:
    li      sp, 0x1FF0
    li      s0, 0x10000000      # GPIO_OUT (LED)
    li      a0, 10
    li      a1, 5
    jal     ra, add_func        # ra'ya don; a0 = topla(10,5) = 15
    andi    a0, a0, 0x3F
    sw      a0, 0(s0)           # LED'lere yaz (4 LED)
hold:
    j       hold
# --- alt program: a0 = a0 + a1 ---
add_func:
    add     a0, a0, a1
    ret                         # jalr x0, 0(ra)
