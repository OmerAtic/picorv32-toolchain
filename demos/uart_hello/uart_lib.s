# ============================================================
# uart_lib.s - Basit UART yardimci kutuphanesi
# ============================================================
# Memory map:
#   0x1000_0004 -> UART_TX (write byte)
#
# Disa actigi semboller:
#   uart_putc(c)        - tek karakteri UART'a yazar
#   uart_puts(ptr)      - null-terminator'a kadar string yazar
#   uart_put_hex32(val) - 32-bit degeri 8 hex karakter olarak yazar
# ============================================================

.section .text
.global uart_putc
.global uart_puts
.global uart_put_hex32

# ----------------------------------
# uart_putc(a0=char) -> void
# ----------------------------------
uart_putc:
    li      t0, 0x10000004      # UART base
    sw      a0, 0(t0)
    ret

# ----------------------------------
# uart_puts(a0=ptr) -> void
# Null-terminator'a kadar yazar.
# ----------------------------------
uart_puts:
    addi    sp, sp, -16
    sw      ra, 12(sp)
    sw      s0, 8(sp)
    sw      s1, 4(sp)

    addi    s0, a0, 0           # ptr
    li      s1, 0x10000004      # UART base

puts_loop:
    lb      t0, 0(s0)           # *ptr
    beqz    t0, puts_done
    sw      t0, 0(s1)           # UART_TX
    addi    s0, s0, 1
    j       puts_loop

puts_done:
    lw      ra, 12(sp)
    lw      s0, 8(sp)
    lw      s1, 4(sp)
    addi    sp, sp, 16
    ret

# ----------------------------------
# uart_put_hex32(a0=val) -> void
# 8 hex karakter (kucuk harf) yazar.
# ----------------------------------
uart_put_hex32:
    addi    sp, sp, -16
    sw      ra, 12(sp)
    sw      s0, 8(sp)
    sw      s1, 4(sp)
    sw      s2, 0(sp)

    addi    s0, a0, 0           # val
    li      s1, 0x10000004      # UART base
    li      s2, 8                # kalan nibble sayisi

hex_loop:
    addi    s2, s2, -1
    # Mevcut nibble: bit (s2*4) konumundan al
    # SLL/SRL kullanmak yerine basit shift dongusu (kac kez 4)
    addi    t1, s0, 0           # t1 = val
    addi    t2, s2, 0           # t2 = sayi
shift_loop:
    beqz    t2, shift_done
    srli    t1, t1, 4
    addi    t2, t2, -1
    j       shift_loop
shift_done:
    andi    t1, t1, 0xF         # nibble

    # Hex karaktere cevir: <10 ise '0'+n, degilse 'a'+n-10
    li      t3, 10
    blt     t1, t3, is_digit
    addi    t1, t1, -10
    addi    t1, t1, 0x61        # 'a'
    j       emit_char
is_digit:
    addi    t1, t1, 0x30        # '0'
emit_char:
    sw      t1, 0(s1)           # UART_TX

    bnez    s2, hex_loop

    lw      ra, 12(sp)
    lw      s0, 8(sp)
    lw      s1, 4(sp)
    lw      s2, 0(sp)
    addi    sp, sp, 16
    ret
