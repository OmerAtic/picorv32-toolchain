// CPU YOK: btn2'yi dogrudan UART'a basar (saf donanim).
// btn2 idle(1) -> '0' , basili(0) -> '1' gonderir. Periyodik.
module btn_uart_hw_top (
    input  wire       clk,
    input  wire       btn2,
    output wire       uart_tx,
    output wire [5:0] led
);
    reg [7:0] por = 0; reg rstn = 0;
    always @(posedge clk) if (por != 8'hFF) begin por<=por+1; rstn<=0; end else rstn<=1;

    reg [15:0] slow = 0; reg send = 0; reg [7:0] d = 8'h30; wire busy;
    always @(posedge clk) begin
        send <= 0; slow <= slow + 1;
        if (slow == 0 && !busy) begin
            d    <= btn2 ? 8'h30 : 8'h31;   // idle->'0', basili->'1'
            send <= 1;
        end
    end
    uart_tx #(.CLOCKS_PER_BIT(234)) tx (.clk(clk),.resetn(rstn),.valid(send),.data(d),.tx(uart_tx),.busy(busy));
    assign led = {btn2, 5'b11111};   // led5 de dogrudan btn2 (gorsel)
endmodule
