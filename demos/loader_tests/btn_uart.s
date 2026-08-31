# btn_uart.s - BTN_IN'i surekli UART'a basar (seri porttan dogrulanir)
# Buton bosta '0', basili '1' gonderir. Loop'un kostugunu da kanitlar.
.section .text
.global _start
_start:
    li      sp, 0x1FF0
    li      s0, 0x10000004      # UART_TX
    li      s1, 0x1000000C      # BTN_IN
loop:
    lw      a0, 0(s1)           # butonu oku
    andi    a0, a0, 1           # bit0
    addi    a0, a0, 0x30        # '0' veya '1' ASCII
    sw      a0, 0(s0)           # UART'a yaz
    li      t0, 150000          # gecikme (UART baytI bitsin + akisi yavaslat)
d:  addi    t0, t0, -1
    bnez    t0, d
    j       loop
