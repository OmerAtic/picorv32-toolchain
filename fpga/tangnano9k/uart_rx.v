// ============================================================
// uart_rx.v - 8N1 UART alici (receiver)
// ============================================================
// Seri hattan (rx) gelen baytlari yakalar.
// 1 start biti + 8 veri biti + 1 stop biti, parity yok.
// Her bit ortasinda ornekleme yapar (en guvenli nokta).
//
// Tang Nano 9K: 27 MHz clk, 115200 baud => CLOCKS_PER_BIT = 234
//   27_000_000 / 115_200 = 234.375 -> 234 (hata ~%0.16, kabul edilir)
//
// Cikis: 'valid' 1 cycle pulse olur ve 'data' o an gecerli bayttir.
// ============================================================

module uart_rx #(
    parameter CLOCKS_PER_BIT = 234
) (
    input  wire       clk,
    input  wire       resetn,
    input  wire       rx,          // seri giris (asenkron)
    output reg  [7:0] data,        // alinan bayt
    output reg        valid        // 1 cycle pulse: yeni bayt hazir
);

    // Asenkron rx hattini 2 flop ile senkronize et (metastability korumasi)
    reg rx_sync_0, rx_sync_1;
    always @(posedge clk) begin
        rx_sync_0 <= rx;
        rx_sync_1 <= rx_sync_0;
    end
    wire rx_in = rx_sync_1;

    localparam IDLE  = 2'd0;
    localparam START = 2'd1;
    localparam DATA  = 2'd2;
    localparam STOP  = 2'd3;

    reg [1:0]  state;
    reg [15:0] clk_count;
    reg [2:0]  bit_index;

    always @(posedge clk) begin
        if (!resetn) begin
            state     <= IDLE;
            clk_count <= 0;
            bit_index <= 0;
            data      <= 8'h00;
            valid     <= 1'b0;
        end else begin
            valid <= 1'b0;   // valid sadece 1 cycle yuksek kalir

            case (state)
                // --- Bos: start biti (rx=0) bekle ---
                IDLE: begin
                    clk_count <= 0;
                    bit_index <= 0;
                    if (rx_in == 1'b0)   // dusen kenar = start
                        state <= START;
                end

                // --- Start bitinin ORTASINA git, hala 0 mi diye bak ---
                START: begin
                    if (clk_count == (CLOCKS_PER_BIT-1)/2) begin
                        if (rx_in == 1'b0) begin
                            clk_count <= 0;
                            state     <= DATA;   // gercek start biti
                        end else begin
                            state <= IDLE;       // gurultu, vazgec
                        end
                    end else begin
                        clk_count <= clk_count + 1'b1;
                    end
                end

                // --- 8 veri bitini, her birinin ortasinda ornekle ---
                DATA: begin
                    if (clk_count < CLOCKS_PER_BIT-1) begin
                        clk_count <= clk_count + 1'b1;
                    end else begin
                        clk_count   <= 0;
                        data[bit_index] <= rx_in;   // LSB once gelir
                        if (bit_index < 7) begin
                            bit_index <= bit_index + 1'b1;
                        end else begin
                            bit_index <= 0;
                            state     <= STOP;
                        end
                    end
                end

                // --- Stop biti: 1 bit boyu bekle, sonra valid bas ---
                STOP: begin
                    if (clk_count < CLOCKS_PER_BIT-1) begin
                        clk_count <= clk_count + 1'b1;
                    end else begin
                        clk_count <= 0;
                        valid     <= 1'b1;   // bayt hazir!
                        state     <= IDLE;
                    end
                end

                default: state <= IDLE;
            endcase
        end
    end

endmodule
