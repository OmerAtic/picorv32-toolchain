# ============================================================
# test3_func_btn.s - TEST 3: Fonksiyon cagrisi + buton girisi
# ============================================================
# Amac: FPGA'daki S2 butonunu okur.
#   - Buton basili ise: 'topla' alt programini cagirir (10+5=15)
#     ve sonucu LED'lerde gosterir.
#   - Buton basili degilse: LED'lerde 3 gosterir.
#
# Zorluk: fonksiyon cagrisi (jal/ret, ra register'i) + bellek
#         haritali giris (buton) okuma + kosullu dallanma.
# Memory map:
#   GPIO_OUT (LED) = 0x1000_0000
#   BTN_IN         = 0x1000_000C   (bit0 = S2 butonu, basili=1)
# ============================================================

.section .text
.global _start

_start:
    li      sp, 0x1FF0
    li      s0, 0x10000000      # GPIO_OUT (LED)
    li      s1, 0x1000000C      # BTN_IN adresi

main_loop:
    lw      a0, 0(s1)           # buton durumunu oku
    andi    a0, a0, 1           # sadece bit0
    beqz    a0, button_off      # buton basili degil mi?

    # --- buton basili: topla fonksiyonunu cagir ---
    li      a0, 10
    li      a1, 5
    jal     ra, add_func        # a0 = topla(a0, a1) = 15
    j       show

button_off:
    li      a0, 3               # buton bos -> 3 goster

show:
    andi    a0, a0, 0x3F
    sw      a0, 0(s0)           # LED'lere yaz
    j       main_loop

# --- alt program: iki sayiyi toplar (a0 = a0 + a1) ---
add_func:
    add     a0, a0, a1
    ret                         # ra'ya don
