# ============================================================
# main.s - UART "Hello, FPGA from PicoRV32!" demosu
# ============================================================
# uart_lib.s'in 3 fonksiyonunu cagirarak ekrana
# bir karsilama mesaji ve hex sayi yazar.
#
# Beklenen UART cikti:
#   Hello, FPGA from PicoRV32!
#   counter = 0xdeadbeef
# ============================================================

.section .text
.global _start
.extern uart_putc
.extern uart_puts
.extern uart_put_hex32

_start:
    li      sp, 0x1FF0

    # 1) Greeting yaz
    la      a0, greeting
    call    uart_puts

    # 2) "counter = 0x" yaz
    la      a0, counter_label
    call    uart_puts

    # 3) Hex deger
    la      a0, magic
    lw      a0, 0(a0)
    call    uart_put_hex32

    # 4) Newline
    li      a0, 0x0A
    call    uart_putc

    # 5) Sim done sinyali
    li      t0, 0x10000008
    li      a0, 1
    sw      a0, 0(t0)

hang:
    j       hang

# ============================================================
# Veri bolumu
# ============================================================
.section .data

greeting:
    .string "Hello, FPGA from PicoRV32!\n"

counter_label:
    .string "counter = 0x"

.align 4                # .word'ten once 4-byte hizalama gerekli
magic:
    .word   0xDEADBEEF
