// Butonlari dogrudan LED'lere baglar (loader/CPU yok).
// Aktif-dusuk LED + aktif-dusuk buton: butona basinca ilgili LED YANAR.
//   S1 (pin3) -> LED0 ,  S2 (pin4) -> LED1
module btn_test_top (
    input  wire       btn1,   // S1 pin 3
    input  wire       btn2,   // S2 pin 4
    output wire [5:0] led
);
    assign led[0] = btn1;       // basili(0) -> LED0 yanar
    assign led[1] = btn2;       // basili(0) -> LED1 yanar
    assign led[5:2] = 4'b1111;  // digerleri sonuk
endmodule
