// ============================================================
// soc.v - PicoRV32 + 8 KB BRAM + GPIO + UART (SoC top'u)
// ============================================================
// Memory map:
//   0x0000_0000 - 0x0000_1FFF : BRAM (8 KB, $readmemh ile init)
//   0x1000_0000               : GPIO_OUT  (32-bit write/read)
//   0x1000_0004               : UART_TX   (8-bit alt, $write ile basilir)
//   0x1000_0008               : SIM_DONE  (write 1 -> testbench durur)
//
// Bu modul iverilog ile simulasyon icindir; FPGA wrapper'i fpga/soc_top.v'dir.
// ============================================================

module soc #(
    // FPGA'da BRAM'i ilk degerlerle yuklemek icin kullanilir.
    // Bos string ise simulasyonda +hex=<path> plusarg'i okunur.
    parameter INIT_FILE = ""
) (
    input  wire        clk,
    input  wire        resetn,
    output wire [31:0] gpio_out,
    output wire        uart_valid,
    output wire [ 7:0] uart_data,
    output wire        sim_done
);

    // PicoRV32 mem interface
    wire        mem_valid;
    wire        mem_instr;
    reg         mem_ready;
    wire [31:0] mem_addr;
    wire [31:0] mem_wdata;
    wire [ 3:0] mem_wstrb;
    reg  [31:0] mem_rdata;

    // ----------------------------------
    // PicoRV32 cekirdek
    // ----------------------------------
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
        .ENABLE_IRQ_QREGS (0),
        .ENABLE_TRACE     (0),
        .COMPRESSED_ISA   (0),
        .CATCH_MISALIGN   (1),
        .CATCH_ILLINSN    (1),
        .PROGADDR_RESET   (32'h0000_0000),
        .STACKADDR        (32'h0000_1FF0)
    ) cpu (
        .clk      (clk),
        .resetn   (resetn),
        .trap     (),
        .mem_valid(mem_valid),
        .mem_instr(mem_instr),
        .mem_ready(mem_ready),
        .mem_addr (mem_addr),
        .mem_wdata(mem_wdata),
        .mem_wstrb(mem_wstrb),
        .mem_rdata(mem_rdata),
        // ek look-ahead arabirimleri kullanilmiyor
        .mem_la_read   (),
        .mem_la_write  (),
        .mem_la_addr   (),
        .mem_la_wdata  (),
        .mem_la_wstrb  (),
        // IRQ kapali
        .irq         (32'h0),
        .eoi         (),
        // Trace kapali
        .trace_valid (),
        .trace_data  ()
    );

    // ----------------------------------
    // BRAM (8 KB = 2048 word)
    // ----------------------------------
    localparam MEM_WORDS = 2048;
    reg [31:0] mem [0:MEM_WORDS-1];

    // BRAM init: simulasyonda +hex= plusarg, FPGA'da INIT_FILE parametresi
    initial begin : init_block
        reg [1023:0] hex_path;
        integer i;
        for (i = 0; i < MEM_WORDS; i = i + 1)
            mem[i] = 32'h00000013; // varsayilan: NOP
        if (INIT_FILE != "") begin
            $display("[soc] INIT_FILE=%0s", INIT_FILE);
            $readmemh(INIT_FILE, mem);
        end
        else if ($value$plusargs("hex=%s", hex_path)) begin
            $display("[soc] $readmemh %0s", hex_path);
            $readmemh(hex_path, mem);
        end
    end

    // ----------------------------------
    // GPIO ve UART register'lari
    // ----------------------------------
    reg [31:0] r_gpio_out;
    reg        r_sim_done;
    reg        r_uart_valid;
    reg [ 7:0] r_uart_data;

    assign gpio_out   = r_gpio_out;
    assign uart_valid = r_uart_valid;
    assign uart_data  = r_uart_data;
    assign sim_done   = r_sim_done;

    initial begin
        r_gpio_out   = 32'h0;
        r_sim_done   = 1'b0;
        r_uart_valid = 1'b0;
        r_uart_data  = 8'h0;
    end

    // ----------------------------------
    // Adres decode + bus arabirimi
    // ----------------------------------
    wire is_bram = (mem_addr[31:16] == 16'h0000);  // 0x0000_xxxx
    wire is_io   = (mem_addr[31:16] == 16'h1000);  // 0x1000_xxxx

    wire [12:0] bram_word_addr = mem_addr[14:2];   // 8 KB / 4 = 2048

    integer j;

    always @(posedge clk) begin
        // UART pulse (sadece tek cycle)
        r_uart_valid <= 1'b0;
        mem_ready    <= 1'b0;
        mem_rdata    <= 32'h0;

        if (mem_valid && !mem_ready) begin
            // BRAM
            if (is_bram) begin
                if (mem_wstrb == 4'b0000) begin
                    // Read
                    mem_rdata <= mem[bram_word_addr];
                end else begin
                    // Write (byte-strobe)
                    if (mem_wstrb[0]) mem[bram_word_addr][ 7: 0] <= mem_wdata[ 7: 0];
                    if (mem_wstrb[1]) mem[bram_word_addr][15: 8] <= mem_wdata[15: 8];
                    if (mem_wstrb[2]) mem[bram_word_addr][23:16] <= mem_wdata[23:16];
                    if (mem_wstrb[3]) mem[bram_word_addr][31:24] <= mem_wdata[31:24];
                end
                mem_ready <= 1'b1;
            end
            // I/O
            else if (is_io) begin
                case (mem_addr[7:0])
                    8'h00: begin // GPIO_OUT
                        if (mem_wstrb != 4'b0000) r_gpio_out <= mem_wdata;
                        mem_rdata <= r_gpio_out;
                        mem_ready <= 1'b1;
                    end
                    8'h04: begin // UART_TX
                        if (mem_wstrb != 4'b0000) begin
                            r_uart_data  <= mem_wdata[7:0];
                            r_uart_valid <= 1'b1;
                            $write("%c", mem_wdata[7:0]);
                            $fflush;
                        end
                        mem_rdata <= 32'h0;
                        mem_ready <= 1'b1;
                    end
                    8'h08: begin // SIM_DONE
                        if (mem_wstrb != 4'b0000)
                            r_sim_done <= mem_wdata[0];
                        mem_rdata <= {31'h0, r_sim_done};
                        mem_ready <= 1'b1;
                    end
                    default: begin
                        mem_rdata <= 32'h0;
                        mem_ready <= 1'b1;
                    end
                endcase
            end
            else begin
                // Bilinmeyen adres - rdata=0, ready
                mem_rdata <= 32'hDEADCAFE;
                mem_ready <= 1'b1;
            end
        end
    end

endmodule
