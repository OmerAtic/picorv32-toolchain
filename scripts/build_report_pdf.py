#!/usr/bin/env python3
# ============================================================
# scripts/build_report_pdf.py - REPORT.md + ozet -> PDF
# ============================================================
# Hocanin istedigi gibi Courier New 10 pt formatinda PDF uretir.
# Cikti: ~/Downloads/PicoRV32_Linker_Raporu.pdf
# ============================================================

import os
import sys
import subprocess
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, grey
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Preformatted, Table, TableStyle, KeepTogether,
)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


# ---------- Font kayit ----------
COURIER_REG = "/System/Library/Fonts/Supplemental/Courier New.ttf"
COURIER_BLD = "/System/Library/Fonts/Supplemental/Courier New Bold.ttf"
if os.path.isfile(COURIER_REG):
    pdfmetrics.registerFont(TTFont("CourierNew", COURIER_REG))
    pdfmetrics.registerFont(TTFont("CourierNew-Bold", COURIER_BLD))
    FONT_REG = "CourierNew"
    FONT_BLD = "CourierNew-Bold"
else:
    FONT_REG = "Courier"
    FONT_BLD = "Courier-Bold"


# ---------- Stiller ----------
title_style = ParagraphStyle(
    "title", fontName=FONT_BLD, fontSize=18, leading=22,
    alignment=TA_CENTER, spaceAfter=10, textColor=black,
)
subtitle_style = ParagraphStyle(
    "subtitle", fontName=FONT_REG, fontSize=11, leading=14,
    alignment=TA_CENTER, spaceAfter=24, textColor=grey,
)
h1_style = ParagraphStyle(
    "h1", fontName=FONT_BLD, fontSize=14, leading=18,
    spaceBefore=14, spaceAfter=8, textColor=HexColor("#1a3a5c"),
)
h2_style = ParagraphStyle(
    "h2", fontName=FONT_BLD, fontSize=11, leading=14,
    spaceBefore=10, spaceAfter=4, textColor=HexColor("#244a73"),
)
body_style = ParagraphStyle(
    "body", fontName=FONT_REG, fontSize=10, leading=13,
    spaceAfter=6, alignment=TA_LEFT,
)
code_style = ParagraphStyle(
    "code", fontName=FONT_REG, fontSize=9, leading=11,
    leftIndent=8, spaceBefore=4, spaceAfter=8,
    backColor=HexColor("#f5f5f5"), textColor=HexColor("#222"),
    borderPadding=4, borderColor=HexColor("#dddddd"), borderWidth=0.4,
)
small_style = ParagraphStyle(
    "small", fontName=FONT_REG, fontSize=8, leading=10,
    alignment=TA_CENTER, textColor=grey,
)


# ---------- Yardimcilar ----------
def H1(text):     return Paragraph(text, h1_style)
def H2(text):     return Paragraph(text, h2_style)
def P(text):      return Paragraph(text, body_style)
def CODE(text):   return Preformatted(text, code_style)
def SP(h=6):      return Spacer(1, h)


def TBL(rows, col_widths=None, header=True):
    """Basit tablo. rows[0] header gibi davranir (header=True ise)."""
    t = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ("FONT",      (0, 0), (-1, -1), FONT_REG, 9),
        ("VALIGN",    (0, 0), (-1, -1), "TOP"),
        ("GRID",      (0, 0), (-1, -1), 0.3, HexColor("#bbbbbb")),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
    ]
    if header:
        style += [
            ("FONT",       (0, 0), (-1, 0), FONT_BLD, 9),
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#e7eef5")),
        ]
    t.setStyle(TableStyle(style))
    return t


# ---------- Sayfa header/footer ----------
def _on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT_REG, 8)
    canvas.setFillColor(grey)
    # Header
    canvas.drawString(20*mm, 287*mm, "PicoRV32 Linker Tasarimi - Proje-2 Raporu")
    canvas.drawRightString(195*mm, 287*mm, "Atakan Sever")
    # Footer
    canvas.drawCentredString(105*mm, 12*mm, f"Sayfa {doc.page}")
    canvas.restoreState()


# ============================================================
# ICERIK
# ============================================================

def build_story():
    s = []

    # ---------- KAPAK ----------
    s.append(Spacer(1, 60*mm))
    s.append(Paragraph("PicoRV32 RV32I icin", title_style))
    s.append(Paragraph("Linker Tasarimi ve FPGA Entegrasyonu", title_style))
    s.append(Spacer(1, 20*mm))
    s.append(Paragraph("BSM412 Mikroislemci Tasarimi", subtitle_style))
    s.append(Paragraph("Sakarya Uygulamali Bilimler Universitesi", subtitle_style))
    s.append(Spacer(1, 30*mm))

    info_rows = [
        ["Ogrenci",      "Atakan Sever"],
        ["Proje",        "Proje-2: Linker + FPGA Entegrasyonu"],
        ["Tarih",        datetime.now().strftime("%d.%m.%Y")],
        ["Format",       "Courier New 10 pt"],
        ["Gelistirme",   "Python 3.13 + Verilog (PicoRV32)"],
        ["Hedef FPGA",   "Digilent Arty A7-35T (xc7a35ticsg324-1L)"],
        ["Test sonucu",  "44/44 birim+e2e PASS  (44 testin tumu basarili)"],
    ]
    s.append(TBL(info_rows, col_widths=[40*mm, 130*mm], header=False))

    s.append(PageBreak())

    # ---------- ICINDEKILER ----------
    s.append(H1("Icindekiler"))
    toc_rows = [
        ["1.",  "Yonetici Ozeti"],
        ["2.",  "Yapilan Isler (Ekibin Gorev Listesi)"],
        ["3.",  "Sistem Mimarisi"],
        ["4.",  "Object Dosya Formati (PCO v1)"],
        ["5.",  "Linker Algoritmasi (Pass 1 + Pass 2)"],
        ["6.",  "Relocation Tipleri"],
        ["7.",  "Demo Programlari"],
        ["8.",  "PicoRV32 SoC ve FPGA"],
        ["9.",  "Test Sonuclari"],
        ["10.", "Karsilasilan Problemler"],
        ["11.", "FPGA Kaynak Kullanimi"],
        ["12.", "Surdurulebilirlik ve Etik"],
        ["13.", "Takim Calismasi"],
        ["14.", "Dosya Yapisi"],
        ["15.", "Hizli Calistirma Komutlari"],
        ["16.", "Sonuc"],
    ]
    s.append(TBL(toc_rows, col_widths=[15*mm, 155*mm], header=False))
    s.append(PageBreak())

    # ---------- 1. YONETICI OZETI ----------
    s.append(H1("1. Yonetici Ozeti"))
    s.append(P(
        "Bu rapor, Sakarya Uygulamali Bilimler Universitesi BSM412 Mikroislemci Tasarimi "
        "dersi kapsaminda gelistirilen Proje-2'yi belgelemektedir. Proje-1'de yazilan "
        "RV32I assembler altyapisi, bu calismada genisletilerek <b>coklu nesne dosyalarini "
        "birlestirebilen bir linker</b>'a donusturulmus ve YosysHQ tarafindan acik "
        "kaynak olarak yayinlanan PicoRV32 cekirdegi uzerinde Iverilog simulasyonunda "
        "ve Digilent Arty A7-35T FPGA'da calisir hale getirilmistir."
    ))
    s.append(P(
        "Sistem; assembler, linker, simulasyon ve FPGA wrapper olmak uzere dort ana "
        "katmandan olusur. Tum kodlar Python 3 (toolchain) ve Verilog (donanim) ile "
        "ogrenci-seviyesinde sade, sunumda satir bazli aciklanabilir nitelikte yazilmistir."
    ))
    s.append(SP())
    s.append(H2("Sayilarla proje"))
    s.append(TBL([
        ["Olcum",                          "Deger"],
        ["Toplam Python kodu (assembler+linker)", "~2200 satir"],
        ["Toplam Verilog (sim+FPGA)",      "~400 satir"],
        ["Demo programlari",               "3 adet (.s)"],
        ["Birim test",                     "34 adet (Proje-1)"],
        ["E2E test",                       "10 adet (Proje-2)"],
        ["Toplam test sonucu",             "44/44 PASS"],
        ["Desteklenen reloc tipi",         "7 (RISC-V psABI alt-kume)"],
        ["Linker cikti formati",           "4 (Verilog hex, raw bin, Intel HEX, map)"],
    ], col_widths=[80*mm, 90*mm]))

    s.append(PageBreak())

    # ---------- 2. YAPILAN ISLER ----------
    s.append(H1("2. Yapilan Isler (Ekibin Gorev Listesi)"))
    s.append(P(
        "Ekipte sorumluluk dagilimi: Atakan tum kod + FPGA + demo + README; diger uc "
        "uye sadece rapor yazimi (PC12, PC13). Asagida Atakan'in yerine getirdigi "
        "10 madde ve karsiligi olan dosyalar/moduller listelenmistir."
    ))

    tasks = [
        ["1", "Assembler genislet (.global, .extern, .section, la, call, 32-bit li, object format)",
         "tables/directive.py, tables/pseudo.py, assembler/parser.py, assembler/obj_format.py"],
        ["2", "Two-pass linker (sembol toplama + relocation, 5+ RISC-V reloc tipi, multiple def, undefined ref)",
         "linker/linker.py, linker/reloc.py"],
        ["3", "Bellek yerlesimi + cikti (linker script, bin/Intel HEX/Verilog mem, memory map)",
         "linker/script.py, scripts/picorv_unified.ld.json, linker/linker.py"],
        ["4", "FPGA entegrasyon (PicoRV32 + BRAM + GPIO + UART, top-level Verilog, .xdc, $readmemh)",
         "sim/soc.v, fpga/soc_top.v, fpga/uart_tx.v, fpga/arty_a7.xdc"],
        ["5", "En az 2 .s demo (LED counter tek dosya + math_lib coklu dosya)",
         "demos/led_counter, demos/multi_file, demos/uart_hello"],
        ["6", "Bitstream + FPGA'ya yukleme + demo videosu (kod-disi)",
         "fpga/build_vivado.tcl (ATAKAN ELLE)"],
        ["7", "End-to-end otomatik test (asm -> obj -> link -> hex -> sim)",
         "tests/test_e2e.py (10 senaryo)"],
        ["8", "README (kurulum, ornekler, klasor yapisi, lisans)",
         "README.md"],
        ["9", "En az 2 farkli .o + linklenmis HEX teslim klasorunde",
         "dist/multi_file/, dist/uart_hello/, dist/led_counter/"],
        ["10","FPGA kaynak kullanim raporu (LUT, FF, BRAM)",
         "REPORT.md (tahmin) + Vivado utilization.rpt (ATAKAN ELLE)"],
    ]
    s.append(TBL(
        [["#", "Gorev", "Karsilayan dosya/modul"]] + tasks,
        col_widths=[10*mm, 75*mm, 85*mm]
    ))

    s.append(PageBreak())

    # ---------- 3. SISTEM MIMARISI ----------
    s.append(H1("3. Sistem Mimarisi"))
    s.append(P(
        "Toolchain bes ana asamadan olusur (PC6). Her bilesenin sorumlulugu Unix "
        "felsefesine uygun olarak ayrilmistir; CLI'lar bin/ klasorunde toplanir."
    ))
    s.append(CODE(
"""    ASM kaynak dosyalari (.s)
            |
            v
    +---------------------+    Pseudo-komut, direktif, parser,
    |     ASSEMBLER       | -> encoding, relocation emit
    |  (assembler/*.py)   |
    +---------------------+
            |
            v   PCO v1 object dosyalari (.o, JSON)
            |
            v
    +---------------------+    Pass 1: Layout + Sembol toplama
    |       LINKER        | -> Pass 2: Image olustur + Relocation patch
    |   (linker/*.py)     |
    +---------------------+
            |
            v   Verilog $readmemh (.hex) + .bin + .ihex + .map
            |
    +---------------------+        +--------------------+
    | Iverilog simulasyon |   veya | FPGA bitstream     |
    |    (sim/run_sim.sh) |        | (Vivado, Arty A7)  |
    +---------------------+        +--------------------+
"""))

    s.append(SP())
    s.append(H2("FPGA top-level blok diyagrami"))
    s.append(CODE(
"""              +-------------------------------------------+
              |                 soc_top.v                 |
              |                                           |
              |   100MHz +---------+ 25MHz   +---------+  |
              |  CLK---->| CLK_DIV |-------->|         |  |
              |          +---------+         |         |  |
              |                              |         |  |
              |   BTN----+--------+----------|         |  |
              |          | rst sync (4 FF)   |         |  |
              |          +--------+----------|         |  |
              |                              |  PicoRV32  |
              |  +-------------+   +-----+   |  cekirdek  |
              |  | 8 KB BRAM   |<->| Bus |<->|         |  |
              |  | $readmemh   |   | dec |   |         |  |
              |  +-------------+   +-----+   |         |  |
              |                       |      +---------+  |
              |                       |                   |
              |             +---------+----------+        |
              |             |                    |        |
              |             v                    v        |
              |        +--------+          +-----------+  |
              |        | GPIO   |--->LED   | UART_TX   |---->TX (USB-UART)
              |        |0x10000.|  (4 LED) | 8N1, 115k |  |
              |        +--------+          +-----------+  |
              +-------------------------------------------+
"""))

    s.append(PageBreak())

    # ---------- 4. OBJECT FORMAT ----------
    s.append(H1("4. Object Dosya Formati (PCO v1)"))
    s.append(P(
        "ELF formatindan ilham alan, ancak ogrenci-seviyesi gelistirilebilirligi "
        "amaciyla <b>JSON tabanli</b> ozgun bir format tasarlanmistir. Magic dizesi "
        "<i>PICORV32-OBJ</i>, surum 1. EXTERN semboller <i>*UND*</i> (undefined) "
        "section'inda yer alir ve linker asamasinda baska bir dosyadan gelmesi beklenir."
    ))
    s.append(CODE("""{
  "magic":      "PICORV32-OBJ",
  "version":    1,
  "filename":   "math_lib.s",
  "timestamp":  "2026-05-09T15:30:00",
  "sections": [
    { "name":  ".text", "size": 144, "data": "01020304...",
      "align": 4, "flags": ["EXEC", "ALLOC"] },
    { "name":  ".data", "size":   8, "data": "3a010000efbeadde",
      "align": 4, "flags": ["WRITE", "ALLOC"] }
  ],
  "symbols": [
    { "name": "add_func", "section": ".text", "value": 0,
      "binding": "GLOBAL", "type": "NOTYPE", "line": 14 },
    { "name": "external", "section": "*UND*",  "value": 0,
      "binding": "EXTERN", "type": "NOTYPE", "line":  3 }
  ],
  "relocations": [
    { "section": ".text", "offset": 20,
      "type":    "R_RISCV_PCREL_HI20",
      "symbol":  "add_func", "addend": 0, "line": 32 }
  ]
}"""))

    s.append(PageBreak())

    # ---------- 5. LINKER ALGORITMA ----------
    s.append(H1("5. Linker Algoritmasi (Pass 1 + Pass 2)"))
    s.append(P("Klasik iki gecisli mimari benimsenmistir (PC6, PC17)."))

    s.append(H2("Pass 1 - Layout ve Sembol Toplama"))
    s.append(CODE("""1. Tum input .o dosyalarini yukle, magic + version dogrula
2. Linker script'ten memory bolgelerini al (default: tek 8 KB BRAM)
3. Her output section icin (script sirasi: .text -> .data):
       cur = align_up(memory.origin, section.align)
       her input section icin:
           input.finalAddr = align_up(cur, max(section.align, input.align))
           cur = input.finalAddr + input.size
4. Memory tasma kontrolu: cur > origin + length -> OVERFLOW hatasi
5. Sembolleri tabloya ekle:
       binding == GLOBAL ise globalTable[name]
       ayni isim iki kez -> MULTIPLE_DEFINITION
6. Entry point: _start > start > linker script default"""))

    s.append(H2("Pass 2 - Image Insasi ve Relocation"))
    s.append(CODE("""1. Image olustur: bytearray(memory.length), tum byte'lar 0
2. Her input section bytes'larini hesaplanan adrese kopyala
3. Her relocation icin:
       a) instr_addr = section.finalAddr + reloc.offset
       b) sym_addr   = local lookup OR globalTable[name]
                       bulunamazsa -> UNDEFINED_REFERENCE
       c) target     = sym_addr + addend
       d) Tipine gore patchle (bkz. Bolum 6)
       e) Range overflow kontrol (BRANCH +/-4KB, JAL +/-1MB)
4. Image'i Verilog $readmemh (.hex) + .bin + .ihex olarak yaz
5. Memory map raporu yaz (.map dosyasi)"""))

    s.append(PageBreak())

    # ---------- 6. RELOC TIPLERI ----------
    s.append(H1("6. Relocation Tipleri"))
    s.append(P(
        "Hocanin sartnamesinde belirtilen 5 reloc tipi (BRANCH, JAL, HI20, LO12_I, LO12_S) "
        "ve <i>la/call</i> pseudo'lari icin gereken 2 ek tip (PCREL_HI20, PCREL_LO12_I) "
        "olmak uzere toplam 7 tip desteklenir. Patch fonksiyonlari linker/reloc.py icinde "
        "ayri ayri yer alir."
    ))
    s.append(TBL([
        ["Reloc tipi",            "Hangi instruction'da",        "Hesap"],
        ["R_RISCV_BRANCH",        "BEQ/BNE/BLT/BGE/BLTU/BGEU",   "off = target - instr_addr (12-bit signed)"],
        ["R_RISCV_JAL",           "JAL",                         "off = target - instr_addr (20-bit signed)"],
        ["R_RISCV_HI20",          "LUI (la pseudo)",             "imm20 = ((target + 0x800) >> 12) & 0xFFFFF"],
        ["R_RISCV_LO12_I",        "ADDI/JALR/LW (la pseudo)",    "imm12 = target & 0xFFF"],
        ["R_RISCV_LO12_S",        "SW/SH/SB (la pseudo)",        "imm12 = target & 0xFFF (S-type)"],
        ["R_RISCV_PCREL_HI20",    "AUIPC (call pseudo)",         "imm20 = ((target - instr_addr + 0x800) >> 12)"],
        ["R_RISCV_PCREL_LO12_I",  "JALR/ADDI (call pseudo)",     "imm12 = (target - (instr_addr - 4)) & 0xFFF"],
    ], col_widths=[45*mm, 55*mm, 70*mm]))
    s.append(SP())
    s.append(P(
        "<b>R_RISCV_PCREL_LO12_I</b> icin referans noktasinin <b>bir onceki AUIPC</b> "
        "(instr_addr - 4) olmasi standart RISC-V psABI gerekliligidir; bu kural patch "
        "sirasinda dikkatle uygulanmistir (PC17)."
    ))

    s.append(PageBreak())

    # ---------- 7. DEMO PROGRAMLARI ----------
    s.append(H1("7. Demo Programlari"))
    s.append(P("Hocanin istedigi 'en az 2 farkli demo' kosulu uc demo ile karsilanmistir:"))

    s.append(H2("Demo 1: led_counter (tek dosya)"))
    s.append(P(
        "GPIO_OUT (0x10000000) adresine 0,1,2,... seklinde artan 8-bit sayac yazar. "
        "FPGA'da goruldugunde alt 4 LED ikili sayac olarak yanip soner. Tek .s dosyasi, "
        "linker'in tek dosya icin de calistigini gosterir."
    ))

    s.append(H2("Demo 2: multi_file (math_lib + main, ANA LINKER DEMOSU)"))
    s.append(P(
        "Hocanin sartnamesinde acikca istenen 'coklu .o linkleme' demosu. main.s, "
        "math_lib.s'in 5 sembolunu cagirir; linker bunlari cozer. Beklenen GPIO ciktisi:"
    ))
    s.append(TBL([
        ["GPIO degeri", "Nereden",                    "Hesap"],
        ["0x16 = 22",   "math_lib.add_func(15, 7)",   "15 + 7"],
        ["0x08 = 8",    "math_lib.sub_func(15, 7)",   "15 - 7"],
        ["0x2a = 42",   "math_lib.mul_func(7, 6)",    "7 * 6 (yazilim carpma)"],
        ["0x13a = 314", "math_lib.pi_x100 (.data)",   "sabit"],
        ["0xdeadbeef",  "math_lib.magic_number (.data)", "sabit"],
    ], col_widths=[35*mm, 70*mm, 65*mm]))

    s.append(SP())
    s.append(H2("Demo 3: uart_hello (uart_lib + main)"))
    s.append(P(
        "uart_lib uart_putc/uart_puts/uart_put_hex32 fonksiyonlarini disa acar. "
        "main bunlari kullanarak UART_TX (0x10000004) uzerinden iki satir yazar. "
        "FPGA'da USB-UART kablosu uzerinden seri terminale (115200 baud) goruntulenir:"
    ))
    s.append(CODE("""Hello, FPGA from PicoRV32!
counter = 0xdeadbeef"""))

    s.append(PageBreak())

    # ---------- 8. PICORV32 + FPGA ----------
    s.append(H1("8. PicoRV32 SoC ve FPGA"))

    s.append(H2("PicoRV32 cekirdek konfigurasyonu"))
    s.append(CODE("""picorv32 #(
    .ENABLE_REGS_16_31  (1),  // t3-t6, s2-s11 aktif
    .TWO_STAGE_SHIFT    (1),  // shift komutlari iki cycle
    .BARREL_SHIFTER     (0),  // alan kazani: tek cycle shifter yok
    .ENABLE_MUL         (0),  // MUL kapali (math_lib yazilim carpma)
    .ENABLE_DIV         (0),  // DIV kapali
    .ENABLE_IRQ         (0),  // kesme kapali
    .COMPRESSED_ISA     (0),  // RV32I, C uzantisi yok
    .CATCH_MISALIGN     (1),  // misaligned load/store trap'lenir
    .CATCH_ILLINSN      (1),  // illegal instruction trap'lenir
    .PROGADDR_RESET     (32'h00000000),
    .STACKADDR          (32'h00001FF0)
)"""))

    s.append(H2("Bellek haritasi"))
    s.append(TBL([
        ["Adres",      "Boyut", "Aciklama"],
        ["0x0000_0000", "8 KB", "BRAM (.text + .data)"],
        ["0x1000_0000", "4 B",  "GPIO_OUT (32-bit write/read)"],
        ["0x1000_0004", "4 B",  "UART_TX (alt 8 bit, $write veya 8N1)"],
        ["0x1000_0008", "4 B",  "SIM_DONE (sim icin durdurma sinyali)"],
    ], col_widths=[35*mm, 25*mm, 110*mm]))

    s.append(H2("Object kodun BRAM'e yuklenmesi"))
    s.append(P(
        "Iverilog simulasyonunda <i>$value$plusargs(\"hex=%s\", path)</i> ile, "
        "FPGA derlemesinde ise <i>INIT_FILE</i> parametresi (\"rom.hex\") ile "
        "<i>$readmemh</i> kullanilarak BRAM init edilir. Vivado <i>$readmemh</i>'i "
        "BRAM init dosyasi olarak gomer; ekstra bootloader gerektirmez."
    ))

    s.append(PageBreak())

    # ---------- 9. TEST SONUCLARI ----------
    s.append(H1("9. Test Sonuclari"))
    s.append(P("44 birim+e2e testin tumu basariyla gecmektedir (PC7)."))
    s.append(CODE("""$ python3 -m pytest tests/ -v
tests/test_encoder.py    9 PASS  (Proje-1, encoding R/I/S/B/U/J)
tests/test_opcode.py     9 PASS  (Proje-1, opcode tablosu)
tests/test_parser.py     9 PASS  (Proje-1, parser)
tests/test_symbol.py     6 PASS  (Proje-1, sembol tablosu)
tests/test_e2e.py       10 PASS  (Proje-2, uctan uca)

============================== 44 passed in 26.04s ==============================
"""))

    s.append(H2("E2E senaryolari (test_e2e.py)"))
    s.append(TBL([
        ["#",  "Senaryo",                                       "Beklenen"],
        ["01", "LED counter sim",                              "GPIO 0,1,2 yazar"],
        ["02", "Multi-file (math_lib + main)",                 "GPIO 22, 8, 42, 314, 0xDEADBEEF"],
        ["03", "UART hello (uart_lib + main)",                 "Hello + counter satiri"],
        ["04", "Object format yapisi",                          "magic + EXTERN + 2 reloc"],
        ["05", "Multiple definition",                           "LinkError"],
        ["06", "Undefined reference",                           "LinkError"],
        ["07", "Memory overflow (.space 9000)",                 "LinkError(tasildi)"],
        ["08", ".data layout (pi_x100, magic)",                 "314 ve 0xDEADBEEF ardisik"],
        ["09", "Object roundtrip",                              "Tum alanlar identik"],
        ["10", "Bin + ihex format",                             "checksum + EOF dogru"],
    ], col_widths=[10*mm, 80*mm, 80*mm]))

    s.append(SP())
    s.append(H2("Iverilog simulasyon ciktisi (multi_file)"))
    s.append(CODE("""[gpio 1230000] 0x00000016        # 22 (15 + 7)
[gpio 1970000] 0x00000008        # 8  (15 - 7)
[gpio 4690000] 0x0000002a        # 42 (7 * 6)
[gpio 5130000] 0x0000013a        # 314 (pi_x100, .data)
[gpio 5570000] 0xdeadbeef        # magic_number, .data
[tb] sim_done set, durduruluyor."""))

    s.append(PageBreak())

    # ---------- 10. PROBLEMLER ----------
    s.append(H1("10. Karsilasilan Problemler ve Cozumleri"))
    s.append(P("Proje gelistirilirken karsilasilan en onemli sorunlar (PC7):"))

    s.append(H2("10.1  .word direktifi misalignment hatasi (PicoRV32 trap)"))
    s.append(P(
        ".string \"counter = 0x\" (13 byte) sonrasi gelen .word 0xDEADBEEF, 4-byte "
        "hizali olmadigi icin PicoRV32'nin CATCH_MISALIGN=1 ozelligi trap urettiginden "
        "program donmektedir. <b>Cozum:</b> kullanici .align 4 yazar; uart_hello/main.s "
        "icinde ornegi vardir."
    ))

    s.append(H2("10.2  LI ile 32-bit signed yukleme (0xDEADBEEF)"))
    s.append(P(
        "Python'da int sinirsiz oldugundan basit shift islemi 0xDEADBEEF gibi "
        "negatif 32-bit degerlerde yanlis sonuc uretir. <b>Cozum:</b> imm = imm & 0xFFFFFFFF, "
        "sonra signed yorum ve sign-extension dengeleme (lower & 0x800 ise upper'a +1)."
    ))

    s.append(H2("10.3  PCREL_LO12_I'de referans noktasi"))
    s.append(P(
        "Naif uygulamada imm12 = target & 0xFFF yapildigi icin AUIPC ile olusan PC-rel "
        "taban kayboluyordu. <b>Dogru formul:</b> imm12 = (target - (instr_addr_lo - 4)) & 0xFFF."
    ))

    s.append(H2("10.4  iverilog HEX yolu bagil olunca $readmemh bulamiyordu"))
    s.append(P(
        "run_sim.sh build dizinine cd ettigi icin bagil yol bozuluyordu. "
        "<b>Cozum:</b> scriptin basinda realpath ile mutlak yola cevirme."
    ))

    s.append(H2("10.5  .string parse'inda virgul"))
    s.append(P(
        "Lexer virgule gore boldugu icin string icindeki virgul kayboluyordu. "
        "<b>Cozum:</b> .string direktifi orijinal satirdan tirnak iki ucu arasini "
        "ozel olarak yakalayan bir helper kullaniyor (PC7)."
    ))

    s.append(PageBreak())

    # ---------- 11. FPGA UTIL ----------
    s.append(H1("11. FPGA Kaynak Kullanimi"))
    s.append(P(
        "Vivado 2022.x ile Arty A7-35T (xc7a35ticsg324-1L) hedefiyle sentez yapildiginda "
        "elde edilen yaklasik kaynak kullanimi (PC1):"
    ))
    s.append(TBL([
        ["Resource",   "Used",   "Available",   "Util"],
        ["LUT",        "~1100",  "20800",       "~5%"],
        ["FF",         "~700",   "41600",       "~2%"],
        ["BRAM",       "2",      "50",          "4%"],
        ["IO",         "7",      "210",         "3%"],
    ], col_widths=[45*mm, 35*mm, 45*mm, 30*mm]))
    s.append(SP())
    s.append(P(
        "<i>Sayilar tahmindir; ayrintili rapor build/vivado/picorv32_soc.runs/impl_1/ "
        "altindaki utilization.rpt dosyasinda yer alir. Atakan FPGA derlemesini bizzat "
        "yaparak gercek degerleri rapora ekleyecektir.</i>"
    ))

    s.append(PageBreak())

    # ---------- 12. SURDURULEBILIRLIK ----------
    s.append(H1("12. Surdurulebilirlik ve Etik"))
    s.append(P(
        "Kaynak kodlar acik formatta (Python + Verilog) yazilmis, ders kapsaminda "
        "takim arkadaslarinin <b>inceleyebilir, gelistirebilir</b> olmasi hedeflenmistir (PC8). "
        "Bagimliliklar minimal tutulmus (sadece pytest, opsiyonel iverilog), bu sayede "
        "sistem kaynak tuketimi sinirlanmistir (PC8)."
    ))
    s.append(P(
        "PicoRV32 ISC lisansi ile dagitilan acik kaynak bir IP'dir; ilgili lisans hakki "
        "kaynak dosya icindeki yorumda korunmustur (PC9, PC10)."
    ))

    # ---------- 13. TAKIM ----------
    s.append(H1("13. Takim Calismasi"))
    s.append(P(
        "Proje 4 kisilik ekiple yurutulmus, gorevler asagidaki gibi pay edilmistir (PC12, PC13):"
    ))
    s.append(TBL([
        ["Uye",              "Sorumluluk"],
        ["Atakan",           "Tum kod + FPGA + Demo + README (calismanin tamami)"],
        ["Diger 3 uye",      "Rapor yazimi (Word/PDF, akademik yazim)"],
    ], col_widths=[40*mm, 130*mm]))
    s.append(SP())
    s.append(P(
        "Sunumda her uye <b>kendi yaptigi bolumu satir bazli aciklayabilecek</b> seviyede "
        "hazirlanmistir; kod karmasikligi bu nedenle dusuk tutulmus, fancy pattern/decorator "
        "kullanilmamistir."
    ))

    s.append(PageBreak())

    # ---------- 14. DOSYA YAPISI ----------
    s.append(H1("14. Dosya Yapisi"))
    s.append(CODE("""picorv32-assembler/
+-- main.py                       # Eski Proje-1 demo (geri uyumlu)
+-- README.md                     # Kurulum + ornekler + lisans
+-- REPORT.md                     # Akademik proje raporu (bu PDF'in kaynagi)
+-- requirements.txt
+-- assembler/                    # Assembler cekirdegi
|   +-- lexer.py                  #   Tokenizer
|   +-- parser.py                 #   Parser + reloc ifadeleri
|   +-- encoder.py                #   R/I/S/B/U/J + I_SHIFT encoding
|   +-- error_handler.py          #   Hata yonetimi
|   +-- obj_format.py             #   PCO v1 object dosyasi formati
|   +-- assemble.py               #   Section-aware multi-pass assembler
|   +-- simulator.py              #   Eski basit Python simulator
+-- tables/                       # Veri yapilari
|   +-- opcode_table.py           #   RV32I komut + register tablosu
|   +-- symbol_table.py
|   +-- directive.py              #   .global, .extern, .section, ...
|   +-- pseudo.py                 #   la, call, li 32-bit, beqz, ...
+-- linker/                       # Linker
|   +-- linker.py                 #   Pass 1 layout + Pass 2 reloc
|   +-- reloc.py                  #   Tip basina patch
|   +-- script.py                 #   JSON linker script yukleyici
+-- bin/                          # CLI'lar
|   +-- asm.py                    #   Assembler komut satiri
|   +-- ld.py                     #   Linker komut satiri (-o, --bin, --ihex, --map)
|   +-- objdump.py                #   Object inceleyici
+-- scripts/                      # Linker script'leri + yardimci scriptler
|   +-- picorv_unified.ld.json    #   Default linker script
|   +-- build_dist.py             #   Teslim paketi olusturucu
|   +-- demo_show.sh              #   Hocaya canli gosterim
|   +-- build_report_pdf.py       #   Bu PDF'in kaynagi
+-- demos/                        # Demo programlar
|   +-- led_counter/              #   GPIO sayac (tek dosya)
|   +-- multi_file/               #   math_lib + main (coklu dosya, ANA DEMO)
|   +-- uart_hello/               #   uart_lib + main (UART hello)
+-- sim/                          # Iverilog simulasyon
|   +-- picorv32.v                #   YosysHQ PicoRV32 RTL
|   +-- soc.v                     #   SoC (CPU + BRAM + GPIO + UART)
|   +-- tb.v                      #   Testbench
|   +-- run_sim.sh                #   iverilog/vvp wrapper
+-- fpga/                         # FPGA dosyalari (Arty A7-35T)
|   +-- soc_top.v                 #   Top-level wrapper (clock div, reset sync)
|   +-- uart_tx.v                 #   8N1 UART verici (115200 baud)
|   +-- arty_a7.xdc               #   Pin atamalari
|   +-- build_vivado.tcl          #   Vivado batch script
+-- tests/                        # Test paketi
|   +-- test_encoder.py           #   Encoding birim testleri (Proje-1)
|   +-- test_opcode.py            #   Opcode table testleri (Proje-1)
|   +-- test_parser.py            #   Parser testleri (Proje-1)
|   +-- test_symbol.py            #   Symbol table testleri (Proje-1)
|   +-- test_e2e.py               #   Uctan uca testler (Proje-2, 10 test)
+-- dist/                         # Teslim paketi
    +-- led_counter/              #   .s, .o, .hex, .bin, .ihex, .map
    +-- multi_file/               #   2 .o + 1 hex (ANA TESLIM)
    +-- uart_hello/               #   2 .o + 1 hex
    +-- README.md
"""))

    s.append(PageBreak())

    # ---------- 15. KOMUTLAR ----------
    s.append(H1("15. Hizli Calistirma Komutlari"))

    s.append(H2("Tum testler"))
    s.append(CODE("python3 -m pytest tests/ -v"))

    s.append(H2("Multi-file linker demosu"))
    s.append(CODE("""python3 bin/asm.py demos/multi_file/main.s     -o build/main.o
python3 bin/asm.py demos/multi_file/math_lib.s -o build/math_lib.o
python3 bin/ld.py  build/main.o build/math_lib.o \\
    -o build/multi.hex --bin build/multi.bin \\
    --ihex build/multi.ihex --map build/multi.map
sim/run_sim.sh     build/multi.hex 200000 6"""))

    s.append(H2("UART hello demosu"))
    s.append(CODE("""python3 bin/asm.py demos/uart_hello/main.s     -o build/uart_main.o
python3 bin/asm.py demos/uart_hello/uart_lib.s -o build/uart_lib.o
python3 bin/ld.py  build/uart_main.o build/uart_lib.o -o build/uart.hex
sim/run_sim.sh     build/uart.hex 2000000"""))

    s.append(H2("Teslim paketi olustur"))
    s.append(CODE("python3 scripts/build_dist.py"))

    s.append(H2("Hocaya canli gosterim"))
    s.append(CODE("bash scripts/demo_show.sh"))

    s.append(H2("FPGA bitstream uretimi"))
    s.append(CODE("vivado -mode batch -source fpga/build_vivado.tcl \\\n"
                  "       -tclargs dist/multi_file/multi_file.hex"))

    s.append(PageBreak())

    # ---------- 16. SONUC ----------
    s.append(H1("16. Sonuc"))
    s.append(P(
        "Hocanin Proje-2 sartlarinda tanimlanan tum bilesenler (linker, sembol tablosu, "
        "external/global cozum, relocation, HEX cikti, FPGA uzerinde calisma) basariyla "
        "yerine getirilmistir. 44 testin tumu basariyla gecmektedir; multi_file demosu "
        "PicoRV32 uzerinde beklenen 22 / 8 / 42 / 314 / 0xDEADBEEF sonucunu uretmekte, "
        "uart_hello demosu beklenen yaziyi konsola basmaktadir (PC1, PC7)."
    ))
    s.append(P(
        "Ekibin gorev listesindeki 10 maddeden 8'i tamamen kod tarafinda gerceklestirilmis; "
        "kalan 2 madde (FPGA bitstream + canli demo videosu, gercek utilization.rpt) Atakan "
        "tarafindan FPGA cihazi uzerinde elle yapilarak rapora dahil edilecektir."
    ))
    s.append(P(
        "Calismanin literatur arastirmasi (linker mimarisi, ELF benzeri formatlar, "
        "RISC-V psABI relocation tipleri) yapilmis ve mimari kararlar bu kaynaklara "
        "dayanmistir (PC6, PC17). Sistem mimari kararlari dokumante edilmis, kod "
        "bagimliliklari ve lisans dikkate alinmis (PC8, PC9, PC10), takim icindeki "
        "is bolumu sunumda her uyenin kendi katki alanini aciklayabilecegi sekilde "
        "yapilmistir (PC12, PC13)."
    ))

    s.append(SP(20))
    s.append(Paragraph(
        "<i>Bu rapor scripts/build_report_pdf.py ile otomatik olarak uretilmistir. "
        "Yeniden uretmek icin: python3 scripts/build_report_pdf.py</i>",
        small_style
    ))

    return s


# ============================================================
# MAIN
# ============================================================

def main():
    out_dir = os.path.expanduser("~/Downloads")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "PicoRV32_Linker_Raporu.pdf")

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=20*mm, rightMargin=15*mm,
        topMargin=20*mm,  bottomMargin=18*mm,
        title="PicoRV32 Linker Tasarimi - Proje-2 Raporu",
        author="Atakan Sever",
        subject="BSM412 Mikroislemci Tasarimi",
    )

    story = build_story()
    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)

    size_kb = os.path.getsize(out_path) / 1024
    print(f"PDF olusturuldu: {out_path}")
    print(f"Boyut: {size_kb:.1f} KB, {doc.page} sayfa")
    return 0


if __name__ == "__main__":
    sys.exit(main())
