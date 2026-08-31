// ============================================================
// soc_top.v - FPGA top-level wrapper (Digilent Arty A7-35T)
// ============================================================
// 100 MHz board clock'u CLK_DIV ile bolerek CPU clock uretir.
// 4-flop reset senkronizatoru kullanir.
// SoC'i instantiate eder, GPIO'yu LED'lere, UART'i pinlere bagilar.
//
// Pin atamalari fpga/arty_a7.xdc'de.
// ============================================================

module soc_top (
    input  wire       CLK100MHZ,    // E3 - on-board oscillator
    input  wire       BTN_RST,      // C2 - reset push button (active high)
    output wire [3:0] LED,          // H5, J5, T9, T10 - 4 LED
    output wire       UART_TXD      // D10 - UART TX to host
);

    // ----------------------------------
    // Clock divider: 100 MHz -> 25 MHz (CPU)
    // 4'e bol; PicoRV32 25 MHz cevikse iyi
    // ----------------------------------
    reg [1:0] clk_div = 2'b00;
    always @(posedge CLK100MHZ) clk_div <= clk_div + 1'b1;
    wire cpu_clk = clk_div[1];

    // ----------------------------------
    // Reset senkronizatoru (4-flop)
    // BTN_RST aktif yuksek; resetn cpu_clk domain'inde aktif dusuk
    // ----------------------------------
    reg [3:0] rst_sync = 4'b0000;
    always @(posedge cpu_clk) begin
        rst_sync <= {rst_sync[2:0], ~BTN_RST};
    end
    wire cpu_resetn = rst_sync[3];

    // ----------------------------------
    // SoC
    // ----------------------------------
    wire [31:0] gpio_out;
    wire        uart_valid;
    wire [ 7:0] uart_data;
    wire        sim_done; // FPGA'da kullanilmaz

    soc #(
        .INIT_FILE ("rom.hex")    // build_vivado.tcl bu dosyayi proje srcs'ine kopyalar
    ) soc_i (
        .clk        (cpu_clk),
        .resetn     (cpu_resetn),
        .gpio_out   (gpio_out),
        .uart_valid (uart_valid),
        .uart_data  (uart_data),
        .sim_done   (sim_done)
    );

    // ----------------------------------
    // GPIO -> LED (alt 4 bit)
    // ----------------------------------
    assign LED = gpio_out[3:0];

    // ----------------------------------
    // UART TX (115_200 baud @ 25 MHz cpu_clk)
    // 25_000_000 / 115_200 ≈ 217
    // ----------------------------------
    uart_tx #(.CLOCKS_PER_BIT(217)) tx_i (
        .clk     (cpu_clk),
        .resetn  (cpu_resetn),
        .valid   (uart_valid),
        .data    (uart_data),
        .tx      (UART_TXD),
        .busy    ()
    );

endmodule
