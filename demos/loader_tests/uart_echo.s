# uart_echo.s - PC'den UART ile gelen baytI okur, geri echo'lar + LED'e yazar
# GIRIS testi: FPGA'nin UART girisini kullanir (hocanin 'giris' sarti).
# Memory map: UART_TX=0x10000004, RX_DATA=0x10000010, RX_READY=0x10000014, GPIO=0x10000000
.section .text
.global _start
_start:
    li      sp, 0x1FF0
    li      s0, 0x10000004      # UART_TX
    li      s1, 0x10000010      # UART_RX_DATA
    li      s2, 0x10000014      # UART_RX_READY
    li      s3, 0x10000000      # GPIO (LED)
wait_byte:
    lw      a0, 0(s2)           # ready?
    andi    a0, a0, 1
    beqz    a0, wait_byte       # veri yoksa bekle
    lw      a0, 0(s1)           # gelen baytI oku
    sw      a0, 0(s0)           # UART'a echo
    sw      a0, 0(s3)           # LED'e yaz (alt 6 bit)
    j       wait_byte
