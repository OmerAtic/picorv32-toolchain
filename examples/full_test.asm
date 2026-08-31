# ============================================
# full_test.asm - Tum Komut Formatlarini Test
# Her RV32I formati icin en az bir ornek
# ============================================

.text

# --- R-Type (10 komut) ---
        ADD  x1, x2, x3
        SUB  x4, x5, x6
        AND  x7, x8, x9
        OR   x10, x11, x12
        XOR  x13, x14, x15
        SLL  x16, x17, x18
        SRL  x19, x20, x21
        SRA  x22, x23, x24
        SLT  x25, x26, x27
        SLTU x28, x29, x30

# --- I-Type (immediate) ---
        ADDI  x1, x0, 42
        SLTI  x2, x1, 100
        XORI  x3, x1, 0xFF
        ORI   x4, x0, 0x0A
        ANDI  x5, x1, 0x0F

# --- I-Type (load) ---
        LW   x6, 0(x1)
        LH   x7, 4(x1)
        LB   x8, 8(x1)

# --- I-Type (JALR) ---
        JALR x0, x1, 0

# --- S-Type (store) ---
        SW   x1, 0(x2)
        SH   x3, 4(x2)
        SB   x4, 8(x2)

# --- B-Type (branch) ---
loop:   BEQ  x1, x2, done
        BNE  x1, x0, loop
        BLT  x3, x4, done
        BGE  x5, x6, loop
        BLTU x7, x8, done
        BGEU x9, x10, loop

# --- U-Type ---
        LUI   x11, 0xABCDE
        AUIPC x12, 0x00010

# --- J-Type ---
        JAL  x1, loop

done:   ADDI x0, x0, 0
