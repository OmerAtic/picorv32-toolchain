// ============================================================
// loader.v - FPGA tarafi yukleyici (Loader) sonlu durum makinesi
// ============================================================
// 3. Proje'nin cekirdegi.
//
// Gorevi:
//   - PC'den UART ile gelen paketleri yakalar,
//   - her paketin CRC-16'sini kontrol eder (veri kaybini onler),
//   - dogru paketin verisini BRAM'e (islemci ana bellegi) yazar,
//   - host'a ACK (0x79) / NAK (0x6E) yaniti gonderir,
//   - RUN komutu gelince 'loading' sinyalini dusurur; ust modul
//     bununla islemcinin reset hattini birakir ve program calisir.
//
// Paket bicimi (host -> FPGA):
//   WRITE: 0x7E 0x01 ADDR_L ADDR_H NWORDS <NWORDS*4 bayt veri> CRC_H CRC_L
//   RUN  : 0x7E 0x02 CRC_H CRC_L
//   CRC, CMD baytindan veri sonuna kadarki tum baytlar uzerinden.
//
// Yukleme suresince islemci reset'te tutulur (loading=1), BRAM yazim
// portu loader'a aittir. RUN'dan sonra (loading=0) BRAM islemciye gecer.
// ============================================================

module loader (
    input  wire        clk,
    input  wire        resetn,        // board reset (aktif dusuk)

    // UART alicidan gelen bayt
    input  wire        rx_valid,
    input  wire [7:0]  rx_data,

    // UART vericiye ACK/NAK gondermek icin
    output reg         tx_send,       // 1 cycle pulse
    output reg  [7:0]  tx_data,
    input  wire        tx_busy,

    // BRAM yazim portu (word adresli)
    output reg         mem_we,        // 1 cycle pulse: bir word yaz
    output reg  [10:0] mem_waddr,     // word adres (0..2047)
    output reg  [31:0] mem_wdata,

    // Durum
    output reg         loading        // 1=yukleme suruyor (CPU reset'te)
);

    // ---- Protokol sabitleri (host ile AYNI) ----
    localparam SYNC      = 8'h7E;
    localparam CMD_WRITE = 8'h01;
    localparam CMD_RUN   = 8'h02;
    localparam ACK       = 8'h79;   // 'y'
    localparam NAK       = 8'h6E;   // 'n'

    // ---- FSM durumlari ----
    localparam S_SYNC    = 4'd0;   // 0x7E bekle
    localparam S_CMD     = 4'd1;   // komut baytI
    localparam S_ADDR_L  = 4'd2;   // adres alt baytI
    localparam S_ADDR_H  = 4'd3;   // adres ust baytI
    localparam S_NWORDS  = 4'd4;   // word sayisi
    localparam S_DATA    = 4'd5;   // veri baytlari
    localparam S_CRC_H   = 4'd6;   // gelen CRC ust
    localparam S_CRC_L   = 4'd7;   // gelen CRC alt
    localparam S_CHECK   = 4'd8;   // CRC karsilastir, ACK/NAK
    localparam S_WAITTX  = 4'd9;   // ACK/NAK gonderimi bitsin
    localparam S_RUN     = 4'd10;  // program calisiyor (kalici)

    reg [3:0]  state;
    reg [7:0]  cmd;
    reg [15:0] crc;            // hesaplanan CRC
    reg [15:0] rx_crc;         // pakette gelen CRC
    reg [10:0] addr;           // su anki yazim word adresi
    reg [7:0]  nwords;         // paketteki word sayisi
    reg [7:0]  word_count;     // yazilan word sayaci
    reg [1:0]  byte_in_word;   // 0..3 (word icindeki bayt)
    reg [31:0] cur_word;       // toplanan word

    // ---- CRC-16/CCITT-FALSE: bir bayt isle ----
    // poly=0x1021, host'taki crc16_ccitt ile birebir ayni.
    function [15:0] crc16_next;
        input [15:0] crc_in;
        input [7:0]  b;
        integer i;
        reg [15:0] c;
        begin
            c = crc_in ^ (b << 8);
            for (i = 0; i < 8; i = i + 1) begin
                if (c[15])
                    c = (c << 1) ^ 16'h1021;
                else
                    c = (c << 1);
            end
            crc16_next = c;
        end
    endfunction

    always @(posedge clk) begin
        if (!resetn) begin
            state        <= S_SYNC;
            loading      <= 1'b1;     // reset sonrasi: yukleme modu
            tx_send      <= 1'b0;
            mem_we       <= 1'b0;
            addr         <= 11'd0;
            byte_in_word <= 2'd0;
            word_count   <= 8'd0;
            crc          <= 16'hFFFF;
        end else begin
            // pulse sinyalleri varsayilan 0
            tx_send <= 1'b0;
            mem_we  <= 1'b0;

            case (state)
                // --- 0x7E senkron baytI bekle ---
                S_SYNC: begin
                    if (rx_valid && rx_data == SYNC) begin
                        crc   <= 16'hFFFF;   // her paket icin CRC sifirla
                        state <= S_CMD;
                    end
                end

                // --- komut ---
                S_CMD: begin
                    if (rx_valid) begin
                        cmd <= rx_data;
                        crc <= crc16_next(crc, rx_data);
                        if (rx_data == CMD_WRITE)
                            state <= S_ADDR_L;
                        else if (rx_data == CMD_RUN)
                            state <= S_CRC_H;   // RUN'da adres/veri yok
                        else
                            state <= S_SYNC;    // bilinmeyen komut
                    end
                end

                // --- adres alt baytI ---
                S_ADDR_L: begin
                    if (rx_valid) begin
                        addr[7:0] <= rx_data;
                        crc       <= crc16_next(crc, rx_data);
                        state     <= S_ADDR_H;
                    end
                end

                // --- adres ust baytI (sadece 3 bit kullanilir: 0..2047) ---
                S_ADDR_H: begin
                    if (rx_valid) begin
                        addr[10:8] <= rx_data[2:0];
                        crc        <= crc16_next(crc, rx_data);
                        state      <= S_NWORDS;
                    end
                end

                // --- paketteki word sayisi ---
                S_NWORDS: begin
                    if (rx_valid) begin
                        nwords       <= rx_data;
                        crc          <= crc16_next(crc, rx_data);
                        word_count   <= 8'd0;
                        byte_in_word <= 2'd0;
                        if (rx_data == 8'd0)
                            state <= S_CRC_H;   // bos paket
                        else
                            state <= S_DATA;
                    end
                end

                // --- veri baytlari: 4 bayt = 1 word (kucuk-endian) ---
                S_DATA: begin
                    if (rx_valid) begin
                        crc <= crc16_next(crc, rx_data);
                        // baytI dogru pozisyona koy
                        case (byte_in_word)
                            2'd0: cur_word[7:0]   <= rx_data;
                            2'd1: cur_word[15:8]  <= rx_data;
                            2'd2: cur_word[23:16] <= rx_data;
                            2'd3: cur_word[31:24] <= rx_data;
                        endcase

                        if (byte_in_word == 2'd3) begin
                            // word tamamlandi -> BRAM'e yaz
                            mem_we    <= 1'b1;
                            mem_waddr <= addr;
                            mem_wdata <= {rx_data, cur_word[23:0]};
                            addr      <= addr + 1'b1;
                            byte_in_word <= 2'd0;
                            word_count   <= word_count + 1'b1;
                            if (word_count + 1'b1 == nwords)
                                state <= S_CRC_H;   // paketin tum word'leri bitti
                        end else begin
                            byte_in_word <= byte_in_word + 1'b1;
                        end
                    end
                end

                // --- gelen CRC ust baytI (CRC hesabina DAHIL DEGIL) ---
                S_CRC_H: begin
                    if (rx_valid) begin
                        rx_crc[15:8] <= rx_data;
                        state        <= S_CRC_L;
                    end
                end

                // --- gelen CRC alt baytI ---
                S_CRC_L: begin
                    if (rx_valid) begin
                        rx_crc[7:0] <= rx_data;
                        state       <= S_CHECK;
                    end
                end

                // --- CRC karsilastir, ACK/NAK gonder ---
                S_CHECK: begin
                    if (rx_crc == crc) begin
                        tx_data <= ACK;
                        tx_send <= 1'b1;
                    end else begin
                        tx_data <= NAK;
                        tx_send <= 1'b1;
                    end
                    state <= S_WAITTX;
                end

                // --- ACK/NAK gonderimi bitene kadar bekle ---
                S_WAITTX: begin
                    if (!tx_busy && !tx_send) begin
                        // CRC dogru ve komut RUN ise: programi baslat
                        if (rx_crc == crc && cmd == CMD_RUN) begin
                            loading <= 1'b0;     // islemci reset'ten birakilir
                            state   <= S_RUN;
                        end else begin
                            state <= S_SYNC;     // sonraki paket / tekrar
                        end
                    end
                end

                // --- program calisiyor; board reset'e kadar burada kal ---
                S_RUN: begin
                    loading <= 1'b0;
                end

                default: state <= S_SYNC;
            endcase
        end
    end

endmodule
