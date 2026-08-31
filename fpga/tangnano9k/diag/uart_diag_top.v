// ============================================================
// uart_diag_top.v - UART/clock/reset TESHIS tasarimi
// ============================================================
// Amac: Loader'dan bagimsiz olarak donanimin temel calismasini test:
//   - LED'ler yanip soner  -> clock + reset + bitstream calisiyor
//   - UART'tan surekli 'U' (0x55) gonderir -> uart_tx pini + port kimligi
//   - Gelen baytI echo'lar -> uart_rx pini calisiyor
// ============================================================

module uart_diag_top (
    input  wire       clk,        // 27 MHz (pin 52)
    input  wire       btn1,       // (pin 3) kullanilmiyor ama cst'de var
    input  wire       uart_rx,    // PC -> FPGA (pin 18)
    output wire       uart_tx,    // FPGA -> PC (pin 17)
    output wire [5:0] led         // pin 10..16 (aktif dusuk)
);
    // POR
    reg [7:0] por = 8'h00;
    reg       rstn = 1'b0;
    always @(posedge clk) begin
        if (por != 8'hFF) begin por <= por + 1'b1; rstn <= 1'b0; end
        else rstn <= 1'b1;
    end

    // LED blink (gozle gorunur)
    reg [24:0] cnt = 0;
    always @(posedge clk) cnt <= cnt + 1'b1;
    assign led = ~{6{cnt[23]}};

    // UART RX
    wire [7:0] rxd;
    wire       rxv;
    uart_rx #(.CLOCKS_PER_BIT(234)) U_RX (
        .clk(clk), .resetn(rstn), .rx(uart_rx), .data(rxd), .valid(rxv));

    // UART TX: gelen baytI echo'la, bosta periyodik 'U' gonder
    reg        send = 1'b0;
    reg [7:0]  sdata = 8'h55;
    reg [15:0] slow = 0;
    wire       txbusy;
    always @(posedge clk) begin
        send <= 1'b0;
        slow <= slow + 1'b1;
        if (rxv) begin
            sdata <= rxd;            // echo
            send  <= 1'b1;
        end else if (slow == 16'd0 && !txbusy) begin
            sdata <= 8'h55;          // 'U'
            send  <= 1'b1;
        end
    end
    uart_tx #(.CLOCKS_PER_BIT(234)) U_TX (
        .clk(clk), .resetn(rstn), .valid(send), .data(sdata),
        .tx(uart_tx), .busy(txbusy));

endmodule
