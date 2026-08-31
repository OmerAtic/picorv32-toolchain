# ============================================================
# main.s - Multi-file linker demosu (ana program)
# ============================================================
# math_lib.s'in 3 fonksiyonu ve 2 veri sembolunu cagirir:
#   add_func(15, 7)  -> 22
#   sub_func(15, 7)  -> 8
#   mul_func(7, 6)   -> 42
#   pi_x100          -> 314
#   magic_number     -> 0xDEADBEEF
#
# Sonuclari sirayla GPIO'ya yazar.
# ============================================================

.section .text
.global _start

# Math kutuphanesinden ihtiyac duydugumuz semboller
.extern add_func
.extern sub_func
.extern mul_func
.extern pi_x100
.extern magic_number

_start:
    li      sp, 0x1FF0
    li      s0, 0x10000000      # GPIO_OUT

    # ---- 1) add_func(15, 7) = 22 ----
    li      a0, 15
    li      a1, 7
    call    add_func
    sw      a0, 0(s0)

    # ---- 2) sub_func(15, 7) = 8 ----
    li      a0, 15
    li      a1, 7
    call    sub_func
    sw      a0, 0(s0)

    # ---- 3) mul_func(7, 6) = 42 ----
    li      a0, 7
    li      a1, 6
    call    mul_func
    sw      a0, 0(s0)

    # ---- 4) pi_x100 (.data sembolu) = 314 ----
    la      t0, pi_x100
    lw      a0, 0(t0)
    sw      a0, 0(s0)

    # ---- 5) magic_number (.data sembolu) = 0xDEADBEEF ----
    la      t0, magic_number
    lw      a0, 0(t0)
    sw      a0, 0(s0)

    # ---- Simulator'a "bittim" sinyali ----
    li      t0, 0x10000008
    li      a0, 1
    sw      a0, 0(t0)

# Sonsuz dongu (CPU'yu durdur)
hang:
    j       hang
