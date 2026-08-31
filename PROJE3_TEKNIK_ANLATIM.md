# PROJE-3 — TEKNİK ANLATIM & SUNUM SAVUNMA KILAVUZU
## "Bu projede ne yaptık, kod nasıl çalışıyor, LED nasıl yanıyor, Gowin nasıl kullanılıyor?"

> Bu belge, sunumdaki **bireysel sorular** içindir. Her başlık, hocanın sorabileceği
> bir soruya cevaptır. Amaç: ekibin **her dosyanın ne yaptığını ve akışın nasıl
> işlediğini satır mantığıyla** anlatabilmesi.

---

## 0. TEK CÜMLEYLE: Bu projede ne yaptık?

> "Önceki iki projede yazdığımız **assembler** ve **linker** ile makine kodu üretiyoruz.
> Bu projede, o makine kodunu **bilgisayardan seri port (UART) ile FPGA'e gönderip**,
> FPGA üzerindeki **PicoRV32 işlemcisinin belleğine yazan ve işlemciyi çalıştıran**
> bir **yükleyici (loader)** tasarladık. Yani programı bitstream'e gömmeden, kart
> çalışırken yüklüyoruz."

Üç parça vardır:
1. **PC tarafı (yazılım):** `host/host_send.py` — Python, makine kodunu paketleyip CRC ile gönderir.
2. **FPGA tarafı (donanım):** `fpga/tangnano9k/*.v` — UART alıcı + Loader FSM + PicoRV32 + bellek.
3. **Araç zinciri:** Yosys/nextpnr/apicula (sentez) + openFPGALoader (karta yükleme).

---

## 1. UÇTAN UCA AKIŞ (en önemli bölüm)

Bir programın yazılmasından LED'in yanmasına kadar **8 adım**:

```
 [1] test1_math.s         (Assembly kaynak — biz yazdık)
        │  python bin/asm.py
        ▼
 [2] test1_math.o         (PCO v1 = JSON object dosyası: makine kodu + semboller)
        │  python bin/ld.py
        ▼
 [3] test1_math.bin       (ham makine kodu, 4'er bayt, küçük-endian)
        │  python host/host_send.py  (PC)
        ▼
 [4] UART çerçeveleri      (SYNC+CMD+ADRES+VERİ+CRC paketleri) ── seri port ──►
        ▼
 [5] uart_rx.v            (FPGA: seri biti bayta çevirir)
        ▼
 [6] loader.v (FSM)       (CRC kontrol → doğruysa BRAM'e yaz, ACK gönder)
        ▼
 [7] PicoRV32 reset'ten bırakılır (RUN komutu) → BRAM'deki programı çalıştırır
        ▼
 [8] sw a0,0(GPIO) → r_gpio_out=42 → led=~42 → LED'ler yanar
```

Adım 1-3 = **yazılım (PC)**. Adım 5-8 = **donanım (FPGA)**. Adım 4 = ikisinin arasındaki **protokol**.

---

## 2. "LED NASIL YANIYOR?" (adım adım, donanım sorusu)

Diyelim program LED'e 42 yazıyor. Sinyal şu yolu izler:

1. **Assembly:** `test1_math.s` içinde
   ```asm
   li   s0, 0x10000000     # GPIO_OUT adresi
   ...
   sw   a0, 0(s0)          # a0(=42) -> GPIO_OUT'a yaz
   ```
   `0x1000_0000` adresi **GPIO_OUT** (LED) register'ının adresidir (bellek-haritalı I/O).

2. **İşlemci (PicoRV32):** `sw` komutunu çalıştırınca bellek arayüzünü sürer:
   `mem_valid=1`, `mem_addr=0x10000000`, `mem_wstrb=1111` (yaz), `mem_wdata=42`.

3. **SoC adres çözme** (`soc_loader.v`, bölüm 5'teki `always` bloğu):
   - `is_io = (mem_addr[31:16] == 16'h1000)` → bu adres bir I/O adresi mi? **Evet.**
   - `case (mem_addr[7:0])` → alt bayt `0x00` → **GPIO_OUT** durumu.
   - `r_gpio_out <= mem_wdata;` → register 42 olur. `mem_ready <= 1` (işlem bitti).

4. **SoC çıkışı:** `assign gpio_out = r_gpio_out;` → `gpio_out = 42`.

5. **Üst modül** (`tangnano9k_top.v`):
   ```verilog
   assign led = ~gpio_out[5:0];   // 42 = 0b101010 -> led = 0b010101
   ```
   LED'ler **aktif-düşük**: pinde `0` = LED yanar. `42`'nin tersi `010101` olduğu için
   **LED1, LED3, LED5 yanar** (bir-atla desen).

6. **Pin ataması** (`tangnano9k.cst`): `led[0..5]` fiziksel pin `10,11,13,14,15,16`'ya bağlı.

> **Özet cevap:** "Program `0x1000_0000` adresine yazıyor; SoC bunu GPIO register'ına
> çeviriyor; üst modülde bu register'ın **terslenmiş** alt 6 biti LED pinlerine
> bağlanıyor (LED'ler aktif-düşük). Yani LED deseni = yazılan sayının ikili
> gösterimi."

---

## 3. "KOD KARTA NASIL GEÇİYOR?" (yükleme akışı, en kritik kısım)

Program, kart çalışırken UART ile yüklenir. Sırayla:

### 3a. PC tarafı — `host/host_send.py`
- `load_words()`: `.bin` dosyasını okur, her 4 baytı bir 32-bit komut yapar.
- `make_write_frame()`: komutları paketler:
  `[0x7E SYNC][0x01 WRITE][ADRES][word sayısı][veri...][CRC]`
- `crc16_ccitt()`: her paket için **CRC-16/CCITT** hesaplar (veri bütünlüğü).
- `send_with_ack()`: paketi seri porttan yollar, FPGA'den **ACK (0x79)** bekler;
  **NAK (0x6E)** veya cevap gelmezse paketi **yeniden gönderir** (en çok 5 kez).
- Tüm veri gidince **RUN** paketi (`0x7E 0x02 CRC`) gönderir.

### 3b. FPGA UART alıcı — `uart_rx.v`
Seri hattaki bitleri bayta çevirir (8N1: 1 start + 8 veri + 1 stop). Her bitin
**ortasında** örnekleme yapar (en güvenli nokta). Bir bayt tamamlanınca
`valid` sinyalini 1 cycle yükseltir.

### 3c. Loader FSM — `loader.v` (projenin kalbi)
Bir **sonlu durum makinesi** gelen baytları yorumlar:
- `S_SYNC` → `0x7E` bekle
- `S_CMD` → WRITE mi RUN mı?
- `S_ADDR_L/H`, `S_NWORDS` → adres ve sayıyı al
- `S_DATA` → her 4 baytı bir word yapıp **BRAM'e yaz** (`mem_we`, `mem_waddr`, `mem_wdata`)
- `S_CRC_H/L` → paketteki CRC'yi al
- `S_CHECK` → **hesaplanan CRC == gelen CRC** mı? Doğruysa ACK, yanlışsa NAK gönder
- `S_RUN` → RUN komutu doğruysa `loading=0` yap (işlemci serbest)

CRC, `crc16_next()` fonksiyonuyla **her bayt geldikçe** hesaplanır; host'taki Python
CRC'siyle **bit-bit aynıdır** (poly `0x1021`, başlangıç `0xFFFF`).

### 3d. İşlemci reset kontrolü — `soc_loader.v`
```verilog
wire cpu_resetn = resetn & ~loading;
```
- **Yükleme sırasında** (`loading=1`): `cpu_resetn=0` → PicoRV32 **reset'te bekler**,
  BRAM yazım portu **loader'a** aittir.
- **RUN'dan sonra** (`loading=0`): `cpu_resetn=1` → PicoRV32 **adres 0'dan** başlar,
  BRAM **işlemciye** geçer.

### 3e. Çalışma
İşlemci BRAM'deki programı çalıştırır; `sw` ile GPIO'ya yazınca **LED yanar** (bölüm 2).

> **Özet cevap:** "PC, makine kodunu CRC'li paketler halinde UART'tan yolluyor.
> FPGA'deki FSM her paketin CRC'sini kontrol edip doğruysa belleğe yazıyor, yanlışsa
> NAK ile tekrar istiyor. Yükleme bitince işlemciyi reset'ten bırakıyoruz; o da
> belleğe yazılan programı çalıştırıyor."

---

## 4. DOSYA DOSYA: HANGİ KOD NE YAPIYOR?

### Yazılım (PC tarafı)
| Dosya | Görev | İlişkili |
|---|---|---|
| `assembler/*.py` | **Proje-1:** Assembly → makine kodu (lexer→parser→encoder, iki geçiş) | `bin/asm.py` çağırır |
| `linker/*.py` | **Proje-2:** Çoklu `.o` birleştir + adres ata + `.bin`/`.hex` üret | `bin/ld.py` çağırır |
| `bin/asm.py` | Assembler CLI: `.s → .o` | `assembler.assemble.assemble_file` |
| `bin/ld.py` | Linker CLI: `.o → .bin/.hex/.map` | `linker.linker.link_objects` |
| **`host/host_send.py`** | **Proje-3 (YENİ):** `.bin`'i CRC'li paketlerle UART'tan gönderir | seri port, FPGA loader |

### Donanım (FPGA tarafı — `fpga/tangnano9k/`)
| Dosya | Görev | İlişkili |
|---|---|---|
| **`uart_rx.v`** | UART **alıcı** (seri → bayt), bit-ortası örnekleme | `loader.v`'ye bayt verir |
| **`loader.v`** | **Loader FSM** + CRC-16: paket çöz, doğrula, BRAM'e yaz, ACK/NAK, RUN | `uart_rx`, `uart_tx`, BRAM, `loading` |
| **`soc_loader.v`** | **SoC:** PicoRV32 + 8KB BRAM (loader/CPU mux) + I/O (GPIO/UART/buton) | hepsini birbirine bağlar |
| **`tangnano9k_top.v`** | **Üst modül:** saat, reset (POR), buton (S1), LED bağlama | `soc_loader`'ı sarmalar |
| `../uart_tx.v` | UART **verici** (bayt → seri); ACK/NAK + program çıktısı | `loader` ve CPU paylaşır |
| `../../sim/picorv32.v` | **PicoRV32 çekirdeği** (YosysHQ, hazır IP) | `soc_loader` instance eder |
| `tangnano9k.cst` | **Pin atamaları** (Gowin): clk52, LED10-16, btn3, UART17/18 | sentez |
| `tangnano9k.sdc` | Zamanlama kısıtı (27 MHz) | sentez |
| `build_oss.sh` | **Sentez script'i:** yosys→nextpnr→gowin_pack | bitstream üretir |

### Test programları (`demos/loader_tests/`)
| Dosya | Ne test eder |
|---|---|
| `test1_math.s` | Aritmetik → LED (matematik) |
| `test2_loop.s` | Döngü + dallanma → sayan LED |
| `test3_func_btn.s` | **Buton → fonksiyon çağrısı** (S1 bas → 15, boş → 3) |
| `test_func.s` / `test_funcloop.s` | Fonksiyon çağrısı (jal/ret) görsel demo |
| `test4_uart.s` | `.data` + string + alt program → UART çıkış |
| `uart_echo.s` | **UART giriş** oku → echo (giriş demosu) |

### Simülasyon (`sim/`)
| Dosya | Görev |
|---|---|
| `tb_loader.v` | Loader el-sıkışma + **bozuk CRC → NAK** testi |
| `tb_loader_file.v` | **Gerçek toolchain** çıktısını oynatıp uçtan uca test |
| `run_loader_sim.sh` / `run_loader_pipeline.sh` | Testleri çalıştıran script'ler |

---

## 5. VERİ YAPILARI ve ALGORİTMALAR (hoca "algoritma" sorarsa)

### 5a. UART çerçeve protokolü (veri yapısı)
```
WRITE:  0x7E | 0x01 | ADDR_L ADDR_H | NWORDS | <NWORDS×4 bayt> | CRC_H CRC_L
RUN:    0x7E | 0x02 | CRC_H CRC_L
ACK=0x79  NAK=0x6E
```
Neden böyle? **SYNC** baytı paket başını bulmak için; **CRC** veri bütünlüğü için;
**ACK/NAK** el-sıkışma (güvenilir aktarım) için.

### 5b. CRC-16/CCITT algoritması (hata kontrolü)
Her bayt için: `crc ^= (bayt<<8)`, sonra 8 kez: en üst bit 1 ise
`crc=(crc<<1)^0x1021` değilse `crc=crc<<1`. **Aynı algoritma** Python (`crc16_ccitt`)
ve Verilog (`crc16_next`)'de. ≤16-bit patlama hatalarını garanti yakalar.
→ "Loader Doğruluğu" puanının temeli.

### 5c. Loader FSM (algoritma)
11 durumlu sonlu durum makinesi (bölüm 3c). Karmaşıklık: her gelen bayt **O(1)**
işlenir; N baytlık program **O(N)** sürede yüklenir.

### 5d. BRAM çoklayıcı (mux) — kaynak paylaşımı
Tek bir 8KB BRAM iki "sahip" arasında paylaşılır:
- `loading=1` → loader yazar (CPU reset'te, çakışma yok).
- `loading=0` → CPU okur/yazar.
`if (loading) ... else if (mem_valid) ...` ile çözülür. Bu, **donanım-yazılım ortak
tasarımının** (co-design) kalbidir.

### 5e. İki geçişli assembler/linker (Proje-1/2 hatırlatma)
Sembol (etiket) adresleri ileri referans olabildiği için **iki geçiş**: 1. geçiş
adresleri/sembolleri toplar, 2. geçiş makine kodunu üretir. `symbol_table.py` =
dict (O(1) etiket→adres). `opcode_table.py` = komut→opcode/funct eşlemesi.

---

## 6. "GOWIN / ARAÇ ZİNCİRİ NASIL KULLANILIYOR?"

Verilog kodu doğrudan FPGA'de çalışmaz; **bitstream**'e çevrilmesi gerekir. Biz
**açık kaynak** akış kullandık (Gowin EDA GUI'sine alternatif):

```
Verilog (.v) ──[1] Yosys──► netlist ──[2] nextpnr──► yerleşim ──[3] gowin_pack──► .fs
                synth_gowin          (yerleştir+yönlendir)        (bitstream)
                                                                      │
                                                          [4] openFPGALoader
                                                                      ▼
                                                                 Tang Nano 9K
```

1. **Yosys** (`synth_gowin`): Verilog'u Gowin mantık hücrelerine (LUT, DFF, BSRAM) çevirir.
   - 8KB belleğimiz **4 BSRAM bloğuna** maplendi (LUT'a değil → verimli).
2. **nextpnr-himbaechel**: hücreleri fiziksel konuma yerleştirir, pinleri `.cst`'ye
   göre bağlar, yolları çizer. Sonuç: LUT %26, DFF %14, BSRAM 15%, **Fmax 87.5 MHz**.
   - **Kritik bayrak:** `--vopt disable_gp_clock_routing` — bunu vermezsek nextpnr,
     saat ağını **buton pininden** geçirip onu saat-girişi yapar ve buton okunmaz.
3. **gowin_pack** (apicula): yerleşimi gerçek `.fs` bitstream'ine çevirir.
4. **openFPGALoader**: bitstream'i karta yükler.
   - Bu kartta **SRAM yüklemesi kalıcı olmadığı** için **FLASH**'a yazıyoruz:
     `openFPGALoader -b tangnano9k -f impl/loader.fs` → sonra **kabloyu tak-çıkar**.

Tek komut: `bash fpga/tangnano9k/build_oss.sh` (1-3 adımı yapar).

> **Not:** Gowin EDA (resmi GUI) ile de aynısı yapılabilir; aynı `.v` + `.cst` + `.sdc`,
> üst modül `tangnano9k_top`. Sentez raporu oradan da alınır.

---

## 7. BELLEK HARİTASI (sık sorulur)

| Adres | İsim | Yön | Açıklama |
|---|---|---|---|
| `0x0000_0000`–`0x1FFF` | BRAM | R/W | 8 KB program + veri |
| `0x1000_0000` | GPIO_OUT | yaz | 6 LED |
| `0x1000_0004` | UART_TX | yaz | seri çıkış (alt 8 bit) |
| `0x1000_000C` | BTN_IN | oku | S1 butonu (bit0) |
| `0x1000_0010` | UART_RX_DATA | oku | gelen bayt |
| `0x1000_0014` | UART_RX_READY | oku | yeni bayt var mı (bit0) |

`is_io = (mem_addr[31:16]==0x1000)` ile I/O bölgesi, `is_bram = (==0x0000)` ile bellek
ayırt edilir.

---

## 8. HOCANIN SORABİLECEĞİ SORULAR + CEVAPLAR

**S: Programı neden UART'tan yüklüyorsunuz, bitstream'e gömseniz olmaz mı?**
C: Gömersek her program değişikliğinde yeniden sentez (dakikalar) + yeniden
programlama gerekir. Loader ile saniyeler içinde yeni program yükleriz — gerçek
gömülü sistemlerdeki "firmware güncelleme" mantığı.

**S: CRC olmasa ne olur?**
C: Seri hattaki tek bir bit hatası, belleğe yanlış komut yazar → işlemci çöker
(CATCH_ILLINSN trap) ya da yanlış çalışır. CRC + NAK-tekrar ile **veri kaybını kesin
önlüyoruz**. (Simülasyonda bozuk CRC → NAK → tekrar ile kanıtladık.)

**S: Yükleme sırasında işlemci ne yapıyor?**
C: **Reset'te bekliyor** (`cpu_resetn = resetn & ~loading`). Böylece loader belleğe
yazarken işlemci araya girmez (çakışma olmaz). Yükleme bitince reset bırakılır.

**S: İşlemci nasıl adres 0'dan başlıyor?**
C: PicoRV32 parametresi `PROGADDR_RESET = 0`. Reset bırakılınca PC=0 olur, ilk komutu
adres 0'dan getirir. Biz de programı 0'a yüklüyoruz.

**S: LED neden ters? (aktif-düşük)**
C: Kartta LED'in bir ucu 3.3V'a bağlı; FPGA pini `0` çekince akım akar, LED yanar.
Bu yüzden `led = ~gpio` yazıyoruz (1 yazınca yansın diye terslerken).

**S: Butonu okumakta neden zorlandınız?**
C: Buton pini saat-yetenekli bir GP pin. nextpnr, saat ağını bu pinden geçirip onu
saat-girişi yapıyordu. **Sistematik teşhisle** (izole buton testi çalıştı, CPU okuma
testi çalıştı → sorun yerleşimde) bulduk; `--vopt disable_gp_clock_routing` ile çözdük.
(Bu, "deney tasarımı ve analiz" — PÇ7.)

**S: Baud hızı nasıl tutuyor?**
C: 27 MHz saat / 115200 baud ≈ 234. Yani her bit 234 saat cycle'ı sürer
(`CLOCKS_PER_BIT=234`). Alıcı her bitin ortasında (117. cycle) örnekler.

**S: 8KB bellek FPGA'de nasıl duruyor?**
C: Sentez aracı, `reg [31:0] mem[0:2047]` dizisini **4 BSRAM bloğuna** mapledi (LUT'a
değil) — kaynak raporunda BSRAM 4/26 görünüyor.

**S: Bu projede sizin yazdığınız ne, hazır olan ne?**
C: Hazır: PicoRV32 çekirdeği (YosysHQ). **Bizim yazdığımız:** host_send.py, uart_rx.v,
loader.v (FSM+CRC), soc_loader.v (SoC+mux+I/O), tangnano9k_top.v, tüm testler ve
constraint dosyaları. Assembler/linker önceki projelerden (genişletildi).

---

## 9. KISA DEMO KOMUTLARI (sunumda)

```bash
# 1) Program derle
python3 bin/asm.py demos/loader_tests/test1_math.s -o build/loader_tests/t1.o
python3 bin/ld.py  build/loader_tests/t1.o -o build/loader_tests/t1.hex --bin build/loader_tests/t1.bin

# 2) (bir kez) bitstream üret + karta FLASH'la, sonra kabloyu tak-çıkar
bash fpga/tangnano9k/build_oss.sh
openFPGALoader -b tangnano9k -f impl/loader.fs

# 3) Programı UART'tan yükle (port adını 'ls /dev/cu.usbserial-*' ile bul)
python3 host/host_send.py --port /dev/cu.usbserial-1101 --file build/loader_tests/t1.bin
#   -> LED'lerde 42

# 4) Donanımsız doğrulama (simülasyon)
bash sim/run_loader_pipeline.sh
```
