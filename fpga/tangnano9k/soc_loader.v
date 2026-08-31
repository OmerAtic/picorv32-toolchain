// ============================================================
// soc_loader.v - Loader'li SoC (PicoRV32 + BRAM + IO + Loader)
// ============================================================
// 3. Proje ana modulu. Iki calisma modu vardir:
//
//   1) YUKLEME MODU (loading=1):
//      - PicoRV32 reset'te tutulur (cpu_resetn=0)
//      - UART'tan gelen program Loader FSM tarafindan BRAM'e yazilir
//      - UART verici loader'a aittir (ACK/NAK gonderir)
//
//   2) CALISMA MODU (loading=0, RUN komutundan sonra):
//      - PicoRV32 reset'ten birakilir, adres 0'dan baslar
//      - BRAM islemciye aittir (komut/veri okur-yazar)
//      - UART verici islemciye aittir (program seri cikti basabilir)
//
// Bellek haritasi (calisma modu):
//   0x0000_0000 - 0x0000_1FFF : BRAM (8 KB)
//   0x1000_0000               : GPIO_OUT  (LED'ler)
//   0x1000_0004               : UART_TX   (alt 8 bit)
//   0x1000_000C               : BTN_IN    (butonlar, salt okunur)
//
// NOT (Gowin sentez): BRAM, senkron-okumali + byte-strobe yazili
// olarak yazildi; GowinSynthesis bunu BSRAM blogu olarak cikartir.
// Eger arac LUT'a maplerse MEM_WORDS'u dusurun ya da Gowin SDPB IP
// kullanin.
// ============================================================

module soc_loader #(
    parameter CLOCKS_PER_BIT = 234   // 27 MHz / 115200 baud
) (
    input  wire        clk,
    input  wire        resetn,       // board reset (aktif dusuk)
    input  wire        uart_rx_pin,  // PC'den FPGA'e
    output wire        uart_tx_pin,  // FPGA'den PC'ye
    input  wire [1:0]  btn_in,       // butonlar (test programlari okur)
    output wire [31:0] gpio_out      // LED'lere baglanir
);

    // ============================================================
    // 1) UART ALICI
    // ============================================================
    wire [7:0] rx_data;
    wire       rx_valid;

    uart_rx #(.CLOCKS_PER_BIT(CLOCKS_PER_BIT)) rx_i (
        .clk    (clk),
        .resetn (resetn),
        .rx     (uart_rx_pin),
        .data   (rx_data),
        .valid  (rx_valid)
    );

    // ============================================================
    // 2) LOADER FSM
    // ============================================================
    wire        loading;
    wire        ld_tx_send;
    wire [7:0]  ld_tx_data;
    wire        ld_mem_we;
    wire [10:0] ld_mem_waddr;
    wire [31:0] ld_mem_wdata;
    wire        tx_busy;

    loader loader_i (
        .clk      (clk),
        .resetn   (resetn),
        .rx_valid (rx_valid),
        .rx_data  (rx_data),
        .tx_send  (ld_tx_send),
        .tx_data  (ld_tx_data),
        .tx_busy  (tx_busy),
        .mem_we   (ld_mem_we),
        .mem_waddr(ld_mem_waddr),
        .mem_wdata(ld_mem_wdata),
        .loading  (loading)
    );

    // CPU reset: board reset VE yukleme bitmis olmali
    wire cpu_resetn = resetn & ~loading;

    // ============================================================
    // 3) PicoRV32 CEKIRDEK
    // ============================================================
    wire        mem_valid;
    wire        mem_instr;
    reg         mem_ready;
    wire [31:0] mem_addr;
    wire [31:0] mem_wdata;
    wire [ 3:0] mem_wstrb;
    reg  [31:0] mem_rdata;

    picorv32 #(
        .ENABLE_COUNTERS  (0),
        .ENABLE_COUNTERS64(0),
        .ENABLE_REGS_16_31(1),
        .ENABLE_REGS_DUALPORT(1),
        .TWO_STAGE_SHIFT  (1),
        .BARREL_SHIFTER   (0),
        .ENABLE_MUL       (0),
        .ENABLE_DIV       (0),
        .ENABLE_FAST_MUL  (0),
        .ENABLE_IRQ       (0),
        .COMPRESSED_ISA   (0),
        .CATCH_MISALIGN   (1),
        .CATCH_ILLINSN    (1),
        .PROGADDR_RESET   (32'h0000_0000),
        .STACKADDR        (32'h0000_1FF0)
    ) cpu (
        .clk      (clk),
        .resetn   (cpu_resetn),
        .trap     (),
        .mem_valid(mem_valid),
        .mem_instr(mem_instr),
        .mem_ready(mem_ready),
        .mem_addr (mem_addr),
        .mem_wdata(mem_wdata),
        .mem_wstrb(mem_wstrb),
        .mem_rdata(mem_rdata),
        .mem_la_read (), .mem_la_write(), .mem_la_addr(),
        .mem_la_wdata(), .mem_la_wstrb(),
        .irq (32'h0), .eoi (),
        .trace_valid(), .trace_data()
    );

    // ============================================================
    // 4) Giris/Cikis register'lari
    // ============================================================
    reg [31:0] r_gpio_out;
    reg        r_uart_valid;
    reg [ 7:0] r_uart_data;
    reg [ 7:0] r_rx_data;     // UART'tan gelen son bayt (calisma modu)
    reg        r_rx_ready;    // 1 = okunmamis yeni bayt var

    assign gpio_out = r_gpio_out;

    // ============================================================
    // 5) BRAM (8 KB = 2048 word) + veri yolu - TEK clocked blok
    //    Yukleme modunda loader yazar; calisma modunda CPU okur/yazar.
    //    (sim/soc.v ile ayni, kanitli desen + senkron BRAM okuma)
    // ============================================================
    localparam MEM_WORDS = 2048;
    reg [31:0] mem [0:MEM_WORDS-1];

    wire        is_bram = (mem_addr[31:16] == 16'h0000);
    wire        is_io   = (mem_addr[31:16] == 16'h1000);
    wire [10:0] cpu_word_addr = mem_addr[12:2];   // 8 KB / 4 = 2048

    // Simulasyon icin baslangic degeri (Gowin'de de zararsiz)
    integer k;
    initial begin
        for (k = 0; k < MEM_WORDS; k = k + 1)
            mem[k] = 32'h0000_0013;    // NOP
        r_gpio_out   = 32'h0;
        r_uart_valid = 1'b0;
        r_uart_data  = 8'h0;
        r_rx_data    = 8'h0;
        r_rx_ready   = 1'b0;
        mem_ready    = 1'b0;
    end

    always @(posedge clk) begin
        r_uart_valid <= 1'b0;     // UART pulse: 1 cycle
        mem_ready    <= 1'b0;

        if (loading) begin
            // --- YUKLEME: loader BRAM'e program yaziyor ---
            if (ld_mem_we)
                mem[ld_mem_waddr] <= ld_mem_wdata;
        end
        else if (mem_valid && !mem_ready) begin
            // --- CALISMA: islemci veri yolu ---
            if (is_bram) begin
                if (mem_wstrb == 4'b0000) begin
                    mem_rdata <= mem[cpu_word_addr];           // okuma
                end else begin
                    if (mem_wstrb[0]) mem[cpu_word_addr][ 7: 0] <= mem_wdata[ 7: 0];
                    if (mem_wstrb[1]) mem[cpu_word_addr][15: 8] <= mem_wdata[15: 8];
                    if (mem_wstrb[2]) mem[cpu_word_addr][23:16] <= mem_wdata[23:16];
                    if (mem_wstrb[3]) mem[cpu_word_addr][31:24] <= mem_wdata[31:24];
                end
                mem_ready <= 1'b1;
            end
            else if (is_io) begin
                case (mem_addr[7:0])
                    8'h00: begin // GPIO_OUT -> LED
                        if (mem_wstrb != 4'b0000) r_gpio_out <= mem_wdata;
                        mem_rdata <= r_gpio_out;
                        mem_ready <= 1'b1;
                    end
                    8'h04: begin // UART_TX
                        if (mem_wstrb != 4'b0000) begin
                            r_uart_data  <= mem_wdata[7:0];
                            r_uart_valid <= 1'b1;
                        end
                        mem_rdata <= 32'h0;
                        mem_ready <= 1'b1;
                    end
                    8'h0C: begin // BTN_IN (salt okunur)
                        mem_rdata <= {30'h0, btn_in};
                        mem_ready <= 1'b1;
                    end
                    8'h10: begin // UART_RX_DATA (okununca ready temizlenir)
                        mem_rdata  <= {24'h0, r_rx_data};
                        r_rx_ready <= 1'b0;
                        mem_ready  <= 1'b1;
                    end
                    8'h14: begin // UART_RX_READY (bit0 = yeni bayt var mi)
                        mem_rdata <= {31'h0, r_rx_ready};
                        mem_ready <= 1'b1;
                    end
                    default: begin
                        mem_rdata <= 32'h0;
                        mem_ready <= 1'b1;
                    end
                endcase
            end
            else begin
                mem_rdata <= 32'hDEAD_CAFE;
                mem_ready <= 1'b1;
            end
        end

        // UART RX yakalama (calisma modu): gelen baytI sakla.
        // En sonda oldugu icin ayni cycle'da hem yeni bayt hem okuma gelirse
        // yeni bayt kazanir (r_rx_ready=1 kalir).
        if (!loading && rx_valid) begin
            r_rx_data  <= rx_data;
            r_rx_ready <= 1'b1;
        end
    end

    // ============================================================
    // 6) UART VERICI - loader (ACK/NAK) ile CPU (program ciktisi) muxlu
    // ============================================================
    wire       tx_valid = loading ? ld_tx_send : r_uart_valid;
    wire [7:0] tx_data  = loading ? ld_tx_data  : r_uart_data;

    uart_tx #(.CLOCKS_PER_BIT(CLOCKS_PER_BIT)) tx_i (
        .clk    (clk),
        .resetn (resetn),
        .valid  (tx_valid),
        .data   (tx_data),
        .tx     (uart_tx_pin),
        .busy   (tx_busy)
    );

endmodule
