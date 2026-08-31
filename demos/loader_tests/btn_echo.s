# btn_echo.s - BTN_IN'i dogrudan LED'e yazar (SoC buton yolu izole testi)
.section .text
.global _start
_start:
    li      sp, 0x1FF0
    li      s0, 0x10000000      # GPIO_OUT (LED)
    li      s1, 0x1000000C      # BTN_IN
loop:
    lw      a0, 0(s1)           # butonu oku
    sw      a0, 0(s0)           # dogrudan LED'e yaz (bit0 -> LED0)
    j       loop
