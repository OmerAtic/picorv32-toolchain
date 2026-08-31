// ============================================================
// tb_loader.v - Loader uctan uca simulasyon testi (iverilog)
// ============================================================
// Bu testbench, gercek donanim olmadan Loader'in dogrulugunu kanitlar:
//   1) PC'nin yerine UART uzerinden bir program paketi gonderir
//      (WRITE cercevesi, CRC-16 ile),
//   2) FPGA'nin ACK (0x79) gonderdigini dogrular,
//   3) RUN cercevesi gonderir,
//   4) PicoRV32 reset'ten birakilinca programin GPIO_OUT'a 42 (0x2A)
//      yazdigini dogrular.
//
// Yuklenen program (elle RV32I kodlandi):
//   addi a0, x0, 42       ; a0 = 42
//   lui  a1, 0x10000      ; a1 = 0x10000000 (GPIO_OUT adresi)
//   sw   a0, 0(a1)        ; GPIO_OUT = 42
//   jal  x0, 0            ; sonsuz dongu (burada kal)
//
// Calistirma: sim/run_loader_sim.sh
// ============================================================

`timescale 1ns/1ps

module tb_loader;

    // Simulasyonu hizlandirmak icin kucuk bit suresi
    localparam CPB = 16;   // CLOCKS_PER_BIT (sim)

    reg clk = 0;
    reg resetn = 0;
    reg rx = 1'b1;             // UART hatti bosta 1
    wire tx;
    wire [31:0] gpio_out;
    reg [1:0] btn = 2'b00;

    always #5 clk = ~clk;      // 100 MHz sim clock (periyot 10 ns)

    // ---- DUT ----
    soc_loader #(.CLOCKS_PER_BIT(CPB)) dut (
        .clk        (clk),
        .resetn     (resetn),
        .uart_rx_pin(rx),
        .uart_tx_pin(tx),
        .btn_in     (btn),
        .gpio_out   (gpio_out)
    );

    // ---- CRC-16/CCITT (loader/host ile ayni) ----
    function [15:0] crc16_next;
        input [15:0] crc_in;
        input [7:0]  b;
        integer i;
        reg [15:0] c;
        begin
            c = crc_in ^ (b << 8);
            for (i = 0; i < 8; i = i + 1)
                c = c[15] ? (c << 1) ^ 16'h1021 : (c << 1);
            crc16_next = c;
        end
    endfunction

    // ---- Bir baytI UART ile gonder (8N1, LSB once) ----
    task uart_send_byte(input [7:0] b);
        integer i;
        begin
            // start biti
            rx = 1'b0;
            repeat (CPB) @(posedge clk);
            // 8 veri biti
            for (i = 0; i < 8; i = i + 1) begin
                rx = b[i];
                repeat (CPB) @(posedge clk);
            end
            // stop biti
            rx = 1'b1;
            repeat (CPB) @(posedge clk);
        end
    endtask

    // ---- Arka planda tx hattini SUREKLI dinleyen UART cozucu ----
    // (Boylece ACK start bitini kaciran kenar-yaris sorunu olmaz.)
    reg  [7:0] last_byte;
    integer    rx_count;
    integer    ri;
    initial    rx_count = 0;
    always begin
        @(negedge tx);                         // start biti
        repeat (CPB + CPB/2) @(posedge clk);   // bit0 ortasina git
        for (ri = 0; ri < 8; ri = ri + 1) begin
            last_byte[ri] = tx;                // LSB once
            repeat (CPB) @(posedge clk);
        end
        rx_count = rx_count + 1;               // yeni bayt geldi
    end

    // ---- Sonraki FPGA baytini bekle (seviye-duyarli, yaris yok) ----
    integer prev_count;
    task wait_byte(output [7:0] b);
        begin
            wait (rx_count > prev_count);
            prev_count = rx_count;
            b = last_byte;
        end
    endtask

    // ---- Test programi (4 word) ----
    reg [31:0] prog [0:3];
    reg [7:0]  body [0:63];
    integer    body_len;
    reg [15:0] crc;
    reg [7:0]  ack;
    integer    j, w;

    initial begin
        $dumpfile("sim/tb_loader.vcd");
        $dumpvars(0, tb_loader);

        prev_count = 0;

        prog[0] = 32'h02A00513; // addi a0,x0,42
        prog[1] = 32'h100005B7; // lui  a1,0x10000
        prog[2] = 32'h00A5A023; // sw   a0,0(a1)
        prog[3] = 32'h0000006F; // jal  x0,0

        // ---- WRITE cercevesi govdesi: CMD,ADDR_L,ADDR_H,NWORDS,veri ----
        body[0] = 8'h01;        // CMD_WRITE
        body[1] = 8'h00;        // ADDR_L (word 0)
        body[2] = 8'h00;        // ADDR_H
        body[3] = 8'h04;        // NWORDS = 4
        for (w = 0; w < 4; w = w + 1) begin
            body[4 + w*4 + 0] = prog[w][ 7: 0];
            body[4 + w*4 + 1] = prog[w][15: 8];
            body[4 + w*4 + 2] = prog[w][23:16];
            body[4 + w*4 + 3] = prog[w][31:24];
        end
        body_len = 4 + 16;      // 20 bayt

        // CRC hesapla
        crc = 16'hFFFF;
        for (j = 0; j < body_len; j = j + 1)
            crc = crc16_next(crc, body[j]);

        // ---- Reset ----
        resetn = 0;
        repeat (20) @(posedge clk);
        resetn = 1;
        repeat (20) @(posedge clk);

        // ---- TEST 1: BOZUK CRC -> NAK beklenir (veri dogrulama kaniti) ----
        $display("[tb] [NAK testi] Bilerek BOZUK CRC ile WRITE gonderiliyor...");
        uart_send_byte(8'h7E);
        for (j = 0; j < body_len; j = j + 1)
            uart_send_byte(body[j]);
        uart_send_byte(crc[15:8] ^ 8'hFF);     // CRC'yi boz
        uart_send_byte(crc[7:0]);
        wait_byte(ack);
        if (ack == 8'h6E) $display("[tb] [NAK testi] BASARILI: bozuk paket NAK (0x6E) ile reddedildi.");
        else $display("[tb] [NAK testi] UYARI: yanit 0x%02x (NAK 0x6E beklenmisti).", ack);

        // ---- TEST 2: DOGRU WRITE -> ACK beklenir ----
        $display("[tb] WRITE paketi gonderiliyor (%0d bayt veri)...", body_len);
        uart_send_byte(8'h7E);                 // SYNC
        for (j = 0; j < body_len; j = j + 1)
            uart_send_byte(body[j]);
        uart_send_byte(crc[15:8]);             // CRC_H
        uart_send_byte(crc[7:0]);              // CRC_L

        // ---- ACK bekle ----
        wait_byte(ack);
        if (ack == 8'h79) $display("[tb] WRITE -> ACK (0x79) alindi. OK");
        else begin
            $display("[tb] HATA: WRITE yaniti 0x%02x (ACK degil)", ack);
            $finish;
        end

        // ---- RUN cercevesi: SYNC,0x02,CRC ----
        crc = 16'hFFFF;
        crc = crc16_next(crc, 8'h02);
        $display("[tb] RUN paketi gonderiliyor...");
        uart_send_byte(8'h7E);
        uart_send_byte(8'h02);
        uart_send_byte(crc[15:8]);
        uart_send_byte(crc[7:0]);

        wait_byte(ack);
        if (ack == 8'h79) $display("[tb] RUN -> ACK (0x79) alindi. Islemci basliyor.");
        else begin
            $display("[tb] HATA: RUN yaniti 0x%02x", ack);
            $finish;
        end

        // ---- Program calissin, GPIO_OUT'u kontrol et ----
        repeat (200) @(posedge clk);
        if (gpio_out == 32'd42) begin
            $display("[tb] BASARILI: GPIO_OUT = %0d (beklenen 42).", gpio_out);
            $display("[tb] === LOADER TESTI GECTI ===");
        end else begin
            $display("[tb] BASARISIZ: GPIO_OUT = %0d (beklenen 42).", gpio_out);
        end

        $finish;
    end

    // guvenlik: takilirsa bitir
    initial begin
        #5_000_000;
        $display("[tb] TIMEOUT - simulasyon cok uzun surdu.");
        $finish;
    end

endmodule
