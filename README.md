# PicoRV32 Toolchain (Assembler + Linker + FPGA)

Sakarya Uygulamali Bilimler Universitesi BSM412 Mikroislemci Tasarimi
dersi icin gelistirilen, RV32I alt kumesini destekleyen tam bir
"assembler + linker + sim + FPGA" zinciri. Proje-1 (assembler)
korunmus, uzerine Proje-2 (linker + PicoRV32 entegrasyonu) eklenmistir.

## Ozellikler

### Assembler (Proje-1 + Proje-2 eklemeleri)

- Two-pass assembler, RV32I komutlari + I-Shift (SLLI/SRLI/SRAI)
- Direktifler:
  Proje-1: `.text`, `.data`, `.word`, `.byte`, `.org`, `.end`
  Proje-2: `.section`, `.global`/`.globl`, `.extern`,
           `.string`/`.asciz`/`.ascii`, `.space`/`.skip`,
           `.half`, `.align`
- Pseudo-komutlar:
  Proje-1: `li`, `mv`, `j`, `nop`, `ret`, `not`, `neg`
  Proje-2: `la`, `call`, `beqz`, `bnez`, `bgez`, `bltz`, `jr`
- Relocation ifadeleri: `%hi(sym)`, `%lo(sym)`,
  `%pcrel_hi(sym)`, `%pcrel_lo(sym)`
- PCO v1 object dosyasi (JSON tabanli)

### Linker

- Coklu `.o` dosyasini birlestirir
- Sembol tablosu yonetimi (LOCAL/GLOBAL/EXTERN)
- 7 RISC-V relocation tipi destegi:
  `R_RISCV_BRANCH`, `R_RISCV_JAL`,
  `R_RISCV_HI20`, `R_RISCV_LO12_I`, `R_RISCV_LO12_S`,
  `R_RISCV_PCREL_HI20`, `R_RISCV_PCREL_LO12_I`
- JSON tabanli linker script
- Verilog `$readmemh` HEX cikti + memory map raporu
- Hata kontrolleri: `MULTIPLE_DEFINITION`, `UNDEFINED_REFERENCE`,
  memory overflow, range overflow

### Donanim (sim + FPGA)

- PicoRV32 (YosysHQ) RTL'si (sim/picorv32.v)
- 8 KB BRAM + GPIO + UART + SIM_DONE SoC'u (sim/soc.v)
- Iverilog testbench (sim/tb.v)
- Digilent Arty A7-35T icin FPGA wrapper (fpga/soc_top.v + .xdc + Vivado tcl)

## Kurulum

```bash
# Sadece Python 3.9+ ve pytest gerekli
pip install -r requirements.txt

# Simulasyon icin Iverilog
brew install icarus-verilog        # macOS
sudo apt install iverilog          # Ubuntu

# FPGA icin Vivado 2020.x+ (Arty A7-35T)
```

## Hizli Baslangic

### 1) Tek dosya - eski Proje-1 demosu (geri uyumlu)

```bash
python3 main.py examples/basic.asm
```

### 2) Coklu dosya assembler + linker

```bash
mkdir -p build

# Assemble
python3 bin/asm.py demos/multi_file/main.s     -o build/main.o
python3 bin/asm.py demos/multi_file/math_lib.s -o build/math_lib.o

# Link (otomatik linker script)
python3 bin/ld.py build/main.o build/math_lib.o \
    -o build/multi.hex --map build/multi.map

# Object dump
python3 bin/objdump.py build/main.o --all
```

### 3) Iverilog ile simulasyon

```bash
sim/run_sim.sh build/multi.hex 200000 6
# Beklenen: GPIO 0x16 (22), 0x08, 0x2a (42), 0x13a (314), 0xdeadbeef
```

### 4) UART hello demosu

```bash
python3 bin/asm.py demos/uart_hello/main.s     -o build/uart_main.o
python3 bin/asm.py demos/uart_hello/uart_lib.s -o build/uart_lib.o
python3 bin/ld.py build/uart_main.o build/uart_lib.o -o build/uart.hex
sim/run_sim.sh build/uart.hex 2000000
# Beklenen: "Hello, FPGA from PicoRV32!" + "counter = 0xdeadbeef"
```

### 5) Teslim paketi olustur (dist/ klasoru)

```bash
python3 scripts/build_dist.py
# Cikti: dist/<demo>/<demo>.{s,o,hex,bin,ihex,map}
```

Hocaya teslim icin gerekli **en az 2 farkli .o + linklenmis HEX** burada
(multi_file: `main.o + math_lib.o + multi_file.hex`).

### 6) FPGA bitstream uretimi (Vivado batch)

```bash
vivado -mode batch -source fpga/build_vivado.tcl -tclargs dist/multi_file/multi_file.hex
# Cikti: build/soc_top.bit
```

### Cikti Formatlari

`bin/ld.py` 3 formatta cikti uretebilir:

| Bayrak    | Format                       | Kullanim                       |
| --------- | ---------------------------- | ------------------------------ |
| `-o`      | Verilog `$readmemh` (text)   | BRAM init (sim + Vivado)       |
| `--bin`   | Raw binary (LE)              | Bootloader / direkt bellek     |
| `--ihex`  | Intel HEX                    | EEPROM/flash programlayicilar  |
| `--map`   | Memory map raporu            | Inceleme / rapor               |

```bash
python3 bin/ld.py build/main.o build/math_lib.o \
    -o build/multi.hex --bin build/multi.bin --ihex build/multi.ihex --map build/multi.map
```

## Proje Yapisi

```
picorv32-assembler/
├── main.py                  # Eski Proje-1 demo (geri uyumlu)
├── assembler/               # Assembler cekirdegi
│   ├── lexer.py             #   Tokenizer
│   ├── parser.py            #   Yapisal parser + reloc ifadeleri
│   ├── encoder.py           #   R/I/S/B/U/J + I_SHIFT encoding
│   ├── error_handler.py     #   Hata yonetimi
│   ├── obj_format.py        #   PCO v1 object dosyasi formati
│   └── assemble.py          #   Section-aware multi-pass assembler
├── tables/                  # Veri yapilari
│   ├── opcode_table.py      #   RV32I komut + register tablosu
│   ├── symbol_table.py      #   Label-adres haritasi
│   ├── directive.py         #   Direktif islemcileri
│   └── pseudo.py            #   Pseudo-komut donusturucu
├── linker/                  # Linker (Proje-2)
│   ├── linker.py            #   Pass 1 layout + Pass 2 reloc
│   ├── reloc.py             #   Relocation tipi basina patcher
│   └── script.py            #   JSON linker script yukleyici
├── bin/                     # CLI'lar
│   ├── asm.py               #   Assembler komut satiri
│   ├── ld.py                #   Linker komut satiri
│   └── objdump.py           #   Object dosyasi inceleyici
├── scripts/                 # Linker script'leri + teslim
│   ├── picorv_unified.ld.json
│   └── build_dist.py        #   Teslim paketi olusturucu
├── demos/                   # Demo programlar
│   ├── led_counter/         #   GPIO sayac (tek dosya)
│   ├── multi_file/          #   math_lib + main (coklu dosya)
│   └── uart_hello/          #   uart_lib + main (UART hello)
├── sim/                     # Iverilog simulasyon
│   ├── picorv32.v           #   YosysHQ PicoRV32 RTL
│   ├── soc.v                #   SoC (CPU + BRAM + GPIO + UART)
│   ├── tb.v                 #   Testbench
│   └── run_sim.sh           #   iverilog/vvp wrapper
├── fpga/                    # FPGA dosyalari (Arty A7-35T)
│   ├── soc_top.v            #   Top-level wrapper (clock div, reset sync)
│   ├── uart_tx.v            #   8N1 UART verici (115_200 baud)
│   ├── arty_a7.xdc          #   Pin atamalari
│   └── build_vivado.tcl     #   Vivado batch script
├── tests/                   # Test paketi
│   ├── test_encoder.py      #   Encoding birim testleri (Proje-1)
│   ├── test_opcode.py       #   Opcode table testleri (Proje-1)
│   ├── test_parser.py       #   Parser testleri (Proje-1)
│   ├── test_symbol.py       #   Symbol table testleri (Proje-1)
│   └── test_e2e.py          #   Uctan uca testler (Proje-2, 9 test)
└── REPORT.md                # Akademik proje raporu
```

## Object Dosya Formati (PCO v1)

JSON tabanli, insan-okunur:

```json
{
  "magic":      "PICORV32-OBJ",
  "version":    1,
  "filename":   "math_lib.s",
  "timestamp":  "2026-05-09T15:30:00",
  "sections": [
    { "name": ".text", "size": 144, "data": "0102...",
      "align": 4, "flags": ["EXEC", "ALLOC"] }
  ],
  "symbols": [
    { "name": "add_func", "section": ".text", "value": 0,
      "binding": "GLOBAL", "type": "NOTYPE", "line": 14 }
  ],
  "relocations": [
    { "section": ".text", "offset": 20,
      "type": "R_RISCV_PCREL_HI20",
      "symbol": "add_func", "addend": 0, "line": 32 }
  ]
}
```

## Memory Map (Linker Default)

| Adres        | Boyut  | Aciklama                  |
| ------------ | ------ | ------------------------- |
| 0x0000_0000  | 8 KB   | BRAM (.text + .data)      |
| 0x1000_0000  | 4 B    | GPIO_OUT (32-bit)         |
| 0x1000_0004  | 4 B    | UART_TX (alt 8 bit)       |
| 0x1000_0008  | 4 B    | SIM_DONE (sim icin)       |

## Testler

```bash
python3 -m pytest tests/ -v
# 44/44 PASS (34 birim + 10 e2e)
```

## Ekip

Sakarya Uygulamalı Bilimler Üniversitesi, Mikroişlemci Tasarımı dersi kapsamında
4 kişilik ekiple geliştirilmiştir.

| Sorumluluk | Kişi |
| ---------- | ---- |
| Loader FSM + UART RX (donanım) | |
| Host yazılımı + protokol/CRC | |
| SoC entegrasyonu + Tang Nano 9K sentez | |
| Test senaryoları + rapor | |

## Lisans

Bu proje akademik amaclidir. PicoRV32 (sim/picorv32.v) YosysHQ tarafindan
ISC lisansi ile dagitilir. Bu repository'de bulunan diger kaynak kodlar
MIT benzeri sartlar altinda dersi alanlarin ortak kullanimina aciktir.
