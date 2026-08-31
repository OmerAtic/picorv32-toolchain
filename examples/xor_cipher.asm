# ============================================
# xor_cipher.asm - XOR Sifreleme Senaryosu
# ============================================
# Bellekteki veriyi bir anahtar ile XOR'layarak
# sifreler ve sonucu bellege geri yazar.
#
# Algoritma:
#   for i = 0 to 3:
#       data[i] = data[i] XOR key
#
# Bu senaryo su komutlari test eder:
#   - LW/SW (bellek okuma/yazma)
#   - XOR (mantiksal islem)
#   - ADDI (sayac artirma, adres hesabi)
#   - BLT (kosullu dallanma, dongu)
#   - Label ve forward reference
# ============================================

.text

# --- Baslangic degerleri ---
        ADDI x0, x10, x0       # x10 = veri baslangic adresi (0x100)
        ADDI x10, x10, 256    # x10 = 0x100 (256)
        ADDI x11, x0, 0x4B    # x11 = sifreleme anahtari (0x4B = 75)
        ADDI x12, x0, 0       # x12 = sayac (i = 0)
        ADDI x13, x0, 4       # x13 = veri uzunlugu (4 word)

# --- Sifreleme dongusu ---
loop:   LW   x14, 0(x10)      # x14 = bellekten veri oku
        XOR  x14, x14, x11    # x14 = veri XOR anahtar (sifreleme)
        SW   x14, 0(x10)      # sifreli veriyi bellege yaz
        ADDI x10, x10, 4      # sonraki adrese gec (+4 byte)
        ADDI x12, x12, 1      # sayac++
        BLT  x12, x13, loop   # sayac < 4 ise donguye don

# --- Program sonu ---
done:   ADDI x0, x0, 0        # NOP
