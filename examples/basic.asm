# ============================================
# basic.asm - Temel RV32I Komut Ornekleri
# PicoRV32 Assembler Test Dosyasi
# ============================================

.text

# R-Type ornekleri (register-register)
start:  ADD  x1, x2, x3       # x1 = x2 + x3
        SUB  x4, x5, x6       # x4 = x5 - x6
        AND  x7, x8, x9       # x7 = x8 & x9
        OR   x10, x11, x12    # x10 = x11 | x12
        XOR  x13, x14, x15    # x13 = x14 ^ x15
        SLT  x16, x17, x18    # x16 = (x17 < x18) ? 1 : 0

# I-Type ornekleri (immediate)
        ADDI x1, x0, 100      # x1 = 0 + 100 = 100
        ADDI x2, x1, -50      # x2 = 100 + (-50) = 50
        ANDI x3, x1, 0xFF     # x3 = x1 & 255
        ORI  x4, x0, 0x0A     # x4 = 0 | 10

# Load/Store ornekleri
        LW   x5, 0(x1)        # x5 = bellek[x1 + 0]
        SW   x5, 4(x1)        # bellek[x1 + 4] = x5
        LB   x6, 0(x2)        # x6 = bellek[x2] (1 byte)
        SB   x6, 1(x2)        # bellek[x2 + 1] = x6 (1 byte)

# Branch ornekleri (kosullu dallanma)
        BEQ  x1, x2, end      # x1 == x2 ise end'e git
        BNE  x1, x0, start    # x1 != 0 ise start'a git

# U-Type ornekleri
        LUI  x7, 0x12345      # x7 = 0x12345 << 12
        AUIPC x8, 0x00001     # x8 = PC + (1 << 12)

# J-Type ornekleri
        JAL  x1, start        # x1 = PC+4, start'a atla

end:    ADDI x0, x0, 0        # NOP - program sonu
