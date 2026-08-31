# Teslim Paketi (Proje-2)

Bu klasorde hocanin sartnamesinde istenen tum kod artifactlari yer alir:
en az 2 farkli .o dosyasi + bunlarin linklenmis HEX ciktisi.

## Klasor Icerigi

Her demo icin ayri alt klasor:

```
dist/
  led_counter/
      led_counter.s         # kaynak
      led_counter.o         # PCO v1 object dosyasi
      led_counter.hex       # Verilog $readmemh formati (BRAM init)
      led_counter.bin       # raw binary (LE)
      led_counter.ihex      # Intel HEX
      led_counter.map       # memory map raporu

  multi_file/               # math_lib + main (linker demosu, 2 dosya)
      main.s, math_lib.s
      main.o, math_lib.o    # 2 farkli object dosyasi
      multi_file.hex        # linklenmis cikti
      multi_file.bin
      multi_file.ihex
      multi_file.map

  uart_hello/               # uart_lib + main (UART demosu, 2 dosya)
      ...
```

## Beklenen Davranislar (iverilog simulasyonunda dogrulandi)

| Demo         | Beklenen Cikti                                                |
| ------------ | ------------------------------------------------------------- |
| led_counter  | GPIO_OUT 0,1,2,3,... yazar (8-bit overflow)                   |
| multi_file   | GPIO 22, 8, 42, 314, 0xDEADBEEF (sirasiyla)                   |
| uart_hello   | UART: "Hello, FPGA from PicoRV32!\ncounter = 0xdeadbeef\n" |

## FPGA Yukleme

`*.hex` dosyalari Vivado'da `$readmemh` ile BRAM'e yuklenir.
`fpga/build_vivado.tcl` scripti hex dosyasini otomatik kopyalar:

```bash
vivado -mode batch -source fpga/build_vivado.tcl \
       -tclargs dist/multi_file/multi_file.hex
```

## Tekrar Uretim

Bu klasor bilgisayardan silinirse asagidaki komutla yeniden uretilir:

```bash
python3 scripts/build_dist.py
```
