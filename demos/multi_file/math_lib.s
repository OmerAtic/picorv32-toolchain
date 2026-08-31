# ============================================================
# math_lib.s - Demo math kutuphanesi
# ============================================================
# 3 fonksiyon expose eder: add_func, sub_func, mul_func
# 2 veri sembolu expose eder: pi_x100, magic_number
#
# PicoRV32'de MUL kapali oldugu icin yazilim carpma kullanilir
# (mul_func bir for-loop ile kumulatif toplama yapar).
# ============================================================

.section .text
.global add_func
.global sub_func
.global mul_func

# ----------------------------------
# add_func(a0, a1) -> a0 + a1
# ----------------------------------
add_func:
    add     a0, a0, a1
    ret

# ----------------------------------
# sub_func(a0, a1) -> a0 - a1
# ----------------------------------
sub_func:
    sub     a0, a0, a1
    ret

# ----------------------------------
# mul_func(a0, a1) -> a0 * a1   (yazilim carpma)
# Algoritma: a1 kez a0'i kendine ekle.
# Negatif degerleri desteklemiyoruz (basit demo).
# ----------------------------------
mul_func:
    addi    t0, x0, 0           # sonuc = 0
    addi    t1, a1, 0           # sayac = a1
    beqz    t1, mul_done        # a1 == 0 ise donus
mul_loop:
    add     t0, t0, a0
    addi    t1, t1, -1
    bnez    t1, mul_loop
mul_done:
    addi    a0, t0, 0
    ret

# ============================================================
# Veri bolumu (.data) - global semboller
# ============================================================
.section .data
.global pi_x100
.global magic_number

pi_x100:
    .word   314

magic_number:
    .word   0xDEADBEEF
