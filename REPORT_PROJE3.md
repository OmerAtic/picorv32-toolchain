# PROJE-3 RAPORU
## PicoRV İşlemci Alt Kümesi (RV32I) için FPGA Tabanlı Loader Tasarımı

> **Ders:** BIL302  ·  **Üniversite:** Sakarya Uygulamalı Bilimler Üniversitesi, Bilgisayar Mühendisliği
> **Hedef Donanım:** Sipeed Tang Nano 9K (Gowin GW1NR-LV9QN88PC6)
> **Tarih:** 06.2026
>
> _Bu rapor PDF'e çevrildiğinde tüm metin **Courier New 10 pt** olmalıdır._
> _Dosya adı: `BIL302_PROJE3_A.XX_B.YY_C.ZZ_170526.PDF`_

**Ekip (DOLDURUNUZ):**

| Öğrenci | Numara | Ana Sorumluluk |
| ------- | ------ | -------------- |
| A. ...  | ...        | Loader FSM + UART RX (donanım) |
| B. ...  | ...    | Host yazılımı + protokol/CRC |
| C. ...  | ...    | SoC entegrasyonu + Tang Nano 9K constraint/sentez |
| D. ...  | ...    | Test senaryoları + rapor + video |

---

## ÖZET

Bu projede, daha önceki iki projede geliştirilen **assembler** (Proje-1) ve
**linker** (Proje-2) üzerine, linker çıktısını (`.bin`) bir PC'den seri port
(UART) üzerinden Sipeed Tang Nano 9K FPGA kartına aktaran ve PicoRV32 işlemci
çekirdeği üzerinde **fiziksel olarak çalıştıran** özgün bir **yükleyici
(loader)** sistem yazılımı tasarlanmıştır. Sistem; PC tarafında Python ile
yazılmış paketleyici bir host uygulaması, FPGA tarafında bir UART alıcı, bir
**CRC-16 doğrulamalı sonlu durum makinesi (FSM) loader** ve PicoRV32 + BRAM
SoC'undan oluşur. Veri kaybını kesin olarak önlemek için her paket CRC-16/CCITT
ile korunmuş, hatalı paketler NAK ile reddedilip yeniden istenmiştir. Tüm zincir
(assembler → linker → host → loader → işlemci) iverilog simülasyonunda uçtan uca
otomatik testlerle doğrulanmıştır (PÇ7).

---

## 1. GİRİŞ VE LİTERATÜR ARAŞTIRMASI

Bir programın işlemci üzerinde çalışabilmesi için, makine kodunun belleğe
yerleştirilip program sayacının (PC) başlangıç adresine yönlendirilmesi gerekir.
Gömülü sistemlerde bu görevi **yükleyici (loader)** üstlenir. Bu projede amaç,
kendi geliştirdiğimiz toolchain'in ürettiği makine kodunu, sentez anında
belleğe gömmek (`$readmemh`) yerine, **çalışma anında** seri haberleşme ile
FPGA'e yükleyip çalıştırmaktır. Böylece bitstream'i yeniden üretmeden farklı
programlar denenebilir; bu, ticari geliştirme akışlarındaki "flash/RAM
programlama" adımının eğitimsel bir karşılığıdır (PÇ6).

### 1.1. Gömülü Sistemlerde Program Yükleme Mimarileri

Literatürde FPGA/MCU tabanlı sistemlerde üç temel yükleme arayüzü yaygındır:

| Arayüz | Avantaj | Dezavantaj | Tipik kullanım |
| ------ | ------- | ---------- | -------------- |
| **UART** | Çok basit (2 telli), her kartta var, yazılımı kolay | Düşük hız (≤ ~1 Mbps) | Bootloader, ISP, hata ayıklama |
| **SPI**  | Daha hızlı, flash'a doğrudan yazım | Daha çok pin, master/slave kurulumu | Flash programlama, XIP |
| **JTAG** | Standart, devre-içi (in-circuit), debug | Özel donanım/adaptör, karmaşık protokol | Üretim programlama, debug |

Sipeed Tang Nano 9K kartı, **onboard BL702** çipi sayesinde USB-C üzerinden
hem JTAG hem **USB-UART köprüsü** sunar [5]. Bu projede, ek adaptör
gerektirmemesi, düşük karmaşıklığı ve öğrenci seviyesinde tam olarak
açıklanabilir olması nedeniyle **UART** seçilmiştir. Seçim, klasik "bootstrap
loader" kavramının (Beck, _System Software_) modern bir donanım karşılığıdır
ve hocamızın eğitim amaçlı mikro-bilgisayar mimarisi çalışmalarındaki
assembler/bellek-organizasyonu yaklaşımıyla uyumludur [7] (PÇ6).

### 1.2. Seri Haberleşme ve Veri Doğrulama Protokolleri

Seri hatta gürültü kaynaklı bit hataları olabileceğinden, aktarılan kodun
bütünlüğü **hata kontrol kodları** ile doğrulanmalıdır. Başlıca yöntemler:

- **Checksum (toplama sağlaması):** Baytların modüler toplamı. Hesabı çok
  ucuzdur ancak bit-yer-değiştirme ve çift hataları yakalama gücü zayıftır.
- **CRC (Cyclic Redundancy Check):** Veriyi bir polinoma bölerek kalanı üretir.
  Patlama (burst) hatalarını yüksek olasılıkla yakalar; donanımda bir kaydırma
  yazmacı ile ucuza gerçeklenir.

Koopman ve Chakravarty'nin gömülü ağlar için CRC polinom seçimi üzerine
çalışması [3], kısa mesajlarda CRC'nin checksum'a kıyasla belirgin biçimde
üstün Hamming uzaklığı sağladığını göstermektedir. Bu nedenle projede
**CRC-16/CCITT-FALSE** (üreteç polinomu `0x1021`, başlangıç `0xFFFF`) [4]
seçilmiştir: 16 bit ek yük ile ≤ 4095 bayt mesajlarda tüm tek-bit, çift-bit ve
≤ 16 bitlik patlama hatalarını garanti yakalar. Aynı algoritma host (Python) ve
FPGA (Verilog) tarafında **bit-bit aynı** gerçeklenerek uçtan uca tutarlılık
sağlanmıştır (PÇ6, PÇ7).

> **Atıf kriteri (≥3):** Bu bölümde RISC-V resmi ISA dokümanı [1], PicoRV32
> çekirdeği [2], CRC polinom seçimi akademik makalesi [3] ve ITU-T V.41 CRC
> standardı [4] kullanılmıştır. Bkz. **7. Kaynakça**.

---

## 2. SİSTEM MİMARİSİ VE DONANIM-YAZILIM ORTAK TASARIMI (CO-DESIGN)

Sistem, biri yazılım (PC) diğeri donanım (FPGA) olmak üzere iki tarafın ortak
tasarımıdır (PÇ6):

```
   PC (Host - Python)                  Tang Nano 9K (Gowin GW1NR-9)
 ┌─────────────────────┐            ┌──────────────────────────────────┐
 │ linker .bin/.hex oku │            │  uart_rx (pin 18)                │
 │ paketle + CRC-16 ekle│  USB-UART  │     │  bayt + valid                │
 │ seri porttan gönder  │ ─────────► │     ▼                            │
 │ ACK/NAK bekle        │ ◄───────── │  LOADER FSM ── CRC kontrol        │
 │ (yeniden gönderim)   │  (ACK/NAK) │     │ mem_we/addr/data             │
 │ RUN komutu gönder    │            │     ▼                            │
 └─────────────────────┘            │  BRAM (8 KB) ◄── mux ──► PicoRV32 │
                                     │     │ (yükleme: CPU reset'te)      │
                                     │     ▼ çalışma                     │
                                     │  GPIO→LED / BTN / UART_TX         │
                                     └──────────────────────────────────┘
```

### 2.1. Toolchain Arayüz Standartları

Üç araç arasındaki veri akışı ve dosya formatları net biçimde tanımlanmıştır:

```
 .s  ──asm.py──►  .o (PCO v1, JSON)  ──ld.py──►  .bin (ham, küçük-endian)
                                                  .hex ($readmemh)
                                                  .map (bellek haritası)
```

`.bin`, programın ham makine kodudur (her komut 4 bayt, küçük-endian). Host
uygulaması bu dosyayı okuyup aşağıdaki **çerçeve protokolü** ile paketler:

```
WRITE çerçevesi:  0x7E | 0x01 | ADDR_L | ADDR_H | NWORDS | <NWORDS×4 veri> | CRC_H | CRC_L
RUN   çerçevesi:  0x7E | 0x02 | CRC_H | CRC_L
   0x7E   : SYNC (çerçeve başı)
   ADDR   : word adresi (0..2047), küçük-endian
   NWORDS : pakette taşınan 32-bit word sayısı
   CRC    : CMD baytından veri sonuna kadarki baytlar üzerinden CRC-16/CCITT
FPGA yanıtı:  0x79 = ACK (CRC doğru)  /  0x6E = NAK (CRC yanlış → host tekrar gönderir)
```

El sıkışma (handshake): host her çerçeveden sonra ACK bekler; ancak ACK gelirse
bir sonraki çerçeveyi gönderir. NAK veya zaman aşımında çerçeve yeniden
gönderilir (en çok 5 deneme). Bu, veri kaybını **kesin** olarak önler (PÇ7).

### 2.2. FPGA Loader ve PicoRV32 Bellek Haritası (Memory Map)

**Çalışma modu bellek haritası:**

| Adres | Boyut | Açıklama |
| ----- | ----- | -------- |
| `0x0000_0000 – 0x0000_1FFF` | 8 KB | BRAM (program + veri) |
| `0x1000_0000` | 4 B | GPIO_OUT → 6 LED |
| `0x1000_0004` | 4 B | UART_TX (alt 8 bit) |
| `0x1000_000C` | 4 B | BTN_IN (S1 butonu, salt okunur) |
| `0x1000_0010` | 4 B | UART_RX_DATA (gelen bayt; okununca ready temizlenir) |
| `0x1000_0014` | 4 B | UART_RX_READY (bit0 = yeni bayt var) |

**Loader sonlu durum makinesi (FSM):**

```
        ┌──────────┐  rx=0x7E   ┌────────┐
        │  S_SYNC  │──────────► │ S_CMD  │
        └──────────┘            └───┬────┘
             ▲            WRITE │    │ RUN
             │                  ▼    └────────────────┐
             │           ┌──────────┐                 ▼
             │           │ S_ADDR_L │            ┌──────────┐
             │           └────┬─────┘            │ S_CRC_H  │◄────┐
             │                ▼                  └────┬─────┘     │
             │           ┌──────────┐                 ▼           │
             │           │ S_ADDR_H │            ┌──────────┐     │
             │           └────┬─────┘            │ S_CRC_L  │     │
             │                ▼                  └────┬─────┘     │
             │           ┌──────────┐                 ▼           │
             │           │ S_NWORDS │            ┌──────────┐     │
             │           └────┬─────┘    CRC OK? │ S_CHECK  │     │
             │                ▼          ┌───────┴────┬─────┘     │
             │           ┌──────────┐    │ ACK/NAK    │           │
             │           │  S_DATA  │────┘  gönder    ▼           │
             │           └──────────┘            ┌──────────┐     │
             │   word'ler bitince ───────────────│ S_WAITTX │─────┘
             │                                   └────┬─────┘  (WRITE → S_SYNC)
             │                          RUN & CRC OK  │
             │                                        ▼
             │                                   ┌──────────┐
             └───────────────────────────────── │  S_RUN   │  loading=0
                                                 └──────────┘ (CPU reset serbest)
```

**Yükleme/çalışma geçişi (kritik tasarım):** `loading=1` iken PicoRV32
`cpu_resetn = resetn & ~loading` ile **reset'te** tutulur ve BRAM yazım portu
loader'a aittir. RUN çerçevesi doğru CRC ile alınınca `loading=0` olur; işlemci
reset'ten bırakılır, adres `0`'dan komut getirmeye başlar ve BRAM işlemciye
geçer. UART verici de yükleme sırasında ACK/NAK için loader'a, çalışma sırasında
program çıktısı için işlemciye multiplekslenir (PÇ12).

---

## 3. DENEYSEL ÇALIŞMALAR, TEST VE ANALİZ

### 3.1. Deney Tasarımı ve Test Senaryoları

Sistemin doğruluğu, farklı karmaşıklıkta Assembly test programları ile FPGA'nın
**giriş ve çıkış** birimleri (UART, LED) kullanılarak sınanmıştır (PÇ7):

| # | Program | Test ettiği yetenek | I/O | Donanım sonucu |
| - | ------- | ------------------- | --- | -------------- |
| 1 | `test1_math.s` | Aritmetik (add, slli, addi) | **çıkış**: LED | **42** = LED `101010` ✓ |
| 2 | `test2_loop.s` | Döngü + dallanma + gecikme | **çıkış**: LED | İkili sayaç ✓ |
| 3 | `test_func.s` | **Fonksiyon çağrısı** (jal/ret + alt program) | **çıkış**: LED | `add(10,5)`=**15** = LED `001111` ✓ |
| 4 | `test4_uart.s` | `.data` + `la` + alt program | **çıkış**: UART | `LOADER-OK 42` ✓ |
| 5 | `uart_echo.s` | UART giriş okuma + döngü | **giriş**: UART, **çıkış**: UART/LED | `ABC123`→`ABC123` ✓ |
| 6 | `test3_func_btn.s` | **Buton girişi → fonksiyon çağrısı** | **giriş**: buton (S1) | S1 boş→3, basılı→`add(10,5)`=**15** ✓ |

Böylece FPGA'nın **hem girişi** (S1 butonu + UART RX) **hem çıkışı** (LED + UART TX)
gerçek donanımda kullanılmıştır. `test3` testinde S1 butonuna basıldığında program bir
alt programı (jal/ret) çağırıp 15 üretir (4 LED), bırakıldığında 3 gösterir (2 LED);
`uart_echo` testinde PC'den gönderilen `ABC123` dizesi FPGA tarafından okunup aynen
geri gönderilmiştir.

> **NOT (deney/analiz, PÇ7):** Buton girişi ilk denemede tam tasarımda (clock+UART
> ile) okunamadı; sistematik teşhisle (izole buton testi ✓, CPU okuma testi ✓)
> sorun, nextpnr'ın clock ağını clock-yetenekli buton GP pininden geçirip onu
> clock-girişi moduna almasına bağlandı. Çözüm: yer-yönlendirmeye
> **`--vopt disable_gp_clock_routing`** seçeneği eklendi; bundan sonra buton normal
> GPIO girişi olarak doğru okundu. (S1=pin 3 kullanıldı; S2=pin 4 JTAG ile paylaşımlı
> olduğundan tercih edilmedi. Reset için buton yerine güç döngüsü kullanılır.)

**Simülasyon doğrulaması (iverilog):** İki seviyede test yapılmıştır:

1. **`tb_loader.v`** — El ile kodlanmış bir program ve protokol kullanarak
   loader'ın tam el sıkışmasını doğrular. Ayrıca **bilerek bozulmuş CRC**
   gönderilip NAK (`0x6E`) ile reddedildiği, ardından doğru paketin ACK
   (`0x79`) aldığı kanıtlanır → veri doğrulama mekanizması çalışıyor.

2. **`tb_loader_file.v`** — **Gerçek toolchain çıktısını** kullanır:
   `host_send.py --emit-frames` ile üretilen gerçek çerçeveleri oynatır, böylece
   `assembler → linker → host → loader → PicoRV32` zincirini uçtan uca test eder.

**Elde edilen sonuçlar** (`sim/run_loader_pipeline.sh`):

```
TEST: test1_math       → 2 çerçeve, ACK=2 NAK=0, GPIO_OUT=42   ✓
TEST: test2_loop       → 2 çerçeve, ACK=2 NAK=0, yüklendi/çalıştı ✓
TEST: test3 (btn=0)    → 2 çerçeve, ACK=2 NAK=0, GPIO_OUT=3    ✓
TEST: test3 (btn=1)    → 2 çerçeve, ACK=2 NAK=0, GPIO_OUT=15   ✓
NAK testi (bozuk CRC)  → NAK ile reddedildi, tekrar→ACK        ✓
```

Tüm senaryolar başarıyla geçmiştir; loader hatalı paketi reddedip doğru paketi
kabul etmiş ve işlemci yüklenen programı doğru çalıştırmıştır (PÇ7).

### 3.2. Veri Toplama ve Donanım Metrikleri

**(a) Yükleme süreleri (farklı kod boyutları için).** Teorik alt sınır,
115200 baud'da bayt başına 10 bit (1 start + 8 veri + 1 stop) iletiminden gelir:

```
T_yükleme ≈ (Σ çerçeve_baytı × 10 bit) / 115200  +  N_çerçeve × t_ACK
1 bayt ≈ 86.8 µs
```

`host_send.py`, gerçek kartta yükleme süresini ve verimi (KB/s) otomatik
yazdırır. Aşağıdaki ölçümler **Tang Nano 9K üzerinde gerçek donanımda**
alınmıştır (115200 baud):

| Program | Word | Bayt | Teorik süre | **Ölçülen süre** | **Verim** |
| ------- | ---- | ---- | ----------- | ---------------- | --------- |
| test1 (math) | 12 | 48 | ≈ 4.2 ms | **9.4 ms**  | **4.98 KB/s** |
| test3 (func) | 19 | 76 | ≈ 6.6 ms | **12.4 ms** | **6.00 KB/s** |
| uart_echo    | 17 | 68 | ≈ 5.9 ms | **12.6 ms** | **5.27 KB/s** |
| test4 (UART) | 22 | 88 | ≈ 7.6 ms | **14.5 ms** | **5.94 KB/s** |

Gözlem: yükleme süresi kod boyutuyla yaklaşık doğrusal artar; ölçülenin
teorikten yüksek olması her paket için ACK gidiş-dönüşü ve host tarafı işleme
gecikmesindendir. **Doğrulama:** test4 yüklendikten sonra PicoRV32 UART'tan
`LOADER-OK 42` dizesini geri göndererek programın gerçek FPGA üzerinde
çalıştığı kanıtlanmıştır.

**(b) FPGA kaynak tüketimi.** Tasarım açık kaynak akışıyla (Yosys + nextpnr-
himbaechel + apicula) GW1NR-9C için sentezlenmiştir. **Gerçek** kaynak
kullanımı (nextpnr "Device utilisation" raporundan):

| Kaynak | Kullanılan | Toplam | Yüzde |
| ------ | ---------- | ------ | ----- |
| LUT4   | 2300       | 8640   | **26%** |
| Register (DFF) | 967 | 6480   | **14%** |
| ALU    | 366        | 6480   | 5%    |
| **BSRAM** | **4**   | 26     | **15%** |
| IOB    | 11         | 276    | 3%    |

Maksimum çalışma frekansı **87.5 MHz** olarak raporlanmış olup, 27 MHz sistem
saatinin çok üzerindedir (zamanlama rahatlıkla sağlanır).

> **NOT (PÇ7):** 8 KB ana bellek başarıyla **4 adet BSRAM bloğuna** maplenmiştir
> (LUT'a değil), bu da tasarımın verimli olduğunu gösterir. Sayılar tahmin değil,
> sentez aracının doğrudan çıktısıdır. Gowin EDA kullanılırsa "Resource Usage"
> raporundaki rakamlar benzer olacaktır.

---

## 4. PROJENİN KÜRESEL, TOPLUMSAL VE EKONOMİK ETKİLERİ (PÇ8)

### 4.1. Sürdürülebilirlik ve Yeşil Bilişim (SKA 7, SKA 13)
PicoRV32, boyut-optimize bir RISC-V çekirdeğidir [2]; bu projede yalnızca temel
RV32I alt kümesi, çarpan/bölücü olmadan kullanılmıştır. Daha az transistör/LUT,
daha düşük dinamik güç demektir. Programı bitstream'e gömmek yerine UART ile
yüklemek, her deneme için yeniden sentez/yeniden programlama enerjisini ortadan
kaldırır — geliştirme döngüsünün karbon ayak izini azaltır (SKA 7 Temiz Enerji,
SKA 13 İklim Eylemi). Yazılım tarafında kod boyutu optimizasyonu (kısa
programlar → kısa yükleme → daha az aktif süre) bu etkiyi pekiştirir.

### 4.2. Ekonomik Sürdürülebilirlik ve Teknolojik Bağımsızlık (SKA 8, SKA 9)
RISC-V açık ve telifsiz bir komut kümesi mimarisidir [1]; lisans ücreti
gerektirmez. Kapalı/ticari mimarilere (ör. lisanslı çekirdekler) kıyasla, özgün
bir toolchain + loader geliştirmek Ar-Ge maliyetini düşürür ve **yerli çip
ekosistemi** için temel bir yetkinlik kazandırır (SKA 8 İnsana Yakışır İş ve
Ekonomik Büyüme, SKA 9 Sanayi-Yenilikçilik-Altyapı). Bu çalışma, üniversite
düzeyinde tam bir araç zincirinin (assembler+linker+loader) sıfırdan
kurulabildiğini göstererek dışa bağımlılığı azaltır.

### 4.3. Fonksiyonel Güvenlik ve Sağlık (SKA 3)
Geliştirilen **CRC-16 doğrulamalı, NAK-tekrarlı** loader, koda bozuk komut
yazılmasını engeller. Tıbbi cihaz, otomotiv ve savunma gibi kritik gömülü
sistemlerde, belleğe yanlış bir komutun yazılması ölümcül arızalara yol
açabilir; hata kontrollü yükleme bu riski azaltarak insan hayatı ve iş
güvenliğine katkı sağlar (SKA 3 Sağlıklı Bireyler).

### 4.4. E-Atık Yönetimi ve Döngüsel Ekonomi (SKA 12)
Loader sayesinde aynı FPGA donanımı, fiziksel değişiklik gerektirmeden seri port
üzerinden **uzaktan güncellenebilir (OTA benzeri)**. Bu, cihazın yazılımının
eskimesi nedeniyle çöpe atılmasını geciktirir, donanımın yeniden
kullanılabilirliğini artırır ve elektronik atığı azaltır (SKA 12 Sorumlu Üretim
ve Tüketim).

---

## 5. PROJE YÖNETİMİ VE TAKIM ÇALIŞMASI (PÇ12, PÇ13)

### 5.1. Görev Dağılımı ve Sorumluluk Matrisi (RACI)
> R = Yapan (Responsible), A = Onaylayan (Accountable), C = Danışılan, I = Bilgilendirilen

| İş paketi | A.(Donanım) | B.(Host/Protokol) | C.(SoC/Sentez) | D.(Test/Rapor) |
| --------- | :---------: | :---------------: | :------------: | :------------: |
| UART RX + Loader FSM | **R/A** | C | C | I |
| CRC-16 (host+FPGA tutarlılığı) | C | **R/A** | I | C |
| Host gönderici (paket/ACK/NAK) | I | **R/A** | I | C |
| SoC + BRAM mux + reset gating | C | I | **R/A** | I |
| Tang Nano 9K constraint + Gowin sentez | I | I | **R/A** | C |
| Test senaryoları + simülasyon | C | C | I | **R/A** |
| Rapor + video | I | C | C | **R/A** |

### 5.2. Koordinasyon ve Sürüm Kontrol Yönetimi
Proje **Git** ile sürümlenmiştir (dal: `Atakan-Branch`). Modüller arası **arayüz
sözleşmeleri** (çerçeve protokolü, bellek haritası, CRC parametreleri) önceden
yazılı olarak sabitlenip her üyenin bağımsız çalışabilmesi sağlanmıştır.
Entegrasyon, iverilog simülasyonundaki ortak testbench üzerinden yürütülmüş;
haftalık çevrim-içi/karma toplantılarla ilerleme takip edilmiştir. _(Gantt
şeması ve toplantı notları eklenebilir.)_

---

## 6. BİREYSEL KATKI BEYANI (PÇ12)

> _Her öğrenci ayrı doldurup imzalayacaktır._

**Öğrenci A (...):** "Grup çalışmasından bağımsız olarak ____ modülünü tamamen
kendim tasarladım. Karşılaştığım en büyük teknik problem ____ idi; bunu ____
yaparak tek başıma çözdüm." _(İmza)_

**Öğrenci B / C / D:** _(aynı şablon)_

---

## 7. KAYNAKÇA

[1] A. Waterman, K. Asanović (Ed.), _The RISC-V Instruction Set Manual, Volume I:
    Unprivileged ISA_, RISC-V International.
[2] C. Wolf, _PicoRV32 — A Size-Optimized RISC-V CPU_, YosysHQ.
    https://github.com/YosysHQ/picorv32
[3] P. Koopman, T. Chakravarty, "Cyclic Redundancy Code (CRC) Polynomial
    Selection for Embedded Networks," _Int. Conf. on Dependable Systems and
    Networks (DSN)_, 2004.
[4] ITU-T Recommendation V.41, _Code-Independent Error-Control System_ (CRC-CCITT).
[5] Sipeed, _Tang Nano 9K Datasheet & Documentation_, wiki.sipeed.com.
[6] GOWIN Semiconductor, _GW1NR Series FPGA Products Data Sheet (DS117)_.
[7] H. Öztekin, F. Temurtaş, A. Gülbağ, "BZK.SAU.FPGA10.1: A Modular Approach to
    FPGA-Based Micro Computer Architecture Design for Educational Purpose,"
    _Computer Applications in Engineering Education_, 2014.

---

## EK-A: GERÇEK DONANIMDA ÇALIŞTIRMA ADIMLARI

**1) Programı derle ve linkle:**
```bash
python3 bin/asm.py demos/loader_tests/test1_math.s -o build/loader_tests/test1.o
python3 bin/ld.py  build/loader_tests/test1.o -o build/loader_tests/test1.hex \
        --bin build/loader_tests/test1.bin
```

**2) Bitstream üret (bu projede kullanılan AÇIK KAYNAK akış):**
```bash
# OSS CAD Suite (yosys + nextpnr-himbaechel + apicula) ile:
bash fpga/tangnano9k/build_oss.sh          # -> impl/loader.fs
```
> Alternatif: Gowin EDA (GUI). Üst modül `tangnano9k_top`, kaynaklar
> `fpga/tangnano9k/*.v` + `sim/picorv32.v` + `fpga/uart_tx.v`, constraint
> `tangnano9k.cst`/`.sdc`. Gowin EDA, 1.8 V buton bankını da doğru kurar.

**3) Karta yükle (⚠️ bu kartta SRAM yüklemesi kalıcı olmadığı için FLASH'a):**
```bash
openFPGALoader -b tangnano9k -f impl/loader.fs   # -f = FLASH, sonra kabloyu tak-çıkar
```

**4) Programı seri porttan yükle ve çalıştır:**
```bash
# UART portunu bul (tak-çıkar sonrası ad değişebilir):
ls /dev/cu.usbserial-*        # örn: /dev/cu.usbserial-1101
python3 host/host_send.py --port /dev/cu.usbserial-1101 --file build/loader_tests/test1.bin
# Çıktı: yükleme süresi + "Islemci reset'ten birakildi" → LED'lerde 42

# Giriş testi (UART): program çalışırken PC'den bayt gönder, FPGA echo'lar
python3 host/host_send.py --port /dev/cu.usbserial-1101 --file build/loader_tests/uart_echo.bin --listen 5
```

**4) Simülasyonla doğrula (donanımsız):**
```bash
bash sim/run_loader_sim.sh        # el-kodlu loader testi (ACK/NAK + exec)
bash sim/run_loader_pipeline.sh   # gerçek toolchain → loader → exec (test1/2/3)
```

## EK-B: VİDEO PLANI (≤ 5 dk, özgeçmiş kalitesinde)
1. (0:00–0:30) Problem: "Programı bitstream'e gömmeden, çalışırken UART ile yükle."
2. (0:30–1:30) Mimari animasyonu: host → UART → Loader FSM → BRAM → PicoRV32.
3. (1:30–3:00) **Canlı çıkış demosu:** `host_send.py` ile test1 yükle (LED'de 42),
   test2 sayaç, test4 (UART'tan `LOADER-OK 42`).
4. (3:00–4:00) **Canlı giriş demosu:** (a) `test3` yükle, **S1 butonuna bas** →
   LED 2'den 4'e çıkıyor (buton → fonksiyon çağrısı); (b) `uart_echo` yükle,
   PC'den bayt gönder → FPGA aynen geri yolluyor. Sonra CRC sağlamlığı: bozuk
   paket → NAK → yeniden gönderim (`tb_loader` simülasyonu).
5. (4:00–5:00) Kaynak raporu (LUT %26, BSRAM 4) + sürdürülebilirlik (RISC-V açık
   mimari, OTA, e-atık).
