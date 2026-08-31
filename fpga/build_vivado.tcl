## ============================================================
## build_vivado.tcl - Vivado batch sentez/implementasyon scripti
## ============================================================
## Kullanim:
##   vivado -mode batch -source fpga/build_vivado.tcl -tclargs build/multi.hex
##
## Argumanlar:
##   tclargs[0] = BRAM init icin .hex dosyasi (mutlak yol verilebilir)
## ============================================================

# --- Argumanlar
if { $::argc < 1 } {
    puts "Usage: vivado -mode batch -source build_vivado.tcl -tclargs <hex_file>"
    exit 1
}

set hex_file [lindex $::argv 0]
puts "build_vivado: HEX=$hex_file"

# --- Proje ayarlari ---
set project_name "picorv32_soc"
set part         "xc7a35ticsg324-1L"   ;# Arty A7-35T
set top_module   "soc_top"

# --- Calismak istedigimiz dizin ---
set proj_dir "build/vivado"
file mkdir $proj_dir

# Eger eski proje varsa kapat
catch {close_project}

# --- Yeni proje olustur ---
create_project -force $project_name $proj_dir -part $part

# --- Kaynak dosyalari ekle ---
set rtl_files [list \
    "sim/picorv32.v" \
    "sim/soc.v"      \
    "fpga/uart_tx.v" \
    "fpga/soc_top.v" \
]
add_files -norecurse $rtl_files

# Constraints
add_files -fileset constrs_1 -norecurse "fpga/arty_a7.xdc"

# --- HEX init dosyasini soc.v'nin gorebilecegi yere kopyala ---
# soc.v $readmemh icin yol parametresi alir, fakat FPGA flow'unda
# default'u "rom.hex" olarak ayarliyoruz (soc.v'de gerekirse degistirilir).
# Vivado bu dosyayi default $readmemh path'i olarak gormeli.
set rom_target "$proj_dir/$project_name.srcs/sources_1/rom.hex"
file copy -force $hex_file $rom_target

# soc.v'de $value$plusargs FPGA'da plusarg olmadigi icin etkisiz;
# bunun icin ya soc.v'yi build oncesi yamalayabilirsiniz, ya da
# ayri bir _fpga.v wrapper kullaniyoruz. Simdilik eski $readmemh'i
# default "rom.hex" yapacak sekilde sekillendirelim:
puts "build_vivado: rom.hex kopyalandi -> $rom_target"

# --- Top modulu set et ---
set_property top $top_module [current_fileset]
update_compile_order -fileset sources_1

# --- Sentez ---
puts "build_vivado: SYNTH"
launch_runs synth_1 -jobs 4
wait_on_run synth_1

# --- Implementasyon ---
puts "build_vivado: IMPL"
launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1

# --- Bitstream'i kopyala ---
file copy -force "$proj_dir/$project_name.runs/impl_1/$top_module.bit" \
                 "build/$top_module.bit"

puts "build_vivado: HAZIR -> build/$top_module.bit"
exit 0
