// Clock kullanmaz: LED'leri sabit bir desende yakar (010101).
// Amac: LED pinleri + bitstream konfigurasyonu calisiyor mu?
module led_static_top (output wire [5:0] led);
    assign led = 6'b010101;   // aktif-dusuk: 0=yanar -> LED0,2,4 YANAR; LED1,3,5 SONUK
endmodule
