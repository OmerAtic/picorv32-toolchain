// ============================================================
// tangnano9k_top.v - FPGA top-level (Sipeed Tang Nano 9K)
// ============================================================
// Board: Gowin GW1NR-LV9QN88PC6 (Tang Nano 9K)
//   - 27 MHz onboard clock (pin 52)
//   - 6 LED (pin 10,11,13,14,15,16) - AKTIF DUSUK (0=yanar)
//   - S1 buton (pin 3, ust/IOT bank 1.8V) -> KULLANICI GIRISI (test programlari okur)
//   - UART (onboard BL702 USB-UART): TX pin 17, RX pin 18 @115200
//
// NOT: Reset icin buton kullanilmaz; reset = guc dongusu (kabloyu tak-cikar).
// Giris butonu = S1 (pin 3). S2 (pin 4) JTAG ile paylasimli oldugu icin secilmedi.
// ONEMLI: Butonun GERCEK KARTTA okunabilmesi icin sentezde (build_oss.sh)
// nextpnr'a `--vopt disable_gp_clock_routing` verilmelidir. Aksi halde nextpnr
// clock agini clock-yetenekli buton GP pininden gecirip onu clock-girisi moduna
// alir ve buton normal GPIO olarak okunamaz.
//
// Pin atamalari fpga/tangnano9k/tangnano9k.cst dosyasinda.
// ============================================================

module tangnano9k_top (
    input  wire       clk,        // 27 MHz (pin 52)
    input  wire       btn1,       // S1 kullanici butonu (pin 3) - GIRIS
    input  wire       uart_rx,    // PC -> FPGA (pin 18)
    output wire       uart_tx,    // FPGA -> PC (pin 17)
    output wire [5:0] led         // pin 10,11,13,14,15,16 (aktif dusuk)
);

    // ----------------------------------
    // Power-on reset (POR) - reset icin buton yok
    // ----------------------------------
    reg [7:0] por_cnt    = 8'h00;
    reg       por_resetn = 1'b0;
    always @(posedge clk) begin
        if (por_cnt != 8'hFF) begin
            por_cnt    <= por_cnt + 1'b1;
            por_resetn <= 1'b0;
        end else begin
            por_resetn <= 1'b1;
        end
    end
    wire resetn = por_resetn;

    // ----------------------------------
    // Kullanici girisi: S1 butonu (pin 3), 2-flop senkronizasyon
    // Buton basili degilken hat=1 (pull-up), basiliyken=0.
    // btn_in[0] = ~S1  -> basiliyken 1 okunur.
    // ----------------------------------
    reg [2:0] btn1_sync = 3'b111;
    always @(posedge clk) btn1_sync <= {btn1_sync[1:0], btn1};
    wire [1:0] buttons = {1'b0, ~btn1_sync[2]};   // btn_in[0] = S1 (basili=1)

    // ----------------------------------
    // SoC (Loader + PicoRV32 + BRAM + IO)
    // ----------------------------------
    wire [31:0] gpio_out;

    soc_loader #(
        .CLOCKS_PER_BIT(234)    // 27 MHz / 115200 baud
    ) soc_i (
        .clk        (clk),
        .resetn     (resetn),
        .uart_rx_pin(uart_rx),
        .uart_tx_pin(uart_tx),
        .btn_in     (buttons),
        .gpio_out   (gpio_out)
    );

    // ----------------------------------
    // GPIO -> LED (aktif dusuk: yazilen 1 biti LED'i yakar)
    // ----------------------------------
    assign led = ~gpio_out[5:0];

endmodule
