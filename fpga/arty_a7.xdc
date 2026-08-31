## ============================================================
## arty_a7.xdc - Digilent Arty A7-35T constraint dosyasi
## ============================================================
## PicoRV32 SoC top'u icin pin atamalari, clock spec'i.
## Sadece kullanilan sinyaller etkin; diger pinler comment'li.
## ============================================================

## --- Clock (100 MHz) ---
set_property -dict { PACKAGE_PIN E3   IOSTANDARD LVCMOS33 } [get_ports { CLK100MHZ }];
create_clock -add -name sys_clk_pin -period 10.00 -waveform {0 5} [get_ports { CLK100MHZ }];

## --- Reset push button (BTN0) ---
set_property -dict { PACKAGE_PIN C2   IOSTANDARD LVCMOS33 } [get_ports { BTN_RST }];

## --- LED'ler (LD0..LD3) ---
set_property -dict { PACKAGE_PIN H5   IOSTANDARD LVCMOS33 } [get_ports { LED[0] }];
set_property -dict { PACKAGE_PIN J5   IOSTANDARD LVCMOS33 } [get_ports { LED[1] }];
set_property -dict { PACKAGE_PIN T9   IOSTANDARD LVCMOS33 } [get_ports { LED[2] }];
set_property -dict { PACKAGE_PIN T10  IOSTANDARD LVCMOS33 } [get_ports { LED[3] }];

## --- UART (USB-UART bridge, J17 connector) ---
set_property -dict { PACKAGE_PIN D10  IOSTANDARD LVCMOS33 } [get_ports { UART_TXD }];

## --- Konfigurasyon: BPI quad SPI flash ---
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property CFGBVS VCCO     [current_design]
