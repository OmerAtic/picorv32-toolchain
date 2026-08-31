// ============================================================
// tb_loader_file.v - GERCEK toolchain ciktisini loader ile dogrula
// ============================================================
// Bu testbench tam zinciri otomatik test eder:
//   .s  --(assembler)-->  .o  --(linker)-->  .bin
//       --(host_send.py --emit-frames)-->  cerceve baytlari
//       --(bu TB UART ile oynatir)-->  Loader FSM
//       --(reset birakilir)-->  PicoRV32 programi calistirir
//
// Cerceve dosyasi ve beklenen GPIO degeri plusarg ile verilir:
//   vvp out.out +frames=build/.../test1.frames +expect=42
// ============================================================

`timescale 1ns/1ps

module tb_loader_file;

    localparam CPB = 16;   // CLOCKS_PER_BIT (sim)

    reg clk = 0;
    reg resetn = 0;
    reg rx = 1'b1;
    wire tx;
    wire [31:0] gpio_out;
    reg [1:0] btn = 2'b00;

    always #5 clk = ~clk;

    soc_loader #(.CLOCKS_PER_BIT(CPB)) dut (
        .clk(clk), .resetn(resetn),
        .uart_rx_pin(rx), .uart_tx_pin(tx),
        .btn_in(btn), .gpio_out(gpio_out)
    );

    // ---- Bir baytI UART ile gonder ----
    task uart_send_byte(input [7:0] b);
        integer i;
        begin
            rx = 1'b0; repeat (CPB) @(posedge clk);
            for (i = 0; i < 8; i = i + 1) begin
                rx = b[i]; repeat (CPB) @(posedge clk);
            end
            rx = 1'b1; repeat (CPB) @(posedge clk);
        end
    endtask

    // ---- Arka planda tx'i dinle (ACK/NAK say) ----
    reg [7:0] last_byte;
    integer   ack_count = 0, nak_count = 0, ri;
    always begin
        @(negedge tx);
        repeat (CPB + CPB/2) @(posedge clk);
        for (ri = 0; ri < 8; ri = ri + 1) begin
            last_byte[ri] = tx; repeat (CPB) @(posedge clk);
        end
        if (dut.loader_i.loading) begin
            // yukleme suresince: ACK/NAK
            if (last_byte == 8'h79) ack_count = ack_count + 1;
            else if (last_byte == 8'h6E) nak_count = nak_count + 1;
        end else begin
            // calisma suresince: programin UART ciktisi
            $write("%c", last_byte);
        end
    end

    reg [7:0]   frame [0:511];
    integer     fd, flen, k, nframes, prev_ack, code;
    reg [1023:0] frames_path;
    integer     expected;

    initial begin
        if (!$value$plusargs("frames=%s", frames_path)) begin
            $display("HATA: +frames=<dosya> verilmedi"); $finish;
        end
        if (!$value$plusargs("expect=%d", expected)) expected = -1;
        if ($value$plusargs("btn=%d", k)) btn = k[1:0];   // buton durumu (test3)

        fd = $fopen(frames_path, "r");
        if (fd == 0) begin $display("HATA: dosya acilamadi %0s", frames_path); $finish; end

        // ---- Reset ----
        resetn = 0; repeat (20) @(posedge clk);
        resetn = 1; repeat (20) @(posedge clk);

        // ---- Her cerceveyi gonder, ACK/NAK bekle (gercek el sikisma) ----
        nframes = 0;
        prev_ack = 0;
        while ($fscanf(fd, "%d", flen) == 1) begin
            // cerceve baytlarini oku
            for (k = 0; k < flen; k = k + 1)
                code = $fscanf(fd, "%h", frame[k]);
            nframes = nframes + 1;
            // cerceveyi UART'tan gonder
            for (k = 0; k < flen; k = k + 1)
                uart_send_byte(frame[k]);
            // bu cerceve icin ACK/NAK gelene kadar bekle
            wait ((ack_count + nak_count) > prev_ack);
            prev_ack = ack_count + nak_count;
        end
        $fclose(fd);
        $display("[tb] %0d cerceve gonderildi. ACK=%0d NAK=%0d", nframes, ack_count, nak_count);

        // ---- Program calissin ----
        if (!$value$plusargs("runcycles=%d", code)) code = 3000;
        repeat (code) @(posedge clk);

        $display("[tb] GPIO_OUT=%0d (beklenen %0d)", gpio_out, expected);
        if (nak_count == 0 && (expected < 0 || gpio_out == expected))
            $display("[tb] === GERCEK TOOLCHAIN -> LOADER TESTI GECTI ===");
        else
            $display("[tb] === BASARISIZ ===");
        $finish;
    end

    initial begin
        #20_000_000;
        $display("[tb] TIMEOUT"); $finish;
    end

endmodule
