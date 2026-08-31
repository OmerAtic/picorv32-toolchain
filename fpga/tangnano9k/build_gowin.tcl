# ============================================================
# build_gowin.tcl - Gowin IDE komut satiri (gw_sh) ile bitstream uretimi
# ============================================================
# Kullanim (proje kok dizininden):
#   gw_sh fpga/tangnano9k/build_gowin.tcl
# Cikti:  impl/pnr/picorv_loader.fs  (karta yuklenecek bitstream)
#
# Tang Nano 9K cihazi: GW1NR-LV9QN88PC6/I5  (aile: GW1NR-9C)
# ============================================================

set_device -name GW1NR-9C GW1NR-LV9QN88PC6/I5

# --- Kaynak dosyalar ---
add_file fpga/tangnano9k/tangnano9k_top.v
add_file fpga/tangnano9k/soc_loader.v
add_file fpga/tangnano9k/loader.v
add_file fpga/tangnano9k/uart_rx.v
add_file fpga/uart_tx.v
add_file sim/picorv32.v

# --- Kisitlar ---
add_file fpga/tangnano9k/tangnano9k.cst
add_file fpga/tangnano9k/tangnano9k.sdc

# --- Secenekler ---
set_option -top_module tangnano9k_top
set_option -output_base_name picorv_loader
set_option -verilog_std sysv2017

# Sentez + yerlesim + yonlendirme + bitstream
run all
