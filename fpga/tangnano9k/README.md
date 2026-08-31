# Tang Nano 9K — FPGA Tabanlı UART Loader (Proje-3)

PicoRV32 (RV32I) için, programı **çalışma anında UART ile yükleyip çalıştıran**
loader. Hedef kart: **Sipeed Tang Nano 9K** (Gowin GW1NR-LV9QN88PC6).

## Dosyalar
| Dosya | Görev |
| ----- | ----- |
| `uart_rx.v` | 8N1 UART alıcı (115200 @ 27 MHz, CLOCKS_PER_BIT=234) |
| `loader.v` | CRC-16 doğrulamalı yükleyici FSM (ACK/NAK, RUN) |
| `soc_loader.v` | PicoRV32 + 8 KB BRAM + GPIO/UART/BTN + loader (BRAM mux + reset gating) |
| `tangnano9k_top.v` | Board üst modülü (saat, POR reset, LED active-low, buton) |
| `tangnano9k.cst` | Gowin pin kısıtları (clk52, LED 10-16, btn 3/4, UART 17/18) |
| `tangnano9k.sdc` | 27 MHz saat zamanlaması |
| `../uart_tx.v` | UART verici (ACK/NAK + program çıktısı için, ortak) |
| `../../sim/picorv32.v` | PicoRV32 çekirdeği (YosysHQ) |

## Çalıştırma (özet)
```bash
# Simülasyonla doğrula (donanımsız)
bash sim/run_loader_sim.sh         # loader handshake + CRC NAK testi
bash sim/run_loader_pipeline.sh    # gerçek toolchain → loader → exec (test1/2/3)

# Gerçek kartta: önce Gowin EDA ile bitstream üret (üst modül tangnano9k_top,
# kaynaklar: bu klasör + ../uart_tx.v + ../../sim/picorv32.v), karta yükle.
# Sonra programı seri porttan gönder:
python3 host/host_send.py --port /dev/tty.usbserial-XXXX --file build/loader_tests/test1_math.bin
```

## Pinler (Tang Nano 9K)
clk=52 (27 MHz) · LED[0..5]=10,11,13,14,15,16 (active-low) · S1(reset)=3 ·
S2(buton)=4 · UART_TX=17 · UART_RX=18 (onboard BL702 USB-UART köprüsü).

Ayrıntılı rapor: `REPORT_PROJE3.md`.
