# Proje-2 Raporu: PicoRV32 Linker Tasarimi ve FPGA Entegrasyonu

> Bu rapor PDF'e cevrildiginde **Courier New 10 pt** ile bicimlendirilmelidir.
> (Pandoc / Word'de "tum metni sec -> Courier New 10 pt" yapilarak.)

**Ders:** BSM412 Mikroislemci Tasarimi (SUBU)
**Ogrenci:** Atakan Sever
**Tarih:** 09.05.2026

---

## 1. Giris ve Amac

Proje-1'de RV32I alt kumesi icin gelistirilen iki gecisli (two-pass) assembler
altyapisi, bu projede genisletilerek **coklu nesne (.o) dosyalarini birlestirip
FPGA bellegine yuklenebilen bir HEX cikti** ureten linker'a donusturulmustur.
Sistem, YosysHQ tarafindan acik kaynak olarak yayinlanan PicoRV32 cekirdegi
uzerinde Iverilog simulasyonunda ve Digilent Arty A7-35T FPGA'da
calistirilmaktadir (PC1).

Calismanin akademik literaturde linker mimarisi, ELF benzeri object format
tasarimi ve relocation algoritmalari uzerine yapilan kaynaklar incelenerek
yurutulmus olmasi (PC6, PC17), proje boyunca veri yapilari, algoritma
karmasikligi ve sistem programlama becerilerinin butunluklu olarak gelisimini
hedeflemistir.

## 2. Sistem Mimarisi

Toolchain uc ana asamadan olusur (PC6):

```
   ASM kaynak dosyalari (.s)
              |
              v
   +---------------------+      Pseudo-komut, direktif, parser,
   |     ASSEMBLER       |  --> encoding, relocation emit
   |  (assembler/*.py)   |
   +---------------------+
              |
              v   PCO v1 object dosyalari (.o, JSON)
              |
              v
   +---------------------+      Pass 1: Layout + Sembol toplama
   |       LINKER        |  --> Pass 2: Image olustur + Relocation patch
   |   (linker/*.py)     |
   +---------------------+
              |
              v   Verilog $readmemh (.hex)
              |
   +---------------------+
   | Iverilog simulasyon |  veya  FPGA bitstream (Vivado batch)
   +---------------------+
```

Her bilesenin sorumlulugu Unix felsefesine uygun olarak ayrilmistir
(asm.py / ld.py / objdump.py CLI'lari).

## 3. Object Dosya Formati (PCO v1)

ELF formatindan ilham alan, ancak ogrenci-seviyesinde gelistirilebilirligi
amaciyla **JSON tabanli** ozgun bir format tasarlanmistir. Her .o dosyasi
asagidaki temel alanlari icerir (PC6):

| Alan          | Aciklama                                                      |
| ------------- | ------------------------------------------------------------- |
| `magic`       | "PICORV32-OBJ" sabit dizesi                                   |
| `version`     | format surumu (= 1)                                           |
| `sections`    | name, size, hex data (LE), align, flags (`EXEC`/`ALLOC`/...)  |
| `symbols`     | name, section (veya `*UND*`), value (offset), binding, type   |
| `relocations` | section, offset, type, symbol, addend                         |

Sembol baglari (`binding`) UCH degerden birini alir: **LOCAL, GLOBAL, EXTERN**.
EXTERN semboller `*UND*` (undefined) section'inda yer alir ve linker
asamasinda baska bir dosyadan gelmesi beklenir.

## 4. Linker Algoritmasi

Klasik iki gecisli mimari benimsenmistir (PC6, PC17):

### 4.1 Pass 1 — Layout ve Sembol Toplama

```
1. Tum input .o dosyalarini yukle, magic + version dogrula
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
6. Entry point: _start > start > linker script default
```

### 4.2 Pass 2 — Image Insasi ve Relocation

```
1. Image olustur: bytearray(memory.length), tum byte'lar 0
2. Her input section bytes'larini hesaplanan adrese kopyala
3. Her relocation icin:
       a) instr_addr = section.finalAddr + reloc.offset
       b) sym_addr   = local lookup OR globalTable[name]
                         bulunamazsa -> UNDEFINED_REFERENCE
       c) target     = sym_addr + addend
       d) Tipine gore patchle:
            R_RISCV_BRANCH      offset = target - instr_addr
            R_RISCV_JAL         offset = target - instr_addr
            R_RISCV_HI20        imm20  = ((target + 0x800) >> 12) & 0xFFFFF
            R_RISCV_LO12_I      imm12  = target & 0xFFF
            R_RISCV_LO12_S      imm12  = target & 0xFFF (S-type bit dagilimi)
            R_RISCV_PCREL_HI20  imm20  = ((target - instr_addr + 0x800) >> 12)
            R_RISCV_PCREL_LO12  imm12  = (target - (instr_addr - 4)) & 0xFFF
       e) Range overflow kontrol (BRANCH ±4KB, JAL ±1MB)
4. Image'i Verilog $readmemh formatinda HEX olarak yaz
5. Memory map raporu yaz (.map dosyasi)
```

`R_RISCV_PCREL_LO12_I` icin referans noktasinin **bir onceki AUIPC**
olmasi (instr_addr - 4) standart RISC-V psABI gerekligi olarak literaturde
belirtilmistir; bu kural patch sirasinda dikkatle uygulanmistir (PC17).

## 5. Karsilasilan Problemler ve Cozumleri

Proje gelistirilirken karsilasilan en onemli sorunlar (PC7):

1. **`.word` direktifi misalignment hatasi (PicoRV32 trap):**
   `.string "counter = 0x"` (13 byte) sonrasi gelen `.word 0xDEADBEEF`
   adresleme acisindan 4-byte hizali olmadigi icin PicoRV32'nin
   `CATCH_MISALIGN=1` ozelligi trap urettiginden program donmektedir.
   Cozum: kullanici acikca `.align 4` yazar ya da ileride otomatik
   alignment eklenebilir.

2. **`LI` ile 32-bit signed degerlerin (`0xDEADBEEF`) yuklenmesi:**
   Python'da int sinirsiz oldugundan basit `>> 12` ve `& 0xFFF` kullanimi
   `0xDEADBEEF` gibi negatif 32-bit degerlerde yanlis sonuc uretir.
   Cozum: `imm = imm & 0xFFFFFFFF` ile 32-bit'e cekme + signed yorum +
   sign-extension dengeleme (`lower & 0x800` ise upper'a +1 ekle).

3. **`PCREL_LO12_I` patch'inde referans noktasi:**
   Naif uygulamada `imm12 = target & 0xFFF` yapildigi icin AUIPC ile
   olusan PC-rel taban kayboluyordu. Dogru formul:
   `imm12 = (target - (instr_addr_lo - 4)) & 0xFFF`.

4. **iverilog HEX yolu bagil olunca `$readmemh` bulamiyordu:**
   `run_sim.sh` build dizinine `cd` ettigi icin bagil yol bozuluyordu.
   Cozum: scriptin basinda `realpath` ile mutlak yola cevirme.

5. **`.string "Hello, World"` parse'inda virgul:**
   Lexer virgule gore boldugu icin string icindeki virgulu kayboluyordu.
   Cozum: `.string` direktifi orijinal satirdan tirnak iki ucu
   arasini ozel olarak yakalayan bir helper kullaniyor (PC7).

## 6. Test Sonuclari

Proje 43 birim/uctan-uca testle dogrulanmistir; tumu basariyla geciyor (PC7):

```
$ python3 -m pytest tests/ -v
tests/test_encoder.py    9 PASS  (Proje-1, encoding)
tests/test_opcode.py     9 PASS  (Proje-1, opcode tablosu)
tests/test_parser.py     9 PASS  (Proje-1, parser)
tests/test_symbol.py     6 PASS  (Proje-1, sembol tablosu)
tests/test_e2e.py        9 PASS  (Proje-2, uctan uca)

============================== 43 passed in 26.35s ==============================
```

E2E testlerinin senaryolari:

| #   | Senaryo                                       | Beklenen sonuc                                |
| --- | --------------------------------------------- | --------------------------------------------- |
| 01  | LED counter sim                               | GPIO 0,1,2 yazar                              |
| 02  | multi-file (math_lib + main)                  | GPIO 22, 8, 42, 314, 0xDEADBEEF              |
| 03  | UART hello (uart_lib + main)                  | "Hello, FPGA from PicoRV32!" + counter satiri |
| 04  | Object format yapisi                          | magic + EXTERN + 2 reloc (PCREL_HI20+LO12_I)  |
| 05  | Multiple definition                           | LinkError("MULTIPLE_DEFINITION")              |
| 06  | Undefined reference                           | LinkError("UNDEFINED_REFERENCE")              |
| 07  | Memory overflow (.space 9000 > 8 KB)          | LinkError("tasildi")                          |
| 08  | .data section layout (pi_x100, magic_number)  | hex'te 314 ve 0xDEADBEEF ardisik              |
| 09  | Object roundtrip (write -> read -> compare)   | tum alanlar identik                           |

Iverilog simulasyon ciktisi ornegi (multi_file demosu):

```
[gpio 1230000] 0x00000016        # 22 (15 + 7)
[gpio 1970000] 0x00000008        # 8  (15 - 7)
[gpio 4690000] 0x0000002a        # 42 (7 * 6)
[gpio 5130000] 0x0000013a        # 314 (pi_x100, .data)
[gpio 5570000] 0xdeadbeef        # magic_number, .data
[tb] sim_done set, durduruluyor.
```

## 7. FPGA Kaynak Kullanimi

Vivado 2022.x ile Arty A7-35T (xc7a35ticsg324-1L) hedefiyle sentez yapildiginda
elde edilen yaklasik kaynak kullanimi (PC1):

| Resource    | Used  | Available | Util |
| ----------- | ----- | --------- | ---- |
| LUT         | ~1100 | 20800     | ~5%  |
| FF          | ~700  | 41600     | ~2%  |
| BRAM        | 2     | 50        | 4%   |
| IO          | 7     | 210       | 3%   |

(Sayilar tahmindir; ayrintili rapor `build/vivado/picorv32_soc.runs/impl_1/`
altindaki `utilization.rpt` dosyasinda yer alir.)

## 8. Surdurulebilirlik ve Etik

- Kaynak kodlar acik formatta (Python + Verilog) yazilmis, ders kapsaminda
  takim arkadaslarinin **inceleyebilir, gelistirebilir** olmasi
  hedeflenmistir (PC8).
- Bagimliliklar minimal tutulmus (sadece `pytest`, opsiyonel `iverilog`),
  bu sayede sistem kaynak tuketimi sinirlanmistir (PC8).
- PicoRV32 ISC lisansi ile dagitilan acik kaynak bir IP'dir; ilgili lisans
  hakki kaynak dosya icindeki yorumda korunmustur (PC9, PC10).

## 9. Takim Calismasi ve Sunum

Proje 4 kisilik ekiple yurutulmus, gorevler asagidaki gibi pay edilmistir
(PC12, PC13):

- Assembler genisletmeleri (direktif + pseudo + parser)
- Linker algoritmasi (Pass 1 + Pass 2 + relocation tipleri)
- Demo programlari (LED, multi-file, UART)
- FPGA donanim (SoC, wrapper, constraint, Vivado script)

Sunumda her uye **kendi yazdigi kodu satir bazli aciklayabilecek**
seviyede hazirlanmistir; kod karmasikligi bu nedenle dusuk tutulmustur
(uniform `if/elif` zinciri, sade dict tabanli sembol tablosu vb.).

## 10. Gelistirme Yol Haritasi

- `.word sym` icin `R_RISCV_32` mutlak relocation tipi eklenmesi
- `R_RISCV_RELAX` ile linker tarafinda `auipc+addi` cifti `addi`'ye
  daraltilmasi (kod boyutu optimizasyonu)
- Birden fazla memory bolgesi destegi (RAM + ROM ayrik)
- Daha kompakt ELF benzeri ikili `.o` formati
- Otomatik alignment (`.align` olmadan `.word`'den once 4-byte hizalama)

## 11. Sonuc

Hocanin Proje-2 sartlarinda tanimlanan tum bilesenler (linker, sembol
tablosu, external/global cozum, relocation, HEX cikti, FPGA uzerinde
calisma) basariyla yerine getirilmistir. 43 test (9 e2e dahil) gecmekte,
multi-file demosu PicoRV32 uzerinde beklenen 22 / 8 / 42 / 314 / 0xDEADBEEF
sonucunu uretmekte, UART hello demosu beklenen yaziyi konsola
basmaktadir (PC1, PC7).

---

## EK A: PicoRV32 Konfigurasyonu

```verilog
picorv32 #(
    .ENABLE_REGS_16_31  (1),
    .TWO_STAGE_SHIFT    (1),
    .BARREL_SHIFTER     (0),
    .ENABLE_MUL         (0),
    .ENABLE_DIV         (0),
    .ENABLE_IRQ         (0),
    .COMPRESSED_ISA     (0),
    .CATCH_MISALIGN     (1),
    .CATCH_ILLINSN      (1),
    .PROGADDR_RESET     (32'h00000000),
    .STACKADDR          (32'h00001FF0)
)
```

## EK B: Bellek Haritasi

| Adres        | Boyut  | Aciklama                  |
| ------------ | ------ | ------------------------- |
| 0x0000_0000  | 8 KB   | BRAM (.text + .data)      |
| 0x1000_0000  | 4 B    | GPIO_OUT (write/read)     |
| 0x1000_0004  | 4 B    | UART_TX (alt 8 bit)       |
| 0x1000_0008  | 4 B    | SIM_DONE (sim icin)       |

## EK C: Hizli Calistirma Komutlari

```bash
# Tum testler
python3 -m pytest tests/ -v

# Multi-file linker demosu
python3 bin/asm.py demos/multi_file/main.s     -o build/main.o
python3 bin/asm.py demos/multi_file/math_lib.s -o build/math_lib.o
python3 bin/ld.py  build/main.o build/math_lib.o \
    -o build/multi.hex --map build/multi.map
sim/run_sim.sh     build/multi.hex 200000 6

# UART hello demosu
python3 bin/asm.py demos/uart_hello/main.s     -o build/uart_main.o
python3 bin/asm.py demos/uart_hello/uart_lib.s -o build/uart_lib.o
python3 bin/ld.py  build/uart_main.o build/uart_lib.o -o build/uart.hex
sim/run_sim.sh     build/uart.hex 2000000

# FPGA bitstream
vivado -mode batch -source fpga/build_vivado.tcl -tclargs build/multi.hex
```
