// ============================================================
// tb.v - PicoRV32 SoC testbench (iverilog uyumlu)
// ============================================================
// Plusargs:
//   +hex=<path>      : BRAM init dosyasi (Verilog $readmemh format)
//   +cycles=N        : maksimum cycle sayisi (default: 200_000)
//   +max_gpio=M      : kac kez GPIO degismesi gozledikten sonra dur (default: 0=devre disi)
//   +trace=<file>    : VCD trace cikti (opsiyonel)
//
// Sim_done sinyali geldiginde (1 olunca) testbench durur.
// ============================================================

`timescale 1ns / 1ps

module tb;
    reg  clk    = 1'b0;
    reg  resetn = 1'b0;

    // 50 MHz simulasyon clock'u (20 ns periyot)
    always #10 clk = ~clk;

    initial begin
        // 5 cycle reset
        #100 resetn = 1'b1;
    end

    wire [31:0] gpio_out;
    wire        sim_done;
    wire        uart_valid;
    wire [ 7:0] uart_data;

    soc dut (
        .clk      (clk),
        .resetn   (resetn),
        .gpio_out (gpio_out),
        .uart_valid(uart_valid),
        .uart_data (uart_data),
        .sim_done (sim_done)
    );

    // ----------------------------------
    // GPIO degisimi izleme + maksimum gozlem sayisi
    // ----------------------------------
    reg  [31:0] last_gpio = 32'h0;
    integer     gpio_changes = 0;
    integer     max_gpio_changes = 0;

    always @(posedge clk) begin
        if (resetn) begin
            if (gpio_out !== last_gpio) begin
                $display("[gpio %0t] 0x%08x", $time, gpio_out);
                last_gpio <= gpio_out;
                gpio_changes <= gpio_changes + 1;
                if (max_gpio_changes != 0 && gpio_changes + 1 >= max_gpio_changes) begin
                    $display("[tb] max_gpio (%0d) saglandi, durduruluyor.",
                             max_gpio_changes);
                    $finish;
                end
            end
        end
    end

    // ----------------------------------
    // sim_done sinyali izleme
    // ----------------------------------
    always @(posedge clk) begin
        if (resetn && sim_done) begin
            $display("[tb] sim_done set, durduruluyor (cycle=%0t).", $time);
            $finish;
        end
    end

    // ----------------------------------
    // Maksimum cycle sayisi (timeout)
    // ----------------------------------
    integer max_cycles = 200_000;
    integer cycle_count = 0;

    always @(posedge clk) begin
        if (resetn) begin
            cycle_count <= cycle_count + 1;
            if (cycle_count >= max_cycles) begin
                $display("[tb] max_cycles (%0d) asildi, durduruluyor.",
                         max_cycles);
                $finish;
            end
        end
    end

    // ----------------------------------
    // Plusargs ve VCD
    // ----------------------------------
    reg [1023:0] vcd_path;

    initial begin
        if (!$value$plusargs("cycles=%d", max_cycles))
            max_cycles = 200_000;
        if (!$value$plusargs("max_gpio=%d", max_gpio_changes))
            max_gpio_changes = 0;

        if ($value$plusargs("trace=%s", vcd_path)) begin
            $dumpfile(vcd_path);
            $dumpvars(0, tb);
        end

        $display("[tb] PicoRV32 SoC simulasyonu basliyor (max_cycles=%0d, max_gpio=%0d).",
                 max_cycles, max_gpio_changes);
    end

endmodule
