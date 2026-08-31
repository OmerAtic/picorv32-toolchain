# ============================================================
# test4_uart.s - TEST 4: UART'a string yazar (seri porttan dogrulama)
# ============================================================
# Amac: Loader ile yuklenip calisinca UART_TX'ten "LOADER-OK 42\n"
# yazar. Boylece sonuc, LED'e bakmadan PC'de seri porttan dogrulanabilir
# (host_send.py RUN sonrasi bu ciktiyi yazdirir).
#
# Zorluk: .data section + string + la (adres yukleme) + alt program (putc).
# Memory map: UART_TX = 0x1000_0004
# ============================================================

.section .data
msg:    .string "LOADER-OK 42\n"

.section .text
.global _start

_start:
    li      sp, 0x1FF0
    li      s0, 0x10000004      # UART_TX adresi
    la      s1, msg             # string baslangic adresi

print_loop:
    lb      a0, 0(s1)           # siradaki baytI oku
    beqz    a0, done            # 0 (string sonu) ise bitir
    jal     ra, putc            # baytI UART'a bas
    addi    s1, s1, 1           # sonraki bayt
    j       print_loop

done:
    j       done                # burada kal

# --- putc: a0'daki baytI UART'a yazar, sonra UART baytI bitene kadar bekler ---
putc:
    sw      a0, 0(s0)           # UART_TX'e yaz
    li      t0, 8000            # gecikme (1 UART baytI ~2340 cycle @27MHz)
putc_wait:
    addi    t0, t0, -1
    bnez    t0, putc_wait
    ret
