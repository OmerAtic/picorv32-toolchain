// ============================================================
// tangnano9k.sdc - Gowin zamanlama kisiti
// ============================================================
// 27 MHz saat -> periyot = 1/27e6 = 37.037 ns
create_clock -name clk -period 37.037 -waveform {0 18.518} [get_ports {clk}]
