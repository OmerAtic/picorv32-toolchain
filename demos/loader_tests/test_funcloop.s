# test_funcloop.s - Fonksiyonu DONGUDE tekrar cagirir (gorsel fonksiyon demosu)
# Her adimda add_func(toplam,5) cagrilir -> LED 5,10,15,20,... diye sayar.
# Boylece her LED artisi = bir jal/ret fonksiyon cagrisi.
.section .text
.global _start
_start:
    li      sp, 0x1FF0
    li      s0, 0x10000000      # GPIO_OUT (LED)
    li      s1, 0               # toplam = 0
loop:
    mv      a0, s1              # a0 = toplam
    li      a1, 5               # a1 = 5
    jal     ra, add_func        # a0 = topla(toplam, 5)  <-- FONKSIYON CAGRISI
    mv      s1, a0              # toplam = a0
    andi    a0, a0, 0x3F        # alt 6 bit
    sw      a0, 0(s0)           # LED'e goster

    li      a1, 500000          # gecikme (gozle gorunur)
d:  addi    a1, a1, -1
    bnez    a1, d
    j       loop
# --- alt program: a0 = a0 + a1 ---
add_func:
    add     a0, a0, a1
    ret
