// ============================================================
// uart_tx.v - 8N1 UART verici (sabit baud)
// ============================================================
// Bir byte'i CLOCKS_PER_BIT cycle'da gonderir (start + 8 data + stop).
// SoC'un uart_valid pulse'unu bekler, ondan sonra TX'e basar.
//
// Default: 100 MHz clk, 115_200 baud => CLOCKS_PER_BIT = 868
// CPU 25 MHz olursa CLOCKS_PER_BIT degisir (parametre).
// ============================================================

module uart_tx #(
    parameter CLOCKS_PER_BIT = 868     // 100 MHz / 115_200 baud
) (
    input  wire       clk,
    input  wire       resetn,
    input  wire       valid,           // 1 cycle pulse: data hazir
    input  wire [7:0] data,
    output reg        tx,
    output wire       busy
);

    localparam IDLE  = 2'd0;
    localparam START = 2'd1;
    localparam DATA  = 2'd2;
    localparam STOP  = 2'd3;

    reg [1:0]  state;
    reg [15:0] clk_count;
    reg [2:0]  bit_index;
    reg [7:0]  shift;

    assign busy = (state != IDLE);

    always @(posedge clk) begin
        if (!resetn) begin
            state     <= IDLE;
            tx        <= 1'b1;
            clk_count <= 0;
            bit_index <= 0;
            shift     <= 0;
        end else begin
            case (state)
                IDLE: begin
                    tx        <= 1'b1;
                    clk_count <= 0;
                    bit_index <= 0;
                    if (valid) begin
                        shift <= data;
                        state <= START;
                    end
                end

                START: begin
                    tx <= 1'b0;  // start bit
                    if (clk_count < CLOCKS_PER_BIT - 1)
                        clk_count <= clk_count + 1;
                    else begin
                        clk_count <= 0;
                        state     <= DATA;
                    end
                end

                DATA: begin
                    tx <= shift[bit_index];
                    if (clk_count < CLOCKS_PER_BIT - 1)
                        clk_count <= clk_count + 1;
                    else begin
                        clk_count <= 0;
                        if (bit_index < 7)
                            bit_index <= bit_index + 1;
                        else begin
                            bit_index <= 0;
                            state     <= STOP;
                        end
                    end
                end

                STOP: begin
                    tx <= 1'b1;
                    if (clk_count < CLOCKS_PER_BIT - 1)
                        clk_count <= clk_count + 1;
                    else begin
                        clk_count <= 0;
                        state     <= IDLE;
                    end
                end

                default: state <= IDLE;
            endcase
        end
    end

endmodule
